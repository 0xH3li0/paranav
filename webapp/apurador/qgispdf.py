"""Ponte Flask → render do A3 via QGIS (server-side).

PyQGIS vive no **python do sistema**, não no venv do app. Então o render roda como
**subprocesso** sob `xvfb-run` chamando `apurador/qgis_render.py`. Habilitado por env
`APURADOR_QGIS=1` (default off → dev/mac cai no fallback reportlab `mappdf.py`).
"""
import os
import json
import subprocess
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_RENDER = os.path.join(_HERE, "qgis_render.py")
# python do SISTEMA (com PyQGIS) — NÃO o do venv. Override por env se preciso.
_SYS_PY = os.environ.get("APURADOR_QGIS_PYTHON", "/usr/bin/python3")
_TIMEOUT = int(os.environ.get("APURADOR_QGIS_TIMEOUT", "150"))


def qgis_enabled() -> bool:
    return str(os.environ.get("APURADOR_QGIS", "")).lower() in ("1", "true", "yes", "on")


def render_map_pdf_qgis(obj, brand: str) -> bytes:
    """Renderiza o A3 do mapa/prova `obj` via QGIS e devolve os bytes do PDF.

    `obj` é um `Mapa` ou uma `Prova` (ambos expõem `mapdata()`). Levanta exceção em
    falha — o chamador faz fallback para `mappdf.render_map_pdf`.
    """
    data = obj.mapdata()
    # campos de evento que `mapdata()` não inclui (usados na tarja do A3)
    data["brand"] = brand
    data["type"] = (getattr(obj, "type", "") or "")
    data["titulo"] = (getattr(obj, "titulo", "") or "")
    data["declinacao"] = (getattr(obj, "declinacao", "") or data.get("declinacao", ""))

    with tempfile.TemporaryDirectory() as td:
        inp = os.path.join(td, "in.json")
        outp = os.path.join(td, "out.pdf")
        with open(inp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        cmd = ["xvfb-run", "-a", _SYS_PY, _RENDER, inp, outp]
        r = subprocess.run(cmd, capture_output=True, timeout=_TIMEOUT)
        if r.returncode != 0 or not os.path.exists(outp):
            err = (r.stderr or b"").decode("utf-8", "ignore")[-600:]
            raise RuntimeError("render QGIS falhou (rc=%s): %s" % (r.returncode, err))
        with open(outp, "rb") as fh:
            return fh.read()


def render_map_pdf_auto(obj, brand: str) -> bytes:
    """A3 do mapa/prova: tenta o QGIS (se habilitado), cai no reportlab (`mappdf`)
    em falha ou no dev/mac. Devolve bytes do PDF."""
    if qgis_enabled():
        try:
            return render_map_pdf_qgis(obj, brand)
        except Exception:
            pass  # degrada para o gerador reportlab
    from io import BytesIO
    from .mappdf import render_map_pdf
    buf = BytesIO()
    render_map_pdf(obj, brand, buf)
    return buf.getvalue()
