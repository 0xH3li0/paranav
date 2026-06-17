"""Folha A4 de imagens dos pontos (B4 / Fase 3).

Para cada ponto da prova: recorte de **satélite (Esri World Imagery)** centrado
no ponto, enquadrando área MAIOR que o raio, com o **anel do raio** desenhado e o
nome/raio. Vários por folha A4 (grade). Imagens **north-up** (orientação dos tiles),
com indicador de norte por célula.

Requer rede (busca de tiles) + staticmap + Pillow. Falha graciosa por ponto.
"""
from __future__ import annotations
import math
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ESRI = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/tile/{z}/{y}/{x}")
TYPECOL = {"SP": (0.08, 0.50, 0.24), "FP": (0.72, 0.11, 0.11),
           "TP": (0.18, 0.43, 0.94), "HG": (0.48, 0.32, 0.77), "TG": (0.85, 0.47, 0.02)}
IMG_W, IMG_H = 480, 320     # px do recorte de satélite


def _mpp(lat, z):
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** z)


def _zoom_for(lat, ground_m, px):
    target = ground_m / px
    z = math.log2(156543.03392 * math.cos(math.radians(lat)) / target)
    return max(1, min(19, int(math.floor(z))))


def _crop(lat, lon, radius, col):
    """Recorte de satélite (PIL) centrado no ponto, com anel do raio. None se falhar."""
    from staticmap import StaticMap
    from PIL import ImageDraw
    ground = max((radius or 0) * 3.0, 400.0)          # vizinhança > raio (mín. 400 m)
    z = _zoom_for(lat, ground, IMG_W)
    m = StaticMap(IMG_W, IMG_H, url_template=ESRI)
    img = m.render(zoom=z, center=(lon, lat)).convert("RGB")
    mpp = _mpp(lat, z)
    cx, cy = IMG_W / 2, IMG_H / 2
    d = ImageDraw.Draw(img)
    rgb = tuple(int(v * 255) for v in col)
    if radius and radius / mpp > 1:
        rpx = radius / mpp
        d.ellipse([cx - rpx, cy - rpx, cx + rpx, cy + rpx], outline=rgb, width=3)
    d.line([cx - 7, cy, cx + 7, cy], fill=rgb, width=2)
    d.line([cx, cy - 7, cx, cy + 7], fill=rgb, width=2)
    d.line([12, 22, 12, 8], fill=(255, 255, 255), width=2)   # seta de norte
    d.text((8, 24), "N", fill=(255, 255, 255))
    bio = BytesIO(); img.save(bio, format="PNG"); bio.seek(0)
    return bio


def render_points_pdf(prova, brand: str, out) -> None:
    """Catálogo A4 (estilo AITA): grade 4-col de recortes de satélite NORTE-ACIMA,
    número grande branco no canto, círculo vermelho do raio + seta de Norte por figura."""
    W, H = A4                                   # retrato (595 × 842 pt)
    c = canvas.Canvas(out, pagesize=A4)
    margin, title_h, gap = 10 * mm, 16 * mm, 4 * mm
    cols = 4
    cell_w = (W - 2 * margin - (cols - 1) * gap) / cols
    img_h = cell_w / (IMG_W / IMG_H)
    label_h = 6 * mm
    cell_h = img_h + label_h
    top = H - margin - title_h
    rows = max(1, int((top - margin + gap) // (cell_h + gap)))
    per_page = cols * rows
    red = (0.86, 0.09, 0.12)

    pts = list(prova.points)

    def header():
        c.setFillColorRGB(0.05, 0.15, 0.35); c.setFont("Helvetica-Bold", 15)
        c.drawString(margin, H - margin - 11, f"Catálogo de pontos — {prova.name}")
        c.setFillColorRGB(0, 0, 0); c.setFont("Helvetica", 9)
        c.drawString(margin, H - margin - 25, f"{brand}  ·  escala {prova.scale}  ·  norte-acima")

    header()
    if not pts:
        c.setFont("Helvetica-Oblique", 11); c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(W / 2, H / 2, "Prova sem pontos — nada a recortar.")
        c.showPage(); c.save()
        return
    for i, pt in enumerate(pts):
        if i and i % per_page == 0:
            c.showPage(); header()
        slot = i % per_page
        r, col = divmod(slot, cols)
        x = margin + col * (cell_w + gap)
        y = top - (r + 1) * img_h - r * (label_h + gap)
        try:
            crop = _crop(pt.lat, pt.lon, pt.radius, red)
            c.drawImage(ImageReader(crop), x, y, width=cell_w, height=img_h)
        except Exception:  # noqa  — sem rede / tile falhou
            c.setFillColorRGB(0.9, 0.9, 0.9); c.rect(x, y, cell_w, img_h, fill=1, stroke=0)
            c.setFillColorRGB(0.4, 0.4, 0.4); c.setFont("Helvetica", 8)
            c.drawCentredString(x + cell_w / 2, y + img_h / 2, "(satélite indisponível)")
        c.setStrokeColorRGB(0.3, 0.3, 0.3); c.setLineWidth(0.6)
        c.rect(x, y, cell_w, img_h, fill=0, stroke=1)
        # número GRANDE no canto sup-esq (sombra escura + branco) — estilo AITA
        c.setFont("Helvetica-Bold", 19)
        c.setFillColorRGB(0.06, 0.06, 0.06); c.drawString(x + 4.2, y + img_h - 19.5, pt.name)
        c.setFillColorRGB(1, 1, 1); c.drawString(x + 3.5, y + img_h - 19, pt.name)
        # legenda abaixo
        c.setFillColorRGB(0, 0, 0); c.setFont("Helvetica-Bold", 8)
        c.drawString(x + 1, y - 10, f"{pt.name} ({pt.type}) · r {int(pt.radius or 0)} m")
    c.showPage(); c.save()
