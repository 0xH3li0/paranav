# Modelo de Dados PROPOSTO — Visão de Produto (não implementado)

> ⚠️ **STATUS: modelo idealizado (relacional) que acompanha o briefing. NÃO reflete o storage atual.**
> O estado atual é **em memória + arquivos JSON** (`webapp/data/provas/*.json`), espelhando o paradigma — ver `CLAUDE.md` e `ARQUITETURA-PARADIGMA.md`. Este esquema (Championship/Task/MapElement/ScoringTerm/…, com uuid/FK) é um **alvo futuro** e só deve ser adotado via tarefa de migração alinhada (ver ROADMAP B6/B9). Não tomar como descrição do código existente.
> Valores calibrados do projeto prevalecem sobre os defaults genéricos daqui (ex.: `emax_s` aqui sugere 180; **o calibrado é 300**).

> Complementa `BRIEFING-CLIENTE.md`. Base: FAI Sporting Code S10 Annex 4 (2025).
> **Escopo MVP:** três navegações — **Pura**, **Tempo Declarado**, **Curve** — com construtor de mapas e apuração.
> Princípio: **tipos de ponto independentes do tipo de prova** e **provas como composição de blocos de pontuação configuráveis**.

---

## 1. Visão geral das entidades

```
Championship 1───* Task *───1 TaskPreset
Task 1───* MapElement
Task 1───* RoutePath          (rota desenhada — essencial p/ Curve)
Task 1───* MapArea            (áreas coloridas — visual no MVP)
Task 1───* ScoringTerm
Task 1───* PenaltyRule
Task 1───* Declaration        (uma por piloto — Declarada e Curve)
Task 1───* PilotResult
PilotResult 1───1 Track (GNSS)
PilotResult 1───* GateCrossing (derivado da Track)
```

---

## 2. Entidades

### 2.1 Championship
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| nome | string | |
| classes | enum[] | AL1/AL2/WL1/WL2/GL1/GL2 (microleves); PF1/PF2/PL1/PL2 (paramotores) |
| arredondamento | enum | `inteiro` \| `1_casa` \| `2_casas` |
| timezone | string | relógio oficial |

### 2.2 Task (prova)
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| championship_id | fk | |
| nome | string | |
| tipo_navegacao | enum | **MVP:** `PURA` \| `DECLARADA` \| `CURVE` |
| preset_id | fk? | template FAI (ex.: 2.A1 p/ Curve) |
| tempo_prova_s | int? | "tempo da prova" (Pura) |
| tolerancia_tempo | json? | esquema de tolerância (ver P2) |
| tmax_segundos | int? | tempo máximo SP→FP |
| sentido_unico | bool | habilita lógica de backtracking |
| pesos_termos | json | peso de cada ScoringTerm (ex.: {Qh:25, Qt:50, Qv:25}) |

> `tipo_navegacao` define quais MapElements/ScoringTerms são esperados:
> - **PURA:** SP, TPs, FP. Sem TG, sem HG (ver P1), sem Declaration.
> - **DECLARADA:** SP, TG, TP, HG, FP. Com Declaration.
> - **CURVE:** RoutePath (curvas) + SP, TP e/ou TG, HG, FP. Com Declaration.

### 2.3 TaskPreset
Template FAI. No MVP: apenas presets das navegações (ex.: `2.A1` Curve Navigation).
| campo | tipo | observação |
|---|---|---|
| codigo | string | ex.: `2.A1` |
| nome | string | |
| tipo_navegacao | enum | |
| termos_default | json | |
| penalidades_default | json | |

### 2.4 MapElement (ponto do mapa) — polimórfico por `tipo`
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| task_id | fk | |
| tipo | enum | **MVP:** `SP` \| `FP` \| `TP` \| `TG` \| `HG` |
| lat / lng | decimal | |
| ordem | int? | posição na sequência da rota |
| visivel_piloto | bool | `false` para HG |
| peso | int? | 1/2/3 (TP) |
| valor_pontos | decimal? | valor do ponto/gate (Vh, ex.: 100) |
| geometria | enum | `RAIO` \| `LINHA` |
| raio_m | decimal? | se RAIO |
| linha_comprimento_m | decimal? | se LINHA |
| sentido_obrigatorio | int? | heading esperado de cruzamento (graus) |
| **— campos de TG —** | | |
| emax_s | int? | erro máximo (default 180) |
| banda_morta_s | int? | |
| penalidade_por_seg | decimal? | |
| **— campos de foto —** | | |
| exige_foto | bool | |
| foto_url | string? | |
| simbolo_marker | enum? | H, I, K, L, N, T, U, X… |

> SP/FP que funcionam como time gate: setar `tipo=SP/FP` + flag interna `is_time_gate=true` (ou os campos de TG preenchidos). Manter um booleano explícito.

### 2.5 RoutePath (rota desenhada) — **novo, essencial para a Curve**
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| task_id | fk | |
| ativa | bool | múltiplas rotas ativas = todas consideradas (cog wheel) |
| segmentos | json | lista ordenada de segmentos |

Cada segmento:
```json
{ "tipo": "RETA" | "ARCO",
  "inicio": [lat,lng],
  "fim": [lat,lng],
  "arco": { "centro": [lat,lng], "raio_m": 0, "sentido": "CW|CCW" }  // se ARCO
}
```
> Formato dos arcos a confirmar (P5): centro+raio, três pontos ou Bézier. Tolerância espacial de aderência à rota em metros (P5).

### 2.6 MapArea (área colorida) — **visual no MVP**
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| task_id | fk | |
| cor | enum | `VERMELHO`(proibida) \| `AMARELO`(atenção) \| `AZUL` \| `VERDE` \| `MARROM` |
| rotulo | string? | |
| poligono | json | lista de vértices [lat,lng] |
| afeta_apuracao | bool | **default `false`** (MVP: tudo visual) |
| penalidade | json? | previsto/desabilitado; usado se P3 confirmar vermelha |

### 2.7 ScoringTerm (bloco de pontuação) — peça central
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| task_id | fk | |
| tipo | enum | **MVP:** `Qh_espacial` \| `Qt_tempo` \| `Qv_velocidade` \| `coleta_distancia` |
| peso | decimal | |
| formula_variante | enum | ver §3 |
| params | json | constantes (Vh, Vt, Emax, Vs…) — validar schema por variante |

### 2.8 PenaltyRule
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| task_id | fk | |
| tipo | enum | **MVP:** `backtracking` \| `atraso_sp` \| `atraso_fp` \| `tempo_excedido` |
| modo | enum | `percentual` \| `pontos_fixos` \| `por_segundo` \| `zera` |
| valor | decimal | ex.: 50(%), 200(pts), 10(pts/s) |
| condicao | json | gatilho |

> Backtracking default por classe: microleve nav `percentual:50`; paramotor nav `percentual:100`. Editável.

### 2.9 Declaration (Declarada e Curve)
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| task_id | fk | |
| pilot_id | fk | |
| sequencia_pontos | json | SP-01, SP-02 … SP-FP |
| tempos_declarados | json | {element_id: segundos} |
| ground_speed_declarada | decimal? | |
| locked_at | timestamp | trava na decolagem |

### 2.10 Track + GateCrossing
**Track**
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| pilot_result_id | fk | |
| origem | enum | `log_gnss` \| `tempo_real_gsm` |
| pontos | blob/json | série [lat,lng,alt,timestamp] |

**GateCrossing** (derivado)
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| track_id | fk | |
| element_id | fk | gate/ponto cruzado |
| timestamp | timestamp | |
| sentido_ok | bool | |
| ordem_ok | bool | |
| valido | bool | resultado após regra de invalidação |

### 2.11 PilotResult
| campo | tipo | observação |
|---|---|---|
| id | uuid | |
| task_id | fk | |
| pilot_id | fk | |
| q_bruto | decimal | Q antes da normalização |
| termos_detalhe | json | breakdown por ScoringTerm |
| penalidades_aplicadas | json | |
| pontuacao_final | decimal | P = 1000 × Q / Qmax |
| status | enum | `valido` \| `zerado` \| `dnf` |

---

## 3. Variantes de fórmula (MVP)

A engine seleciona pela `formula_variante`:
- **Qh_v1** (Curve / 2.A1): `Qh = 1000 × H / Nh`
- **Qh_v2** (genérico): `Qh = Vh × Nh`
- **Qt_v1**: `Qt = Emax × Nt − Et`
- **Qt_v2**: `Qt = Σ (Vt − Ei)`
- **Qv**: `Qv = Vs × S / Smax`
- **coleta_distancia** (Pura): `1000 × NBp / NBmax`

**Normalização final (sempre):** `P = 1000 × Q / Qmax` (melhor Q bruto = 1000 pts).

---

## 4. Algoritmo de validação de sequência (crítico)

Entrada: cruzamentos em ordem cronológica detectados na Track.
1. Descartar cruzamento de gate já cruzado (repetição invalida).
2. Manter só cruzamentos em **ordem crescente** esperada e **sentido** correto.
3. Resultado = maior subsequência válida na ordem.

Exemplo oficial: `1-2-4-3-5-6-5-7` → `1-2-4-6-7` (5 válidos).
> `3` cai por estar fora de ordem (após o `4`); o segundo `5` cai por repetição.

---

## 5. Ordem sugerida de implementação (MVP)

1. `MapElement` + `RoutePath` + `MapArea` + editor de mapa (camadas).
2. Ingestão de `Track` (log GNSS primeiro).
3. Engine de `GateCrossing` + algoritmo de sequência (§4).
4. `ScoringTerm` + variantes (§3) + normalização → `PilotResult`.
5. `PenaltyRule`.
6. `Declaration` (Declarada e Curve).
7. `TaskPreset` das navegações.
8. (Evolução) tempo real/broadcast; demais categorias; área vermelha com efeito.

---

## Apêndice — Entidades adiadas (fora do MVP)
`CORRIDOR` (ANR), `CM`/`WP` (Circle), `DECK` (precisão), termos de economia/distância/seções/ruído/bônus de pouso-decolagem, e área com penalidade ativa. Ver Apêndice A do doc de instruções.
