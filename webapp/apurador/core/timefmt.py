"""Formatação de tempo (UTC -> local) e durações."""
from __future__ import annotations
from typing import Optional


def clock(sec_utc: Optional[int], tz: int = -3) -> str:
    if sec_utc is None:
        return "—"
    s = (round(sec_utc) + tz * 3600) % 86400
    h, m, x = s // 3600, (s % 3600) // 60, s % 60
    return f"{h:02d}:{m:02d}:{x:02d}"


def dur(sec: Optional[float]) -> str:
    if sec is None:
        return "—"
    sec = round(sec)
    h, m, x = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h:02d}:{m:02d}:{x:02d}"


def km(m: Optional[float], d: int = 3) -> str:
    return "—" if m is None else f"{m/1000:.{d}f}"


def one(x: Optional[float], d: int = 1) -> str:
    return "—" if x is None else f"{x:.{d}f}"
