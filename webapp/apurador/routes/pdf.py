"""Rotas de geração/download de PDF: mapa A3, folha A4 de pontos, relatório de voo.

Anexam-se ao MESMO blueprint `main` (importado de `.main`), então os endpoints
continuam `main.<func>` — `url_for(...)` e os templates NÃO mudam. Os geradores
pesados (qgispdf/pointspdf/report) são importados de forma LAZY dentro de cada
rota, para o app subir mesmo sem reportlab/QGIS instalados (degrada com flash).
"""
from __future__ import annotations
import os
import tempfile
from io import BytesIO
from flask import (request, redirect, url_for, current_app, flash, abort,
                   send_file)
from .. import storage, state
from .auth import login_required
from .main import bp


# ---- mapa (geometria pura) ----
@bp.route("/mapas/<slug>/mapa.pdf")
@login_required
def mapa_pdf_only(slug):
    mapa = storage.get_mapa(slug)
    if not mapa:
        abort(404)
    base = request.args.get("base")          # permite exportar em base diferente da salva
    if base in ("esri", "topo", "osm"):
        mapa.base = base
    try:
        from ..qgispdf import render_map_pdf_auto
        buf = BytesIO(render_map_pdf_auto(mapa, current_app.config["BRAND"]))
        buf.seek(0)
    except Exception as e:  # noqa
        flash(f"PDF indisponível ({e}).")
        return redirect(url_for("main.mapa_editor", slug=slug))
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"mapa-{slug}.pdf")


@bp.route("/mapas/<slug>/pontos.pdf")
@login_required
def mapa_pontos_pdf(slug):
    mapa = storage.get_mapa(slug)
    if not mapa:
        abort(404)
    try:
        from ..pointspdf import render_points_pdf
        buf = BytesIO()
        render_points_pdf(mapa, current_app.config["BRAND"], buf)
        buf.seek(0)
    except Exception as e:  # noqa
        flash(f"Imagens indisponíveis ({e}).")
        return redirect(url_for("main.mapa_editor", slug=slug))
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"pontos-{slug}.pdf")


# ---- prova (mapa hidratado) ----
@bp.route("/prova/<slug>/mapa.pdf")
@login_required
def mapa_pdf(slug):
    """Mapa A3 da prova em escala fiel (B3)."""
    prova = storage.get_prova(slug)
    if not prova:
        abort(404)
    try:
        from ..qgispdf import render_map_pdf_auto
        buf = BytesIO(render_map_pdf_auto(prova, current_app.config["BRAND"]))
        buf.seek(0)
    except Exception as e:  # noqa
        flash(f"Geração do mapa PDF indisponível ({e}).")
        return redirect(url_for("main.prova_config", slug=slug))
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"mapa-{slug}.pdf")


@bp.route("/prova/<slug>/pontos.pdf")
@login_required
def pontos_pdf(slug):
    """Folha A4 com recortes de satélite de cada ponto (B4)."""
    prova = storage.get_prova(slug)
    if not prova:
        abort(404)
    try:
        from ..pointspdf import render_points_pdf
        buf = BytesIO()
        render_points_pdf(prova, current_app.config["BRAND"], buf)
        buf.seek(0)
    except Exception as e:  # noqa
        flash(f"Geração das imagens indisponível ({e}). Requer staticmap/Pillow e rede.")
        return redirect(url_for("main.prova_config", slug=slug))
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"pontos-{slug}.pdf")


# ---- relatório de voo por piloto ----
@bp.route("/relatorio/<slug>/<bib>.pdf")
@login_required
def relatorio_pdf(slug, bib):
    prova = storage.get_prova(slug)
    pilot = next((p for p in state.pilots(slug) if p.bib == bib), None)
    if not prova or not pilot:
        abort(404)
    try:
        from .. import report
    except Exception:
        flash("Geração de PDF indisponível (instale reportlab e staticmap).")
        return redirect(url_for("main.relatorio", slug=slug, bib=bib))
    out = os.path.join(tempfile.gettempdir(), f"relatorio-{slug}-{bib}.pdf")
    report.render_report(prova, pilot, out)
    nome = f"relatorio-{pilot.name.replace(' ', '-')}-{slug}.pdf"
    return send_file(out, as_attachment=True, download_name=nome, mimetype="application/pdf")
