"""Backend SQLite — provas + competições + pilotos/tracks em disco persistente.

Sobrevive a restart (resolve B6/B7). Sem dependência nova (stdlib `sqlite3`).
Os fixes do IGC (muitos) são guardados comprimidos: gzip(json([[t,lat,lon,alt],...])).
Provas guardam exatamente `Prova.to_dict()` como JSON (payload), sem normalizar
waypoints — o scoring consome a Prova inteira.
"""
from __future__ import annotations
import gzip
import json
import os
import sqlite3
import threading
from typing import Dict, List, Optional
from ..core.models import Prova, Pilot, Mapa, hydrate
from ..core.igc import Fix

SCHEMA = """
CREATE TABLE IF NOT EXISTS provas (
  slug    TEXT PRIMARY KEY,
  type    TEXT,
  name    TEXT,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mapas (
  slug    TEXT PRIMARY KEY,
  name    TEXT,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS competicoes (
  slug  TEXT PRIMARY KEY,
  name  TEXT,
  salas TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS pilots (
  sala_slug TEXT NOT NULL,
  bib       TEXT NOT NULL,
  name      TEXT NOT NULL DEFAULT '',
  date      TEXT NOT NULL DEFAULT '',
  fixes_gz  BLOB NOT NULL,
  decl      TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (sala_slug, bib)
);
"""


def _pack(fixes) -> bytes:
    return gzip.compress(json.dumps([[f.t, f.lat, f.lon, f.alt] for f in fixes]).encode())


def _unpack(blob: bytes):
    return [Fix(t=r[0], lat=r[1], lon=r[2], alt=r[3]) for r in json.loads(gzip.decompress(blob))]


class SqliteRepo:
    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db = db_path
        self._lock = threading.Lock()
        self._cx = sqlite3.connect(db_path, check_same_thread=False)
        self._cx.executescript(SCHEMA)
        self._cx.commit()

    # ---- provas ----
    def _hydrate(self, prova: Optional[Prova]) -> Optional[Prova]:
        if prova and prova.map_slug:
            mp = self.get_mapa(prova.map_slug)
            if mp:
                hydrate(prova, mp)
        return prova

    def list_provas(self) -> List[Prova]:
        out: List[Prova] = []
        for (payload,) in self._cx.execute("SELECT payload FROM provas ORDER BY slug"):
            try:
                out.append(self._hydrate(Prova.from_dict(json.loads(payload))))
            except Exception as e:  # noqa
                print(f"[sqlite] erro lendo prova: {e}")
        return out

    def provas_by_slug(self) -> Dict[str, Prova]:
        return {p.slug: p for p in self.list_provas()}

    def get_prova(self, slug: str) -> Optional[Prova]:
        row = self._cx.execute("SELECT payload FROM provas WHERE slug=?", (slug,)).fetchone()
        return self._hydrate(Prova.from_dict(json.loads(row[0]))) if row else None

    def save_prova(self, prova: Prova) -> None:
        with self._lock:
            self._cx.execute(
                "INSERT INTO provas(slug,type,name,payload) VALUES(?,?,?,?) "
                "ON CONFLICT(slug) DO UPDATE SET type=excluded.type, name=excluded.name, payload=excluded.payload",
                (prova.slug, prova.type, prova.name,
                 json.dumps(prova.to_dict(), ensure_ascii=False)))
            self._cx.commit()

    # ---- competições ----
    def list_competicoes(self) -> List[dict]:
        out = [{"slug": s, "name": n, "salas": json.loads(sa or "[]")}
               for (s, n, sa) in self._cx.execute("SELECT slug,name,salas FROM competicoes ORDER BY slug")]
        if not out:
            out.append({"name": "Geral", "slug": "geral",
                        "salas": [p.slug for p in self.list_provas()]})
        return out

    def get_competicao(self, slug: str) -> Optional[dict]:
        return next((c for c in self.list_competicoes() if c["slug"] == slug), None)

    def save_competicao(self, slug: str, name: str, salas: List[str]) -> None:
        with self._lock:
            self._cx.execute(
                "INSERT INTO competicoes(slug,name,salas) VALUES(?,?,?) "
                "ON CONFLICT(slug) DO UPDATE SET name=excluded.name, salas=excluded.salas",
                (slug, name, json.dumps(salas)))
            self._cx.commit()

    # ---- mapas (geometria) ----
    def list_mapas(self) -> List[Mapa]:
        out: List[Mapa] = []
        for (payload,) in self._cx.execute("SELECT payload FROM mapas ORDER BY slug"):
            try:
                out.append(Mapa.from_dict(json.loads(payload)))
            except Exception as e:  # noqa
                print(f"[sqlite] erro lendo mapa: {e}")
        return out

    def get_mapa(self, slug: str) -> Optional[Mapa]:
        row = self._cx.execute("SELECT payload FROM mapas WHERE slug=?", (slug,)).fetchone()
        return Mapa.from_dict(json.loads(row[0])) if row else None

    def save_mapa(self, mapa: Mapa) -> None:
        with self._lock:
            self._cx.execute(
                "INSERT INTO mapas(slug,name,payload) VALUES(?,?,?) "
                "ON CONFLICT(slug) DO UPDATE SET name=excluded.name, payload=excluded.payload",
                (mapa.slug, mapa.name, json.dumps(mapa.to_dict(), ensure_ascii=False)))
            self._cx.commit()

    def delete_mapa(self, slug: str) -> None:
        with self._lock:
            self._cx.execute("DELETE FROM mapas WHERE slug=?", (slug,))
            self._cx.commit()

    # ---- pilotos / tracks ----
    def add_pilot(self, slug: str, pilot: Pilot) -> None:
        with self._lock:
            # dedupe por data: substitui se a do novo for vazia, ou a existente vazia, ou >=
            self._cx.execute(
                "INSERT INTO pilots(sala_slug,bib,name,date,fixes_gz,decl) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(sala_slug,bib) DO UPDATE SET "
                "  name=excluded.name, date=excluded.date, fixes_gz=excluded.fixes_gz, decl=excluded.decl "
                "WHERE excluded.date='' OR pilots.date='' OR excluded.date>=pilots.date",
                (slug, pilot.bib, pilot.name, pilot.date or "",
                 _pack(pilot.fixes), json.dumps(pilot.decl or {})))
            self._cx.commit()

    def pilots(self, slug: str) -> List[Pilot]:
        rows = self._cx.execute(
            "SELECT bib,name,date,fixes_gz,decl FROM pilots WHERE sala_slug=? ORDER BY bib", (slug,)).fetchall()
        out = []
        for bib, name, date, blob, decl in rows:
            out.append(Pilot(bib=bib, name=name, date=date or "",
                             fixes=_unpack(blob), decl=json.loads(decl or "{}")))
        return out

    def remove_pilot(self, slug: str, bib: str) -> None:
        with self._lock:
            self._cx.execute("DELETE FROM pilots WHERE sala_slug=? AND bib=?", (slug, bib))
            self._cx.commit()

    def set_declared(self, slug: str, bib: str, tg_name: str, sec_utc) -> None:
        with self._lock:
            row = self._cx.execute(
                "SELECT decl FROM pilots WHERE sala_slug=? AND bib=?", (slug, bib)).fetchone()
            if not row:
                return
            decl = json.loads(row[0] or "{}")
            if sec_utc is None:
                decl.pop(tg_name, None)
            else:
                decl[tg_name] = sec_utc
            self._cx.execute("UPDATE pilots SET decl=? WHERE sala_slug=? AND bib=?",
                             (json.dumps(decl), slug, bib))
            self._cx.commit()

    def reset(self, slug: Optional[str] = None) -> None:
        with self._lock:
            if slug is None:
                self._cx.execute("DELETE FROM pilots")
            else:
                self._cx.execute("DELETE FROM pilots WHERE sala_slug=?", (slug,))
            self._cx.commit()
