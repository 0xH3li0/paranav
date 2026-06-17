#!/usr/bin/env python3
"""Harness de regressão — valida os invariantes SAGRADOS contra os IGCs reais.

Roda os dados de `igcs/` contra as provas em `data/provas/` e confere os valores
de referência do paradigma (ver CLAUDE.md / docs/ROADMAP.md §2). Estes invariantes
são GEOMÉTRICOS (não dependem de tempos declarados, que não são versionados):

  - N1 Venet: 11 TP válidos (de 18), SP→FP = 01:00:47.
  - N2 Melk:  HG 26.   N2 Leandro: HG 16.

Uso:  cd webapp && python3 validate.py
Saída: linha por checagem (OK/FALHA) + status final. Exit code != 0 se regredir.

NÃO precisa de servidor: usa o core diretamente (mesmo caminho do scoring).
"""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from apurador import storage  # noqa: E402
from apurador.core.igc import parse_igc, Fix  # noqa: E402
from apurador.core.models import Pilot  # noqa: E402
from apurador.core.scoring import evaluate, score_prova  # noqa: E402
from apurador.core.geo import densify_polyline  # noqa: E402

IGCS = os.path.join(os.path.dirname(HERE), "igcs")


def _pilot(igc_name: str) -> Pilot:
    path = os.path.join(IGCS, igc_name)
    tr = parse_igc(open(path, encoding="utf-8", errors="ignore").read(), igc_name)
    return Pilot(bib=tr.bib, name=tr.name, date=tr.date, fixes=tr.fixes)


def _fmt(sec):
    if sec is None:
        return "—"
    sec = int(round(sec))
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


# (igc, slug, descrição, função(ev)->valor obtido, esperado)
CHECKS = [
    ("venet-n1.igc", "n1-navegacao-pura", "N1 Venet — TP válidos",
     lambda ev: ev["counts"]["TP"]["valid"], 11),
    ("venet-n1.igc", "n1-navegacao-pura", "N1 Venet — SP→FP (s)",
     lambda ev: int(round(ev["stats"]["time_spfp"])) if ev["stats"]["time_spfp"] else None, 3647),  # 01:00:47
    ("melk-n2.igc", "n2-tempo-declarado", "N2 Melk — HG válidos",
     lambda ev: ev["counts"]["HG"]["valid"], 26),
    ("leandro-n2.igc", "n2-tempo-declarado", "N2 Leandro — HG válidos",
     lambda ev: ev["counts"]["HG"]["valid"], 16),
]


def check_n3() -> bool:
    """N3 (Curve Navigation): piloto sintético voando EXATAMENTE a rota deve
    cobrir 100% do corredor e pontuar o máximo. Invariante determinístico."""
    prova = storage.get_prova("n3-rota-precisao")
    if not prova or prova.type != "n3" or not prova.route.get("coords"):
        print("FALHA  N3 — prova exemplo 'n3-rota-precisao' ausente/ inválida")
        return False
    pts = densify_polyline(prova.route["coords"], 30.0)
    fixes = [Fix(t=i, lat=p[0], lon=p[1], alt=300) for i, p in enumerate(pts)]
    rows = score_prova(prova, [Pilot(bib="T", name="teste", fixes=fixes)])
    r = rows[0]
    ratio_ok = r["inside_ratio"] >= 0.999
    pts_ok = r["points"] == prova.max_points
    ok = ratio_ok and pts_ok and not r["penal"]
    print(f"{'OK   ' if ok else 'FALHA'}  N3 — voo exato na rota: "
          f"inside_ratio={r['inside_ratio']:.3f} (esp≈1.000) pts={r['points']} "
          f"(esp={prova.max_points}) penal={r['penal']}")
    return ok


def main() -> int:
    fails = 0
    for igc, slug, desc, getter, expected in CHECKS:
        prova = storage.get_prova(slug)
        if not prova:
            print(f"FALHA  {desc}: prova '{slug}' não encontrada")
            fails += 1
            continue
        ev = evaluate(prova, _pilot(igc))
        got = getter(ev)
        ok = got == expected
        shown_got = _fmt(got) if "SP→FP" in desc else got
        shown_exp = _fmt(expected) if "SP→FP" in desc else expected
        print(f"{'OK   ' if ok else 'FALHA'}  {desc}: obtido={shown_got} esperado={shown_exp}")
        if not ok:
            fails += 1
    if not check_n3():
        fails += 1
    print("-" * 50)
    if fails:
        print(f"REGRESSÃO: {fails} checagem(ns) falharam.")
        return 1
    print("Baseline OK — invariantes geométricos preservados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
