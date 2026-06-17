"""Fachada do estado de pilotos/tracks por Sala.

Delega ao repositório escolhido por `APURADOR_BACKEND` (ver apurador/repo/):
  - backend "files":  estado EM MEMÓRIA (some ao reiniciar) — histórico.
  - backend "sqlite": estado em disco (sobrevive a restart).
Assinaturas preservadas — as rotas não mudam.
"""
from __future__ import annotations
from typing import List
from .core.models import Pilot
from . import repo


def add_pilot(slug: str, pilot: Pilot) -> None:
    """Adiciona/atualiza por BIB (dedupe: substitui se a data for >=)."""
    repo.get().add_pilot(slug, pilot)


def pilots(slug: str) -> List[Pilot]:
    return repo.get().pilots(slug)


def remove_pilot(slug: str, bib: str) -> None:
    repo.get().remove_pilot(slug, bib)


def set_declared(slug: str, bib: str, tg_name: str, sec_utc) -> None:
    repo.get().set_declared(slug, bib, tg_name, sec_utc)


def reset(slug: str | None = None) -> None:
    repo.get().reset(slug)
