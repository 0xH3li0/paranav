"""Fachada de persistência de PROVAS / MAPAS / COMPETIÇÕES.

Delega ao repositório escolhido por `APURADOR_BACKEND` (ver apurador/repo/).
Assinaturas preservadas — as rotas não mudam. Default = backend de arquivos.

As provas já vêm HIDRATADAS com a geometria do mapa (`map_slug`) pelo repo,
para que scoring/mapdata/PDFs continuem recebendo uma Prova completa.
"""
from __future__ import annotations
from typing import Dict, List
from .core.models import Prova, Mapa
from . import repo


def list_provas() -> List[Prova]:
    return repo.get().list_provas()


def provas_by_slug() -> Dict[str, Prova]:
    return repo.get().provas_by_slug()


def get_prova(slug: str) -> Prova | None:
    return repo.get().get_prova(slug)


def save_prova(prova: Prova) -> None:
    repo.get().save_prova(prova)


# ---- mapas ----
def list_mapas() -> List[Mapa]:
    return repo.get().list_mapas()


def get_mapa(slug: str) -> Mapa | None:
    return repo.get().get_mapa(slug)


def save_mapa(mapa: Mapa) -> None:
    repo.get().save_mapa(mapa)


def delete_mapa(slug: str) -> None:
    repo.get().delete_mapa(slug)


def list_competicoes() -> List[dict]:
    return repo.get().list_competicoes()


def get_competicao(slug: str) -> dict | None:
    return repo.get().get_competicao(slug)
