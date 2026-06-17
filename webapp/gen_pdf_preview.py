import os
os.environ.setdefault("APURADOR_BACKEND", "files")
from apurador import create_app
from apurador import storage
from apurador.mappdf import render_map_pdf
from apurador.pointspdf import render_points_pdf

app = create_app()
with app.app_context():
    mapas = storage.list_mapas()
    obj = mapas[0] if mapas else storage.list_provas()[0]
    print("objeto:", getattr(obj, "name", "?"), "| pontos:", len(obj.points),
          "| frame:", getattr(obj, "frame", None), "| base:", getattr(obj, "base", "?"))
    render_map_pdf(obj, "Aeronav", "/tmp/a3preview.pdf")
    render_points_pdf(obj, "Aeronav", "/tmp/pts_preview.pdf")
    print("OK /tmp/a3preview.pdf", os.path.getsize("/tmp/a3preview.pdf"), "bytes")
    print("OK /tmp/pts_preview.pdf", os.path.getsize("/tmp/pts_preview.pdf"), "bytes")
