"""Apurador de Navegação — app Flask (réplica da stack do paradigma).

Flask + Jinja2 + Bootstrap + Leaflet. Estado em memória + provas em arquivos JSON.
"""
from __future__ import annotations
import os
from flask import Flask

from .core.timefmt import clock, dur, km, one


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("APURADOR_SECRET", "dev-secret-troque-em-producao")
    # credenciais do organizador (em produção: variáveis de ambiente / banco)
    app.config["ORG_EMAIL"] = os.environ.get("APURADOR_EMAIL", "admin@apurador.local")
    app.config["ORG_PASSWORD"] = os.environ.get("APURADOR_PASSWORD", "admin")
    app.config["PILOT_PIN"] = os.environ.get("APURADOR_PIN", "")  # vazio = qualquer PIN aceito (dev)
    # marca do produto (troque em um lugar só, ou via env APURADOR_BRAND)
    app.config["BRAND"] = os.environ.get("APURADOR_BRAND", "Aeronav")
    app.config["TAGLINE"] = os.environ.get("APURADOR_TAGLINE", "Apuração de navegação · Paramotor")
    # endurecimento de sessão em produção (atrás de HTTPS): APURADOR_SECURE=1
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if os.environ.get("APURADOR_SECURE") == "1":
        app.config["SESSION_COOKIE_SECURE"] = True
    # limite de upload (IGCs são pequenos; protege contra payload abusivo)
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("APURADOR_MAX_UPLOAD_MB", "32")) * 1024 * 1024

    @app.context_processor
    def _brand():
        return {"brand": app.config["BRAND"], "tagline": app.config["TAGLINE"]}

    # filtros Jinja para formatação
    app.jinja_env.filters["clock"] = clock
    app.jinja_env.filters["dur"] = dur
    app.jinja_env.filters["km"] = km
    app.jinja_env.filters["one"] = one

    # header de aplicação (como o paradigma: x-apurador-aita)
    @app.after_request
    def _hdr(resp):
        resp.headers["X-Apurador-Nav"] = "yes"
        return resp

    from .routes.main import bp as main_bp
    from .routes import pdf as _pdf_routes  # noqa: F401 — anexa as rotas de PDF ao blueprint main
    from .routes.api import bp as api_bp
    from .routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)
    return app
