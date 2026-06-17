"""Parser de IGC — porta da lógica validada do protótipo.

Lê headers HFPLT (nome), HFCID (BIB) e HFDTE (data) e os B-records por
offsets fixos 1–34. IGCs do Gaggle têm I-record (extensões) após a posição 35;
lemos apenas os offsets fixos, então isso é ignorado de forma segura.
Tempos são UTC (segundos desde 00:00).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Fix:
    t: int       # segundos UTC desde 00:00
    lat: float
    lon: float
    alt: int = 0


@dataclass
class Track:
    name: str
    bib: str
    date: str
    fixes: List[Fix] = field(default_factory=list)


def parse_igc(text: str, fallback_name: str = "") -> Track:
    name = fallback_name
    bib = ""
    date = ""
    fixes: List[Fix] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        up = line.upper()
        if up.startswith("HFPLT"):
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[1].strip():
                name = parts[1].strip()
        elif up.startswith("HFCID"):
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[1].strip():
                bib = parts[1].strip()
        elif up.startswith("HFDTE"):
            m = re.search(r"(\d{2})(\d{2})(\d{2})", line)
            if m:
                date = f"20{m.group(3)}-{m.group(2)}-{m.group(1)}"
        elif line[0] == "B" and len(line) >= 35:
            try:
                hh = int(line[1:3]); mm = int(line[3:5]); ss = int(line[5:7])
                la_d = int(line[7:9]); la_m = int(line[9:14]) / 1000.0; la_h = line[14]
                lo_d = int(line[15:18]); lo_m = int(line[18:23]) / 1000.0; lo_h = line[23]
                palt = int(line[25:30]); galt = int(line[30:35])
            except ValueError:
                continue
            lat = la_d + la_m / 60.0
            if la_h == "S":
                lat = -lat
            lon = lo_d + lo_m / 60.0
            if lo_h == "W":
                lon = -lon
            if abs(lat) <= 90 and abs(lon) <= 180:
                fixes.append(Fix(hh * 3600 + mm * 60 + ss, lat, lon, galt or palt))
    if not bib:
        m = re.search(r"\b(\d{1,4})\b", name)
        bib = m.group(1) if m else (name or "?")
    return Track(name=name or fallback_name, bib=bib, date=date, fixes=fixes)
