"""Autenticação do organizador (sessão por cookie, como o paradigma)."""
from __future__ import annotations
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not session.get("org"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*a, **k)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        pwd = request.form.get("password", "")
        if email == current_app.config["ORG_EMAIL"] and pwd == current_app.config["ORG_PASSWORD"]:
            session["org"] = email
            return redirect(request.args.get("next") or url_for("main.viewer"))
        flash("E-mail ou senha inválidos.")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.pop("org", None)
    return redirect(url_for("auth.login"))
