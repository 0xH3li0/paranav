"""Geração do Mapa A3 da prova em ESCALA FIEL (B3 / Fase 2).

Página A3 paisagem. O conteúdo do mapa (pontos+raios, áreas, corredor N3) é
projetado em **escala real do papel**: em 1:50.000, 1 km de solo = 2 cm no papel.
A rotação da folha (`prova.frame.angle`) é respeitada; a **rosa dos ventos** aponta
o norte real considerando essa rotação. Faixa de informações com marca, escala,
teto/altura mínima e dados da prova.

Vetorial (sem raster de satélite) — atende a fidelidade de escala e orientação.
Reaproveita a geometria do `frame` (mesma de `static/js/builder.js`).
"""
from __future__ import annotations
import math
import os
from io import BytesIO
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

TYPECOL = {"SP": (0.08, 0.50, 0.24), "FP": (0.72, 0.11, 0.11),
           "TP": (0.18, 0.43, 0.94), "HG": (0.48, 0.32, 0.77), "TG": (0.85, 0.47, 0.02)}
M_PER_DEG = 111320.0


def _denom(scale: str) -> int:
    try:
        return int(str(scale).split(":")[1])
    except (IndexError, ValueError):
        return 50000


def _center(prova):
    fr = prova.frame or {}
    if fr.get("lat") is not None:
        return fr["lat"], fr["lon"], math.radians(fr.get("angle", 0) or 0)
    lats = [p.lat for p in prova.points] or [0]
    lons = [p.lon for p in prova.points] or [0]
    return sum(lats) / len(lats), sum(lons) / len(lons), 0.0


_TILE_URLS = {
    "topo": ("https://a.tile.opentopomap.org/{z}/{x}/{y}.png", 17),
    "esri": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", 19),
    "osm":  ("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", 19),
}


def _basemap(c, base, lat0, lon0, ang_deg, mpm, cx, cy, area_w, area_h):
    """Fundo do mapa (tiles da base) sob o vetor, em escala fiel. Silencioso se falhar."""
    try:
        from staticmap import StaticMap
        from PIL import Image
    except Exception:  # noqa
        return
    url, maxz = _TILE_URLS.get(base or "topo", _TILE_URLS["topo"])
    cover = math.hypot(area_w / mpm, area_h / mpm)          # metros de solo (cobre folha rotacionada)
    img_px = 1500
    coslat = math.cos(math.radians(lat0))
    z = int(math.floor(math.log2(156543.03392 * coslat / (cover / img_px))))
    z = max(1, min(maxz, z))
    mpp = 156543.03392 * coslat / (2 ** z)                  # metros por pixel reais
    try:
        m = StaticMap(img_px, img_px, url_template=url, padding_x=0, padding_y=0)
        img = m.render(zoom=z, center=(lon0, lat0)).convert("RGB")
    except Exception:  # noqa  — sem rede / tile falhou
        return
    if ang_deg:
        img = img.rotate(ang_deg, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
    bio = BytesIO(); img.save(bio, format="JPEG", quality=85); bio.seek(0)
    w = img_px * mpp * mpm                                  # tamanho no papel = escala fiel
    c.drawImage(ImageReader(bio), cx - w / 2, cy - w / 2, width=w, height=w)


def render_map_pdf(prova, brand: str, out) -> None:
    """Desenha o mapa A3 da `prova`/`mapa` em `out`, no estilo AITA: NORTE-ACIMA,
    barra lateral esquerda (escala/logo/título/declinação), seta de Norte
    proeminente e turnpoints como círculos vermelhos com número magenta."""
    orient = getattr(prova, "orientation", "paisagem")
    W, H = (A3 if orient == "retrato" else landscape(A3))   # retrato (297×420) | paisagem (420×297)
    c = canvas.Canvas(out, pagesize=(W, H))

    lat0, lon0, ang = _center(prova)           # ang = rotação da folha (faixa endireitada na página)
    denom = _denom(prova.scale)
    mpm = (1000.0 / denom) * mm               # pontos de papel por metro de solo
    cos_a, sin_a, mE = math.cos(ang), math.sin(ang), M_PER_DEG * math.cos(math.radians(lat0))

    # barra lateral (estilo AITA) à esquerda + área do mapa à direita
    margin = 8 * mm
    sb_w = 40 * mm
    mx0, my0 = margin + sb_w + 3 * mm, margin
    mx1, my1 = W - margin, H - margin
    cx, cy = (mx0 + mx1) / 2, (my0 + my1) / 2

    def proj(lat, lon):
        e = (lon - lon0) * mE
        n = (lat - lat0) * M_PER_DEG
        dx = e * cos_a + n * sin_a            # endireita a folha na página (Rot(-ang))
        dy = -e * sin_a + n * cos_a
        return cx + dx * mpm, cy + dy * mpm

    # ---- moldura do mapa + clip ----
    c.setLineWidth(1)
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.rect(mx0, my0, mx1 - mx0, my1 - my0, stroke=1, fill=0)
    c.saveState()
    path = c.beginPath(); path.rect(mx0, my0, mx1 - mx0, my1 - my0); c.clipPath(path, stroke=0)

    # ---- fundo: tiles da base em escala fiel (north-up; ang=0 no editor atual) ----
    _basemap(c, getattr(prova, "base", "topo"), lat0, lon0, math.degrees(ang), mpm, cx, cy, mx1 - mx0, my1 - my0)

    # ---- grade de 1 km ----
    c.setStrokeColorRGB(0.85, 0.85, 0.85); c.setLineWidth(0.3)
    step = 1000 * mpm
    if step > 4:
        k = 0
        while cx + k * step < mx1 or cx - k * step > mx0:
            for x in (cx + k * step, cx - k * step):
                if mx0 <= x <= mx1:
                    c.line(x, my0, x, my1)
            k += 1
        k = 0
        while cy + k * step < my1 or cy - k * step > my0:
            for y in (cy + k * step, cy - k * step):
                if my0 <= y <= my1:
                    c.line(mx0, y, mx1, y)
            k += 1

    # ---- áreas (proibida/atenção) ----
    for a in (prova.areas or []):
        coords = a.get("coords") or []
        if len(coords) < 3:
            continue
        col = (0.9, 0.22, 0.21) if a.get("kind") == "proibida" else (0.98, 0.66, 0.15)
        c.setFillColorRGB(*col); c.setStrokeColorRGB(*col)
        c.setFillAlpha(0.25); c.setLineWidth(1)
        p = c.beginPath(); x, y = proj(coords[0][0], coords[0][1]); p.moveTo(x, y)
        for ll in coords[1:]:
            x, y = proj(ll[0], ll[1]); p.lineTo(x, y)
        p.close(); c.drawPath(p, stroke=1, fill=1); c.setFillAlpha(1)

    # ---- corredor (N3) ----
    route = prova.route or {}
    if route.get("coords") and len(route["coords"]) > 1:
        pts = [proj(ll[0], ll[1]) for ll in route["coords"]]
        half = (route.get("width", 0) / 2.0) * mpm
        left, right = [], []
        for i, (x, y) in enumerate(pts):
            px, py = pts[max(0, i - 1)]; nx, ny = pts[min(len(pts) - 1, i + 1)]
            dx, dy = nx - px, ny - py
            L = math.hypot(dx, dy) or 1.0
            ox, oy = -dy / L * half, dx / L * half
            left.append((x + ox, y + oy)); right.append((x - ox, y - oy))
        c.setFillColorRGB(0.05, 0.65, 0.91); c.setStrokeColorRGB(0.05, 0.65, 0.91)
        c.setFillAlpha(0.15); buf = c.beginPath()
        ring = left + right[::-1]; buf.moveTo(*ring[0])
        for x, y in ring[1:]:
            buf.lineTo(x, y)
        buf.close(); c.drawPath(buf, stroke=0, fill=1); c.setFillAlpha(1)
        c.setLineWidth(1.2); c.setDash(4, 3)
        ln = c.beginPath(); ln.moveTo(*pts[0])
        for x, y in pts[1:]:
            ln.lineTo(x, y)
        c.drawPath(ln, stroke=1, fill=0); c.setDash()

    # ---- pontos — estilo AITA: círculo VERMELHO do raio + número MAGENTA ----
    red, magenta = (0.86, 0.09, 0.12), (0.80, 0.05, 0.55)
    c.setFont("Helvetica-Bold", 9)
    for pt in prova.points:
        x, y = proj(pt.lat, pt.lon)
        c.setStrokeColorRGB(*red); c.setLineWidth(1.2)
        rr = (pt.radius or 0) * mpm
        if rr > 1:
            c.circle(x, y, rr, stroke=1, fill=0)
        c.setFillColorRGB(*red); c.circle(x, y, 1.2, stroke=0, fill=1)
        c.setFillColorRGB(*magenta)
        c.drawString(x + (rr if rr > 3 else 4) + 1, y + (rr * 0.45 if rr > 3 else 2), pt.name)

    # ---- marcadores de pouso (3.A3/3.A5) ----
    for ld in (prova.landings or []):
        x, y = proj(ld["lat"], ld["lon"])
        c.setFillColorRGB(0.10, 0.55, 0.30); c.setStrokeColorRGB(1, 1, 1); c.setLineWidth(0.8)
        c.rect(x - 3, y - 3, 6, 6, stroke=1, fill=1)
        c.setFillColorRGB(0.10, 0.45, 0.25); c.setFont("Helvetica-Oblique", 7)
        c.drawString(x + 4, y - 2, ld.get("name", "Pouso"))
    c.restoreState()

    if not prova.points and not (route.get("coords")):
        c.setFont("Helvetica-Oblique", 11); c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(cx, cy, "Prova sem pontos — adicione pontos no Construtor.")

    # ---- rosa dos ventos (aponta o norte real, girada com a folha) + barra lateral (estilo AITA) ----
    _north_arrow(c, mx0 + 14 * mm, my1 - 14 * mm, ang)
    _sidebar(c, prova, brand, denom, mpm, margin, sb_w, H)

    c.showPage(); c.save()


def _north_arrow(c, ax, ay, ang=0.0):
    """Agulha de Norte estilo AITA: metade esquerda hachurada, metade direita branca, contorno
    preto grosso, 'N' na ponta. `ang` em radianos (rotação da folha) — aponta o NORTE real (= proj)."""
    apex, left, notch, right = (0, 13 * mm), (-5.5 * mm, -8 * mm), (0, -3 * mm), (5.5 * mm, -8 * mm)
    c.saveState()
    c.translate(ax, ay)
    c.rotate(-math.degrees(ang))                     # alinha com proj (norte → (sin a, cos a))
    # metade DIREITA branca
    c.setFillColorRGB(1, 1, 1)
    p = c.beginPath(); p.moveTo(*apex); p.lineTo(*right); p.lineTo(*notch); p.close()
    c.drawPath(p, stroke=0, fill=1)
    # metade ESQUERDA hachurada (linhas a 45° clipadas)
    c.saveState()
    lp = c.beginPath(); lp.moveTo(*apex); lp.lineTo(*left); lp.lineTo(*notch); lp.close()
    c.clipPath(lp, stroke=0)
    c.setStrokeColorRGB(0.1, 0.1, 0.1); c.setLineWidth(0.7)
    y = -12 * mm
    while y < 16 * mm:
        c.line(-9 * mm, y, 9 * mm, y + 18 * mm)
        y += 1.4 * mm
    c.restoreState()
    # contorno grosso
    op = c.beginPath(); op.moveTo(*apex); op.lineTo(*left); op.lineTo(*notch); op.lineTo(*right); op.close()
    c.setStrokeColorRGB(0.06, 0.06, 0.06); c.setLineWidth(2.2)
    c.drawPath(op, stroke=1, fill=0)
    c.setFillColorRGB(0.06, 0.06, 0.06); c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(0, 15 * mm, "N")
    c.restoreState()


def _sidebar(c, prova, brand, denom, mpm, margin, sb_w, H):
    """Barra lateral esquerda estilo AITA: escala (km), logo, título/escala/declinação (texto
    vertical lido de baixo p/ cima) e a marca no rodapé."""
    x0, y0, w, h = margin, margin, sb_w, H - 2 * margin
    c.setFillColorRGB(1, 1, 1); c.setStrokeColorRGB(0.2, 0.2, 0.2); c.setLineWidth(1)
    c.rect(x0, y0, w, h, stroke=1, fill=1)
    cxs = x0 + w / 2

    # --- barra de escala (topo): 0 – 1 – 2 km ---
    one = 1000 * mpm
    if 2 * one > w - 10:                              # encolhe p/ caber nos 40 mm
        one = (w - 12) / 2.0
    bx = x0 + (w - 2 * one) / 2
    byy = H - margin - 16
    c.setStrokeColorRGB(0, 0, 0); c.setFillColorRGB(0, 0, 0); c.setLineWidth(0.8)
    c.rect(bx, byy, one, 3.5, fill=1, stroke=1)
    c.rect(bx + one, byy, one, 3.5, fill=0, stroke=1)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(bx, byy + 6, "0")
    c.drawCentredString(bx + one, byy + 6, "1")
    c.drawCentredString(bx + 2 * one, byy + 6, "2 km")

    # --- logo ---
    ty = byy - 12
    logo = getattr(prova, "logo", "") or ""
    if logo and os.path.exists(logo):
        try:
            img = ImageReader(logo); iw, ih = img.getSize()
            dw = w - 14; dh = dw * (ih / iw)
            if dh > 64:
                dh = 64; dw = dh * (iw / ih)
            c.drawImage(img, cxs - dw / 2, ty - dh, width=dw, height=dh, mask="auto", preserveAspectRatio=True)
        except Exception:  # noqa
            pass

    # --- título + escala + declinação (texto vertical, lido de baixo p/ cima) ---
    title = getattr(prova, "titulo", "") or prova.name or brand
    c.saveState()
    c.translate(cxs - 3, y0 + 16); c.rotate(90)
    c.setFillColorRGB(0.06, 0.13, 0.30); c.setFont("Helvetica-Bold", 16)
    c.drawString(0, 7, title)
    c.setFillColorRGB(0, 0, 0); c.setFont("Helvetica", 9.5)
    c.drawString(0, -9, f"Escala 1:{denom}")
    decl = getattr(prova, "declinacao", "") or ""
    if decl:
        c.drawString(0, -22, f"Declinação Magnética {decl}")
    extra = []
    if getattr(prova, "teto", 0):
        extra.append(f"Teto {prova.teto} m")
    if getattr(prova, "altura_min", 0):
        extra.append(f"Alt. mín {prova.altura_min} m")
    if extra:
        c.drawString(0, -35, "  ·  ".join(extra))
    c.restoreState()

    # --- marca (rodapé, vertical) ---
    c.saveState()
    c.translate(x0 + 13, y0 + 6); c.rotate(90)
    c.setFillColorRGB(0.06, 0.13, 0.30); c.setFont("Helvetica-Bold", 11)
    c.drawString(0, 0, brand)
    c.restoreState()
