# Provas Demo — Paranapanema 2025

**Fonte:** https://demo.paramotorpr.com.br/ (Apurador 2.2.0-demo, acesso autorizado por Alan Braga)  
**Extraído em:** jun/2026 via `/provas/download/<nome>.json`

## O que são

Provas-demo carregadas pelo Alan Braga para demonstrar o Apurador 2.2. São do mesmo venue (Paranapanema, SP) e período do 3º Open CABPP Paranapanema 2025, mas **NÃO são as provas oficiais da competição** de 03/10/2025:

- **N1 demo**: 20 TPs; a prova real teve 30 TPs (confirmado: `round(1000 × TP/30)` reproduz todos os scores do ranking).
- 13 dos 20 TPs demo estão a < 300 m dos TPs inferidos da prova real → mesmo venue, curso simplificado.
- SP do N1 demo: lat=-23.3556, lon=-48.7392; SP inferido da prova real: lat=-23.3246, lon=-48.7202 (~4 km de distância).

## Arquivos

### Raw (formato Apurador 2.2)

| Arquivo | Wpts | Estrutura | Raio SP/FP |
|---------|------|-----------|-----------|
| `demo_N1-Paramotor.json` | 22 | SP+20TP+FP | 250 m |
| `demo_N1-Paratrike.json` | 22 | SP+20TP+FP (idêntico ao Paramotor) | 250 m |
| `demo_N2_FULL.json` | 53 | SP+46HG+3TG+2TP+FP | 250 m |
| `demo_N2.json` | 53 | idem (versão sem saved_at) | 250 m |
| `demo_N4.json` | 35 | SP+27HG+6TP+FP | 400 m |
| `demo_N5.json` | 29 | SP+24HG+3TP+FP | 400 m |
| `demo_ECOLIGHT.json` | 29 | SP+24HG+3TP+FP (idêntico a N5) | 400 m |
| `demo_N5-BASIC.json` | 20 | SP+15HG+3TP+FP | 400 m |
| `demo_Prova_20251021_2211.json` | 53 | SP+46HG+3TG+2TP+FP (= N2_FULL, salvo 21/10) | 250 m |

### Convertidos para nosso formato

| Arquivo | Sala | Uso sugerido |
|---------|------|-------------|
| `prova-n1-paramotor-demo.json` | N1 | Testar scoring N1 com tracks Paramotor |
| `prova-n1-paratrike-demo.json` | N1 | Testar scoring N1 com tracks Paratrike |
| `prova-n2-paratrike-demo.json` | N2 | Testar scoring N2 com tracks Paratrike |
| `prova-n4-light-demo.json` | N4 | Testar scoring N2 com tracks Light N4 |
| `prova-n5-light-demo.json` | N5 | Testar scoring N2 com tracks Light N5 |
| `prova-ecolight-demo.json` | N2 | Testar scoring N2 com tracks ECOLIGHT |

## Schema do Apurador 2.2 (diferenças do nosso)

```json
{
  "wpts": [
    {"name": "SP", "type": "SP", "lat": -23.3556, "lon": -48.7392},
    {"name": "1", "type": "TP", "lat": ..., "lon": ...}
  ],
  "radii": {"SP_FP": 250, "TP": 150, "HG": 150, "TG": 150, "ALT_MAX": 1000},
  "score_settings": {
    "caps": {"tp": 1000, "hg": 0, "vel": 0, "decl_tg": 0},
    "tol_s": 5, "lim_s": 300, "target_min": 0
  },
  "tracks": [...], "igcs": [...], "declared_times": {...}
}
```

Nosso formato: `points[]` com `radius` por ponto; tipo da prova em campo `type`; `w_hg`/`w_tg`/`w_vel` no nível raiz.

## Dois SPs no venue

- **N1/N2 (Paramotor + Paratrike):** SP lat=-23.3556, lon=-48.7392
- **N4/N5/ECOLIGHT (Light):** SP lat=-23.3469, lon=-48.7332 (~1,2 km ao norte)
