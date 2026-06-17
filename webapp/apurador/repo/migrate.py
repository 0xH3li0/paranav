"""Migrações.

1) `migrate(db)` — popula o SQLite a partir dos arquivos JSON (provas, mapas,
   competições). Tracks de pilotos NÃO migram (efêmeros por evento).
2) `split_maps()` — divide cada prova (geometria inline, legado) em um **Mapa**
   (geometria) + **Prova** (scoring, referenciando o mapa via map_slug). Idempotente.

Uso:
    cd webapp
    python3 -m apurador.repo.migrate --split          # provas -> mapa + prova (arquivos)
    python3 -m apurador.repo.migrate [db.sqlite]      # arquivos -> sqlite
"""
from __future__ import annotations
import os
import sys

from .files_backend import FilesRepo
from .sqlite_backend import SqliteRepo
from ..core.models import Mapa


def migrate(db_path: str) -> None:
    src = FilesRepo()
    dst = SqliteRepo(db_path)
    mapas = src.list_mapas()
    for m in mapas:
        dst.save_mapa(m)
    provas = src.list_provas()
    for p in provas:
        dst.save_prova(p)
    comps = [c for c in src.list_competicoes() if c["slug"] != "geral"]
    for c in comps:
        dst.save_competicao(c["slug"], c["name"], c["salas"])
    print(f"Migrado para {db_path}: {len(mapas)} mapa(s), {len(provas)} prova(s), {len(comps)} competição(ões).")


def split_maps() -> None:
    """Cada prova com geometria inline vira Mapa (geometria) + Prova (scoring+map_slug)."""
    repo = FilesRepo()
    n = 0
    for prova in repo.list_provas():
        if prova.map_slug:
            print(f"  pulando {prova.slug} (já tem map_slug={prova.map_slug})")
            continue
        if not prova.points:
            print(f"  pulando {prova.slug} (sem geometria)")
            continue
        mapa = Mapa(name=prova.name, slug=prova.slug, scale=prova.scale,
                    teto=prova.teto, altura_min=prova.altura_min,
                    frame=prova.frame, areas=prova.areas, route=prova.route,
                    landings=prova.landings, points=prova.points)
        repo.save_mapa(mapa)
        prova.map_slug = mapa.slug
        repo.save_prova(prova)   # to_dict() omite geometria quando há map_slug
        n += 1
        print(f"  {prova.slug}: mapa criado ({len(mapa.points)} pts) + prova → map_slug={mapa.slug}")
    print(f"split_maps: {n} prova(s) dividida(s).")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--split":
        split_maps()
    else:
        db = sys.argv[1] if len(sys.argv) > 1 else (
            os.environ.get("APURADOR_DB") or
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "data", "aeronav.db"))
        migrate(db)
