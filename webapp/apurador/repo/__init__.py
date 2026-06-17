"""Camada de repositório PLUGÁVEL por ambiente.

Seleção por env `APURADOR_BACKEND`:
  - "files"  (default): provas em JSON (data/provas) + estado de pilotos EM MEMÓRIA.
               Idêntico ao comportamento histórico — usado em dev e na validação
               sagrada (igcs/ + relatorios-paradigmas).
  - "sqlite": provas + competições + pilotos/tracks em SQLite (disco persistente).
               Sobrevive a restart (resolve B6); usado em produção (VPS).

As fachadas finas `storage.py` e `state.py` delegam para o repo escolhido aqui,
preservando TODAS as assinaturas — nenhuma rota muda.
"""
from __future__ import annotations
import os

_repo = None


def get():
    """Retorna o repositório singleton (escolhido por APURADOR_BACKEND)."""
    global _repo
    if _repo is None:
        backend = (os.environ.get("APURADOR_BACKEND") or "files").lower()
        if backend == "sqlite":
            from .sqlite_backend import SqliteRepo
            db = os.environ.get("APURADOR_DB") or os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "aeronav.db")
            _repo = SqliteRepo(db)
        else:
            from .files_backend import FilesRepo
            _repo = FilesRepo()
    return _repo


def reset_singleton():
    """Descarta o singleton (uso em testes)."""
    global _repo
    _repo = None
