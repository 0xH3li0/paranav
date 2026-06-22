"""Backend de ARQUIVOS — provas em JSON (data/provas) + pilotos EM MEMÓRIA.

É a lógica histórica de `storage.py` + `state.py`, agora atrás da interface Repo.
Risco zero: mesmo I/O e mesma estrutura de estado de antes.
"""
from __future__ import annotations
import json
import os
from typing import Dict, List, Optional
from ..core.models import Prova, Pilot, Mapa, hydrate
from ..core.slugs import slug_from_filename

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(_BASE, "data", "provas")
COMP_DIR = os.path.join(_BASE, "data", "competicoes")
MAPAS_DIR = os.path.join(_BASE, "data", "mapas")


class FilesRepo:
    def __init__(self) -> None:
        # slug da sala -> {bib -> Pilot} (em memória, some ao reiniciar)
        self._pilots: Dict[str, Dict[str, Pilot]] = {}

    # ---- provas ----
    def list_provas(self) -> List[Prova]:
        out: List[Prova] = []
        if not os.path.isdir(DATA_DIR):
            return out
        for fn in sorted(os.listdir(DATA_DIR)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(DATA_DIR, fn), encoding="utf-8") as f:
                    d = json.load(f)
                prova = Prova.from_dict(d)
                if not prova.slug:
                    prova.slug = slug_from_filename(fn, "prova-")
                out.append(self._hydrate(prova))
            except Exception as e:  # noqa
                print(f"[storage] erro lendo {fn}: {e}")
        return out

    def _hydrate(self, prova: Optional[Prova]) -> Optional[Prova]:
        if prova and prova.map_slug:
            mp = self.get_mapa(prova.map_slug)
            if mp:
                hydrate(prova, mp)
        return prova

    def provas_by_slug(self) -> Dict[str, Prova]:
        return {p.slug: p for p in self.list_provas()}

    def get_prova(self, slug: str) -> Optional[Prova]:
        return self.provas_by_slug().get(slug)

    def _file_for_slug(self, slug: str) -> str:
        if os.path.isdir(DATA_DIR):
            for fn in os.listdir(DATA_DIR):
                if fn.endswith(".json") and slug_from_filename(fn, "prova-") == slug:
                    return os.path.join(DATA_DIR, fn)
        return os.path.join(DATA_DIR, f"prova-{slug}.json")

    def save_prova(self, prova: Prova) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(self._file_for_slug(prova.slug), "w", encoding="utf-8") as f:
            json.dump(prova.to_dict(), f, ensure_ascii=False, indent=2)

    # ---- competições ----
    def list_competicoes(self) -> List[dict]:
        out: List[dict] = []
        if os.path.isdir(COMP_DIR):
            for fn in sorted(os.listdir(COMP_DIR)):
                if not fn.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(COMP_DIR, fn), encoding="utf-8") as f:
                        d = json.load(f)
                    out.append({"name": d.get("name", fn), "slug": d.get("slug", fn[:-5]),
                                "salas": d.get("salas", [])})
                except Exception as e:  # noqa
                    print(f"[storage] erro lendo competição {fn}: {e}")
        if not out:
            out.append({"name": "Geral", "slug": "geral",
                        "salas": [p.slug for p in self.list_provas()]})
        return out

    def get_competicao(self, slug: str) -> Optional[dict]:
        return next((c for c in self.list_competicoes() if c["slug"] == slug), None)

    # ---- mapas (geometria) ----
    def list_mapas(self) -> List[Mapa]:
        out: List[Mapa] = []
        if not os.path.isdir(MAPAS_DIR):
            return out
        for fn in sorted(os.listdir(MAPAS_DIR)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(MAPAS_DIR, fn), encoding="utf-8") as f:
                    mp = Mapa.from_dict(json.load(f))
                if not mp.slug:
                    mp.slug = slug_from_filename(fn, "mapa-")
                out.append(mp)
            except Exception as e:  # noqa
                print(f"[storage] erro lendo mapa {fn}: {e}")
        return out

    def get_mapa(self, slug: str) -> Optional[Mapa]:
        return next((m for m in self.list_mapas() if m.slug == slug), None)

    def save_mapa(self, mapa: Mapa) -> None:
        os.makedirs(MAPAS_DIR, exist_ok=True)
        path = os.path.join(MAPAS_DIR, f"mapa-{mapa.slug}.json")
        if os.path.isdir(MAPAS_DIR):
            for fn in os.listdir(MAPAS_DIR):
                if fn.endswith(".json") and slug_from_filename(fn, "mapa-") == mapa.slug:
                    path = os.path.join(MAPAS_DIR, fn)
                    break
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mapa.to_dict(), f, ensure_ascii=False, indent=2)

    def delete_mapa(self, slug: str) -> None:
        if not os.path.isdir(MAPAS_DIR):
            return
        for fn in os.listdir(MAPAS_DIR):
            if fn.endswith(".json") and slug_from_filename(fn, "mapa-") == slug:
                os.remove(os.path.join(MAPAS_DIR, fn))

    # ---- pilotos / tracks (em memória) ----
    def add_pilot(self, slug: str, pilot: Pilot) -> None:
        room = self._pilots.setdefault(slug, {})
        ex = room.get(pilot.bib)
        if ex is None or not ex.date or not pilot.date or pilot.date >= ex.date:
            room[pilot.bib] = pilot

    def pilots(self, slug: str) -> List[Pilot]:
        return list(self._pilots.get(slug, {}).values())

    def remove_pilot(self, slug: str, bib: str) -> None:
        self._pilots.get(slug, {}).pop(bib, None)

    def set_declared(self, slug: str, bib: str, tg_name: str, sec_utc) -> None:
        p = self._pilots.get(slug, {}).get(bib)
        if not p:
            return
        if sec_utc is None:
            p.decl.pop(tg_name, None)
        else:
            p.decl[tg_name] = sec_utc

    def reset(self, slug: Optional[str] = None) -> None:
        if slug is None:
            self._pilots.clear()
        else:
            self._pilots.pop(slug, None)
