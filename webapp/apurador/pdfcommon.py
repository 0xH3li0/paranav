"""Constantes e helpers compartilhados pelos geradores de PDF em reportlab:
`mappdf.py` (mapa A3) e `pointspdf.py` (folha A4 de pontos).

⚠️ O render QGIS (`qgis_render.py`) roda em SUBPROCESSO no python do sistema
(PyQGIS) e NÃO importa daqui — ele mantém suas próprias constantes.
"""
from __future__ import annotations
import math

M_PER_DEG = 111320.0          # metros por grau de latitude (aprox. esférica)

# satélite Esri World Imagery (grátis) — também usado pelo recorte A4
ESRI_TILES = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
              "World_Imagery/MapServer/tile/{z}/{y}/{x}")

# base de fundo do A3: nome -> (template de tile, zoom máximo)
TILE_URLS = {
    "topo": ("https://a.tile.opentopomap.org/{z}/{x}/{y}.png", 17),
    "esri": (ESRI_TILES, 19),
    "osm":  ("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", 19),
}


def mpp(lat: float, z: int) -> float:
    """Metros por pixel reais no zoom `z`, na latitude `lat` (Web Mercator)."""
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** z)


def zoom_for(lat: float, ground_m: float, px: int) -> int:
    """Maior zoom (1..19) cujo recorte de `px` pixels cobre ~`ground_m` m de solo."""
    target = ground_m / px
    z = math.log2(156543.03392 * math.cos(math.radians(lat)) / target)
    return max(1, min(19, int(math.floor(z))))
