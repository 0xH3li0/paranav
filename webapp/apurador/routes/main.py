"""Páginas: igcupload (público), viewer, scores, relatório (organizador)."""
from __future__ import annotations
from flask import (Blueprint, render_template, request, redirect, url_for,
                   current_app, flash, abort, jsonify, session)
from .. import storage, state
from ..core.igc import parse_igc
from ..core.models import Pilot, Mapa
from ..core.scoring import score_prova, evaluate, ranking_geral
from .auth import login_required

bp = Blueprint("main", __name__)


def _slugify(s, fallback="mapa"):
    import re as _re
    import uuid
    base = _re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return base or (fallback + "-" + uuid.uuid4().hex[:6])


def parse_elapsed(s):
    """Aceita 'mm:ss', 'hh:mm:ss' ou segundos. Retorna int (s) ou None."""
    s = (s or "").strip()
    if not s:
        return None
    if ":" in s:
        parts = [int(x) for x in s.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0)
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    try:
        return int(float(s))
    except ValueError:
        return None


@bp.route("/")
def index():
    # organizador logado → painel (Viewer); senão → login.
    # A página pública do piloto continua em /igcupload (link próprio).
    if session.get("org"):
        return redirect(url_for("main.viewer"))
    return redirect(url_for("auth.login"))


@bp.route("/igcupload", methods=["GET", "POST"])
def igcupload():
    provas = storage.list_provas()
    if request.method == "POST":
        slug = request.form.get("sala", "")
        bib = request.form.get("bib", "").strip()
        pin = request.form.get("pin", "")
        f = request.files.get("igc")
        prova = storage.get_prova(slug)
        if not prova:
            flash("Selecione uma Sala válida.")
        elif not bib:
            flash("Informe o BIB.")
        elif current_app.config["PILOT_PIN"] and pin != current_app.config["PILOT_PIN"]:
            flash("PIN inválido.")
        elif not f or not f.filename.lower().endswith(".igc"):
            flash("Envie um arquivo .igc.")
        else:
            tr = parse_igc(f.read().decode("utf-8", "ignore"), f.filename)
            if not tr.fixes:
                flash("IGC sem fixes válidos.")
            else:
                tr.bib = bib or tr.bib
                state.add_pilot(slug, Pilot(bib=tr.bib, name=tr.name, date=tr.date, fixes=tr.fixes))
                flash(f"Track de {tr.name} (BIB {tr.bib}) enviado com sucesso.")
                return redirect(url_for("main.igcupload"))
    return render_template("igcupload.html", provas=provas)


@bp.route("/viewer")
@login_required
def viewer():
    provas = storage.list_provas()
    slug = request.args.get("sala") or (provas[0].slug if provas else "")
    prova = storage.get_prova(slug)
    return render_template("viewer.html", provas=provas, prova=prova, slug=slug,
                           n_pilots=len(state.pilots(slug)))


@bp.route("/scores")
@login_required
def scores():
    provas = storage.list_provas()
    slug = request.args.get("sala") or (provas[0].slug if provas else "")
    prova = storage.get_prova(slug)
    rows = score_prova(prova, state.pilots(slug)) if prova else []
    tg_names = [p.name for p in prova.points if p.type == "TG"] if prova else []
    fp_name = next((p.name for p in prova.points if p.type == "FP"), None) if prova else None
    return render_template("scores.html", provas=provas, prova=prova, slug=slug,
                           rows=rows, tg_names=tg_names, fp_name=fp_name)


@bp.route("/upload/tracks", methods=["GET", "POST"])
@login_required
def upload_tracks():
    """Organizador carrega vários IGCs de uma vez para uma Sala."""
    provas = storage.list_provas()
    if request.method == "POST":
        slug = request.form.get("sala", "")
        prova = storage.get_prova(slug)
        files = request.files.getlist("igcs")
        n = 0
        if prova:
            for f in files:
                if not f.filename.lower().endswith(".igc"):
                    continue
                tr = parse_igc(f.read().decode("utf-8", "ignore"), f.filename)
                if tr.fixes:
                    state.add_pilot(slug, Pilot(bib=tr.bib, name=tr.name, date=tr.date, fixes=tr.fixes))
                    n += 1
            flash(f"{n} track(s) carregado(s) na Sala {slug}.")
            return redirect(url_for("main.scores", sala=slug))
        flash("Selecione uma Sala válida.")
    return render_template("upload_tracks.html", provas=provas)


@bp.route("/competicoes")
@login_required
def competicoes():
    comps = storage.list_competicoes()
    slug = request.args.get("comp") or (comps[0]["slug"] if comps else "")
    comp = storage.get_competicao(slug)
    salas = []
    if comp:
        for ss in comp["salas"]:
            prova = storage.get_prova(ss)
            if prova:
                salas.append({"prova": prova, "pilots": state.pilots(ss)})
    ranking = ranking_geral(salas) if salas else []
    return render_template("competicoes.html", comps=comps, comp=comp, slug=slug,
                           provas=[s["prova"] for s in salas], ranking=ranking)


@bp.route("/declaracoes/<slug>", methods=["GET", "POST"])
@login_required
def declaracoes(slug):
    prova = storage.get_prova(slug)
    if not prova:
        abort(404)
    timed = [p.name for p in prova.points if p.type in ("TG", "FP")]
    pilots = state.pilots(slug)
    if request.method == "POST":
        for i, p in enumerate(pilots):
            for name in timed:
                sec = parse_elapsed(request.form.get(f"d_{i}_{name}"))
                state.set_declared(slug, p.bib, name, sec)
        flash("Tempos declarados salvos.")
        return redirect(url_for("main.scores", sala=slug))
    return render_template("declaracoes.html", prova=prova, slug=slug,
                           pilots=pilots, timed=timed)


# ============================ MAPAS (geometria) ============================
@bp.route("/mapas")
@login_required
def mapas():
    return render_template("mapas_list.html", mapas=storage.list_mapas())


@bp.route("/mapas/novo")
@bp.route("/mapas/<slug>")
@login_required
def mapa_editor(slug=None):
    mapa = storage.get_mapa(slug) if slug else None
    return render_template("mapa_editor.html", mapa=mapa)


@bp.route("/mapas/save", methods=["POST"])
@login_required
def mapa_save():
    import uuid
    d = request.get_json(force=True)
    m = d.get("mapa", {})
    incoming = (m.get("slug") or "").strip().lower()
    slug = incoming or _slugify(m.get("name"), "mapa")
    # mapa NOVO (sem slug) ou "salvar como novo": não sobrescrever um existente
    if (not incoming or m.get("saveAs")) and storage.get_mapa(slug) is not None:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"
    m["slug"] = slug
    m.pop("saveAs", None)
    if m.pop("publish", False):
        m["published"] = True
    d["mapa"] = m
    mapa = Mapa.from_dict(d)
    mapa.slug = slug
    storage.save_mapa(mapa)
    return jsonify({"ok": True, "slug": slug})


@bp.route("/mapas/<slug>/delete", methods=["POST"])
@login_required
def mapa_delete(slug):
    if not storage.get_mapa(slug):
        abort(404)
    usados = [p.name for p in storage.list_provas() if p.map_slug == slug]
    if usados:
        flash(f"Mapa em uso pela(s) prova(s): {', '.join(usados)}. Troque o mapa da prova antes de excluir.")
        return redirect(url_for("main.mapas"))
    storage.delete_mapa(slug)
    flash("Mapa excluído.")
    return redirect(url_for("main.mapas"))


@bp.route("/mapas/<slug>/logo", methods=["POST"])
@login_required
def mapa_logo(slug):
    import os
    mapa = storage.get_mapa(slug)
    if not mapa:
        abort(404)
    f = request.files.get("logo")
    if not f or not f.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        flash("Envie um logo .png/.jpg.")
        return redirect(url_for("main.mapa_editor", slug=slug))
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "logos")
    os.makedirs(base, exist_ok=True)
    ext = ".png" if f.filename.lower().endswith(".png") else ".jpg"
    path = os.path.join(base, f"{slug}{ext}")
    f.save(path)
    mapa.logo = path
    storage.save_mapa(mapa)
    flash("Logo enviado.")
    return redirect(url_for("main.mapa_editor", slug=slug))


@bp.route("/mapas/<slug>/mapa.pdf")
@login_required
def mapa_pdf_only(slug):
    from io import BytesIO
    from flask import send_file
    mapa = storage.get_mapa(slug)
    if not mapa:
        abort(404)
    base = request.args.get("base")          # permite exportar em base diferente da salva
    if base in ("esri", "topo", "osm"):
        mapa.base = base
    try:
        from ..qgispdf import render_map_pdf_auto
        buf = BytesIO(render_map_pdf_auto(mapa, current_app.config["BRAND"]))
        buf.seek(0)
    except Exception as e:  # noqa
        flash(f"PDF indisponível ({e}).")
        return redirect(url_for("main.mapa_editor", slug=slug))
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"mapa-{slug}.pdf")


@bp.route("/mapas/<slug>/pontos.pdf")
@login_required
def mapa_pontos_pdf(slug):
    from io import BytesIO
    from flask import send_file
    mapa = storage.get_mapa(slug)
    if not mapa:
        abort(404)
    try:
        from ..pointspdf import render_points_pdf
        buf = BytesIO()
        render_points_pdf(mapa, current_app.config["BRAND"], buf)
        buf.seek(0)
    except Exception as e:  # noqa
        flash(f"Imagens indisponíveis ({e}).")
        return redirect(url_for("main.mapa_editor", slug=slug))
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"pontos-{slug}.pdf")


@bp.route("/provas")
@login_required
def provas():
    """Lista de provas (aba PROVAS). 'Nova Prova' abre modal que escolhe um mapa."""
    return render_template("provas_list.html",
                           provas=storage.list_provas(), mapas=storage.list_mapas())


@bp.route("/builder")
@bp.route("/builder/<slug>")
@login_required
def builder(slug=None):
    provas = storage.list_provas()
    prova = storage.get_prova(slug) if slug else None
    # prova nova pode vir pré-vinculada a um mapa via ?map=<slug> (modal "Nova Prova")
    preselect_map = request.args.get("map", "") if not prova else ""
    return render_template("builder.html", provas=provas, prova=prova,
                           mapas=storage.list_mapas(), preselect_map=preselect_map)


@bp.route("/builder/save", methods=["POST"])
@login_required
def builder_save():
    import re as _re
    import uuid
    from ..core.models import Prova
    d = request.get_json(force=True)
    p = d.get("prova", {})
    pts = d.get("points", [])

    # --- validação. Com mapa, valida a geometria do MAPA; senão, a inline ---
    tipo = (p.get("type") or "n1").lower()
    map_slug = (p.get("mapSlug") or p.get("map_slug") or "").strip()
    errs = []
    # G2: toda prova NOVA precisa puxar um mapa. Provas legadas (já têm slug) seguem
    # editáveis com geometria inline — não regride o que já existe.
    incoming_slug = (p.get("slug") or "").strip()
    if not incoming_slug and not map_slug:
        errs.append("Toda prova nova precisa referenciar um mapa.")
    if map_slug:
        mp = storage.get_mapa(map_slug)
        if not mp:
            errs.append("Mapa referenciado não encontrado.")
            types, route = [], {}
        else:
            types = [pt.type for pt in mp.points]
            route = mp.route or {}
    else:
        types = [pt.get("type") for pt in pts]
        route = d.get("route") or {}
    if "SP" not in types:
        errs.append("Falta o ponto SP (largada).")
    if "FP" not in types:
        errs.append("Falta o ponto FP (chegada).")
    if tipo == "n3" and len(route.get("coords", []) or []) < 2:
        errs.append("N3 precisa de uma rota com pelo menos 2 vértices.")
    if errs:
        return jsonify({"ok": False, "error": " ".join(errs)}), 400

    # --- slug: deriva do nome; nunca colapsa em "prova" (usa uid); "salvar como nova" evita sobrescrever ---
    slug = (p.get("slug") or "").strip().lower()
    save_as = bool(p.get("saveAs"))
    if not slug:
        base = _re.sub(r"[^a-z0-9]+", "-", (p.get("name") or "").lower()).strip("-")
        slug = base or ("prova-" + uuid.uuid4().hex[:6])
    if save_as and storage.get_prova(slug) is not None:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"   # não sobrescrever uma prova existente

    p["slug"] = slug
    p.pop("saveAs", None)
    d["prova"] = p
    prova = Prova.from_dict(d)
    prova.slug = slug
    storage.save_prova(prova)
    return jsonify({"ok": True, "slug": slug})


@bp.route("/prova/<slug>/config", methods=["GET", "POST"])
@login_required
def prova_config(slug):
    prova = storage.get_prova(slug)
    if not prova:
        abort(404)
    if request.method == "POST":
        f = request.form
        def num(k, default, cast=float):
            try:
                return cast(f.get(k, default))
            except (TypeError, ValueError):
                return default
        # parâmetros da prova
        prova.target_min = int(num("target_min", prova.target_min, int))
        prova.deadline = f.get("deadline", prova.deadline).strip()
        prova.tz = int(num("tz", prova.tz, int))
        prova.max_points = int(num("max_points", prova.max_points, int))
        prova.w_hg = int(num("w_hg", prova.w_hg, int))
        prova.w_tg = int(num("w_tg", prova.w_tg, int))
        prova.w_vel = int(num("w_vel", prova.w_vel, int))
        prova.emax = int(num("emax", prova.emax, int))
        prova.tol = int(num("tol", prova.tol, int))
        prova.window_min = int(num("window_min", prova.window_min, int))
        prova.vel_window_min = int(num("vel_window_min", prova.vel_window_min, int))
        prova.score_model = f.get("score_model", prova.score_model)
        # raios: global por tipo. Default = valor ATUAL (campos escondidos por tipo
        # — ex.: "intermediário" não aparece em N1/N3 — não devem alterar nada).
        cur_spfp = next((pt.radius for pt in prova.points if pt.type in ("SP", "FP")), 200)
        cur_int = next((pt.radius for pt in prova.points if pt.type not in ("SP", "FP")), 150)
        r_spfp = num("radius_sp_fp", cur_spfp)
        r_int = num("radius_intermediate", cur_int)
        prova.apply_radii(r_spfp, r_int)
        # overrides por ponto (campo radius_<i>), se enviados
        for i, pt in enumerate(prova.points):
            v = f.get(f"radius_{i}")
            if v:
                try:
                    pt.radius = float(v)
                except ValueError:
                    pass
        storage.save_prova(prova)
        flash(f"Prova “{prova.name}” atualizada e salva.")
        return redirect(url_for("main.prova_config", slug=slug))
    # GET — defaults para os campos globais
    r_spfp = next((p.radius for p in prova.points if p.type in ("SP", "FP")), 200)
    r_int = next((p.radius for p in prova.points if p.type not in ("SP", "FP")), 150)
    return render_template("config.html", prova=prova, slug=slug,
                           radius_sp_fp=r_spfp, radius_intermediate=r_int)


@bp.route("/prova/<slug>/mapa.pdf")
@login_required
def mapa_pdf(slug):
    """Mapa A3 da prova em escala fiel (B3)."""
    from io import BytesIO
    from flask import send_file
    prova = storage.get_prova(slug)
    if not prova:
        abort(404)
    try:
        from ..qgispdf import render_map_pdf_auto
        buf = BytesIO(render_map_pdf_auto(prova, current_app.config["BRAND"]))
        buf.seek(0)
    except Exception as e:  # noqa
        flash(f"Geração do mapa PDF indisponível ({e}).")
        return redirect(url_for("main.prova_config", slug=slug))
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"mapa-{slug}.pdf")


@bp.route("/prova/<slug>/pontos.pdf")
@login_required
def pontos_pdf(slug):
    """Folha A4 com recortes de satélite de cada ponto (B4)."""
    from io import BytesIO
    from flask import send_file
    prova = storage.get_prova(slug)
    if not prova:
        abort(404)
    try:
        from ..pointspdf import render_points_pdf
        buf = BytesIO()
        render_points_pdf(prova, current_app.config["BRAND"], buf)
        buf.seek(0)
    except Exception as e:  # noqa
        flash(f"Geração das imagens indisponível ({e}). Requer staticmap/Pillow e rede.")
        return redirect(url_for("main.prova_config", slug=slug))
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"pontos-{slug}.pdf")


@bp.route("/relatorio/<slug>/<bib>.pdf")
@login_required
def relatorio_pdf(slug, bib):
    import os, tempfile
    from flask import send_file
    prova = storage.get_prova(slug)
    pilot = next((p for p in state.pilots(slug) if p.bib == bib), None)
    if not prova or not pilot:
        abort(404)
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        import gen_report
    except Exception:
        flash("Geração de PDF indisponível (instale reportlab e staticmap).")
        return redirect(url_for("main.relatorio", slug=slug, bib=bib))
    out = os.path.join(tempfile.gettempdir(), f"relatorio-{slug}-{bib}.pdf")
    gen_report.render_report(prova, pilot, out)
    nome = f"relatorio-{pilot.name.replace(' ', '-')}-{slug}.pdf"
    return send_file(out, as_attachment=True, download_name=nome, mimetype="application/pdf")


@bp.route("/relatorio/<slug>/<bib>")
@login_required
def relatorio(slug, bib):
    prova = storage.get_prova(slug)
    if not prova:
        abort(404)
    pilot = next((p for p in state.pilots(slug) if p.bib == bib), None)
    if not pilot:
        abort(404)
    ev = evaluate(prova, pilot)
    return render_template("relatorio.html", prova=prova, pilot=pilot, ev=ev,
                           points=prova.points)
