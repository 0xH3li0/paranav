"""API JSON — espelha o paradigma (/api/sala/<slug>/mapdata, /api/state/reset)."""
from __future__ import annotations
from flask import Blueprint, jsonify, request, current_app
from .. import storage, state

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/sala/<slug>/mapdata")
def mapdata(slug):
    prova = storage.get_prova(slug)
    if not prova:
        return jsonify({"ok": False, "has_prova": False, "wpts": [], "airspaces": [],
                        "center": {"lat": -22.88, "lon": -42.6}})
    return jsonify(prova.mapdata())


@bp.route("/mapa/<slug>/mapdata")
def mapa_mapdata(slug):
    mapa = storage.get_mapa(slug)
    if not mapa:
        return jsonify({"ok": False, "has_map": False, "wpts": [], "areas": [],
                        "center": {"lat": -22.88, "lon": -42.6}})
    return jsonify(mapa.mapdata())


@bp.route("/sala/<slug>/trackdata")
def trackdata(slug):
    """Trajetos dos pilotos da Sala (para o viewer). Aberto p/ o organizador."""
    out = []
    for p in state.pilots(slug):
        out.append({"bib": p.bib, "name": p.name,
                    "fixes": [[f.lat, f.lon] for f in p.fixes]})
    return jsonify({"ok": True, "tracks": out})


@bp.route("/state/reset", methods=["POST"])
def reset():
    slug = (request.json or {}).get("slug") if request.is_json else request.form.get("slug")
    state.reset(slug)
    return jsonify({"ok": True})
