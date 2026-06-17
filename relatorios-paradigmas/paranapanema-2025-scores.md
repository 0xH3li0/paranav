# 3º Open CABPP Paranapanema 2025 — Scores de referência

**Fonte:** igc.paramotorpr.com.br (Apurador 2.2 de Alan Braga)  
**Evento:** 3º Open CABPP Paranapanema — data do voo: **03/10/2025**  
**Extraído em:** jun/2026 via inspeção do HTML da página (trackData embutido no HTML)

---

## Rankings completos (3 categorias)

### Categoria Paramotor

Provas: P1, N1, E5, P2, ECO-CLASSICA  
*(P1 e P2 não têm track em /mapas — tarefas sem upload de IGC)*

| Nome                      | P1     | N1     | E5     | P2     | ECO    | Total  |
|---------------------------|--------|--------|--------|--------|--------|--------|
| Melk Aita (9)             | nan    | 933.0  | 870.0  | 1000.0 | 600.0  | 3403.0 |
| Marcio Aita Jr (8)        | 1000.0 | 933.0  | 1000.0 | nan    | 420.0  | 3353.0 |
| Erick de Araujo Oliveira (7)| nan  | 1000.0 | nan    | nan    | 980.0  | 1980.0 |
| Rodrigo Campos (1)        | 400.0  | 867.0  | nan    | nan    | 680.0  | 1947.0 |
| Natalia Moreno (6)        | nan    | 600.0  | nan    | nan    | 1000.0 | 1600.0 |
| Natalia Nobre dos Reis (5)| 1000.0 | nan    | nan    | nan    | 580.0  | 1580.0 |
| Luiz Fernando Severnini (4)| nan   | 500.0  | nan    | nan    | 560.0  | 1060.0 |
| Jose Ricardo de Castro (3) | nan   | 267.0  | nan    | nan    | nan    | 267.0  |

**N1 — Total de TPs inferido: 30** (Erick=30, Melk/Marcio=28, Rodrigo=26, Natalia M=18, Luiz F=15, Jose R=8)  
Fórmula: `round(1000 × TP_piloto / 30)` valida ao inteiro para todos.

### Categoria Light

Provas: N4, P8, N5, ECO-LIGHT  
*(P8 não tem track em /mapas — tarefa sem upload de IGC)*

| Nome                           | N4     | P8     | N5     | ECO    | Total  |
|-------------------------------|--------|--------|--------|--------|--------|
| Leandro Tadeu de Aguiar (23)  | 1000.0 | 700.0  | 1000.0 | 1000.0 | 3700.0 |
| Henrique Ventura (22)         | 862.0  | 1000.0 | 648.0  | 1000.0 | 3510.0 |
| Fabiano Tardelli (28)         | 603.0  | 700.0  | 258.0  | 750.0  | 2311.0 |
| Ricardo Negrão (24)           | nan    | nan    | 671.0  | 844.0  | 1515.0 |
| Tiago Rodrigo Antonio Santos (25)| nan | nan    | 567.0  | 688.0  | 1255.0 |
| Marlon Cezar Manfron (26)     | nan    | nan    | nan    | 969.0  | 969.0  |
| Rodrigo Crivellaro (29)       | nan    | nan    | nan    | 813.0  | 813.0  |
| Carlos Cesar Florian (21)     | nan    | 700.0  | nan    | nan    | 700.0  |
| Fred Gomes Pereira            | nan    | nan    | nan    | nan    | 0.0    |
| Leandro Aparecido Fracasso    | nan    | nan    | nan    | nan    | 0.0    |

### Categoria Paratrike

Provas: P1, N1, P3, P1-2, N2  
*(P1, P3, P1-2 não têm track em /mapas — tarefas sem upload de IGC)*

| Nome                                  | P1  | N1   | P3   | P1-2   | N2   | Total  |
|--------------------------------------|-----|------|------|--------|------|--------|
| Itiel Lima (15)                      | nan | 737  | 1000 | 1000.0 | 985  | 3722.0 |
| Anderson Bech & Siany Bech (16)      | nan | 1000 | 651  | 1000.0 | 1000 | 3651.0 |
| Charles Terrell & Algusto Toledo (18)| nan | 737  | 616  | 1000.0 | 949  | 3302.0 |
| Claudio Tonhetta & Danbert (17)      | nan | 158  | 879  | nan    | 579  | 1616.0 |

**N1 Paratrike — Total de TPs inferido: 19** (Anderson=19, Itiel/Charles=14, Tonhetta=3)  
**N2 Paratrike** — mesma fórmula HG+TG+Vel do paradigma N2.

---

## Estrutura das salas com tracks extraíveis

| Sala             | Categoria  | Tipo de prova         | Coluna no ranking |
|-----------------|------------|----------------------|-------------------|
| n1              | Paramotor + Paratrike | Navegação Pura (FAI 3.A1) | N1     |
| n2              | Paratrike  | Tempo Declarado (FAI 3.A6) | N2              |
| n4              | Light      | Navegação 4 (tipo N)  | N4                |
| n5              | Light      | Navegação 5 (tipo N)  | N5                |
| economia-classica| Paramotor | Economia clássica     | ECO               |
| economia-light  | Light      | Economia light        | ECO               |
| e5              | Paramotor  | Economia 5            | E5                |
| preciso-light   | Light      | Precisão light        | ? (sem score vis.)|

---

## Endpoints públicos descobertos (jun/2026)

O site tem três formas de acessar os tracks publicamente (sem login):

| Endpoint | Retorno |
|----------|---------|
| `/view-json/<sala>/web/<file>.json` | HTML viewer (Leaflet, track embutido no JS) |
| `/uploads/<sala>/web/<file>.json` | JSON bruto `{filename, flight_info, track[{lat,lng,time,altitude}]}` |
| `/kml/<sala>/web/<file>.json` | KML do track com dados de voo (duração, distância, etc.) |

**A prova (SP/FP/TP/HG/TG) NÃO está em nenhum desses endpoints.** O admin usa paths criptografados dinamicamente — inacessíveis sem ADMIN_KEY.

## Prova N1 inferida por análise de tracks

Sem acesso à prova oficial, aplicamos clustering espacial (350m) de viradas de bearing (threshold 22°, janela 20s) sobre 6 tracks N1 (Erick, Melk, Marcio, Rodrigo, Natalia M, Luiz), usando o track do Erick (30/30 TPs) para ordenar a sequência.

**Resultado:** 23 de 30 TPs com coordenadas aproximadas + SP + FP  
**7 TPs ausentes** (inferência falhou em dois gaps: 09:54→10:01 e 10:16→10:25)  
**Arquivo:** `relatorios-paradigmas/paranapanema-2025-prova-n1-inferida.json`

Esta prova **NÃO reproduz os scores oficiais** (TPs com coord 0,0 são ignorados pelo scorer + coordenadas dos 23 TPs são aproximadas com ±100-300m de erro).

## Provas demo extraídas (jun/2026)

Alan Braga forneceu acesso a **https://demo.paramotorpr.com.br/** (Apurador 2.2.0-demo, completamente aberto). A página `/provas/load` lista 10 provas salvas, baixáveis via `/provas/download/<nome>.json`.

**Schema do Apurador 2.2** (diferente do nosso): array `wpts` + dict `radii` global (vs nosso `points` com `radius` por ponto); caps em `score_settings.caps.{tp,hg,vel,decl_tg}`; sem campo `type` na raiz; `saved_at` ISO8601.

### Provas disponíveis no demo

| Arquivo | Wpts | Tipos | Radii SP/FP | Obs |
|---------|------|-------|-------------|-----|
| `N1-Paramotor.json` | 22 | SP+20TP+FP | 250m | Mesmo curso que Paratrike |
| `N1-Paratrike.json` | 22 | SP+20TP+FP | 250m | Idêntico ao Paramotor |
| `N2_FULL.json` | 53 | SP+46HG+3TG+2TP+FP | 250m | TGs/TPs coincidem com TPs do N1 |
| `N2.json` | 53 | idem | 250m | Versão anterior (sem saved_at) |
| `N4.json` | 35 | SP+27HG+6TP+FP | 400m | HGs com raio 100m |
| `N5.json` | 29 | SP+24HG+3TP+FP | 400m | Idêntico ao ECOLIGHT |
| `ECOLIGHT.json` | 29 | SP+24HG+3TP+FP | 400m | Mesmo que N5 |
| `N5-BASIC.json` | 20 | SP+15HG+3TP+FP | 400m | Versão reduzida de N5 |
| `Prova_20251021_2211.json` | 53 | SP+46HG+3TG+2TP+FP | 250m | Idêntico a N2_FULL, salvo em 21/10 |

Arquivos salvos em `relatorios-paradigmas/demo-paranapanema-2025/` (raw `demo_*.json` + convertidos para nosso formato `prova-*.json`).

### Relação com a prova oficial do Paranapanema 2025

As provas demo **NÃO são** as provas oficiais do 03/10/2025 — o N1 demo tem 20 TPs; a prova real teve 30 (confirmado pelo `round(1000 × TP/30)` que reproduz todos os scores). Porém há **sobreposição geográfica significativa**: 13 dos 20 TPs demo estão a menos de 300m dos TPs inferidos da prova real — mesmos marcos, curso diferente.

Dois SPs distintos entre as salas:
- N1/N2: SP lat=-23.3556, lon=-48.7392 (Paramotor + Paratrike)
- N4/N5/ECO: SP lat=-23.3469, lon=-48.7332 (Light — SP diferente, ~1,2km ao norte)

## Limitações desta superfície de testes

1. **Waypoints da prova oficial inacessíveis.** Protegidos por ADMIN_KEY no igc.paramotorpr.com.br. Temos: reconstrução parcial (23/30 TPs N1 via inferência) + provas demo do mesmo venue (20 TPs, não reproduzem scores). Para a prova exata: contatar Alan Braga (+5541999636314).

2. **Altitude: 41/50 IGCs com altitude real (82%).** Recuperada de duas fontes: (a) endpoint `/uploads/` do igc.paramotorpr.com.br (~20 tracks, sessão jun/2026); (b) array `tracks` das provas demo (`demo_*.json` — contém GPS completo com altitude de todos os pilotos salvos). Os **9 restantes** permanecem com altitude=0 porque pertencem a salas sem prova demo (e5, economia-classica, preciso-light) e sem altitude no `/uploads/` original:
   - Luiz Fernando Severnini (4): e5, economia-classica
   - Natalia Nobre dos Reis (5): e5, economia-classica
   - Melk Aita (9): e5, economia-classica
   - Ricardo Negrão (24): economia-light, preciso-light
   - Rodrigo Crivellaro (29): n1

3. **Tarefas P1/P2/P3/P8/P1-2 sem tracks.** Essas colunas existem no ranking mas nenhum arquivo de track foi publicado em /mapas. Provavelmente são tarefas de outro formato pontuadas manualmente no admin.

4. **Fuso horário:** tempos em UTC-3 (horário local de São Paulo/Paranapanema). Definir `tz=America/Sao_Paulo` na prova ao apurar.

5. **Erick E5 incompleto:** apenas 66 fixes extraídos (voo muito curto). Provavelmente arquivo de teste ou DQ.

---

## IGCs extraídos (50 arquivos)

Disponíveis em `igcs/3o-open-paranapanema-2025/`:

| Arquivo | Sala | Fixes |
|---------|------|-------|
| 01-Rodrigo-Campos-n1.igc              | n1               | 3656  |
| 01-Rodrigo-Campos-economia-classica.igc| economia-classica| 2056  |
| 01-Rodrigo-Campos-e5.igc             | e5               | 1642  |
| 03-Jose-Ricardo-de-Castro-n1.igc     | n1               | 2862  |
| 04-Luiz-Fernando-Severnini-n1.igc    | n1               | 4152  |
| 04-Luiz-Fernando-Severnini-economia-classica.igc | economia-classica | 1664 |
| 04-Luiz-Fernando-Severnini-e5.igc    | e5               | 1141  |
| 05-Natalia-Nobre-dos-Reis-n1.igc     | n1               | 5596  |
| 05-Natalia-Nobre-dos-Reis-economia-classica.igc | economia-classica | 1360 |
| 05-Natalia-Nobre-dos-Reis-e5.igc     | e5               | 1981  |
| 06-Natalia-Moreno-n1.igc             | n1               | 3394  |
| 06-Natalia-Moreno-economia-classica.igc | economia-classica | 3013 |
| 07-Erick-de-Araujo-Oliveira-n1.igc   | n1               | 3784  |
| 07-Erick-de-Araujo-Oliveira-economia-classica.igc | economia-classica | 2310 |
| 07-Erick-de-Araujo-Oliveira-e5.igc   | e5               | 66 ⚠️ (incompleto) |
| 08-Marcio-Aita-Junior-n1.igc         | n1               | 3561  |
| 08-Marcio-Aita-Junior-economia-classica.igc | economia-classica | 1290 |
| 08-Marcio-Aita-Junior-e5.igc         | e5               | 1654  |
| 09-Melk-Aita-n1.igc                  | n1               | 3624  |
| 09-Melk-Aita-economia-classica.igc   | economia-classica| 1808  |
| 09-Melk-Aita-e5.igc                  | e5               | 1810  |
| 15-Itiel-de-Paula-Lima-n1.igc        | n1               | 4010  |
| 15-Itiel-de-Paula-Lima-n2.igc        | n2               | 3696  |
| 16-Anderson-Bech-n1.igc              | n1               | 3875  |
| 16-Anderson-Bech-n2.igc              | n2               | 3295  |
| 17-Claudio-Tonhetta-n1.igc           | n1               | 5334  |
| 17-Claudio-Tonhetta-n2.igc           | n2               | 3618  |
| 18-Charles-Terrell-Guto-n1.igc       | n1               | 2283  |
| 18-Charles-Terrell-Guto-n2.igc       | n2               | 3376  |
| 21-Carlos-Cesar-Florian-n4.igc       | n4               | 4991  |
| 22-Henrique-Ventura-n4.igc           | n4               | 6038  |
| 22-Henrique-Ventura-n5.igc           | n5               | 5644  |
| 22-Henrique-Ventura-economia-light.igc | economia-light | 1941  |
| 23-Leandro-Tadeu-de-Aguiar-n4.igc    | n4               | 3965  |
| 23-Leandro-Tadeu-de-Aguiar-n5.igc    | n5               | 3837  |
| 23-Leandro-Tadeu-de-Aguiar-economia-light.igc | economia-light | 1677 |
| 24-Ricardo-Negrao-n5.igc             | n5               | 5459  |
| 24-Ricardo-Negrao-economia-light.igc | economia-light   | 712   |
| 24-Ricardo-Negrao-preciso-light.igc  | preciso-light    | 712   |
| 25-Tiago-Rodrigo-Antonio-Santos-n5.igc | n5             | 6423  |
| 25-Tiago-Rodrigo-Antonio-Santos-economia-light.igc | economia-light | 1306 |
| 26-Marlon-Cezar-Manfron-n4.igc       | n4               | 3249  |
| 26-Marlon-Cezar-Manfron-n5.igc       | n5               | 6100  |
| 26-Marlon-Cezar-Manfron-economia-light.igc | economia-light | 1856 |
| 28-Fabiano-Tardelli-n4.igc           | n4               | 6245  |
| 28-Fabiano-Tardelli-n5.igc           | n5               | 1714  |
| 28-Fabiano-Tardelli-economia-light.igc | economia-light  | 1493  |
| 29-Rodrigo-Crivellaro-n1.igc         | n1               | 1967  |
| 29-Rodrigo-Crivellaro-n5.igc         | n5               | 1487  |
| 29-Rodrigo-Crivellaro-economia-light.igc | economia-light | 1603 |
