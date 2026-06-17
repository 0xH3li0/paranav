"""Geometria — distância Haversine (metros). Validado contra o paradigma.

`dist()` é a Haversine usada por N1/N2 — NÃO ALTERAR (quebra calibração).
As funções de polilinha/corredor abaixo são ADITIVAS (sala N3 / Curve Navigation)
e usam projeção equirretangular local — exata o bastante na escala de pernas (km).
"""
from math import radians, sin, cos, asin, sqrt
from typing import List, Sequence, Tuple

R_EARTH = 6_371_000.0  # metros


def dist(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    """Distância em metros entre dois pontos (lat/lon em graus)."""
    d_lat = radians(b_lat - a_lat)
    d_lon = radians(b_lon - a_lon)
    s = (sin(d_lat / 2) ** 2
         + cos(radians(a_lat)) * cos(radians(b_lat)) * sin(d_lon / 2) ** 2)
    return 2 * R_EARTH * asin(min(1.0, sqrt(s)))


# ----- Corredor / rota curva (sala N3 = Curve Navigation) -------------------

def _xy(lat: float, lon: float, lat0: float, lon0: float) -> Tuple[float, float]:
    """Projeção equirretangular local (metros) centrada em (lat0, lon0)."""
    x = radians(lon - lon0) * cos(radians(lat0)) * R_EARTH
    y = radians(lat - lat0) * R_EARTH
    return x, y


def dist_to_segment_m(plat: float, plon: float,
                      alat: float, alon: float,
                      blat: float, blon: float) -> float:
    """Distância (m) do ponto P ao segmento A→B, com clamp nas extremidades."""
    ax, ay = _xy(alat, alon, alat, alon)        # A na origem
    bx, by = _xy(blat, blon, alat, alon)
    px, py = _xy(plat, plon, alat, alon)
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 == 0.0:                              # A == B
        return sqrt((px - ax) ** 2 + (py - ay) ** 2)
    t = ((px - ax) * dx + (py - ay) * dy) / seg2
    t = max(0.0, min(1.0, t))                    # clamp ao segmento
    cx, cy = ax + t * dx, ay + t * dy
    return sqrt((px - cx) ** 2 + (py - cy) ** 2)


def dist_to_polyline_m(lat: float, lon: float,
                       coords: Sequence[Sequence[float]]) -> float:
    """Menor distância (m) do ponto à polilinha (lista de [lat, lon])."""
    if not coords:
        return float("inf")
    if len(coords) == 1:
        return dist(lat, lon, coords[0][0], coords[0][1])
    best = float("inf")
    for i in range(len(coords) - 1):
        a, b = coords[i], coords[i + 1]
        d = dist_to_segment_m(lat, lon, a[0], a[1], b[0], b[1])
        if d < best:
            best = d
    return best


def route_length_m(coords: Sequence[Sequence[float]]) -> float:
    """Comprimento total (m) da polilinha."""
    return sum(dist(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1])
               for i in range(len(coords) - 1)) if len(coords) > 1 else 0.0


def densify_polyline(coords: Sequence[Sequence[float]],
                     step_m: float = 50.0) -> List[List[float]]:
    """Reamostra a polilinha em passos ~step_m (interpolação linear lat/lon).

    Usado para medir cobertura do corredor por amostragem (independe da ordem
    dos fixes). Mantém os vértices originais como âncoras.
    """
    if len(coords) < 2:
        return [list(c) for c in coords]
    out: List[List[float]] = [list(coords[0])]
    for i in range(len(coords) - 1):
        a, b = coords[i], coords[i + 1]
        seg = dist(a[0], a[1], b[0], b[1])
        n = max(1, int(seg // step_m))
        for k in range(1, n + 1):
            f = k / n
            out.append([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f])
    return out
