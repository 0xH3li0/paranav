# Readequação e Roadmap — guia de desenvolvimento com IA

Este documento aplica engenharia de prompts e boas práticas de desenvolvimento assistido por IA para que qualquer agente (ou pessoa) continue o projeto com **instruções precisas, verificáveis e à prova de regressão**.

## 1. Como trabalhar neste projeto (regras para a IA)

1. **Leia primeiro o contexto:** `CLAUDE.md` (fonte da verdade), depois `docs/ARQUITETURA-PARADIGMA.md`, `docs/EVOLUCAO.md` e o spec relevante.
2. **Tarefas pequenas e fechadas.** Uma tarefa = um objetivo com **critério de aceite** (ver §3). Não misturar features.
3. **Nunca quebrar as calibrações.** Antes de mexer em `core/scoring.py` ou nos dados de prova, rode a verificação (§2). Os valores de referência são sagrados:
   - N1 Venet: 11/18 TP, SP→FP 01:00:47, hits ao segundo.
   - N2 Melk: HG 26, erros 19/6/57/116. Leandro: HG 16, erros 190/70. Ranking: Melk 1000 / Leandro 314 / Paulo 0.
4. **Valide sempre contra dados reais** (`igcs/` + `relatorios-paradigmas/`), não contra suposições. Se um número divergir, investigar a causa antes de "ajustar".
5. **Não reintroduzir** o que foi decidido: nada de single-file HTML; stack fixa (Flask+Jinja2+Bootstrap+Leaflet); sem menção a "réplica/cópia".
6. **Documentar ao terminar:** atualizar `CLAUDE.md`/`docs/EVOLUCAO.md` e a memória quando algo relevante mudar.
7. **Dados ≠ código:** provas são JSON em `webapp/data/provas/` (slug minúsculo). `provas/` (raiz) guarda só os CSV de referência.
8. **VPS sempre atualizada:** após mergear, **fazer deploy na VPS `ubuntu-vinhedo`** (`git pull` + `webapp/deploy/update.sh`) para testar/debugar contra o app ao vivo (https://aeronav.helioandre.com). Uma mudança só está "entregue" quando a VPS roda o código novo. Ver `CLAUDE.md` → "Persistência e Deploy".

## 2. Verificação (rodar antes/depois de mexer no scoring)

Dois harness (rodar em `webapp/`):

- **`python3 validate.py`** — gate de regressão: invariantes geométricos **sagrados** N1/N2/N3 (Venet 11/18 TP + 01:00:47; Melk HG 26; Leandro HG 16; N3 voo exato = 1000 pts). Sem servidor; exit code ≠ 0 se regredir. **Rodar sempre antes e depois de mexer no scoring/dados.**
- **`python3 run_tests.py`** — suíte ampla (geo, parser, modelos round-trip, scoring, repos files+sqlite, rotas via test client, construtor, PDFs A3/A4, parse dos 50 IGCs do Paranapanema). Hoje passa **69/71** (2 falhas conhecidas: testes de `builder_save` sem mapa, anteriores à regra G2 — atualizar quando G2 fechar).

App de pé: `cd webapp && python run.py` → http://localhost:5050 (login admin@apurador.local / admin).

## 3. Backlog priorizado (cada item com Definition of Done)

### 🎯 Alinhamento de escopo — IA dos 4 módulos (prioridade)
> Fonte: `docs/ESCOPO-PRODUTO.md` (Márcio, 16/06). Alvo: nav `MAPA · PROVAS · COMPETIÇÕES · PILOTOS`. **Não tocar nas calibrações N1/N2** ao mexer (validate.py verde antes/depois).

- **G1 — Aba PROVAS = lista + "Nova Prova" (modal de mapa).** Hoje "Provas" abre o `/builder` direto.
  - **Aceite:** `/provas` mostra a lista das provas salvas; "Nova Prova" abre modal que lista mapas; ao escolher, cai no builder já com o mapa carregado.
- **G2 — Aposentar o "modo legado" do builder (desenho inline sem mapa).** Toda prova puxa um mapa.
  - **Aceite:** não há caminho de criar prova sem mapa; provas antigas sem `map_slug` continuam abrindo (compat).
- **G3 — Módulo PILOTOS.** Hoje só "Enviar IGC" + pilotos em memória/BIB.
  - **Aceite:** cadastro de piloto; **logbook** de IGCs por piloto; seleção de IGC para uma prova; **replay** do voo; tela de infos do voo (decolagem/pouso/tempo/alt máx).
- **G4 — Módulo COMPETIÇÕES com conteúdo do Márcio.** Hoje a aba é rasa.
  - **Aceite:** reservar mapa (impressão); puxar catálogo de pontos; puxar provas; inscrever pilotos do cadastro; definir data.
- **G5 — Renomear a nav para a sequência canônica.** Scores vira visão de resultado; "Enviar IGC" migra para PILOTOS.
  - **Aceite:** navbar = `MAPA · PROVAS · COMPETIÇÕES · PILOTOS`.

### ✅ Concluído (junho/2026)
- **Separação Mapa × Prova + Editor de Mapa.** Entidade `Mapa` (geometria: pontos/áreas/rota/folha A3/escala/teto/altura/logo) separada da `Prova` (`map_slug` + scoring). `get_prova()` **hidrata** a geometria → scoring/PDFs inalterados (regressão verde). Editor `/mapas` hoje em **MapLibre GL + Terra Draw** (rotação nativa; áreas verde/vermelho/amarelo — inicialmente foi Leaflet-Geoman, migrado na Fase 14), 2 etapas (escala+folha → desenho), logo no rodapé. Prova **puxa o mapa** (seletor + preview). Migração `migrate.py --split`. Persistência `mapas` em files+sqlite. **N3 renomeado p/ "Navegação em Curva".**
- **Fase 2 (a fazer) — Análise estilo Earth Pro:** régua (distância + **rumo magnético** via geographiclib/pygeomag, km/NM), **vento** (slider recalcula solo/deriva por perna), **simular voo** (fantasma na rota), **espaço aéreo** (sobreposição).
- **Fase 3 (a fazer) — Rota-auto + export:** rota ligando waypoints com distância/rumo por perna; **exportar GPX/WPT** (gpxpy) p/ GPS/XCTrack.
- **N3 — Curve Navigation (corredor curvo, FAI 3.A2).** Sala `type=n3`: corredor `prova.route={coords,width}` + SP/FP; score = `max_points × inside_ratio`. Geometria aditiva em `core/geo.py`; ramo N3 em `scoring.py`; UI scores/viewer; exemplo `prova-N3-rota-precisao.json`. **⚠️ não-calibrado** (sem dado real — ver B5). N1/N2 intocados. Invariante no `validate.py`.
- **B0 — Construtor: desenho de rota/corredor (N3).** Modo "Rota (N3)" no `/builder`: polilinha (vértices arrastáveis) + largura + buffer; salva em `prova.route` + KML.
- **B1 — Construtor: colocação de pontos.** Criação numerada (SP→TP…), peso pelo anel (N1), arraste ao vivo, renomear/remover na tabela e **"Renumerar TP"** (1..N). Round-trip salvar/reabrir validado.
- **B2 — Construtor: áreas e elementos.** Vértices de áreas **arrastáveis**; clique-direito remove vértice; clique na área remove-a. **Marcadores de pouso** (3.A3/3.A5): novo modo "🛬 Pouso", `prova.landings=[{name,lat,lon}]` (serializado, em mapdata, render em viewer + A3 + KML).
- **B3 — Fase 2: Mapa A3 (PDF) em escala fiel.** `apurador/mappdf.py` + rota `/prova/<slug>/mapa.pdf` (link em Scores). A3 paisagem, projeção em **escala real** (1 km = 20,00 mm em 1:50.000), rosa dos ventos **orientada pelo ângulo da folha**, faixa com marca/escala/teto/altura, pontos+raios, áreas, corredor N3 e pousos. Funciona em produção (reportlab 3.6 no Python 3.8).
- **B4 — Fase 3: Folha A4 de imagens dos pontos.** `apurador/pointspdf.py` + rota `/prova/<slug>/pontos.pdf` (link em Scores). Recorte de **satélite Esri** por ponto (vizinhança > raio), anel do raio + norte, grade na A4, nome/raio. Fallback gracioso por ponto se a rede falhar.
- **Deploy ao vivo:** **https://aeronav.helioandre.com** (Cloudflare Tunnel → gunicorn 172.19.0.1:8050 → systemd, backend sqlite). gitea e demais serviços intactos.
- **Revisão de usabilidade do Construtor (jun/2026):** painel em 5 cards; **UI condicional ao tipo** (HG só N2, Anéis só N1, Rota/corredor só N3, raio interm. só N2, janela só N1/N3) no `/builder` **e** no `/prova/<slug>/config`; **seletor "próximo ponto"**; **rascunho automático** (localStorage) + aviso de não salvo; **Salvar** vs **Salvar como nova** (slug robusto, sem sobrescrever); **validação** ao salvar (SP/FP, N3 rota, raios) no cliente e servidor. Bugs corrigidos: vértices de área como marcadores arrastáveis (fim do clique-cria-ponto e do mapa travado), `stopPropagation` correto, escape HTML/XML (KML válido), PDFs tratam prova sem pontos.
- **B6 — Persistência robusta (SQLite).** Camada `apurador/repo/` plugável (`files`|`sqlite`) + `migrate.py`. Backend `sqlite` faz tracks sobreviverem a restart. Validado (paridade + persistência).
- **B7 — Publicação online (VPS).** Decidido **VPS `ubuntu-vinhedo`** (não serverless — app stateful). Artefatos em `webapp/deploy/`. Rollout no servidor pendente (definir domínio/tunnel).
- **`validate.py`** — harness de regressão (§2). Restaurada a prova N1 (sobrescrita por um teste "TESTE BARRETOS").
- **Higiene de arquitetura + reconciliação de docs (jun/2026).** Helpers extraídos (`core/slugs.py`, `pdfcommon.py`); `gen_report.py` → `apurador/report.py` (import relativo, sem hack de `sys.path`); rotas de PDF isoladas em `routes/pdf.py` (mesmo blueprint `main` → endpoints inalterados); `repo/base.py` Protocol ganhou os métodos de mapa; `TYPECOL` morto removido dos geradores; credencial dev do login só em `DEBUG`. CLAUDE.md/docs/memória alinhados ao código (editor = MapLibre+Terra Draw; suíte `validate.py`+`run_tests.py`; A3 = QGIS). `validate.py` verde · `run_tests.py` 69/71.

### B1 — Construtor: colocação de pontos (passo 2) ✅ (ver "Concluído")

### B2 — Construtor: áreas e elementos (passo 3) ✅ (ver "Concluído")

### B3 — Fase 2: Mapa A3 (PDF) em escala fiel ✅ (ver "Concluído")
Atende o aceite: 1 km = 20,00 mm em 1:50.000 (exato); rosa orientada pela rotação. Pendente opcional: fundo de satélite (raster) sob o mapa — hoje é vetorial (pontos/áreas/corredor/grade).

### B4 — Fase 3: Folha A4 de imagens dos pontos ✅ (ver "Concluído")
Recortes north-up (tiles Esri são north-up) com indicador de norte por célula. Pendente opcional: rotacionar os recortes pelo ângulo da folha quando `frame.angle ≠ 0`.

### B5 — Score Vel (confirmar fórmula exata)
- **Bloqueado por dado.** Estrutura = `Qv = Vs × S/Smax` (regulamento). 
- **Fazer quando houver dado:** obter um Scores do paradigma com **Vel > 0 para ≥ 2 pilotos** e calibrar; definir `vel_window_min` real do briefing.
- **Aceite:** reproduzir o Vel de ≥ 2 pilotos na casa decimal.

### B6 — Persistência robusta ✅ (ver "Concluído")
Backend `sqlite` via `apurador/repo/`. Resta opcional: persistir competições criadas pela UI.

### B7 — Publicação online ✅ (ver "Concluído")
No ar em **https://aeronav.helioandre.com** (Cloudflare Tunnel → gunicorn `172.19.0.1:8050` → systemd, backend sqlite). Deploy/atualização via `webapp/deploy/update.sh`. Ver `webapp/deploy/README-deploy.md`.

### B8 — Autenticação de piloto (BIB/PIN) e gestão de evento
- **Fazer:** cadastro de pilotos (BIB/PIN), como o paradigma; dedupe por BIB já existe.
- **Aceite:** piloto envia IGC autenticando por BIB/PIN.

---

### Itens do briefing do cliente (B9+) — visão de produto, fora do foco calibrado
> Origem: pendências P1–P6 em `docs/ESCOPO-PRODUTO.md`. **Não conflitam** com N1/N2 nem com as calibrações; entram como evolução. Antes de qualquer um, reler `docs/README.md` (hierarquia) e não tocar nos valores sagrados (Emax 300, tol 5, hit = aprox. máxima).

#### B9 — Prova "Curve" com arcos (refino da N3) — opcional
- **A N3 já existe** (Navegação em Curva, corredor curvo `prova.route`, FAI 3.A2) — ⚠️ **não-calibrada** (ver B5). Este item é o **refino**: suportar `RoutePath` com **arcos** (raio+ângulo / Bézier) além da polilinha atual, com tolerância espacial equivalente à régua de papel (ver P5 em `ESCOPO-PRODUTO.md`).
- **Aceite:** desenhar curva com arcos no editor, salvar e o track ser apurado contra a rota (sem regredir N1/N2).

#### B10 — Penalidade de backtracking (parametrizável)
- **Fazer:** detectar virada >90° saindo do corredor/rota ou reentrar antes de sair; penalidade **por prova** (paramotor nav = 100%; microleve = 50%). Não "zera" universal.
- **Aceite:** track com backtracking aplica a penalidade configurada; sem backtracking, score inalterado (não regredir N1/N2).

#### B11 — Área vermelha com efeito na apuração — BLOQUEADO por P3
- **Fazer (se confirmado):** campo `afeta_apuracao`/`penalidade` já previsto no modelo; ativar penalidade ao voar em área proibida. Hoje é só visual.
- **Aceite:** track que cruza área proibida com a regra ativa recebe a penalidade; com regra inativa, nada muda.

#### B12 — Declaração pré-decolagem (Declarada/Curve)
- **Fazer:** lock dos tempos declarados por gate na decolagem (`locked_at`); hoje os tempos são editados por piloto na config.
- **Aceite:** após o lock, a declaração não é mais editável e é a usada no scoring.

## 4. Convenções fixas
- Stack: **Flask + Jinja2 + Bootstrap 5.3.3 + Leaflet 1.9.4**. Backend modular em `apurador/` (core/routes/templates/static).
- UI/labels e comentários em **PT-BR**. Marca via `APURADOR_BRAND` (padrão Aeronav).
- API JSON espelha o paradigma (`/api/sala/<slug>/mapdata`). Slug de prova sempre minúsculo.
- Mapa de satélite: **Esri World Imagery** (grátis) + OSM/OpenTopoMap. Não usar tiles do Google (licença).

## 5. Definition of Done (geral)
- Critério de aceite do item satisfeito **e** verificação do §2 sem regressão.
- `node --check` nos `.js` alterados; app sobe sem erro.
- Docs/memória atualizados quando a mudança for relevante.
