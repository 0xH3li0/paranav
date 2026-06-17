"""Modelos de dados da prova (dataclasses)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

POINT_TYPES = ("SP", "TP", "HG", "TG", "FP")


@dataclass
class Point:
    name: str
    type: str          # SP|TP|HG|TG|FP
    radius: float      # metros
    lat: float
    lon: float
    weight: float = 1.0
    alt: float = 0.0


@dataclass
class Prova:
    name: str
    type: str = "n1"           # n1 | n2
    slug: str = ""
    map_slug: str = ""         # referência ao Mapa (geometria). Vazio = geometria inline (legado)
    target_min: int = 60
    deadline: str = ""         # "HH:MM" local
    tz: int = -3               # UTC offset
    max_points: int = 1000
    w_hg: int = 400
    w_tg: int = 200
    w_vel: int = 400
    emax: int = 300   # calibrado contra o N2-score do paradigma (TG+FP, relativo)
    tol: int = 5      # tolerância de tempo (s): erro <= tol conta como 0 (banda morta)
    window_min: int = 60   # janela de tempo SP→FP (min). DQ se minutos completos > window_min (FAI 3.A1)
    vel_window_min: int = 0  # N2: prazo p/ pontuar Vel (min). 0 = sem prazo. SP→FP > prazo zera só o Vel
    score_model: str = "relative"  # N1: 'relative' (FAI NBp/NBmax) | 'percent' (TP/total)
    # produção de mapa
    scale: str = "1:50000"     # 1:50000 | 1:100000 | 1:150000
    teto: int = 0              # teto (m); 0 = não definido
    altura_min: int = 0        # altura mínima (m); 0 = não definido
    areas: List[dict] = field(default_factory=list)  # [{kind:'proibida'|'atencao', name, coords:[[lat,lon],...]}]
    frame: dict = field(default_factory=dict)  # folha A3: {lat, lon, angle} (centro + rotação em graus)
    # N3 (Curve Navigation): corredor curvo {coords:[[lat,lon],...], width: <metros, largura TOTAL>}
    route: dict = field(default_factory=dict)
    # marcadores de pouso (3.A3/3.A5) — anotação de mapa: [{name, lat, lon}]
    landings: List[dict] = field(default_factory=list)
    points: List[Point] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Prova":
        p = d.get("prova", d)
        pts = [Point(**{k: pt[k] for k in ("name", "type", "radius", "lat", "lon")
                        if k in pt}, weight=pt.get("weight", 1.0), alt=pt.get("alt", 0.0))
               for pt in d.get("points", [])]
        return Prova(
            name=p.get("name", "Prova"), type=p.get("type", "n1"), slug=p.get("slug", ""),
            map_slug=p.get("mapSlug", p.get("map_slug", "")),
            target_min=p.get("targetMin", p.get("target_min", 60)),
            deadline=p.get("deadline", ""), tz=p.get("tz", -3),
            max_points=p.get("maxPoints", p.get("max_points", 1000)),
            w_hg=p.get("wHG", 400), w_tg=p.get("wTG", 200), w_vel=p.get("wVel", 400),
            emax=p.get("emax", 300), tol=p.get("tol", 5),
            window_min=p.get("windowMin", p.get("window_min", 60)),
            vel_window_min=p.get("velWindowMin", p.get("vel_window_min", 0)),
            score_model=p.get("scoreModel", p.get("score_model", "relative")),
            scale=p.get("scale", "1:50000"), teto=p.get("teto", 0),
            altura_min=p.get("alturaMin", p.get("altura_min", 0)),
            areas=d.get("areas", p.get("areas", [])),
            frame=d.get("frame", p.get("frame", {})),
            route=d.get("route", p.get("route", {})),
            landings=d.get("landings", p.get("landings", [])),
            points=pts,
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "prova": {
                "name": self.name, "type": self.type, "slug": self.slug,
                "mapSlug": self.map_slug,
                "targetMin": self.target_min, "deadline": self.deadline, "tz": self.tz,
                "maxPoints": self.max_points, "wHG": self.w_hg, "wTG": self.w_tg,
                "wVel": self.w_vel, "emax": self.emax, "tol": self.tol,
                "windowMin": self.window_min, "velWindowMin": self.vel_window_min,
                "scoreModel": self.score_model,
                "scale": self.scale, "teto": self.teto, "alturaMin": self.altura_min,
            },
        }
        # Com mapa, a geometria vive no Mapa (não duplicar no JSON da prova).
        if self.map_slug:
            return out
        out["points"] = [{"name": pt.name, "type": pt.type, "radius": pt.radius,
                          "weight": pt.weight, "lat": pt.lat, "lon": pt.lon, "alt": pt.alt}
                         for pt in self.points]
        out["areas"] = self.areas
        out["frame"] = self.frame
        out["route"] = self.route
        out["landings"] = self.landings
        return out

    def apply_radii(self, radius_sp_fp: float, radius_intermediate: float) -> None:
        """Aplica raio global por tipo: SP/FP vs demais (TP/HG/TG)."""
        for pt in self.points:
            pt.radius = radius_sp_fp if pt.type in ("SP", "FP") else radius_intermediate

    def mapdata(self) -> Dict[str, Any]:
        lats = [pt.lat for pt in self.points] or [0]
        lons = [pt.lon for pt in self.points] or [0]
        return {
            "ok": True,
            "has_prova": bool(self.points),
            "center": {"lat": sum(lats) / len(lats), "lon": sum(lons) / len(lons)},
            "wpts": [{"name": pt.name, "type": pt.type, "radius": pt.radius,
                      "lat": pt.lat, "lon": pt.lon} for pt in self.points],
            "airspaces": [],
            "route": self.route or None,
            "landings": self.landings or [],
        }


# cores das áreas: kind -> cor (verde/vermelho/amarelo, conforme o cliente)
AREA_KINDS = {"proibida": "vermelho", "atencao": "amarelo", "livre": "verde"}


@dataclass
class Mapa:
    """Geometria/cartografia reutilizável (separada da Prova).

    Guarda pontos tipados, áreas, rota, folha A3, escala, teto/altura e logo.
    Vários mapas podem existir na mesma área; a Prova referencia um via `map_slug`.
    Expõe os MESMOS atributos de geometria de `Prova` (duck-typing) para reusar
    os geradores de PDF (`mappdf`/`pointspdf`) e `mapdata` sem alteração.
    """
    name: str
    slug: str = ""
    scale: str = "1:50000"        # 1:50000 | 1:100000 | 1:150000
    orientation: str = "paisagem"  # paisagem | retrato (folha A3)
    base: str = "esri"            # esri | osm | topo
    style: str = "pontos"         # estilo de exibição (ex.: 'pontos')
    teto: int = 0
    altura_min: int = 0
    logo: str = ""                # caminho do logotipo (rodapé do mapa A3)
    published: bool = False       # "Publicar": marcado como pronto/final
    # metadados do evento (rodapé/informações da prova)
    organizador: str = ""
    titulo: str = ""
    local: str = ""
    data: str = ""
    declinacao: str = ""          # declinação magnética (ex.: "23° 10' W") — exibida no A3
    frame: dict = field(default_factory=dict)   # folha A3 {lat, lon, angle}
    areas: List[dict] = field(default_factory=list)   # [{kind:'proibida'|'atencao'|'livre', name, coords}]
    route: dict = field(default_factory=dict)   # corredor N3 {coords, width}
    landings: List[dict] = field(default_factory=list)
    points: List[Point] = field(default_factory=list)
    type: str = ""                # duck-type p/ os geradores de PDF (mapa não tem tipo de prova)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Mapa":
        m = d.get("mapa", d)
        pts = [Point(**{k: pt[k] for k in ("name", "type", "radius", "lat", "lon") if k in pt},
                     weight=pt.get("weight", 1.0), alt=pt.get("alt", 0.0))
               for pt in d.get("points", [])]
        return Mapa(
            name=m.get("name", "Mapa"), slug=m.get("slug", ""),
            scale=m.get("scale", "1:50000"), orientation=m.get("orientation", "paisagem"),
            base=m.get("base", "esri"), style=m.get("style", "pontos"),
            teto=m.get("teto", 0), altura_min=m.get("alturaMin", m.get("altura_min", 0)),
            logo=m.get("logo", ""), published=bool(m.get("published", False)),
            organizador=m.get("organizador", ""), titulo=m.get("titulo", ""),
            local=m.get("local", ""), data=m.get("data", ""),
            declinacao=m.get("declinacao", ""),
            frame=d.get("frame", m.get("frame", {})),
            areas=d.get("areas", m.get("areas", [])),
            route=d.get("route", m.get("route", {})),
            landings=d.get("landings", m.get("landings", [])),
            points=pts,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapa": {"name": self.name, "slug": self.slug, "scale": self.scale,
                     "orientation": self.orientation, "base": self.base, "style": self.style,
                     "teto": self.teto, "alturaMin": self.altura_min, "logo": self.logo,
                     "published": self.published,
                     "organizador": self.organizador, "titulo": self.titulo,
                     "local": self.local, "data": self.data, "declinacao": self.declinacao},
            "points": [{"name": pt.name, "type": pt.type, "radius": pt.radius,
                        "weight": pt.weight, "lat": pt.lat, "lon": pt.lon, "alt": pt.alt}
                       for pt in self.points],
            "areas": self.areas, "frame": self.frame, "route": self.route,
            "landings": self.landings,
        }

    def mapdata(self) -> Dict[str, Any]:
        lats = [pt.lat for pt in self.points] or ([self.frame["lat"]] if self.frame.get("lat") else [0])
        lons = [pt.lon for pt in self.points] or ([self.frame["lon"]] if self.frame.get("lon") else [0])
        return {
            "ok": True, "has_map": bool(self.points or self.frame),
            "name": self.name, "scale": self.scale, "orientation": self.orientation,
            "base": self.base, "style": self.style,
            "teto": self.teto, "altura_min": self.altura_min, "logo": self.logo,
            "center": {"lat": sum(lats) / len(lats), "lon": sum(lons) / len(lons)},
            "wpts": [{"name": pt.name, "type": pt.type, "radius": pt.radius,
                      "lat": pt.lat, "lon": pt.lon} for pt in self.points],
            "areas": self.areas, "frame": self.frame,
            "route": self.route or None, "landings": self.landings or [],
        }


def hydrate(prova: "Prova", mapa: "Mapa") -> "Prova":
    """Copia a geometria do mapa para a prova (mantém scoring) — chamado no load.
    Assim `evaluate()/score_prova()/mapdata()/mappdf` recebem uma Prova completa."""
    prova.points = mapa.points
    prova.areas = mapa.areas
    prova.frame = mapa.frame
    prova.route = mapa.route
    prova.landings = mapa.landings
    prova.scale = mapa.scale
    prova.teto = mapa.teto
    prova.altura_min = mapa.altura_min
    # atributos dinâmicos (não-campos) p/ o A3 PDF usar a base/orientação/logo do mapa
    prova.base = mapa.base
    prova.orientation = mapa.orientation
    prova.logo = mapa.logo
    prova.declinacao = getattr(mapa, "declinacao", "")
    return prova


@dataclass
class Pilot:
    bib: str
    name: str
    date: str = ""
    fixes: list = field(default_factory=list)     # List[Fix]
    decl: Dict[str, int] = field(default_factory=dict)  # nome do TG -> seg UTC declarado
