"""Helpers de slug (string puro, sem I/O) — usados por rotas e backends.

Dois conceitos DISTINTOS (por isso duas funções):
  - slugify(name, fallback):       NOME livre   -> slug minúsculo (a-z0-9 + hífens).
  - slug_from_filename(fn, prefix): nome de ARQUIVO -> slug (tira extensão e prefixo).
"""
from __future__ import annotations
import os
import re
import uuid


def slugify(name: str, fallback: str = "item") -> str:
    """Converte um nome livre em slug minúsculo (a-z0-9 separados por hífen).

    Vazio nunca colapsa em string vazia: vira '<fallback>-<uid>'.
    """
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return base or f"{fallback}-{uuid.uuid4().hex[:6]}"


def slug_from_filename(fn: str, prefix: str = "") -> str:
    """Deriva o slug do nome do arquivo: tira a extensão e o `prefix` (ex.: 'prova-')."""
    return os.path.splitext(fn)[0].replace(prefix, "").lower()
