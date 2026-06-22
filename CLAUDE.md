# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Antes de codar, leia:** `docs/README.md` (índice + hierarquia de autoridade), `docs/ESCOPO-PRODUTO.md` (**o que** construir — IA dos 4 módulos), depois `docs/ROADMAP.md` (regras de trabalho com IA + backlog com critérios de aceite), `docs/EVOLUCAO.md` (histórico/decisões) e `docs/ARQUITETURA-PARADIGMA.md`. **Regra de ouro:** não quebrar as calibrações — validar contra os dados reais (`igcs/` + `relatorios-paradigmas/`) antes e depois de mexer no scoring.
>
> ⚠️ **Atenção a defaults genéricos do FAI** que divergem das calibrações (ex.: Emax 180 ≠ **300 calibrado**) e a códigos de microleve (`2.A1`) — este é paramotor (**Part 3**: N1=`3.A1`, N2=`3.A6`). Em conflito, vale o **estado atual calibrado**. Escopo do produto: `docs/ESCOPO-PRODUTO.md`.

## O que é

Plataforma de **navegação de paramotor** com **dois pilares**: um **Criador de Mapas** (editor do organizador, feito do zero) + um **Apurador de Provas** (scoring a partir do IGC, espelhando o paradigma **https://demo.paramotorpr.com.br/**). UI/labels em português (BR).

**IA canônica = 4 módulos em sequência: `MAPA → PROVAS → COMPETIÇÕES → PILOTOS`** (alinhamento com o Márcio, 16/06/2026). Detalhe e gaps código×escopo em **`docs/ESCOPO-PRODUTO.md`** (fonte da verdade de *escopo*). Regra de separação: **aba MAPA só tem mapas crus editáveis**; prova vive na **aba PROVAS** (lista + "Nova Prova" → escolhe um mapa).

**Entregável atual: app web Flask em `webapp/`** — réplica com a **mesma stack do paradigma** (Python + **Flask + Jinja2**, **Bootstrap 5.3.3**, **Leaflet 1.9.4**). Provas em **arquivos JSON** (dev) ou **SQLite** (produção). **Mapa × Prova são separados:** um **Mapa** guarda a geometria (pontos, áreas, rota, folha A3, escala, teto/altura, logo); a **Prova** referencia um mapa via `map_slug` + scoring. Salas: **N1 (Navegação Pura)**, **N2 (Tempo Declarado)** e **N3 (Navegação em Curva / Curve Navigation — corredor curvo, estende o paradigma)**.

> Pivô: o projeto começou como app HTML single-file e migrou para Flask (decisão do Helio: "HTML puro não faz mais sentido"). Os protótipos `.html` foram removidos — a lógica de parser/scoring deles foi validada contra dados reais e **portada para Python** em `webapp/apurador/core/`. Entregável único é o `webapp/`.

## Arquivos principais

- **`webapp/`** — a aplicação Flask (entregável). Ver `webapp/README.md`.
- **`docs/`** — documentação. Índice e hierarquia em `docs/README.md`. Escopo do produto: `ESCOPO-PRODUTO.md` (IA dos 4 módulos). Estado atual: `ROADMAP.md` (guia de dev + backlog), `EVOLUCAO.md` (histórico), `ARQUITETURA-PARADIGMA.md` (engenharia reversa); produção de mapa: `CONSTRUTOR-PLANO.md`, `ESPEC-PRODUCAO-MAPAS.md`.
- **`webapp/data/provas/*.json`** — provas (CANÔNICO; o app lê daqui). `provas/` (raiz) guarda só os **CSV de referência** da extração.
- **`igcs/`** — IGCs reais: `igcs/*.igc` (Venet/Melk/Leandro/Paulo — calibração sagrada N1/N2) + `igcs/3o-open-paranapanema-2025/` (**50 pseudo-IGCs** do 3º Open CABPP Paranapanema 2025 em 8 salas: n1/n2/n4/n5/economia-classica/economia-light/e5/preciso-light, extraídos do Apurador 2.2). **`relatorios-paradigmas/`** — relatórios do paradigma (referência de validação) + `paranapanema-2025-scores.md` (ranking completo do Apurador 2.2 — 3 categorias). **`relatorios/`** — PDFs gerados pelo app. **`Regulamento/`** — FAI Annex 4 2025.
- **`Iniciar-Aeronav.command`** — atalho macOS para subir o app (porta 5050).

## Rodar / desenvolver / testar

```bash
cd webapp
pip install -r requirements.txt   # Flask (use --break-system-packages no sandbox)
python run.py                     # http://localhost:5050 (5000 é ocupada pelo AirPlay do macOS)
```

Login dev do organizador: **admin@apurador.local / admin** (env: `APURADOR_EMAIL/PASSWORD/SECRET/PIN/BRAND`). No Mac, dar 2 cliques em `Iniciar-Aeronav.command`.

Não há suíte de testes formal. Para validar de verdade, usar o **test client** do Flask com os IGCs reais em `igcs/` e conferir contra `relatorios-paradigmas/`. Valores de referência (não regredir):
- **Venet (N1):** 11/18 TP, SP→FP **01:00:47**, horários de hit ao segundo.
- **Melk (N2):** HG 26, erros TG/FP **19/6/57/116**. **Leandro (N2):** HG 16, erros **190/70**.
- **Ranking N2 (4 pilotos):** Melk 1000 · Leandro 314 · Paulo 0 (idêntico ao `N2-score`).
- Estatísticas de voo (decolagem/pouso/tempo/altitude máx) idênticas ao paradigma.

## Arquitetura (`webapp/apurador/`)

- **`__init__.py`** — `create_app()` (Flask factory; registra filtros Jinja `clock/dur/km/one` e blueprints).
- **`state.py`** / **`storage.py`** — **fachadas finas** que delegam à camada `repo/` (backend `files` ou `sqlite`, por `APURADOR_BACKEND`). `state` = pilotos por sala com **dedupe por BIB** (data mais recente); `storage` = provas/competições. Slug de prova sempre minúsculo (no backend `files` vem do nome do arquivo: `prova-N1-navegacao-pura.json` → `n1-navegacao-pura`).
- **`repo/`** — `files_backend.py` (JSON + memória, histórico), `sqlite_backend.py` (disco persistente — fixes comprimidos em gzip; tabelas `provas`/`mapas`/`pilots`), `migrate.py` (JSON→SQLite e `--split` provas→mapa+prova), `base.py` (interface). **Mapas** ficam em `data/mapas/*.json` (files) ou tabela `mapas` (sqlite). `get_prova()` **HIDRATA** a geometria do mapa (`map_slug`) na Prova → scoring/mapdata/PDFs recebem uma Prova completa, sem mudar o `core`.
- **`models.py`** — `Mapa` (geometria reutilizável) + `Prova` (`map_slug` + scoring); `hydrate(prova, mapa)` copia geometria. Áreas têm 3 cores: `kind` proibida(vermelho)/atencao(amarelo)/livre(verde).
- **`core/`** — núcleo portado e validado:
  - `geo.py` — Haversine `dist()` (metros; NÃO alterar). Aditivas p/ N3: `dist_to_polyline_m`, `dist_to_segment_m`, `route_length_m`, `densify_polyline`.
  - `igc.py` — `parse_igc()`: headers `HFPLT/HFCID/HFDTE` + B-records por offsets **fixos** 1–34. IGCs do Gaggle têm I-record (extensões) após a posição 35 — ler só offsets fixos; **NÃO** mudar para parsing dependente do tamanho da linha. Tempos UTC.
  - `models.py` — `Prova` (campos extra: `route` corredor N3, `landings` pousos), `Point`, `Pilot`; `Prova.mapdata()` gera o JSON do endpoint. **A3 = QGIS** (`qgis_render.py` PyQGIS headless + `qgispdf.py` wrapper subprocesso, estilo AITA; `mappdf.py` é **fallback** reportlab, usado no dev/sem-QGIS). `pointspdf.py` gera a folha A4 de pontos. Liga/desliga o QGIS por env `APURADOR_QGIS=1`.
  - `scoring.py` — `evaluate()` (detecção de hit + stats + cobertura de corredor N3) e `score_prova()` (N1/N2/N3).
  - `timefmt.py` — `clock()` (UTC→local pelo `tz` da prova), `dur()`.
- **`routes/`** — `auth.py` (login/logout por sessão), `api.py` (`/api/sala/<slug>/mapdata`, `/trackdata`, `/state/reset`), `main.py` (igcupload público, viewer, scores, competicoes, upload/tracks, relatorio, relatorio_pdf, **prova_config** = `/prova/<slug>/config`, **builder** = `/builder[/<slug>]` + `/builder/save`).
- **Editor de Mapa** (`/mapas`, `static/js/mapa_editor.js`). **Referência de mapa = mapas AITA (QGIS), não o programa do Marcinho.** **Etapa 1** "Novo Mapa": nome, escala, **orientação (retrato/paisagem)**, base (topo/satélite/OSM), teto AMSL, alt. mínima, bloco **EVENTO** (organizador/título/data/local) + posicionar a **folha A3**. **"Criar mapa" CAPTURA a área** → trava o mapa na folha (`setMaxBounds`; **zoom livre p/ precisão**), escurece fora. **Etapa 2** (barra estilo Earth Pro): **Mover · Adicionar ponto · Desenhar polígono · retângulo · círculo · Rota · Desfazer · Refazer** + **Salvar/Publicar/Preview**; painel **"Dados do Mapa"** (Estilo/Rodapé/Logo/Pontos(n)/Áreas(n)/Auto-calculados). Áreas via **Leaflet-Geoman** (polígono auto-fechável, verde/vermelho/amarelo; retângulo/círculo viram polígono). Rotas `/mapas/<slug>/mapa.pdf` (orientação respeitada, logo no rodapé) e `/pontos.pdf`. **A geometria mora aqui, não na prova.**
- **Construtor de Prova** (`/builder`, `static/js/builder.js`): **puxa um Mapa** (seletor; geometria vira preview somente-leitura) e define **tipo + scoring**. No modo legado (sem mapa) ainda desenha geometria inline. Editor sobre satélite Esri (grátis) + OSM/Topo. Pontos clicáveis (nome/tipo/raio/peso), áreas proibidas/atenção desenháveis, teto/altura mín/escala. Gera **hidden gates** (N2), **anéis de peso** (N1 — 2 anéis centrados no ponto médio SP–FP que dividem a prova em 3 faixas iguais até a borda da folha A3; raios derivados da folha, não fixos; peso 1·2·3 cresce com a distância), **rota/corredor curvo** (N3), renumeração de TP, **vértices de área editáveis** e **marcadores de pouso** (3.A3/3.A5). Salva como prova (JSON) + exporta KML. **Mapa A3 PDF estilo AITA via QGIS** (`apurador/qgis_render.py`+`qgispdf.py`; `mappdf.py` é fallback) → `/prova/<slug>/mapa.pdf`; **folha A4 de imagens dos pontos** (recorte satélite Esri) em `apurador/pointspdf.py` → `/prova/<slug>/pontos.pdf`. As 3 fases de produção de mapa estão entregues (ver `docs/ESPEC-PRODUCAO-MAPAS.md`). **UI condicional ao tipo** (`data-types`/`applyTypeUI()`): só mostra o que se aplica a n1/n2/n3 — mesma regra em `/prova/<slug>/config`. Tem **seletor "próximo ponto"**, **rascunho automático** (localStorage) + aviso de não salvo, **Salvar** vs **Salvar como nova**, e **validação** no salvar (SP/FP, N3 rota, raios) no cliente e em `builder_save`. Pontos clicáveis (nome/tipo/raio/peso), áreas proibidas/atenção desenháveis, teto/altura mín/escala. Gera **hidden gates** (N2), **anéis de peso** (N1 — 2 anéis centrados no ponto médio SP–FP que dividem a prova em 3 faixas iguais até a borda da folha A3; raios derivados da folha, não fixos; peso 1·2·3 cresce com a distância), **rota/corredor curvo** (N3), renumeração de TP, **vértices de área editáveis** e **marcadores de pouso** (3.A3/3.A5). Salva como prova (JSON) + exporta KML. **Mapa A3 PDF estilo AITA via QGIS** (`apurador/qgis_render.py`+`qgispdf.py`; `mappdf.py` é fallback) → `/prova/<slug>/mapa.pdf`; **folha A4 de imagens dos pontos** (recorte satélite Esri) em `apurador/pointspdf.py` → `/prova/<slug>/pontos.pdf`. As 3 fases de produção de mapa estão entregues (ver `docs/ESPEC-PRODUCAO-MAPAS.md`). **UI condicional ao tipo** (`data-types`/`applyTypeUI()`): só mostra o que se aplica a n1/n2/n3 — mesma regra em `/prova/<slug>/config`. Tem **seletor "próximo ponto"**, **rascunho automático** (localStorage) + aviso de não salvo, **Salvar** vs **Salvar como nova**, e **validação** no salvar (SP/FP, N3 rota, raios) no cliente e em `builder_save`.
- **`templates/`** — Jinja2 (Bootstrap + Leaflet); **`static/`** — `igcupload.js`, `viewer.js`, `app.css`.

## Pipeline de scoring — pontos chave

- **Tipos de ponto:** `SP` (largada), `FP` (chegada), `TP` (turnpoint), `HG` (hidden gate, valida trajeto), `TG` (time gate, confere tempo).
- **Raios (confirmado no vídeo do paradigma):** N1 = 200 m em todos; **N2 = SP/FP 200 m, intermediários (TP/HG/TG) 150 m**. Raios **ajustáveis** em `/prova/<slug>/config` (global por tipo + override por ponto), persistidos no JSON via `storage.save_prova()`. `Emax=300 s` confirmado pelo vídeo ("Lim (s): 300").
- **Marcação do "hit" = APROXIMAÇÃO MÁXIMA ao centro** (`hit_t` = instante de menor distância), usada em "Hora do hit", dist. ao centro, **tempo SP→FP** e no **"Voado" dos time gates** (gate e SP referenciados pelo hit_t). **Confere EXATO com o paradigma** — N1 Venet (13 hits) e N2 Melk (erros 19/6/57/116). `entry_t` (1ª entrada no raio) fica guardado mas NÃO é usado no scoring. `evaluate()` também calcula stats de voo (decolagem/pouso, alt máx, dist/tempo/vel SP→FP).
- **N1 (Navegação Pura) = FAI 3.A1 Pure Navigation** (paramotor, Part 3 — NÃO a 2.A1 de microleves). Score padrão **relativo `max_points × NBp/NBmax`** (TP válidos do piloto ÷ melhor entre não-DQ); opção `percent` (TP/total) em `score_model`. **Janela de tempo (`window_min`, padrão 60):** DQ se os **minutos completos** de SP→FP **> window_min** (regra: segundos só desclassificam após completar o minuto seguinte — 60:47→60 válido, 61:00→61 DQ). "Tempo acima do alvo" é flag informativo (3.A1 não gradua tempo, só a janela).
- **N2 (Tempo declarado):** Total (máx 1000) = ScoreHG + ScoreTG + ScoreVel. **Os caps `w_hg/w_tg/w_vel` são configuráveis por prova** (no paradigma: "Caps (pesos máx)"). Defaults do nosso código = **calibrados contra o Paranapanema**: **HG 400 / TG 200 / Vel 400** (reproduz Melk 1000 — `validate.py` verde). ⚠️ **O default genérico do paradigma-demo é o split OPOSTO (DECL/TG 400 / VEL 200)** — não confundir default de UI com a config real da prova; sempre conferir o cap configurado na prova.
  - **`Score HG = w_hg × HG_piloto / melhor_HG`** — **CONFIRMADO exato** contra os relatórios reais.
  - **`Score TG = w_tg × Qt / melhor_Qt`**, com `Qt = Σ max(0, Emax − erro_ef)` sobre os **TG E o FP** (o FP entra como ponto de tempo — coluna "Erro FP"), **`Emax=300 s`**. **CALIBRADO exato** contra o N2-score (Melk 200, Leandro 67,9, Paulo/Venet 0).
  - **Tolerância `tol` (regra da prova, padrão 5 s):** banda morta — `erro_ef = 0 se |erro| ≤ tol senão |erro|`. NÃO é subtração linear (essa quebra a calibração). O erro EXIBIDO continua cru; só o Qt usa `erro_ef`. Cada piloto declara seus PRÓPRIOS tempos (não são comuns — Leandro difere de Melk/Marcelo).
  - **Score Vel** (`w_vel`): relativo entre os *finishers* dentro do prazo (`vel_window_min`); `melhor_tempo/tempo`, senão 0. Corresponde a **`Qv = Vs × S/Smax`** do regulamento (3.A6/3.A7). Com `vel_window_min` ~50 min, o ranking dos 4 reproduz o paradigma (Melk 1000/Leandro 314/Paulo 0). Falta só calibrar a magnitude com 2+ pilotos de Vel>0 (ver `docs/ROADMAP.md` B5).
  - Pesos `w_hg/w_tg/w_vel/emax` ficam em `Prova` (configuráveis).
- **N3 (Navegação em Curva / Curve Navigation) = FAI 3.A2 (corredor curvo).** Sala que estende o paradigma (NÃO existe no original do Alan Braga). A prova tem um **corredor curvo** `prova.route = {coords:[[lat,lon],...], width}` (largura TOTAL em m) + cilindros **SP/FP**. Score = `max_points × inside_ratio`, onde `inside_ratio` = fração das amostras da rota (densificadas a 50 m) visitadas por algum fix dentro do corredor (janela entre os hits de SP e FP). Gate: sem SP **e** FP cruzados → 0. Reaproveita a **janela de tempo** do N1 (`window_min`). Geometria em `core/geo.py` (`dist_to_polyline_m`, `densify_polyline` — aditivas, não tocam `dist`). **⚠️ MODELO NÃO-CALIBRADO** — não há relatório real de corredor (mesma situação do Score Vel/B5); confirmar contra dado real quando houver. N1/N2 permanecem intocados.
- **Corte de validade:** sem cruzar SP/FP/TP válidos → score 0, mesmo com HGs.

## Persistência e Deploy

- **Backends plugáveis** por env `APURADOR_BACKEND` (camada `apurador/repo/`): `files` (default — provas em `data/provas/*.json` + pilotos EM MEMÓRIA; usado em dev e na validação sagrada) ou `sqlite` (provas + competições + pilotos/tracks em `data/aeronav.db`; sobrevive a restart). `storage.py` e `state.py` são **fachadas finas** que delegam ao repo — assinaturas preservadas, rotas não mudam. Migrar JSON→SQLite: `python3 -m apurador.repo.migrate`.
- **Deploy = VPS dedicado `ubuntu-vinhedo`** (NÃO Vercel/Supabase — app é stateful, serverless não encaixa). gunicorn + systemd + nginx (ou Cloudflare Tunnel), backend `sqlite`. Artefatos e passo a passo em `webapp/deploy/` (`README-deploy.md`, `aeronav.service`, `aeronav.nginx.conf`, `aeronav.env.example`). App escuta só em `127.0.0.1:8050`; **não derrubar** os serviços já ativos (gitea/redis/bind9/mediamtx).
- **⚠️ Manter a VPS sempre atualizada com o código novo (regra de trabalho).** Depois de qualquer alteração mergeada, **fazer o deploy na VPS** para que testes/debug aconteçam contra o app ao vivo (https://aeronav.helioandre.com). Fluxo: commitar/pushar → na VPS, `git pull` + `webapp/deploy/update.sh` (puxa código, instala deps, roda `migrate.py` se preciso, reinicia o systemd e checa o health). Não considerar uma mudança "entregue" enquanto a VPS estiver rodando código antigo.
- **Regressão:** `cd webapp && python3 validate.py` (harness que checa os invariantes sagrados N1/N2 + o invariante N3). Rodar antes e depois de mexer no scoring.

## Regulamento de referência

**FAI Section 10 Annex 4**, versão **2025** (em vigor desde 01/01/2025). Ao calibrar Score TG/Vel, usar o regulamento atual, não a edição 2020.

## Convenções

- **Stack fixa: Flask + Jinja2 + Bootstrap + Leaflet** (mesma do paradigma). Não trocar de framework sem alinhar.
  - **Exceção (alinhada com o Helio):** o **editor `/mapas`** (`templates/mapa_editor.html` + `static/js/mapa_editor.js`) usa **MapLibre GL JS + Terra Draw** — único jeito elegante de ter **rotação nativa do mapa + desenho sob rotação** (a folha A3 fica sempre na horizontal e o terreno gira; "recorte em qualquer ângulo, vista alinhada", com zoom ao vivo). Toolbar flutua **dentro** do mapa (estilo Earth Pro). **Só o editor** é MapLibre; **viewer/scores/builder de prova continuam Leaflet**. Mantém `bearing == frame.angle`; `frame={lat,lon,angle}` persiste centro+bearing. Contrato de dados (`/mapas/save`, `Mapa`, `/api/mapa/<slug>/mapdata`) inalterado — Terra Draw fala GeoJSON `[lng,lat]`, conversão p/ `[lat,lon]` é local ao editor. A3 PDF usa a **captura do canvas** (`/mapas/<slug>/capture` → `data/captures/<slug>.png`) como fundo; fallback = `mappdf._basemap` (tiles remontados).
- Backend modular em `apurador/` (core / routes / templates / static). NÃO voltar a single-file.
- API JSON deve **espelhar o paradigma** (mesmos caminhos e formato de `mapdata`).
- UI/labels e comentários de código em **PT-BR**.
- Provas são dados (JSON em `data/provas/`), não código — slug sempre minúsculo.
