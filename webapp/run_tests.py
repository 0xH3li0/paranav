#!/usr/bin/env python3
"""Rotina de testes completa do Aeronav — avalia o que funciona e o que não.

Cobre: geometria (geo.py), parser IGC, modelos (round-trip), scoring/regressão
sagrada (N1/N2/N3), repositórios files+sqlite (paridade/persistência), rotas Flask
(test client), construtor (validação/salvar), PDFs A3/A4, e os IGCs do Paranapanema.

Uso:  python3 webapp/run_tests.py      (a partir da raiz do projeto)
Saída: linha por checagem (OK/FALHA), agrupada por seção, + resumo final.
"""
from __future__ import annotations
import os, sys, glob, json, tempfile, math
from io import BytesIO

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
IGCS = os.path.join(ROOT, "igcs")
os.environ.setdefault("APURADOR_EMAIL", "admin@apurador.local")
os.environ.setdefault("APURADOR_PASSWORD", "admin")

results = []   # (secao, nome, ok, detalhe)


def ck(sec, nome, ok, detalhe=""):
    results.append((sec, nome, bool(ok), detalhe))


def section(title):
    print("\n== " + title + " ==")


def run(sec, nome, fn):
    """Executa fn() -> (ok, detalhe) capturando exceções."""
    try:
        ok, det = fn()
    except Exception as e:
        ok, det = False, f"EXCEÇÃO: {type(e).__name__}: {e}"
    ck(sec, nome, ok, det)
    print(f"  {'OK   ' if ok else 'FALHA'}  {nome}" + (f"  — {det}" if det else ""))


# ───────────────────────── A. GEOMETRIA ─────────────────────────
def test_geo():
    section("A. Geometria (core/geo.py)")
    from apurador.core import geo

    def t_dist():
        d = geo.dist(0, 0, 0, 1)            # 1° lon no equador ≈ 111.195 km
        return abs(d - 111195) < 500, f"dist(0,0,0,1)={d:.0f} m"
    run("geo", "Haversine dist()", t_dist)

    def t_seg():
        # ponto 0.001° ao norte do meio de um segmento leste-oeste
        d = geo.dist_to_segment_m(0.001, 0.5, 0, 0, 0, 1)
        exp = geo.dist(0.001, 0.5, 0, 0.5)
        return abs(d - exp) < 1.0, f"cross-track={d:.1f} m (esp {exp:.1f})"
    run("geo", "dist_to_segment_m (perpendicular)", t_seg)

    def t_seg_clamp():
        # ponto além da extremidade B → distância até B (clamp)
        d = geo.dist_to_segment_m(0, 2, 0, 0, 0, 1)
        exp = geo.dist(0, 2, 0, 1)
        return abs(d - exp) < 1.0, f"clamp={d:.1f} m (esp {exp:.1f})"
    run("geo", "dist_to_segment_m (clamp na ponta)", t_seg_clamp)

    def t_poly():
        coords = [[0, 0], [0, 1], [1, 1]]
        d = geo.dist_to_polyline_m(0.0005, 0.5, coords)
        return d < 80, f"dist à polilinha={d:.1f} m"
    run("geo", "dist_to_polyline_m", t_poly)

    def t_len():
        L = geo.route_length_m([[0, 0], [0, 1]])
        return abs(L - 111195) < 500, f"len={L:.0f} m"
    run("geo", "route_length_m", t_len)

    def t_dens():
        pts = geo.densify_polyline([[0, 0], [0, 1]], 1000.0)
        # ~111 km / 1 km ≈ 112 pontos, monotônico em lon
        mono = all(pts[i][1] <= pts[i + 1][1] for i in range(len(pts) - 1))
        return len(pts) > 100 and mono, f"{len(pts)} amostras, monotônico={mono}"
    run("geo", "densify_polyline", t_dens)

    def t_inscribed():
        # porta da lógica JS inscribedRadius: retângulo 4000×2000 m, centro deslocado
        def inscribed(c, fr, w, h):
            hw, hh = w / 2, h / 2
            a = math.radians(fr.get("angle", 0))
            coslat = math.cos(math.radians(fr["lat"]))
            e = (c[1] - fr["lon"]) * 111320 * coslat
            n = (c[0] - fr["lat"]) * 111320
            dx = e * math.cos(a) + n * math.sin(a)
            dy = -e * math.sin(a) + n * math.cos(a)
            return min(hw - abs(dx), hh - abs(dy))
        fr = {"lat": -22.85, "lon": -42.55, "angle": 0}
        # centro = frame center → raio inscrito = min(hw,hh) = 1000
        r = inscribed([fr["lat"], fr["lon"]], fr, 4000, 2000)
        return abs(r - 1000) < 5, f"raio inscrito (centro)={r:.0f} m (esp 1000)"
    run("geo", "anéis: raio inscrito na folha (porta JS)", t_inscribed)


# ───────────────────────── B. PARSER IGC ─────────────────────────
def test_igc():
    section("B. Parser IGC (core/igc.py)")
    from apurador.core.igc import parse_igc
    files = sorted(glob.glob(os.path.join(IGCS, "*.igc")))

    def t_count():
        return len(files) >= 6, f"{len(files)} arquivos .igc na raiz de igcs/"
    run("igc", "IGCs presentes", t_count)

    for f in files:
        name = os.path.basename(f)
        def t(f=f, name=name):
            tr = parse_igc(open(f, encoding="utf-8", errors="ignore").read(), name)
            ok = len(tr.fixes) > 100 and tr.bib
            # fixes ordenados no tempo (majoritariamente)
            return ok, f"{len(tr.fixes)} fixes, BIB={tr.bib}, data={tr.date or '—'}"
        run("igc", f"parse {name}", t)


# ───────────────────────── C. MODELOS ─────────────────────────
def test_models():
    section("C. Modelos — round-trip (core/models.py)")
    from apurador import storage
    from apurador.core.models import Prova, Mapa
    import apurador.repo as repo
    repo.reset_singleton()
    # Prova: round-trip de scoring + map_slug (geometria vive no Mapa quando há map_slug)
    for pr in storage.list_provas():
        def t(pr=pr):
            rt = Prova.from_dict(pr.to_dict())
            same = (rt.slug == pr.slug and rt.type == pr.type and rt.map_slug == pr.map_slug and
                    rt.window_min == pr.window_min and rt.max_points == pr.max_points)
            # sem mapa (legado): geometria deve ser preservada inline
            if not pr.map_slug:
                same = same and len(rt.points) == len(pr.points)
            return same, f"map_slug={pr.map_slug or '—'}, {len(pr.points)} pts (hidratados)"
        run("models", f"round-trip prova {pr.slug} ({pr.type})", t)
    # Mapa: round-trip da geometria
    for mp in storage.list_mapas():
        def t(mp=mp):
            rt = Mapa.from_dict(mp.to_dict())
            same = (rt.slug == mp.slug and len(rt.points) == len(mp.points) and
                    rt.scale == mp.scale and rt.route.get("width") == mp.route.get("width") and
                    len(rt.areas) == len(mp.areas) and len(rt.landings) == len(mp.landings))
            return same, f"{len(mp.points)} pts, áreas={len(mp.areas)}, route={'sim' if mp.route else 'não'}"
        run("models", f"round-trip mapa {mp.slug}", t)


# ───────────────────────── D. SCORING / REGRESSÃO ─────────────────────────
def test_scoring():
    section("D. Scoring — regressão sagrada (core/scoring.py)")
    from apurador import storage
    from apurador.core.igc import parse_igc, Fix
    from apurador.core.models import Pilot
    from apurador.core.scoring import evaluate, score_prova
    from apurador.core.geo import densify_polyline
    import apurador.repo as repo
    repo.reset_singleton()

    def pilot(igc):
        tr = parse_igc(open(os.path.join(IGCS, igc), encoding="utf-8", errors="ignore").read(), igc)
        return Pilot(bib=tr.bib, name=tr.name, date=tr.date, fixes=tr.fixes)

    n1 = storage.get_prova("n1-navegacao-pura")
    n2 = storage.get_prova("n2-tempo-declarado")
    n3 = storage.get_prova("n3-rota-precisao")

    ev = evaluate(n1, pilot("venet-n1.igc"))
    run("scoring", "N1 Venet — 11 TP válidos", lambda ev=ev: (ev["counts"]["TP"]["valid"] == 11, str(ev["counts"]["TP"]["valid"])))
    run("scoring", "N1 Venet — SP→FP 01:00:47 (3647s)", lambda ev=ev: (round(ev["stats"]["time_spfp"]) == 3647, f"{round(ev['stats']['time_spfp'])}s"))
    evm = evaluate(n2, pilot("melk-n2.igc"))
    run("scoring", "N2 Melk — HG 26", lambda evm=evm: (evm["counts"]["HG"]["valid"] == 26, str(evm["counts"]["HG"]["valid"])))
    evl = evaluate(n2, pilot("leandro-n2.igc"))
    run("scoring", "N2 Leandro — HG 16", lambda evl=evl: (evl["counts"]["HG"]["valid"] == 16, str(evl["counts"]["HG"]["valid"])))

    def t_n3():
        pts = densify_polyline(n3.route["coords"], 30.0)
        fx = [Fix(t=i, lat=p[0], lon=p[1], alt=300) for i, p in enumerate(pts)]
        r = score_prova(n3, [Pilot(bib="T", name="t", fixes=fx)])[0]
        return r["points"] == n3.max_points and r["inside_ratio"] >= 0.999, f"pts={r['points']} ratio={r['inside_ratio']:.3f}"
    run("scoring", "N3 — voo exato na rota = score máx", t_n3)

    def t_dq():
        # N1: piloto que cruza SP e FP mas leva > janela (window_min) → DQ
        sp = next(p for p in n1.points if p.type == "SP")
        fp = next(p for p in n1.points if p.type == "FP")
        win = (n1.window_min or 60)
        fx = [Fix(t=0, lat=sp.lat, lon=sp.lon, alt=100),
              Fix(t=(win + 2) * 60, lat=fp.lat, lon=fp.lon, alt=100)]
        r = score_prova(n1, [Pilot(bib="D", name="d", fixes=fx)])[0]
        return r["points"] == 0 and any("janela" in p.lower() for p in r["penal"]), f"pts={r['points']} penal={r['penal']}"
    run("scoring", "N1 — DQ fora da janela de tempo", t_dq)


# ───────────────────────── E. REPOSITÓRIOS ─────────────────────────
def test_repo():
    section("E. Repositórios — files vs sqlite (apurador/repo/)")
    from apurador.repo.files_backend import FilesRepo
    from apurador.repo.sqlite_backend import SqliteRepo
    from apurador.repo.migrate import migrate
    from apurador.core.igc import parse_igc
    from apurador.core.models import Pilot
    from apurador.core.scoring import score_prova

    db = os.path.join(tempfile.mkdtemp(), "t.db")
    migrate(db)
    fi, sq = FilesRepo(), SqliteRepo(db)

    run("repo", "paridade list_provas (files == sqlite)",
        lambda: ([p.slug for p in fi.list_provas()] == [p.slug for p in sq.list_provas()],
                 ", ".join(p.slug for p in sq.list_provas())))

    ven = parse_igc(open(os.path.join(IGCS, "venet-n1.igc"), encoding="utf-8", errors="ignore").read(), "v")
    p = Pilot(bib="V", name="V", fixes=ven.fixes)
    sN = score_prova(sq.get_prova("n1-navegacao-pura"), [p])[0]
    fN = score_prova(fi.get_prova("n1-navegacao-pura"), [p])[0]
    run("repo", "N1 score igual nos dois backends", lambda: (sN["points"] == fN["points"], f"sqlite={sN['points']} files={fN['points']}"))

    def t_persist():
        sq.add_pilot("n1-navegacao-pura", p)
        sq2 = SqliteRepo(db)   # simula restart (nova conexão)
        got = sq2.pilots("n1-navegacao-pura")
        ok = len(got) == 1 and len(got[0].fixes) == len(ven.fixes)
        sq2.set_declared("n1-navegacao-pura", "V", "FP", 3647)
        ok = ok and SqliteRepo(db).pilots("n1-navegacao-pura")[0].decl.get("FP") == 3647
        sq2.reset("n1-navegacao-pura")
        ok = ok and len(SqliteRepo(db).pilots("n1-navegacao-pura")) == 0
        return ok, "add→restart→decl→reset"
    run("repo", "sqlite: piloto sobrevive a restart + decl + reset", t_persist)


# ───────────────────────── F. ROTAS / APP (test client, sqlite isolado) ─────────────────────────
def test_routes():
    section("F. Rotas Flask (test client, sqlite isolado)")
    from apurador.repo.migrate import migrate
    import apurador.repo as repo
    db = os.path.join(tempfile.mkdtemp(), "app.db")
    migrate(db)
    os.environ["APURADOR_BACKEND"] = "sqlite"
    os.environ["APURADOR_DB"] = db
    repo.reset_singleton()

    from apurador import create_app, state
    from apurador.core.igc import parse_igc
    from apurador.core.models import Pilot
    app = create_app()
    c = app.test_client()

    run("rotas", "GET /login (200)", lambda: (c.get("/login").status_code == 200, ""))
    r = c.post("/login", data={"email": "admin@apurador.local", "password": "admin"})
    run("rotas", "POST /login (302 redirect)", lambda r=r: (r.status_code == 302, f"code={r.status_code}"))

    pages = [
        ("/viewer", "viewer"),
        ("/scores?sala=n1-navegacao-pura", "scores N1"),
        ("/scores?sala=n2-tempo-declarado", "scores N2"),
        ("/scores?sala=n3-rota-precisao", "scores N3"),
        ("/competicoes", "competições"),
        ("/builder", "builder (novo)"),
        ("/builder/n2-tempo-declarado", "builder (editar N2)"),
        ("/prova/n1-navegacao-pura/config", "config N1"),
        ("/prova/n2-tempo-declarado/config", "config N2"),
        ("/prova/n3-rota-precisao/config", "config N3"),
        ("/igcupload", "igcupload (público)"),
        ("/api/sala/n1-navegacao-pura/mapdata", "API mapdata N1"),
        ("/api/sala/n3-rota-precisao/mapdata", "API mapdata N3"),
        ("/api/sala/n1-navegacao-pura/trackdata", "API trackdata"),
    ]
    for url, name in pages:
        run("rotas", f"GET {name} (200)", lambda url=url: (c.get(url).status_code == 200, f"code={c.get(url).status_code}"))

    # config N3 não deve mostrar pesos N2; config N2 deve
    run("rotas", "config N3 esconde pesos N2", lambda: ("Score HG" not in c.get("/prova/n3-rota-precisao/config").get_data(as_text=True), ""))
    run("rotas", "config N2 mostra pesos N2", lambda: ("Score HG" in c.get("/prova/n2-tempo-declarado/config").get_data(as_text=True), ""))

    # mapdata N1 não tem route; N3 tem
    run("rotas", "mapdata: route só na N3", lambda: (
        c.get("/api/sala/n1-navegacao-pura/mapdata").get_json().get("route") is None and
        bool(c.get("/api/sala/n3-rota-precisao/mapdata").get_json().get("route")), ""))

    # adiciona piloto e testa relatório + trackdata
    ven = parse_igc(open(os.path.join(IGCS, "venet-n1.igc"), encoding="utf-8", errors="ignore").read(), "v")
    state.add_pilot("n1-navegacao-pura", Pilot(bib=ven.bib, name=ven.name, date=ven.date, fixes=ven.fixes))
    run("rotas", "relatório de piloto (200)", lambda: (c.get(f"/relatorio/n1-navegacao-pura/{ven.bib}").status_code == 200, ""))
    run("rotas", "trackdata traz o piloto", lambda: (len(c.get("/api/sala/n1-navegacao-pura/trackdata").get_json().get("tracks", [])) == 1, ""))

    # builder save: validação + salvar
    SP = {"name": "SP", "type": "SP", "radius": 200, "weight": 1, "lat": -22.85, "lon": -42.6, "alt": 0}
    FP = {"name": "FP", "type": "FP", "radius": 200, "weight": 1, "lat": -22.88, "lon": -42.5, "alt": 0}
    TP = {"name": "1", "type": "TP", "radius": 200, "weight": 1, "lat": -22.86, "lon": -42.55, "alt": 0}
    run("rotas", "builder_save rejeita sem FP (400)", lambda: (c.post("/builder/save", json={"prova": {"name": "x", "type": "n1"}, "points": [SP, TP]}).status_code == 400, ""))
    run("rotas", "builder_save rejeita N3 sem rota (400)", lambda: (c.post("/builder/save", json={"prova": {"name": "x3", "type": "n3"}, "points": [SP, FP], "route": {}}).status_code == 400, ""))
    rsave = c.post("/builder/save", json={"prova": {"name": "TESTE rotina", "type": "n1"}, "points": [SP, TP, FP]})
    slug_saved = rsave.get_json().get("slug")
    run("rotas", "builder_save aceita n1 válido", lambda: (rsave.get_json().get("ok") and slug_saved, f"slug={slug_saved}"))
    r_as = c.post("/builder/save", json={"prova": {"name": "TESTE rotina", "type": "n1", "saveAs": True}, "points": [SP, FP]})
    run("rotas", "salvar como nova → slug diferente", lambda: (r_as.get_json().get("slug") != slug_saved, f"slug2={r_as.get_json().get('slug')}"))

    # PDFs via rota
    run("rotas", "mapa.pdf via rota (200, application/pdf)", lambda: (
        (lambda rr: rr.status_code == 200 and rr.headers.get("Content-Type") == "application/pdf")(c.get("/prova/n1-navegacao-pura/mapa.pdf")), ""))

    # ---- Mapas (editor) ----
    run("rotas", "GET /mapas (lista) 200", lambda: (c.get("/mapas").status_code == 200, ""))
    run("rotas", "GET /mapas/novo 200", lambda: (c.get("/mapas/novo").status_code == 200, ""))
    run("rotas", "GET editar mapa n1 200", lambda: (c.get("/mapas/n1-navegacao-pura").status_code == 200, ""))
    run("rotas", "API /api/mapa/<slug>/mapdata tem wpts", lambda: (len(c.get("/api/mapa/n1-navegacao-pura/mapdata").get_json().get("wpts", [])) == 20, ""))
    # salvar um mapa novo (geometria + frame + área + rota)
    mapobj = {"mapa": {"name": "Mapa rotina", "scale": "1:50000", "base": "esri", "teto": 0, "alturaMin": 0},
              "points": [SP, FP], "frame": {"lat": -22.85, "lon": -42.6, "angle": 0},
              "areas": [{"kind": "livre", "name": "", "coords": [[-22.86, -42.58], [-22.86, -42.55], [-22.88, -42.55]]}],
              "route": {"coords": [[-22.85, -42.6], [-22.88, -42.5]], "width": 250}, "landings": []}
    rmap = c.post("/mapas/save", json=mapobj)
    mslug = rmap.get_json().get("slug")
    run("rotas", "POST /mapas/save cria mapa", lambda: (rmap.get_json().get("ok") and mslug, f"slug={mslug}"))
    run("rotas", "mapa salvo tem 2 pts + 1 área + rota (via API)", lambda: (
        (lambda d: len(d.get("wpts", [])) == 2 and len(d.get("areas", [])) == 1 and bool(d.get("route")))(
            c.get(f"/api/mapa/{mslug}/mapdata").get_json()), ""))
    run("rotas", "mapa A3 PDF do mapa (200)", lambda: (c.get(f"/mapas/{mslug}/mapa.pdf").status_code == 200, ""))
    # criar prova referenciando o mapa salvo (sem geometria inline) — hidrata e pontua
    rp = c.post("/builder/save", json={"prova": {"name": "Prova do mapa", "type": "n1", "mapSlug": mslug},
                                       "points": [SP, FP]})
    pslug = rp.get_json().get("slug")
    run("rotas", "prova referencia mapa (builder_save)", lambda: (rp.get_json().get("ok"), f"slug={pslug}"))
    run("rotas", "prova puxa geometria do mapa (mapdata hidratado)", lambda: (
        len(c.get(f"/api/sala/{pslug}/mapdata").get_json().get("wpts", [])) == 2, ""))


# ───────────────────────── G. PDFs (geração direta) ─────────────────────────
def test_pdfs():
    section("G. PDFs (mappdf / pointspdf)")
    import apurador.repo as repo
    repo.reset_singleton()
    os.environ.pop("APURADOR_BACKEND", None)   # volta p/ files (provas reais)
    os.environ.pop("APURADOR_DB", None)
    repo.reset_singleton()
    from apurador import storage
    from apurador.mappdf import render_map_pdf
    from apurador.pointspdf import render_points_pdf
    from apurador.core.models import Prova

    for slug in ["n1-navegacao-pura", "n2-tempo-declarado", "n3-rota-precisao"]:
        pr = storage.get_prova(slug)
        run("pdf", f"mapa A3 {slug}", lambda pr=pr: ((lambda b: (render_map_pdf(pr, "Aeronav", b), b.getvalue()[:5] == b"%PDF-")[1])(BytesIO()), ""))
    # pointspdf: usa N3 (2 pontos) p/ ser rápido (busca tiles de rede)
    pr3 = storage.get_prova("n3-rota-precisao")
    run("pdf", "folha A4 pontos (N3, 2 pts)", lambda: ((lambda b: (render_points_pdf(pr3, "Aeronav", b), b.getvalue()[:5] == b"%PDF-")[1])(BytesIO()), "requer rede p/ tiles"))
    # bordas: prova sem pontos não explode
    empty = Prova(name="vazia", type="n1", slug="x")
    run("pdf", "mapa A3 de prova sem pontos não explode", lambda: ((lambda b: (render_map_pdf(empty, "Aeronav", b), b.getvalue()[:5] == b"%PDF-")[1])(BytesIO()), ""))
    run("pdf", "folha A4 de prova sem pontos não explode", lambda: ((lambda b: (render_points_pdf(empty, "Aeronav", b), b.getvalue()[:5] == b"%PDF-")[1])(BytesIO()), ""))


# ───────────────────────── H. PARANAPANEMA (50 IGCs) ─────────────────────────
def test_paranapanema():
    section("H. Paranapanema 2025 — superfície de testes")
    from apurador.core.igc import parse_igc
    d = os.path.join(IGCS, "3o-open-paranapanema-2025")
    files = sorted(glob.glob(os.path.join(d, "*.igc"))) if os.path.isdir(d) else []
    if not files:
        ck("paran", "diretório presente", False, "3o-open-paranapanema-2025/ não encontrado")
        print("  FALHA  diretório 3o-open-paranapanema-2025/ ausente")
        return
    ok_count = 0
    for f in files:
        try:
            tr = parse_igc(open(f, encoding="utf-8", errors="ignore").read(), os.path.basename(f))
            if len(tr.fixes) > 10:
                ok_count += 1
        except Exception:
            pass
    run("paran", f"parse de {len(files)} pseudo-IGCs", lambda: (ok_count == len(files), f"{ok_count}/{len(files)} com fixes"))


def main():
    print("=" * 64)
    print("ROTINA DE TESTES COMPLETA — Aeronav")
    print("=" * 64)
    for fn in (test_geo, test_igc, test_models, test_scoring, test_repo, test_routes, test_pdfs, test_paranapanema):
        try:
            fn()
        except Exception as e:
            ck(fn.__name__, "seção", False, f"EXCEÇÃO NA SEÇÃO: {e}")
            print(f"  FALHA  seção {fn.__name__}: {e}")

    print("\n" + "=" * 64)
    total = len(results)
    fails = [r for r in results if not r[2]]
    by_sec = {}
    for sec, nome, ok, det in results:
        s = by_sec.setdefault(sec, [0, 0])
        s[0] += 1
        if ok:
            s[1] += 1
    print("RESUMO POR SEÇÃO:")
    for sec, (tot, passed) in by_sec.items():
        print(f"  {sec:10} {passed}/{tot}")
    print("-" * 64)
    if fails:
        print(f"PROBLEMAS ENCONTRADOS ({len(fails)}):")
        for sec, nome, ok, det in fails:
            print(f"  [{sec}] {nome} — {det}")
    print("-" * 64)
    print(f"TOTAL: {total - len(fails)}/{total} OK" + ("  ✅ TUDO VERDE" if not fails else f"  ⚠ {len(fails)} FALHA(S)"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
