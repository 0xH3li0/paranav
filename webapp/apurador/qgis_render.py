#!/usr/bin/env python3
"""Render do Mapa A3 no estilo AITA via QGIS (Print Layout) — server-side, headless.

Roda no **python do sistema** (que tem PyQGIS), NÃO no venv do app, e sob `xvfb-run`.
É invocado como subprocesso por `apurador/qgispdf.py`:

    xvfb-run -a python3 apurador/qgis_render.py entrada.json saida.pdf

A `entrada.json` é o dict de `Mapa.mapdata()` (core/models.py) acrescido de campos de
evento (`declinacao`, `titulo`, `brand`, `type`). A geometria do app é desenhada em
EPSG:3857 (Web Mercator) — obrigatório para o basemap XYZ pintar e a escala sair fiel.

Espelha os mapas N1/N2 da AITA (que são saídas de QGIS Print Layout):
basemap topográfico, pontos em círculo vermelho rotulados, **HG não impresso**, rota
ligando os waypoints (N2) ou corredor (N3), A3 retrato/paisagem, 1:50000 fiel,
folha rotacionável (recorte diagonal), rosa-dos-ventos, barra de escala e tarja.
"""
import os
import sys
import json

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsRasterLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemScaleBar, QgsLayoutItemLabel,
    QgsLayoutItemPicture, QgsLayoutSize, QgsLayoutPoint, QgsLayoutExporter,
    QgsUnitTypes, QgsMarkerSymbol, QgsLineSymbol, QgsFillSymbol,
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings,
    QgsRectangle, QgsLayoutItem, QgsLayoutItemShape,
)
from qgis.PyQt.QtGui import QFont, QColor

# bases de tiles suportadas (mesma intenção de pdfcommon.TILE_URLS; aqui é
# duplicado de propósito: este módulo roda no python do SISTEMA, fora do venv)
_BASES = {
    "topo": ("https://tile.opentopomap.org/{z}/{x}/{y}.png", 17),
    "esri": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", 19),
    "osm":  ("https://tile.openstreetmap.org/{z}/{x}/{y}.png", 19),
}
# SVGs de rosa-dos-ventos que costumam existir no pacote do QGIS (com fallback)
_NORTH_SVGS = [
    "/usr/share/qgis/svg/arrows/NorthArrow_02.svg",
    "/usr/share/qgis/svg/wind_roses/WindRose_01.svg",
    "/usr/share/qgis/svg/arrows/NorthArrow_04.svg",
]
CRS3857 = "EPSG:3857"
CRS4326 = "EPSG:4326"


def _denom(scale):
    try:
        return int(str(scale).split(":")[1])
    except (IndexError, ValueError):
        return 50000


def _add_points_layer(project, wpts, name, types):
    """Camada de pontos em memória (EPSG:4326) filtrando por `types`."""
    sel = [p for p in wpts if p.get("type") in types]
    vl = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string&field=type:string", name, "memory")
    dp = vl.dataProvider()
    for p in sel:
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(p["lon"], p["lat"])))
        f.setAttributes([p.get("name", ""), p.get("type", "")])
        dp.addFeature(f)
    vl.updateExtents()
    project.addMapLayer(vl, False)
    return vl, sel


def _label(vl, size=8, color=None):
    st = QgsPalLayerSettings()
    st.fieldName = "name"
    tf = QgsTextFormat()
    tf.setFont(QFont("Sans", size))
    tf.setSize(size)
    tf.setColor(color or QColor(20, 20, 20))
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(0.8)
    buf.setColor(QColor(255, 255, 255))
    tf.setBuffer(buf)
    st.setFormat(tf)
    vl.setLabeling(QgsVectorLayerSimpleLabeling(st))
    vl.setLabelsEnabled(True)


def render(payload, out_pdf):
    QgsApplication.setPrefixPath("/usr", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    try:
        project = QgsProject.instance()
        project.setCrs(QgsCoordinateReferenceSystem(CRS3857))

        wpts = payload.get("wpts", [])
        ptype = (payload.get("type") or "").lower()
        order = []  # camadas do fundo p/ cima

        # ---- basemap (best-effort) ----
        url, zmax = _BASES.get(payload.get("base") or "topo", _BASES["topo"])
        rl = QgsRasterLayer("type=xyz&url=%s&zmax=%d&zmin=0" % (url, zmax), "base", "wms")
        base_ok = rl.isValid()
        if base_ok:
            project.addMapLayer(rl, False)
            order.append(rl)

        # ---- áreas (proibida=vermelho / atenção=amarelo) ----
        areas = payload.get("areas") or []
        if areas:
            al = QgsVectorLayer("Polygon?crs=EPSG:4326&field=kind:string", "areas", "memory")
            adp = al.dataProvider()
            for a in areas:
                coords = a.get("coords") or []
                if len(coords) < 3:
                    continue
                ring = [QgsPointXY(c[1], c[0]) for c in coords]
                f = QgsFeature()
                f.setGeometry(QgsGeometry.fromPolygonXY([ring]))
                f.setAttributes([a.get("kind", "")])
                adp.addFeature(f)
            al.updateExtents()
            al.renderer().setSymbol(QgsFillSymbol.createSimple({
                "color": "230,40,40,60", "outline_color": "200,30,30,200", "outline_width": "0.4"}))
            project.addMapLayer(al, False)
            order.append(al)

        # ---- rota / corredor ----
        route = payload.get("route") or {}
        wp = [p for p in wpts if p.get("type") in ("SP", "FP", "TP", "TG")]
        declared = any(p.get("type") in ("TG", "HG") for p in wpts) or ptype == "n2"
        if ptype == "n3" and route.get("coords"):
            # corredor N3: a linha central (buffer fica como evolução)
            rl_line = QgsVectorLayer("LineString?crs=EPSG:4326", "rota", "memory")
            lf = QgsFeature()
            lf.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(c[1], c[0]) for c in route["coords"]]))
            rl_line.dataProvider().addFeature(lf)
            rl_line.renderer().setSymbol(QgsLineSymbol.createSimple({"color": "13,166,232,255", "width": "0.6"}))
            project.addMapLayer(rl_line, False)
            order.append(rl_line)
        elif declared and len(wp) >= 2:
            # N2: linha rosa ligando os waypoints reais na ordem do arquivo
            ll = QgsVectorLayer("LineString?crs=EPSG:4326", "rota", "memory")
            lf = QgsFeature()
            lf.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(p["lon"], p["lat"]) for p in wp]))
            ll.dataProvider().addFeature(lf)
            ll.renderer().setSymbol(QgsLineSymbol.createSimple({"color": "255,0,255,255", "width": "1.4"}))
            project.addMapLayer(ll, False)
            order.append(ll)

        # ---- landings (3.A3/3.A5) ----
        landings = payload.get("landings") or []
        if landings:
            dl = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "landings", "memory")
            ddp = dl.dataProvider()
            for d in landings:
                f = QgsFeature()
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(d["lon"], d["lat"])))
                f.setAttributes([d.get("name", "Pouso")])
                ddp.addFeature(f)
            dl.updateExtents()
            dl.renderer().setSymbol(QgsMarkerSymbol.createSimple({
                "name": "square", "color": "26,140,77,255", "outline_color": "255,255,255,255",
                "outline_width": "0.3", "size": "2.4"}))
            project.addMapLayer(dl, False)
            order.append(dl)

        # ---- waypoints reais (AITA NÃO imprime HG) — círculo vermelho + rótulo ----
        vl, sel = _add_points_layer(project, wpts, "waypoints", ("SP", "FP", "TP", "TG"))
        vl.renderer().setSymbol(QgsMarkerSymbol.createSimple({
            "name": "circle", "color": "0,0,0,0",
            "outline_color": "230,20,30,255", "outline_width": "0.7", "size": "4"}))
        # AITA: rótulo magenta no N1, azul no N2
        _label(vl, 9, QColor(204, 13, 140) if ptype == "n1" else QColor(20, 40, 160))
        project.addMapLayer(vl, False)
        order.append(vl)

        # extensão dos dados (4326) p/ centrar o mapa
        ext_layer = vl if sel else (rl if base_ok else vl)
        data_ext = vl.extent() if sel else None

        # ---- layout A3: N2/retrato = tarja inferior | N1/paisagem = coluna lateral esquerda (AITA) ----
        # ⚠️ posições/rotação afinadas contra amostra de produção (QGIS não roda no dev).
        orient = payload.get("orientation", "paisagem")
        pw, ph = (297, 420) if orient == "retrato" else (420, 297)
        landscape = orient != "retrato"
        MM = QgsUnitTypes.LayoutMillimeters
        SBW, BARH = 48.0, 26.0   # largura da coluna lateral (paisagem) / altura da tarja (retrato)
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        layout.pageCollection().page(0).setPageSize(QgsLayoutSize(pw, ph, MM))

        m = QgsLayoutItemMap(layout)
        if landscape:                       # AITA N1: info à esquerda, mapa à direita
            m.attemptMove(QgsLayoutPoint(SBW + 4, 6, MM))
            m.attemptResize(QgsLayoutSize(pw - SBW - 10, ph - 12, MM))
        else:                               # AITA N2: mapa em cima, tarja embaixo
            m.attemptMove(QgsLayoutPoint(6, 6, MM))
            m.attemptResize(QgsLayoutSize(pw - 12, ph - BARH, MM))
        # setLayers espera TOPO->fundo; `order` foi montado fundo->topo, então inverte
        m.setLayers(list(reversed(order)))
        m.setCrs(QgsCoordinateReferenceSystem(CRS3857))
        ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem(CRS4326),
                                    QgsCoordinateReferenceSystem(CRS3857), project)
        if data_ext is not None and not data_ext.isEmpty():
            m.setExtent(ct.transformBoundingBox(data_ext))
        elif payload.get("center"):
            c = payload["center"]
            p3857 = ct.transform(QgsPointXY(c["lon"], c["lat"]))
            m.setExtent(QgsRectangle(p3857.x() - 5000, p3857.y() - 5000, p3857.x() + 5000, p3857.y() + 5000))
        m.setScale(_denom(payload.get("scale")))                 # 1:50000 fiel
        frame = payload.get("frame") or {}
        if frame.get("angle"):
            m.setMapRotation(float(frame["angle"]))              # recorte diagonal
        layout.addLayoutItem(m)

        # ---- coluna lateral branca (paisagem/N1, estilo AITA) — atrás da escala/título/logo ----
        if landscape:
            side = QgsLayoutItemShape(layout)
            try:
                side.setShapeType(QgsLayoutItemShape.Rectangle)
            except Exception:
                pass
            side.attemptMove(QgsLayoutPoint(0, 0, MM))
            side.attemptResize(QgsLayoutSize(SBW, ph, MM))
            side.setSymbol(QgsFillSymbol.createSimple({
                "color": "255,255,255,255", "outline_color": "140,140,140,255", "outline_width": "0.3"}))
            layout.addLayoutItem(side)

        # ---- rosa-dos-ventos (sincronizada com o mapa -> aponta norte real sob rotação) ----
        svg = next((s for s in _NORTH_SVGS if os.path.exists(s)), None)
        if svg:
            na = QgsLayoutItemPicture(layout)
            na.setPicturePath(svg)
            rsz = 20.0 if landscape else 16.0
            na.attemptResize(QgsLayoutSize(rsz, rsz, MM))
            na.attemptMove(QgsLayoutPoint(SBW + 8, 9, MM) if landscape
                           else QgsLayoutPoint(10, 10, MM))
            try:
                na.setLinkedMap(m)
                na.setNorthMode(QgsLayoutItemPicture.GridNorth)
            except Exception:
                pass
            layout.addLayoutItem(na)

        # ---- barra de escala 0-1-2 km ----
        sb = QgsLayoutItemScaleBar(layout)
        sb.setStyle("Single Box")
        sb.setLinkedMap(m)
        sb.setUnits(QgsUnitTypes.DistanceKilometers)
        sb.setUnitLabel("km")
        sb.setUnitsPerSegment(1)
        sb.setNumberOfSegments(2)
        sb.setNumberOfSegmentsLeft(0)
        sb.update()
        sb.attemptMove(QgsLayoutPoint(7, 22, MM) if landscape
                       else QgsLayoutPoint(10, ph - 18, MM))
        layout.addLayoutItem(sb)

        # ---- título + escala + declinação (vertical na coluna p/ N1; tarja inferior p/ N2) ----
        brand = payload.get("brand", "Aeronav")
        title = payload.get("titulo") or payload.get("name") or brand
        decl = payload.get("declinacao", "")
        denom = _denom(payload.get("scale"))
        info = "%s     Escala 1:%d" % (title, denom)
        if decl:
            info += "     Declinação Magnética %s" % decl
        lbl = QgsLayoutItemLabel(layout)
        lbl.setText(info)
        lbl.setFont(QFont("Sans", 11))
        if landscape:
            lbl.attemptResize(QgsLayoutSize(ph * 0.6, 10, MM))
            try:
                lbl.setReferencePoint(QgsLayoutItem.Middle)       # gira/posiciona pelo centro
            except Exception:
                pass
            lbl.attemptMove(QgsLayoutPoint(SBW * 0.5, ph * 0.5, MM))   # centro da coluna esquerda
            try:
                lbl.setItemRotation(270)                          # lê de baixo p/ cima (estilo AITA N1)
            except Exception:
                pass
        else:
            lbl.attemptMove(QgsLayoutPoint(pw * 0.30, ph - 18, MM))
            lbl.attemptResize(QgsLayoutSize(pw * 0.68, 12, MM))
        layout.addLayoutItem(lbl)

        # ---- logo (coluna esquerda no N1 / rodapé direito no N2), se houver ----
        logo = payload.get("logo") or ""
        if logo and os.path.exists(logo):
            lg = QgsLayoutItemPicture(layout)
            lg.setPicturePath(logo)
            lg.attemptResize(QgsLayoutSize(40, 16, MM))
            lg.attemptMove(QgsLayoutPoint(4, ph - 24, MM) if landscape
                           else QgsLayoutPoint(pw - 48, ph - 19, MM))
            layout.addLayoutItem(lg)

        res = QgsLayoutExporter(layout).exportToPdf(out_pdf, QgsLayoutExporter.PdfExportSettings())
        print("[qgis_render] base_ok=%s waypoints=%d type=%s scale=%d res=%s -> %s"
              % (base_ok, len(sel), ptype or "?", m.scale(), res, out_pdf))
        return res == QgsLayoutExporter.Success
    finally:
        qgs.exitQgis()


def _normalize(d):
    """Aceita tanto o dict de `mapdata()` (com `wpts`) quanto o JSON cru do Mapa
    (`{mapa, points, ...}`) — este último útil para testar standalone contra os
    arquivos de `data/mapas/`."""
    if "wpts" in d:
        return d
    m = d.get("mapa", {})
    pts = d.get("points", [])
    return {
        "name": m.get("name", ""), "scale": m.get("scale", "1:50000"),
        "orientation": m.get("orientation", "paisagem"), "base": m.get("base", "topo"),
        "logo": m.get("logo", ""), "titulo": m.get("titulo", ""),
        "declinacao": m.get("declinacao", ""), "type": d.get("type", m.get("type", "")),
        "brand": d.get("brand", "Aeronav"), "center": None,
        "wpts": [{"name": p.get("name", ""), "type": p.get("type", ""),
                  "radius": p.get("radius", 0), "lat": p["lat"], "lon": p["lon"]} for p in pts],
        "areas": d.get("areas", []), "frame": d.get("frame", {}),
        "route": d.get("route", {}), "landings": d.get("landings", []),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("uso: qgis_render.py entrada.json saida.pdf", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    ok = render(_normalize(data), sys.argv[2])
    sys.exit(0 if ok else 1)
