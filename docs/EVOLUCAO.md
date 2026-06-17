# Evolução do projeto — Apurador de Navegação (Aeronav)

Histórico das decisões e marcos, do protótipo ao estado atual. Serve de contexto para quem (humano ou IA) for continuar o projeto.

## Linha do tempo

### Fase 0 — Protótipo HTML single-file
- App de página única (HTML+JS), foco em apurar navegação de paramotor, espelhando o "Apurador 2.1 / Paradigma" de Alan Braga.
- Validou a lógica de parsing IGC, Haversine e pontuação contra dados reais.
- **Decisão (Helio):** "HTML puro não faz mais sentido" → **pivô para Flask** com a mesma stack do paradigma. Protótipos HTML removidos; lógica portada para Python.

### Fase 1 — Engenharia reversa do paradigma
- Mapeado o app de referência (rotas, API, schema). Documentado em `docs/ARQUITETURA-PARADIGMA.md`.
- Achados: scoring é **server-side**; estado de trabalho **em memória**; endpoint público `/api/sala/<slug>/mapdata`; salas **N1 (Navegação Pura)** e **N2 (Tempo Declarado)**.
- **Extração das provas** N1 e N2 direto do endpoint público (sem login), salvas em `provas/` (CSV de referência) e `webapp/data/provas/` (canônico).

### Fase 2 — Réplica Flask + núcleo portado
- `webapp/` (Flask + Jinja2 + Bootstrap + Leaflet). Núcleo em `apurador/core/`: `igc.py`, `geo.py`, `models.py`, `scoring.py`, `timefmt.py`.
- Validação com IGCs reais: **Venet N1 11/18 TP**, tempos de voo idênticos ao paradigma.

### Fase 3 — Tipos de ponto, estatísticas e relatório
- Modelo SP/FP/TP/HG/TG com raio/peso por ponto. Estatísticas de voo (decolagem/pouso, alt máx, SP→FP, velocidade). Relatório de voo por piloto.

### Fase 4 — Calibração da pontuação (contra dados reais)
- **N2 = Score HG + Score TG + Score Vel** (corresponde à task FAI **3.A6**).
  - `Score HG = wHG × HG/melhor_HG` — confirmado exato.
  - `Score TG = wTG × Qt/melhor_Qt`, `Qt = Σ max(0, Emax−erro_ef)` sobre **TG + FP**, **Emax=300**, tolerância (banda morta) **5 s**. Reproduz Melk 19/6/57/116 e Leandro 190/70 ao segundo.
  - `Score Vel = wVel × melhor_tempo/tempo` entre finishers no prazo — corresponde a `Qv = Vs × S/Smax` do regulamento (3.A6/3.A7). Corte de Vel por prazo (`vel_window_min`).
- **N1 = FAI 3.A1**: `1000 × NBp/NBmax` (relativo) + **janela de tempo** (DQ se minutos completos SP→FP > janela; regra: 60:47 válido, 61:00 DQ).
- **Marcação do hit = aproximação máxima ao centro** (gate e SP). Bate exato com o paradigma (N1 Venet 13 hits Δ0; N2 Melk/Leandro idem). `entry_t` guardado mas não usado.
- **Raios N2 corrigidos**: SP/FP 200 m, intermediários 150 m (confirmado no vídeo do paradigma e relatórios).
- Regulamento de referência: **FAI Section 10 Annex 4 (2025)**, Part 3 (Paramotores), tasks 3.A1–3.A7.

### Fase 5 — Validação ponta-a-ponta dos 4 pilotos (N2)
- Com `vel_window_min` (~50 min): **Melk 1000, Leandro 314, Paulo 0** — idêntico ao `N2-score` do paradigma. HG/TG/Vel todos com base regulamentar.

### Fase 6 — Identidade visual própria (Aeronav)
- Marca **Aeronav** (configurável via `APURADOR_BRAND`), tema azul-marinho, removidas menções a "réplica/cópia".
- Relatórios PDF (`gen_report.py`) com **mapa OSM em alta resolução** (matplotlib+contextily), pontos coloridos/rotulados por tipo, selos, faixa de cabeçalho. Botão "Baixar PDF" server-side.

### Fase 7 — Competições, configuração e usabilidade
- Tela de Competições (ranking geral por BIB). Tela "Configurar prova" (raios, pesos, janela, tolerância, prazo de Vel, modelo de score). Entrada de tempos declarados por piloto.
- Abertura vai para o **login** (organizador); página do piloto em `/igcupload`. Atalho `Iniciar-Aeronav.command` (porta 5050, evita o AirPlay do macOS).

### Fase 8 — Construtor de Prova (produção de mapa) — EM ANDAMENTO
- Editor sobre satélite Esri (grátis): pontos clicáveis, áreas proibidas/atenção, teto/altura mínima, geração de hidden gates (N2) e anéis de peso (N1), salvar + exportar KML.
- **Passo 1 entregue:** busca de região + **folha A3** (escala 1:50k/100k/150k, tamanho real de solo, rotacionável e arrastável).
- Plano completo em `docs/CONSTRUTOR-PLANO.md`. Spec em `docs/ESPEC-PRODUCAO-MAPAS.md`.

### Fase 9 — Curve Navigation (N3), persistência SQLite e deploy VPS (jun/2026)
- **N3 — Rota de Precisão (corredor curvo, FAI 3.A2):** nova sala que **estende** o paradigma (não existe no original). Corredor `prova.route={coords,width}` + SP/FP; score = `max_points × inside_ratio` (cobertura da rota dentro do corredor). Geometria **aditiva** em `core/geo.py` (`dist_to_polyline_m`, `densify_polyline`), ramo `n3` em `scoring.py`, UI em scores/viewer, desenho no `/builder` (B0). **⚠️ modelo não-calibrado** (sem relatório real de corredor; confirmar quando houver — como o Score Vel/B5).
- **Persistência plugável (`apurador/repo/`):** backends `files` (default, dev/validação) e `sqlite` (produção, sobrevive a restart — B6). `state.py`/`storage.py` viraram fachadas. `migrate.py` popula o SQLite.
- **Deploy:** decidido **VPS `ubuntu-vinhedo`** após reavaliar Vercel/Supabase (descartados — o app é stateful e tem libs de PDF pesadas). Artefatos em `webapp/deploy/` (gunicorn+systemd+nginx/cloudflared).
- **Harness `webapp/validate.py`** (atende ROADMAP §2). Achado e corrigido: a prova N1 versionada havia sido **sobrescrita por um teste "TESTE BARRETOS"** — restaurada do CSV canônico.

### Fase 10 — Ampliação da superfície de testes (Paranapanema 2025)
- **Fonte:** igc.paramotorpr.com.br ("Apurador 2.2" de Alan Braga, 3º Open CABPP Paranapanema 2025, 03/10/2025).
- **50 pseudo-IGCs extraídos** de 8 salas (n1/n2/n4/n5/economia-classica/economia-light/e5/preciso-light) da página HTML do app (trackData embutido no HTML; API usa paths encriptados — inacessível). Método: `json.JSONDecoder().raw_decode(html, start)`. Salvos em `igcs/3o-open-paranapanema-2025/`.
- **Ranking completo** (3 categorias: Paramotor, Light, Paratrike) com todas as colunas, capturado e salvo em `relatorios-paradigmas/paranapanema-2025-scores.md`. Provas sem track (P1/P2/P3/P8/P1-2) pontuadas manualmente no admin — não têm arquivo IGC publicado.
- **Inferência de TPs N1:** `round(1000 × TP / 30)` valida ao inteiro para todos os Paramotor (Erick=30 TPs); Paratrike: Anderson=19 TPs.
- **Endpoints públicos descobertos:** `/uploads/<sala>/web/<file>.json` (JSON com altitude real) e `/kml/<sala>/web/<file>.json` (KML do track). Prova oficial (SP/FP/TP) protegida por ADMIN_KEY com paths criptografados — inacessível sem login.
- **Altitude atualizada: 41/50 IGCs (82%).** Fonte primária: endpoint `/uploads/` (~20 tracks, jun/2026). Fonte secundária: array `tracks` das provas demo (`demo_*.json`) — contém GPS+altitude de todos os pilotos salvos em cada prova, permitiu recuperar mais 21 tracks (salas N1, N2, N4, N5, ECOLIGHT). **9 IGCs permanecem com altitude=0** (BIBs 4/5/9 em e5+economia-classica; BIB24 em economia-light+preciso-light; BIB29 em n1) — salas sem prova demo e sem altitude no `/uploads/`.
- **Prova N1 inferida** (`relatorios-paradigmas/paranapanema-2025-prova-n1-inferida.json`): 23/30 TPs + SP + FP reconstruídos por clustering de viradas de bearing em 6 tracks, sequência pelo track do Erick (30/30 TPs). 7 TPs ausentes em gaps 09:54→10:01 e 10:16→10:25. **Não reproduz scores oficiais** — usável como mapa aproximado da área.
- **Demo instance (demo.paramotorpr.com.br):** Alan Braga forneceu acesso ao Apurador 2.2.0-demo (aberto, sem auth). Extraídas 9 provas via `/provas/download/<nome>.json`. Schema do 2.2 mapeado: `wpts` (array plano) + `radii` global + `score_settings.caps`. N1 demo tem 20 TPs (≠ 30 da prova real); 13/20 demo TPs estão a <300m dos TPs inferidos — mesmo venue, curso simplificado. N2 demo tem estrutura completa (46 HG + 3 TG). Provas salvas em `relatorios-paradigmas/demo-paranapanema-2025/` + convertidas para nosso formato.
- **Uso imediato:** testar parser, estatísticas de voo e carregamento em massa com 50 IGCs reais de 3 categorias/8 salas diferentes.

### Fase 11 — Construtor maduro (B1–B4) e produção de mapa completa (jun/2026)
- **B1:** colocação de pontos + "Renumerar TP" (1..N). **B2:** vértices de áreas arrastáveis/removíveis + **marcadores de pouso** (`prova.landings`). 
- **B3:** **Mapa A3 PDF em escala fiel** (`apurador/mappdf.py`, `/prova/<slug>/mapa.pdf`) — 1 km = 20,00 mm em 1:50.000, rosa dos ventos orientada pela rotação da folha. **B4:** **folha A4 de imagens dos pontos** (`apurador/pointspdf.py`, `/prova/<slug>/pontos.pdf`) — recorte de satélite Esri por ponto, anel do raio, grade. As 3 fases de produção de mapa entregues.
- Detalhe: reportlab 4.x incompatível com Python 3.8 do VPS (`usedforsecurity`) → fixado reportlab 3.6 via marker no `requirements.txt`.

### Fase 12 — Revisão de usabilidade do Construtor (jun/2026)
- **UI condicional ao tipo** (`data-types` + `applyTypeUI()` no `onchange`): cada ferramenta/campo só aparece onde se aplica, no `/builder` **e** no `/prova/<slug>/config`. Tabela de pontos só oferece os tipos válidos; trocar o tipo avisa sobre elementos incompatíveis.
- **Facilidade:** painel em 5 cards numerados + **seletor "próximo ponto"** (fim do "1º clique = SP").
- **Salvar o projeto:** **rascunho automático** em localStorage (restaurar/descartar) + `beforeunload`; **Salvar** vs **Salvar como nova**; slug robusto no servidor (nunca colapsa em `prova`).
- **Bugs corrigidos:** vértices de área viraram marcadores arrastáveis nativos (acabou o clique que criava ponto e o mapa que travava); `stopPropagation` correto; escape de HTML (tabela) e XML (KML válido); validação ao salvar (SP/FP, N3 rota, raios) no cliente e servidor; `prova_config` não corrompe mais os raios ao esconder campos; PDFs A3/A4 tratam prova sem pontos.

### Fase 13 — Separação Mapa × Prova + Editor de Mapa (Geoman) (jun/2026)
- **Pedido do cliente (Marcinho):** mapa e prova como tarefas separadas — criar vários mapas na área e, ao montar a prova, puxar o mapa desejado.
- **Modelo:** nova entidade **`Mapa`** (geometria: pontos tipados, áreas, rota, folha A3, escala, teto/altura, logo); **`Prova`** ganha `map_slug` + scoring. `get_prova()` **hidrata** a geometria do mapa → `core/scoring`, `mapdata` e PDFs **não mudaram** (71/71 testes verdes pós-migração, calibração N1/N2/N3 intacta). Persistência `mapas` em files (`data/mapas/*.json`) e sqlite (tabela `mapas`). Migração `migrate.py --split` dividiu as 3 provas em mapa+prova.
- **Editor `/mapas` (`mapa_editor.js`) com Leaflet-Geoman:** desenho de áreas por **polígono auto-fechável** (verde/vermelho/amarelo), edição/arraste/remoção de vértices nativos, waypoints tipados + raio, rota; fluxo em **2 etapas** (escala + folha A3 → desenho); **logo no rodapé** do A3 (`mappdf`). Prova **puxa o mapa** (seletor + preview somente-leitura).
- **2ª rodada de correções do editor:** **seletor de base na barra** (topo/satélite/OSM disponível após recortar); **A3 PDF agora com fundo raster** (tiles da base em escala fiel sob o vetor — `mappdf._basemap`, hidratação leva base/orientação/logo p/ a prova); **excluir mapa** (`/mapas/<slug>/delete` + `delete_mapa` nos backends; bloqueia se prova usa o mapa); CSS da barra (selects/inputs alargados — fim das "letras comidas").
- **Correções de UX/frontend do editor (após teste do cliente):** **tema unificado claro** (corrigido conflito `data-bs-theme=dark` × `app.css` claro — raiz dos erros de enquadramento); **menu reordenado** pelo fluxo lógico (Preparação: Mapas·Provas | Evento: Carregar Tracks·Scores·Competições·Viewer); folha A3 **sem ponto/linha central**, **borda vermelha com seletor de cor**, arrastável; **"Criar mapa" RECORTA** (clip-path — só o retângulo da área visível, resto oculto; zoom livre); barra com **Editar/Mover formas/Remover** (Geoman global modes) + Desfazer/Refazer; **Publicar** (`Mapa.published` + selo) e **Preview** (salva→abre A3) funcionando; **busca com autocomplete** (Nominatim); **localização inicial = geolocalização** do usuário.
- **Refinamento p/ o modelo do Marcinho (após vídeo de referência):** editor reescrito no fluxo **"Mapas FAI"** — Etapa 1 "Novo Mapa FAI" (nome/escala/**orientação retrato-paisagem**/base/teto AMSL/alt.mín/**EVENTO**) + posicionar folha; **"Criar mapa" captura/trava a área** (`setMaxBounds`, **zoom livre p/ precisão**, máscara escurecendo fora); Etapa 2 barra **Mover·Ponto·Polígono·Retângulo·Círculo·Rota·Desfazer·Refazer** + **Salvar/Publicar/Preview** e painel **"Dados do Mapa"** (Estilo/Rodapé/Logo/contadores/Auto-calculados). `Mapa` ganhou `orientation/style/organizador/titulo/local/data`; `mappdf` respeita a orientação. Vídeo analisado por extração de 48 quadros (ffmpeg embutido via `imageio-ffmpeg`).
- **N3 renomeado** de "Rota de Precisão" para **"Navegação em Curva" (Curve Navigation)**.
- Próximo (documentado, não feito): Fase 2 (régua/rumo magnético, vento, simular voo, espaço aéreo) e Fase 3 (rota-auto + export GPX/WPT).

### Fase 14 — Editor de Mapa migrado p/ MapLibre GL + Terra Draw (rotação nativa) (jun/2026)
- **Problema:** Leaflet+Geoman **não giram o mapa ao vivo** — não dava para "recortar em qualquer ângulo e a vista alinhar" mantendo desenho. Pesquisa ampla → solução elegante: motor com **rotação nativa** + lib de desenho que respeita a rotação.
- **Decisão (Helio):** migrar **só o editor `/mapas`** para **MapLibre GL JS 4.7 + Terra Draw 1.0** (via UMD/CDN, sem build). **Viewer/scores/builder de prova continuam Leaflet.** Toolbar **flutua dentro do mapa** (estilo Google Earth Pro).
- **Como ficou:** mantém-se **`bearing == frame.angle`** → a **folha A3 é uma caixa upright** (SVG overlay com máscara de recorte) e o **terreno gira por baixo**; girar (Ctrl+arraste ou controle "Norte") escolhe o ângulo do recorte sem inclinar a folha; **zoom ao vivo** para precisão. Pontos = anel (GeoJSON) + **marcador arrastável** + tabela; áreas (polígono/retângulo/círculo, cor por tipo via `areaKinds`) e rota = **Terra Draw** (modos + select/editar/arrastar/apagar). **Undo/redo** por snapshot.
- **Contrato de dados inalterado** (`/mapas/save`, `Mapa`, `/api/mapa/<slug>/mapdata`): Terra Draw fala GeoJSON `[lng,lat]`; conversão p/ `[lat,lon]` é local ao editor. **71/71 testes verdes** + regressão sagrada N1/N2/N3 intacta.
- **A3 PDF:** novo `POST /mapas/<slug>/capture` recebe o **PNG do canvas** (folha já girada/alinhada) → `data/captures/<slug>.png`; `mappdf._capture_bg` usa essa imagem como fundo em escala fiel; **fallback** = `_basemap` (tiles remontados) para mapas sem captura. (⚠️ orientação/flip do fundo a conferir visualmente no 1º uso.)

## Estado atual (resumo)
- **N1 e N2 apuram fiel ao paradigma** (números batem ao segundo / casa decimal); **N3** funciona (não-calibrado).
- App Flask completo (login, viewer, scores, competições, relatórios PDF, construtor com rota N3/pousos, **mapa A3 + folha A4 de pontos**). Persistência SQLite; deploy no VPS (`https://aeronav.helioandre.com`, Cloudflare Tunnel).
- **Superfície de testes:** IGCs originais (Venet/Melk/Leandro/Paulo) + **50 pseudo-IGCs do Paranapanema 2025** (8 salas, 3 categorias; 41/50 com altitude real; waypoints da prova oficial ainda aguardando Alan Braga).
- **Pendente:** calibrar N3 e Score Vel (B5) quando houver dado; auth de piloto BIB/PIN (B8). Opcionais: fundo de satélite no A3, rotação dos recortes A4 pelo ângulo da folha.
