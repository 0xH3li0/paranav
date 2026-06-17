"""Gerador de relatório de voo (PDF).

Identidade visual própria (marca configurável em BRAND). Mapa OpenStreetMap
(staticmap) + selos coloridos (reportlab).
Uso:
    python gen_report.py <slug> <igc_path> [saida.pdf] [--bib N] [--decl "TG1=1170,..."]
"""
import sys, os, math, argparse, datetime
sys.path.insert(0, os.path.dirname(__file__))
from apurador.core.igc import parse_igc
from apurador.core.scoring import evaluate, score_prova
from apurador.core.timefmt import clock, dur, one, km
from apurador.core.models import Pilot
from apurador import storage

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth

# ---- marca (troque livremente) ----
BRAND = "Aeronav"
TAGLINE = "Apuração de provas de navegação · Paramotor"

# ---- paleta ----
NAVY = HexColor("#0f2c4d"); ACCENT = HexColor("#2f6df0"); TEAL = HexColor("#0fb5a6")
INK = HexColor("#1f2937"); MUT = HexColor("#6b7280"); LINE = HexColor("#e5e7eb")
WHITE = colors.white
CHIP = {"green": ("#dcfce7", "#15803d"), "red": ("#fee2e2", "#b91c1c"),
        "grey": ("#eef2f7", "#334155"), "accent": ("#e0ebff", "#2f6df0")}


def chip(text, kind="grey"):
    bg, fg = CHIP[kind]
    w = stringWidth(text, "Helvetica-Bold", 8) + 16
    t = Table([[text]], colWidths=[w], rowHeights=[14])
    st = [("BACKGROUND", (0,0), (-1,-1), HexColor(bg)), ("TEXTCOLOR", (0,0), (-1,-1), HexColor(fg)),
          ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
          ("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
          ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
          ("TOPPADDING", (0,0), (-1,-1), 0), ("BOTTOMPADDING", (0,0), (-1,-1), 0)]
    try:
        st.append(("ROUNDEDCORNERS", [7, 7, 7, 7]))
    except Exception:
        pass
    t.setStyle(TableStyle(st)); return t


def _circle_coords(lon, lat, radius_m, n=40):
    coslat = math.cos(math.radians(lat)); out = []
    for k in range(n + 1):
        a = 2 * math.pi * k / n
        out.append((lon + (radius_m*math.sin(a))/(111320.0*coslat), lat + (radius_m*math.cos(a))/111320.0))
    return out


MAP_TYPECOL = {"SP": "#15803d", "FP": "#b91c1c", "TP": "#2f6df0", "HG": "#7a52c4", "TG": "#d97706"}
_R3857 = 6378137.0


def _merc(lon, lat):
    return _R3857 * math.radians(lon), _R3857 * math.log(math.tan(math.pi/4 + math.radians(lat)/2))


def _make_map(tr, pts, path):
    """Mapa de alta resolução: basemap OSM + pontos coloridos/rotulados por tipo."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from matplotlib.lines import Line2D
    import contextily as cx

    fx = tr.fixes
    P = [_merc(f.lon, f.lat) for f in fx]
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    fig, ax = plt.subplots(figsize=(11, 7.4))
    ax.plot(xs, ys, color="#2f6df0", lw=2.0, alpha=.9, zorder=4, solid_capstyle="round")
    present = []
    for p in pts:
        px, py = _merc(p.lon, p.lat); col = MAP_TYPECOL.get(p.type, "#555")
        r = p.radius / math.cos(math.radians(p.lat))
        ax.add_patch(Circle((px, py), r, fill=False, ec=col, lw=1.0, alpha=.85, zorder=5))
        big = p.type in ("SP", "FP")
        ax.scatter([px], [py], s=80 if big else 40, c=col, edgecolors="white", linewidths=1.2, zorder=6)
        ax.annotate(p.name, (px, py), fontsize=6, fontweight="bold", color="#1f2937",
                    xytext=(4, 4), textcoords="offset points", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=.7))
        if p.type not in present:
            present.append(p.type)
    padx = max(700, (max(xs)-min(xs))*0.05); pady = max(700, (max(ys)-min(ys))*0.05)
    ax.set_xlim(min(xs)-padx, max(xs)+padx); ax.set_ylim(min(ys)-pady, max(ys)+pady)
    ax.set_aspect("equal"); ax.set_axis_off()
    cx.add_basemap(ax, crs="EPSG:3857", source=cx.providers.OpenStreetMap.Mapnik, attribution_size=5)
    handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=MAP_TYPECOL[t],
                      markeredgecolor='gray', markersize=8, label=t) for t in present]
    ax.legend(handles=handles, loc="lower right", fontsize=7, framealpha=.9, ncol=len(handles))
    fig.tight_layout(pad=0.3); fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig)


def _make_map_fallback(tr, pts, path):
    from staticmap import StaticMap, Line, CircleMarker
    m = StaticMap(1000, 680, url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', padding_x=40, padding_y=40)
    m.add_line(Line([(f.lon, f.lat) for f in tr.fixes], '#2f6df0', 4))
    for p in pts:
        m.add_marker(CircleMarker((p.lon, p.lat), '#ffffff', 12))
        m.add_marker(CircleMarker((p.lon, p.lat), '#d35400', 9))
    m.render().save(path)


def gen(slug, igc_path, out, bib=None, decl=None):
    prova = storage.get_prova(slug)
    if not prova:
        raise SystemExit(f"prova '{slug}' não encontrada")
    tr = parse_igc(open(igc_path, encoding="utf-8", errors="ignore").read(), os.path.basename(igc_path))
    pil = Pilot(bib=bib or tr.bib, name=tr.name, date=tr.date, fixes=tr.fixes)
    if decl:
        for kv in decl.split(","):
            k, v = kv.split("="); pil.decl[k.strip()] = int(v)
    return render_report(prova, pil, out)


def render_report(prova, pil, out):
    """Gera o PDF a partir de uma Prova e um Pilot (fixes já carregados)."""
    tr = pil  # Pilot expõe name/date/fixes
    ev = evaluate(prova, pil); st = ev["stats"]; c = ev["counts"]; pts = prova.points; tz = prova.tz

    import tempfile
    # nome único por chamada: evita corrida entre workers gunicorn no mesmo host
    _fd, mapf = tempfile.mkstemp(prefix="_rep_map_", suffix=".png"); os.close(_fd)
    try:
        _make_map(tr, pts, mapf)
    except Exception as e:
        print("aviso: mapa alta-res falhou (", e, ") — tentando fallback")
        try:
            _make_map_fallback(tr, pts, mapf)
        except Exception as e2:
            print("aviso: mapa indisponível (", e2, ")"); mapf = None

    base = getSampleStyleSheet()
    lab = ParagraphStyle("lab", parent=base["Normal"], fontSize=9, textColor=MUT)
    val = ParagraphStyle("val", parent=base["Normal"], fontSize=9, textColor=INK)
    bold = ParagraphStyle("b", parent=val, fontName="Helvetica-Bold")
    secst = ParagraphStyle("sec", parent=base["Normal"], fontSize=11.5, textColor=NAVY, fontName="Helvetica-Bold")

    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=10*mm, bottomMargin=12*mm,
                            leftMargin=15*mm, rightMargin=15*mm, title=f"Relatório de voo — {tr.name}",
                            author=BRAND)
    S = []

    # ---- faixa de cabeçalho (marca) ----
    brand_cell = [Paragraph(f'<font color="#7fd4ff">▲</font> <b>{BRAND}</b>',
                            ParagraphStyle("br", fontSize=13, leading=16, textColor=WHITE)),
                  Paragraph("Relatório de Voo", ParagraphStyle("ti", fontSize=20, leading=24, textColor=WHITE, fontName="Helvetica-Bold", spaceBefore=3, spaceAfter=3)),
                  Paragraph(TAGLINE, ParagraphStyle("tg", fontSize=8, leading=11, textColor=HexColor("#aecbf2")))]
    pinfo = [Paragraph(f"<b>{tr.name}</b>", ParagraphStyle("pn", fontSize=12, leading=16, textColor=WHITE, alignment=2)),
             Paragraph(f"BIB {pil.bib}", ParagraphStyle("pb", fontSize=9, leading=13, textColor=HexColor("#aecbf2"), alignment=2)),
             Paragraph(f"{prova.name} · {tr.date or '—'}", ParagraphStyle("pp", fontSize=9, leading=13, textColor=HexColor("#aecbf2"), alignment=2))]
    band = Table([[brand_cell, pinfo]], colWidths=(108*mm, 72*mm))
    band.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), NAVY), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                              ("LEFTPADDING", (0,0), (-1,-1), 14), ("RIGHTPADDING", (0,0), (-1,-1), 14),
                              ("TOPPADDING", (0,0), (-1,-1), 12), ("BOTTOMPADDING", (0,0), (-1,-1), 12),
                              ("ROUNDEDCORNERS", [9,9,9,9])]))
    S.append(band); S.append(Spacer(1, 10))

    def sec(title):
        bar = Table([[" "]], colWidths=(4,), rowHeights=(14,))
        bar.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),ACCENT), ("LEFTPADDING",(0,0),(-1,-1),0),
                                 ("RIGHTPADDING",(0,0),(-1,-1),0), ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),0)]))
        t = Table([[bar, Paragraph(title, secst)]], colWidths=(4, 172*mm))
        t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                               ("LEFTPADDING",(0,0),(0,0),0), ("RIGHTPADDING",(0,0),(0,0),0),
                               ("LEFTPADDING",(1,0),(1,0),7), ("RIGHTPADDING",(1,0),(1,0),0),
                               ("TOPPADDING",(0,0),(-1,-1),2), ("BOTTOMPADDING",(0,0),(-1,-1),3)]))
        return t

    def block(rows, w=(46*mm, 44*mm)):
        t = Table(rows, colWidths=w); t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(-1,-1),0)])); return t

    def row(label, value):
        return [Paragraph(label, lab), Paragraph(value, bold) if isinstance(value, str) else value]

    def two(a, b):
        t = Table([[a, b]], colWidths=(90*mm, 90*mm)); t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")])); return t

    def hrow(cells):
        t = Table([cells], hAlign="LEFT"); t.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),5),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)])); return t

    # Dados do IGC
    S.append(sec("Dados do voo"))
    S.append(two(block([row("Decolagem", clock(st["takeoff"], tz)), row("Pouso", clock(st["landing"], tz)),
                        row("Tempo de voo", dur(st["flight"]))]),
                 block([row("Altitude máxima", f"{st['max_alt']} m"),
                        row("Distância SP→FP", f"{km(st['dist_spfp'])} km"),
                        row("Velocidade média", f"{one(st['vel'])} km/h")])))
    S.append(Spacer(1, 6))

    # Prova
    S.append(sec("Dados da prova"))
    cc = hrow([Paragraph("Pontos", lab),
               chip(f"SP {c['SP']['total']}"), chip(f"TP {c['TP']['total']}"), chip(f"HG {c['HG']['total']}"),
               chip(f"TG {c['TG']['total']}"), chip(f"FP {c['FP']['total']}")])
    S.append(cc)
    S.append(Spacer(1, 2))
    S.append(two(block([row("Tempo-alvo", f"{prova.target_min} min")]),
                 block([row("Janela (DQ)", f"{prova.window_min} min"),
                        row("Deadline", prova.deadline or "—")])))
    S.append(Spacer(1, 6))

    # Desempenho
    S.append(sec("Desempenho"))
    passg = hrow([Paragraph("SP", bold), chip("Sim" if st["sp_crossed"] else "Não", "green" if st["sp_crossed"] else "red"),
                  Paragraph("FP", bold), chip("Sim" if st["fp_crossed"] else "Não", "green" if st["fp_crossed"] else "red")])
    def cv(t):
        return hrow([Paragraph(f"{c[t]['crossed']}/{c[t]['total']}", bold), chip(f"{c[t]['valid']} válidos", "green")])
    S.append(two(block([[Paragraph("Passagens", lab), passg],
                        [Paragraph("Turn points (TP)", lab), cv("TP")],
                        [Paragraph("Hidden gates (HG)", lab), cv("HG")]]),
                 block([row("Tempo SP→FP", dur(st["time_spfp"])),
                        [Paragraph("Time gates (TG)", lab), cv("TG")]])))
    S.append(Spacer(1, 4))

    # Situação (janela / validade) + penalidades informativas
    rows_score = score_prova(prova, [pil])
    rscore = rows_score[0]
    dq = any("Desclassificado" in p for p in rscore.get("penal", []))
    situ = chip("DESCLASSIFICADO", "red") if dq else chip("VÁLIDO", "green")
    flags = [p for p in rscore.get("penal", []) if "Desclassificado" not in p]
    sit_cells = [Paragraph("Situação", lab), situ]
    for fl in flags:
        sit_cells.append(chip(fl, "grey"))
    S.append(hrow(sit_cells))
    S.append(Spacer(1, 8))

    # N2: tempos declarados × voados (elapsado desde o SP)
    if prova.type == "n2":
        timed = [(i, p) for i, p in enumerate(pts) if p.type in ("TG", "FP")]
        sp_i = next((i for i, p in enumerate(pts) if p.type == "SP"), None)
        sp_entry = ev["by_id"][sp_i]["hit_t"] if sp_i is not None else None
        if timed:
            S.append(sec("Tempos declarados × voados")); S.append(Spacer(1, 3))
            hd = [Paragraph(f"<b>{h}</b>", ParagraphStyle("h", fontSize=8, textColor=WHITE))
                  for h in ["Gate", "Declarado", "Voado", "Erro", "Situação"]]
            trows = [hd]
            for i, p in timed:
                r = ev["by_id"][i]; dec = pil.decl.get(p.name)
                if r["crossed"] and sp_entry is not None:
                    voado = r["hit_t"] - sp_entry
                    if dec is not None:
                        err = abs(round(voado - dec))
                        within = err <= (prova.tol or 0)
                        trows.append([p.name, dur(dec), dur(voado), f"{err} s",
                                      chip("ok" if within else f"{err}s", "green" if within else "grey")])
                    else:
                        trows.append([p.name, "—", dur(voado), "—", chip("sem declaração", "grey")])
                else:
                    trows.append([p.name, dur(dec) if dec is not None else "—", "—", "—", chip("não cruzou", "red")])
            tt = Table(trows, colWidths=(26*mm, 30*mm, 30*mm, 24*mm, 40*mm), repeatRows=1)
            tts = [("FONTSIZE",(0,0),(-1,-1),8), ("BACKGROUND",(0,0),(-1,0),NAVY),
                   ("LINEBELOW",(0,1),(-1,-1),.3,LINE), ("BOX",(0,0),(-1,-1),.5,LINE),
                   ("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("LEFTPADDING",(0,0),(-1,-1),6),
                   ("TOPPADDING",(0,0),(-1,-1),3), ("BOTTOMPADDING",(0,0),(-1,-1),3),
                   ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, HexColor("#f7f9fc")])]
            tt.setStyle(TableStyle(tts))
            S.append(tt)
            S.append(Spacer(1, 8))

    if mapf:
        S.append(sec("Mapa do voo"))
        S.append(Spacer(1, 3)); S.append(Image(mapf, width=180*mm, height=120*mm))
        S.append(Spacer(1, 8))

    S.append(sec("Pontos da prova"))
    S.append(Spacer(1, 3))
    head = [Paragraph(f"<b>{h}</b>", ParagraphStyle("h", fontSize=8, textColor=WHITE))
            for h in ["Ponto", "Tipo", "Raio", "Cruzado", "Válido", "Hora do hit", "Dist. centro"]]
    rows = [head]
    for i, p in enumerate(pts):
        r = ev["by_id"][i]; nav = p.type in ("SP", "FP")
        valido = Paragraph("—", val) if nav else (chip("Sim", "green") if (r["valid"] and r["crossed"]) else chip("Não", "red"))
        rows.append([f"{p.name}", chip(p.type, "accent"), f"{int(p.radius)} m",
                     "Sim" if r["crossed"] else "Não", valido,
                     clock(r["hit_t"], tz) if r["crossed"] else "—",
                     (f"{one(r['min_d'])} m" if (nav and r["crossed"]) else "—")])
    t = Table(rows, colWidths=(28*mm, 16*mm, 16*mm, 19*mm, 17*mm, 28*mm, 26*mm), repeatRows=1)
    sty = [("FONTSIZE", (0,0), (-1,-1), 8), ("BACKGROUND", (0,0), (-1,0), NAVY),
           ("LINEBELOW", (0,1), (-1,-1), .3, LINE), ("BOX", (0,0), (-1,-1), .5, LINE),
           ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
           ("LEFTPADDING", (0,0), (-1,-1), 6), ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, HexColor("#f7f9fc")])]
    for ri in range(1, len(rows)):
        if rows[ri][3] == "Não":
            sty.append(("TEXTCOLOR", (3, ri), (3, ri), HexColor("#b91c1c")))
    t.setStyle(TableStyle(sty))
    S.append(t)
    S.append(Spacer(1, 8))
    today = datetime.date.today().strftime("%d/%m/%Y")
    S.append(Table([[Paragraph(f"{BRAND} · {TAGLINE}", ParagraphStyle("f", fontSize=7.5, textColor=MUT)),
                     Paragraph(f"Gerado em {today}", ParagraphStyle("f2", fontSize=7.5, textColor=MUT, alignment=2))]],
                   colWidths=(120*mm, 60*mm), style=TableStyle([("LINEABOVE",(0,0),(-1,-1),.5,LINE),("TOPPADDING",(0,0),(-1,-1),4)])))
    doc.build(S)
    if mapf:
        try:
            os.remove(mapf)
        except OSError:
            pass
    return out


def _deadline_sec(prova):
    if not prova.deadline:
        return None
    import re
    m = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", prova.deadline)
    return (int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3) or 0) - prova.tz*3600) if m else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug"); ap.add_argument("igc"); ap.add_argument("out", nargs="?")
    ap.add_argument("--bib"); ap.add_argument("--decl")
    a = ap.parse_args()
    print("gerado:", gen(a.slug, a.igc, a.out or "/tmp/relatorio.pdf", bib=a.bib, decl=a.decl))
