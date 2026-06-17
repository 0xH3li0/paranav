"""Motor de apuração — porta da lógica validada do protótipo HTML.

evaluate(): detecta passagem (1ª entrada no raio) + estatísticas de voo.
score_prova(): pontuação N1 (TP válidos) ou N2 (HG + TG + Vel = max_points).
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from .geo import dist, dist_to_polyline_m, densify_polyline
from .models import Prova, Pilot


def hms_to_sec_local(s: str, tz: int) -> Optional[int]:
    """'HH:MM[:SS]' local -> segundos UTC."""
    if not s:
        return None
    import re
    m = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
    if not m:
        return None
    sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)
    return sec - tz * 3600


def evaluate(prova: Prova, pilot: Pilot) -> Dict[str, Any]:
    fx = pilot.fixes
    by_id: Dict[int, Dict[str, Any]] = {}
    # Dois marcadores de tempo por ponto (confirmado contra o paradigma):
    #  - hit_t  = APROXIMAÇÃO MÁXIMA ao centro (instante de menor distância).
    #             Usado em "Hora do hit", dist. ao centro e tempo SP→FP.
    #             Bate EXATO com o relatório N1 do paradigma (Δ=0 em 13 pontos).
    #  - entry_t = 1ª ENTRADA no raio. Usado no tempo dos time gates (Score TG),
    #             que bate com o "Voado TG" do paradigma (N2).
    for i, pt in enumerate(prova.points):
        entry_t = None
        min_d = float("inf")
        min_t = None
        min_idx = None
        for j, f in enumerate(fx):
            d = dist(f.lat, f.lon, pt.lat, pt.lon)
            if d < min_d:
                min_d = d
                min_t = f.t
                min_idx = j
            if d <= pt.radius and entry_t is None:
                entry_t = f.t
        crossed = entry_t is not None
        by_id[i] = {
            "crossed": crossed,
            "hit_t": float(min_t) if crossed else None,   # aprox. máxima
            "entry_t": float(entry_t) if crossed else None,  # 1ª entrada
            "hit_idx": min_idx if crossed else None,
            "min_d": min_d if min_d != float("inf") else None,
            "valid": crossed,   # validade simplificada = cruzado
        }

    # índices de SP / FP
    sp_i = next((i for i, p in enumerate(prova.points) if p.type == "SP"), None)
    fp_i = next((i for i, p in enumerate(prova.points) if p.type == "FP"), None)
    sp = by_id.get(sp_i) if sp_i is not None else None
    fp = by_id.get(fp_i) if fp_i is not None else None

    max_alt = max((f.alt for f in fx), default=0)
    dist_spfp = time_spfp = vel = None
    if sp and fp and sp["crossed"] and fp["crossed"] and sp["hit_idx"] is not None \
            and fp["hit_idx"] is not None and fp["hit_idx"] > sp["hit_idx"]:
        dist_spfp = 0.0
        for k in range(sp["hit_idx"] + 1, fp["hit_idx"] + 1):
            dist_spfp += dist(fx[k - 1].lat, fx[k - 1].lon, fx[k].lat, fx[k].lon)
        time_spfp = fp["hit_t"] - sp["hit_t"]
        vel = (dist_spfp / 1000) / (time_spfp / 3600) if time_spfp > 0 else 0

    counts = {}
    for t in ("SP", "TP", "HG", "TG", "FP"):
        idxs = [i for i, p in enumerate(prova.points) if p.type == t]
        counts[t] = {
            "total": len(idxs),
            "crossed": sum(1 for i in idxs if by_id[i]["crossed"]),
            "valid": sum(1 for i in idxs if by_id[i]["valid"] and t not in ("SP", "FP")),
        }

    stats = {
        "takeoff": fx[0].t if fx else None,
        "landing": fx[-1].t if fx else None,
        "flight": (fx[-1].t - fx[0].t) if fx else None,
        "max_alt": max_alt,
        "sp_crossed": bool(sp and sp["crossed"]),
        "fp_crossed": bool(fp and fp["crossed"]),
        "fp_hit_t": fp["hit_t"] if fp else None,
        "dist_spfp": dist_spfp,
        "time_spfp": time_spfp,
        "vel": vel,
    }
    # N3 (Curve Navigation): cobertura do corredor curvo. Aditivo; só roda na N3.
    route_ev = None
    if prova.type == "n3" and isinstance(prova.route, dict) and prova.route.get("coords"):
        route_ev = _route_coverage(prova.route, fx, sp, fp)
    return {"by_id": by_id, "stats": stats, "counts": counts, "route": route_ev}


def _route_coverage(route: Dict[str, Any], fx, sp, fp) -> Dict[str, Any]:
    """Cobertura do corredor curvo (sala N3 / Curve Navigation).

    inside_ratio = fração das amostras da rota visitadas por algum fix dentro do
    corredor (janela = entre o hit do SP e do FP). `exits` = nº de saídas do
    corredor. MODELO NÃO-CALIBRADO (sem dado real; ver docs/ROADMAP.md).
    """
    coords = route.get("coords") or []
    half = float(route.get("width") or 0) / 2.0
    if len(coords) < 2 or half <= 0 or not fx:
        return {"inside_ratio": 0.0, "exits": 0, "n_inside": 0, "n_window": 0}
    # janela de fixes entre o hit do SP e do FP (se cruzados); senão, track todo
    i0 = sp["hit_idx"] if sp and sp.get("hit_idx") is not None else 0
    i1 = fp["hit_idx"] if fp and fp.get("hit_idx") is not None else len(fx) - 1
    if i1 < i0:
        i0, i1 = 0, len(fx) - 1
    window = fx[i0:i1 + 1]
    inside = [dist_to_polyline_m(f.lat, f.lon, coords) <= half for f in window]
    exits = sum(1 for k in range(1, len(inside)) if inside[k - 1] and not inside[k])
    # cobertura por amostragem da rota (independe da ordem dos fixes)
    samples = densify_polyline(coords, 50.0)
    covered = 0
    for s in samples:
        if any(dist(f.lat, f.lon, s[0], s[1]) <= half for f in window):
            covered += 1
    inside_ratio = covered / len(samples) if samples else 0.0
    return {"inside_ratio": inside_ratio, "exits": exits,
            "n_inside": sum(inside), "n_window": len(window)}


def ranking_geral(salas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Soma os pontos de cada piloto (chave = BIB) entre várias salas.

    `salas` = [{"prova": Prova, "pilots": [Pilot,...]}, ...].
    Retorna linhas ordenadas por total desc, com pontos por sala.
    """
    agg: Dict[str, Dict[str, Any]] = {}
    for s in salas:
        prova = s["prova"]
        rows = score_prova(prova, s["pilots"])
        for r in rows:
            key = r["pilot"].bib
            entry = agg.setdefault(key, {"bib": key, "name": r["pilot"].name,
                                         "by_sala": {}, "total": 0})
            entry["name"] = r["pilot"].name or entry["name"]
            entry["by_sala"][prova.slug] = r["points"]
            entry["total"] += r["points"]
    out = sorted(agg.values(), key=lambda e: -e["total"])
    return out


def score_prova(prova: Prova, pilots: List[Pilot]) -> List[Dict[str, Any]]:
    rows = [{"pilot": p, "ev": evaluate(prova, p)} for p in pilots]
    deadline = hms_to_sec_local(prova.deadline, prova.tz)
    target = (prova.target_min or 0) * 60

    if prova.type == "n3":
        # ----- Curve Navigation (corredor curvo) -----
        # MODELO PROPOSTO, NÃO-CALIBRADO (sem dado real; ver docs/ROADMAP.md).
        # points = max_points × inside_ratio. Gate: SP+FP cruzados.
        # Janela de tempo reaproveitada do N1 (DQ se minutos completos > window_min).
        for r in rows:
            re_ = r["ev"].get("route")
            st = r["ev"]["stats"]
            tspfp = st["time_spfp"]
            cm = int(tspfp // 60) if tspfp is not None else None
            dq = bool(prova.window_min) and cm is not None and cm > prova.window_min
            ratio = re_["inside_ratio"] if re_ else 0.0
            penal = []
            if not (st["sp_crossed"] and st["fp_crossed"]):
                r["points"] = 0
                penal.append("Sem SP/FP válidos")
            elif dq:
                r["points"] = 0
                penal.append(f"Desclassificado: fora da janela (> {prova.window_min} min)")
            else:
                r["points"] = max(0, round(prova.max_points * ratio))
            r["inside_ratio"] = ratio
            r["route_exits"] = re_["exits"] if re_ else None
            r["penal"] = penal
            r["tie"] = tspfp if tspfp is not None else float("inf")
        rows.sort(key=lambda r: (-r["points"], r["tie"]))
        return rows

    if prova.type == "n1":
        total_tp = sum(1 for p in prova.points if p.type == "TP")
        # NBmax = melhor nº de TPs válidos entre os pilotos NÃO desclassificados
        def completed_min(r):
            t = r["ev"]["stats"]["time_spfp"]
            return (int(t // 60) if t is not None else None)

        def is_dq(r):
            cm = completed_min(r)
            return bool(prova.window_min) and cm is not None and cm > prova.window_min

        valid_rows = [r for r in rows if not is_dq(r)]
        best_tp = max((r["ev"]["counts"]["TP"]["valid"] for r in valid_rows), default=0)
        for r in rows:
            v_tp = r["ev"]["counts"]["TP"]["valid"]
            tspfp = r["ev"]["stats"]["time_spfp"]
            penal = []
            if is_dq(r):
                r["points"] = 0
                penal.append(f"Desclassificado: fora da janela (> {prova.window_min} min)")
            else:
                if prova.score_model == "percent":
                    pts = prova.max_points * v_tp / total_tp if total_tp else 0
                else:  # relative (FAI 3.A1): NBp / NBmax
                    pts = prova.max_points * v_tp / best_tp if best_tp else 0
                r["points"] = max(0, round(pts))
                # flag informativo (sem impacto no score, conforme 3.A1)
                if target > 0 and tspfp is not None and tspfp > target:
                    penal.append("Tempo SP→FP acima do alvo")
            r["penal"] = penal
            r["tie"] = tspfp if tspfp is not None else float("inf")
        rows.sort(key=lambda r: (-r["points"], r["tie"]))
        return rows

    # ----- N2 composto -----
    # Emax CALIBRADO contra o N2-score do paradigma: 300 s, e o FP entra como
    # ponto de tempo junto dos TG (coluna "Erro FP"). Reproduz Leandro 67,9.
    emax = prova.emax or 300
    tol = prova.tol or 0  # banda morta: erro <= tol conta como 0
    best_hg = max((r["ev"]["counts"]["HG"]["valid"] for r in rows), default=0)
    # pontos de tempo = TG + FP
    timed_points = [(i, p) for i, p in enumerate(prova.points) if p.type in ("TG", "FP")]
    sp_idx = next((i for i, p in enumerate(prova.points) if p.type == "SP"), None)
    for r in rows:
        # tempo de gate usa a APROXIMAÇÃO MÁXIMA ao centro (hit_t), p/ o gate e p/ o SP
        # — confirmado contra o paradigma (Melk: 19/6/57/116 exato).
        sp_ref = r["ev"]["by_id"][sp_idx]["hit_t"] if sp_idx is not None else None
        qt = 0.0
        errs = {}
        for i, pt in timed_points:
            hit = r["ev"]["by_id"][i]
            dec_el = r["pilot"].decl.get(pt.name)   # tempo DECLARADO: s elapsado desde o SP
            if hit["crossed"] and dec_el is not None and sp_ref is not None:
                actual_el = hit["hit_t"] - sp_ref   # elapsado real (aprox. máxima) desde o SP
                e = abs(actual_el - dec_el)
                errs[pt.name] = round(e)            # erro CRU para exibição
                eff = 0 if e <= tol else e          # tolerância (banda morta) só no Qt
                qt += max(0, emax - eff)
            else:
                errs[pt.name] = None
        r["qt"] = qt
        r["tg_errs"] = errs
    best_qt = max((r["qt"] for r in rows), default=0)

    vel_lim = (prova.vel_window_min or 0) * 60   # prazo p/ Vel (s); 0 = sem prazo
    finishers = [r for r in rows if r["ev"]["stats"]["sp_crossed"]
                 and r["ev"]["stats"]["fp_crossed"] and r["ev"]["stats"]["time_spfp"] is not None
                 and (deadline is None or r["ev"]["stats"]["fp_hit_t"] <= deadline)
                 and (vel_lim == 0 or r["ev"]["stats"]["time_spfp"] <= vel_lim)]
    best_time = min((r["ev"]["stats"]["time_spfp"] for r in finishers), default=None)

    for r in rows:
        valid_base = (r["ev"]["stats"]["sp_crossed"] and r["ev"]["stats"]["fp_crossed"]
                      and r["ev"]["counts"]["TP"]["valid"] > 0)
        r["s_hg"] = prova.w_hg * r["ev"]["counts"]["HG"]["valid"] / best_hg if best_hg else 0
        r["s_tg"] = prova.w_tg * r["qt"] / best_qt if best_qt else 0
        is_fin = r in finishers
        r["s_vel"] = prova.w_vel * best_time / r["ev"]["stats"]["time_spfp"] if (is_fin and best_time) else 0
        total = r["s_hg"] + r["s_tg"] + r["s_vel"]
        penal = []
        if deadline is not None and r["ev"]["stats"]["fp_hit_t"] is not None \
                and r["ev"]["stats"]["fp_hit_t"] > deadline:
            penal.append("FP após deadline")
        if not valid_base:
            total = 0
            penal.append("Sem SP/FP/TP válidos")
        r["points"] = round(total)
        r["penal"] = penal
        r["tie"] = r["ev"]["stats"]["time_spfp"] if r["ev"]["stats"]["time_spfp"] is not None else float("inf")
    rows.sort(key=lambda r: (-r["points"], r["tie"]))
    return rows
