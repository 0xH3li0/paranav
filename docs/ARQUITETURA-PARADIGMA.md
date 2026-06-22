# Mapeamento do "Apurador 2.1 / Paradigma"

Documento de engenharia reversa do app de referência (`cursoaita.alanbraga.app.br`, "Apurador 2.1", versão `2.2.0-full-aita`, de Alan Braga). Base para construir uma réplica com a mesma stack.

> Legenda de confiança: **[C]** confirmado por observação direta · **[I]** inferido com alta probabilidade.

---

## 1. Propósito

Apurar provas de **navegação de paramotor** a partir de tracks GPS (IGC) dos pilotos, comparando o trajeto voado com o percurso definido (pontos/cilindros), e gerando pontuação e relatórios. Classes de paramotor: **PF1, PF2, PL1, PL2** (o catálogo FAI separa "Microlights" de "Paramotors").

## 2. Stack tecnológica

**Frontend** [C]
- Páginas **renderizadas no servidor** (HTML server-side; templates estilo **Jinja2**, com marcadores de comentário `[ANCHOR:NAVBAR]`, `[ANCHOR:MENU_PROVAS]` etc.).
- **Bootstrap 5.3.3** (CSS/JS via jsDelivr) — layout, navbar, dropdowns.
- **Leaflet 1.9.4** (via unpkg) — mapa e camadas (tiles OSM).
- **JavaScript puro** (sem React/Vue/SPA). Funções do cliente: `ensureMap`, `clearLayers`, `drawWPTs`, `drawAirspaces`, `loadSala`, `parseIGC`, `igcToDec`, `drawTrackPreview`.
- O cliente **só faz pré-visualização** (parseia o IGC e desenha o trajeto/pontos); **não calcula score**.

**Backend** [I, forte]
- **Python server-side, provavelmente Flask + Jinja2** (HTML renderizado no servidor + pequena API JSON + sessão por cookie + redirect server-side para `/login`). O nginx mascara a assinatura exata do framework.
- **Autenticação por sessão** via cookie (login `POST /login` com `email` + `password`; **sem campo CSRF** visível). Cookie httpOnly.
- **Estado de trabalho em memória** [C]: o botão "Iniciar arquivo novo" chama `POST /api/state/reset` e "limpa IGCs, Pontos, Espaços Aéreos e configurações **em memória**". Ou seja, há um "documento de trabalho" mutável por sessão; **Competições** é a camada persistida de eventos.

**Infra** [C]
- Proxy **nginx** (`Server: nginx-more`), compressão **brotli** (`content-encoding: br`).
- Header próprio de aplicação: `x-apurador-aita: yes`.
- `Vary: Accept-Encoding, Cookie` (resposta varia por sessão).

## 3. Autenticação e papéis

- **Organizador**: login por **e-mail + senha** → acessa Viewer, Scores, Config, Competições, uploads, salvar/carregar prova. [C]
- **Piloto**: na página pública `/igcupload`, autentica com **BIB + PIN**, escolhe a **Sala** e envia o `.igc`. **Deduplica por BIB** (substitui se o novo for mais recente). [C]

## 4. Rotas / páginas

| Rota | Acesso | Função |
|---|---|---|
| `/login` | público | login do organizador (email+senha) |
| `/igcupload` | **público** | upload de track pelo piloto (BIB+PIN) + prévia no mapa |
| `/viewer` | login | visualizador de tracks/prova |
| `/scores` | login | tabela de pontuação |
| `/competicoes` | login | gestão de eventos (multi-prova) |
| `/config` | login | configuração |
| `/upload/tracks` | login | carregar IGCs (organizador) |
| `/upload/provas` | login | carregar pontos (WPT/KML) |
| `/upload/espacos` | login | carregar espaços aéreos |
| `/provas/save` · `/provas/load` | login | salvar/carregar prova |

## 5. API JSON

| Endpoint | Método | Acesso | Retorno |
|---|---|---|---|
| `/api/sala/<slug>/mapdata` | GET | **público** | geometria da prova da Sala |
| `/api/state/reset` | POST | login | zera o estado de trabalho em memória |

**Schema de `mapdata`** [C]:
```json
{
  "ok": true,
  "has_prova": true,
  "center": { "lat": -22.827, "lon": -42.522 },
  "wpts": [
    { "name": "SP", "type": "SP", "radius": 200, "lat": -22.8738, "lon": -42.5865 }
  ],
  "airspaces": []
}
```

## 6. Modelo de dados da prova

**Salas** (cada uma = uma prova/tipo): slugs `n1-navegacao-pura` e `n2-tempo-declarado`. [C]

**Tipos de ponto (wpt.type)** [C]:
- `SP` — Start Point (largada). Raio 200 m.
- `FP` — Finish Point (chegada). Raio 200 m.
- `TP` — Turn Point (turnpoint declarado).
- `HG` — Hidden Gate (valida o trajeto).
- `TG` — Time Gate (confere tempo declarado).
- Campos: `name, type, radius, lat, lon` (peso/`weight` aparece nos relatórios).

**Provas reais extraídas** (em `provas/`):
- **N1 — Navegação Pura**: 20 pontos (SP + 18 TP + FP), raio 200 m, tempo-alvo 60 min, deadline 10:45.
- **N2 — Tempo declarado**: 37 pontos (SP + 29 HG + 3 TP + 3 TG + FP), raio 200 m.

> **Extensão fora do paradigma — N3 (Curve Navigation / Rota de Precisão, FAI 3.A2):** o paradigma do Alan Braga só tem N1 e N2. O app adiciona a sala **N3**, baseada num **corredor curvo** (`prova.route`), com score por cobertura da rota. **Não há relatório do paradigma para validar** → modelo **não-calibrado** (ver `docs/ROADMAP.md`). Não altera N1/N2.

## 7. Pipeline de apuração (server-side)

1. Define a prova (pontos por tipo/raio/peso) — Sala.
2. Pilotos enviam IGC (dedupe por BIB) ou organizador carrega em lote.
3. Para cada piloto: parseia IGC → detecta passagem (1ª aproximação dentro do raio, em ordem) → calcula estatísticas de voo.
4. Pontua conforme o tipo de Sala.
5. Renderiza Scores (tabela) e Relatório de voo (por piloto), com saída em **PDF**.

**Estatísticas de voo (relatório)** [C, batem na casa exata com nosso parser]:
decolagem/pouso (hora local), tempo de voo, altitude máxima, SP→FP (tempo/distância/velocidade média), e tabela de pontos: `Cruzado / Válido / Hora do hit / Distância ao centro`.

**Pontuação N1 (Navegação Pura)**: por TP válidos (cruzados na ordem), com penalidades por deadline e tempo-alvo. Pontos do percurso normalizados.

**Pontuação N2 (Tempo declarado)** — Total (máx 1000) = **Score HG + Score TG + Score Vel**:
- **Score HG = wHG × (HG_piloto / melhor_HG)** — `wHG=400`. **[C] confirmado exato** (Leandro 246,2; Paulo 92,3).
- **Score TG** (`wTG=200`) — `Score TG = wTG × Qt / melhor_Qt`, com `Qt = Σ max(0, Emax − |erro|)` sobre os **TG e o FP** (o FP é ponto de tempo — coluna "Erro FP"), **`Emax = 300 s`**. **[C] CALIBRADO exato** contra o N2-score (ajuste com erro ≈0,04: Melk 200, Leandro 67,9, Paulo/Venet 0).
- **Score Vel** (`wVel=400`) — velocidade SP→FP relativa entre *finishers* dentro do deadline; quem passa o FP após o deadline → 0. Estrutura bate (Melk 400, demais 0); **valor exato a confirmar** (só há um valor não-nulo nos dados).
- **Corte de validade**: sem cruzar SP/FP/TP válidos → score 0 (mesmo com HGs). [C]

> Detecção de hit (**RESOLVIDO**): adotamos a **aproximação máxima ao centro** (`hit_t` = instante de menor distância) — bate EXATO com o paradigma (N1 Venet 13 hits Δ0; N2 Melk 19/6/57/116). O `entry_t` (1ª entrada no raio) fica guardado mas **não** é usado no scoring. Detalhe em `CLAUDE.md` → "Pipeline de scoring".

## 8. Detalhes do IGC

- Lê headers `HFPLT` (nome), `HFCID` (BIB, quando presente), `HFDTE` (data). BIB do piloto vem do cadastro (BIB+PIN), não do IGC.
- B-records por offsets fixos 1–34. IGCs do Gaggle têm I-record (extensões) após a posição 35 — ler só os offsets fixos.
- Tempos em UTC; converter para local pelo fuso da prova (ex.: UTC−3).

## 9. Regulamento de referência

FAI **Section 10 Annex 4** (Task Catalogue). Versão em vigor: **2025** (desde 01/01/2025). Famílias de prova: Navegação, Economia, Precisão.

---

## 10. Réplica proposta (mesma stack)

| Paradigma | Réplica |
|---|---|
| Flask + Jinja2 | Flask + Jinja2 |
| Bootstrap 5.3.3 + Leaflet 1.9.4 | idem (mesmas libs/CDN) |
| Sessão por cookie (email+senha) | Flask-Login (+ CSRF via Flask-WTF) |
| Estado em memória + Competições | SQLite (SQLAlchemy) para persistir provas/pilotos/competições |
| `/api/sala/<slug>/mapdata` | mesma API JSON |
| Scoring server-side | porta direta da lógica já validada no protótipo HTML (parser IGC, Haversine, fórmula HG) para Python |
| Relatórios PDF | WeasyPrint ou ReportLab |

A lógica de parsing/scoring do nosso protótipo HTML já foi **validada contra os dados reais** (tempos de voo e contagem de pontos batendo com o paradigma) e porta diretamente para Python.

> ⚠️ **Nota (histórico):** a tabela acima é a *proposta* da Fase 1. O que foi efetivamente construído difere em alguns pontos — PDFs via **reportlab/QGIS** (não WeasyPrint), **auth por sessão** simples (não Flask-Login/CSRF) e **sqlite3 puro** (não SQLAlchemy). A arquitetura real está em `CLAUDE.md` e `webapp/README.md`.

---

## Telas do paradigma — observação ao vivo (https://demo.paramotorpr.com.br/, jun/2026)

> **[C]** Tudo abaixo foi lido direto da demo ao vivo (**"Apurador 2.1", versão `2.2.0-demo`**). A demo está **sem dados carregados**, então estruturas/labels são confiáveis; comportamento dependente de dados (ex.: presets de score) fica como pergunta aberta.

### IA / rotas
`Provas` (dropdown: Novo / Salvar / Carregar Prova `/provas/load` / Carregar Track `/upload/tracks` / Carregar Pontos `/upload/provas` / Carregar Espaços Aéreos `/upload/espacos` / Configurar `/config` / Abrir mundo `/viewer?wid=new`) · `Viewer` `/viewer` · `Scores` `/scores` · `Competições` `/competicoes`.
> Pontos entram por **upload (WPT/KML/CSV)** e pilotos vêm dos **IGCs** — o paradigma **não tem criador de mapa nem cadastro/logbook de piloto**. Nossos módulos **MAPA** e **PILOTOS** (ver `ESCOPO-PRODUTO.md`) são extensões nossas.

### Config (`/config`) — confirma calibrações
- **Raios globais por tipo:** SP/FP, TP, HG, TG (m) + **override por ponto** (vazio = usa o global) + **Peso** por ponto.
- **Limite de altitude (m):** "0 desativa".
- **Declarações:** **`Tol (s) = 5`**, **`Lim (s) = 300`** → idêntico ao nosso `tol=5`, `emax=300`. **[C]**
- **Tempo de Prova:** `Alvo (min)` + `Tol (min) = 5` + **`Pen. na tol = 50%`** → tolerância graduada (não DQ duro). Ver pendência P2 em `ESCOPO-PRODUTO.md`.

### Scores (`/scores`)
- **Caps (pesos máx) — defaults de UI:** `TP 400 · HG 400 · DECL/TG 400 · VEL 200`. **São configuráveis por prova.** ⚠️ Esse split (TG 400 / Vel 200) é o **oposto** do calibrado no Paranapanema (TG 200 / Vel 400) — ver bloco N2 no `CLAUDE.md`.
- **Presets de combinação de termos** (seletor): `TP · TP+ · HG · HG+ · TG · TG+ · TP/HG · TP/HG+ · TG/HG · TG/HG+ · TP/HG/TG/Vel · TP/HG/TG/Vel+`. `TP` = Pura (nosso **N1**); `TP/HG/TG/Vel` = declarada (nosso **N2**). **[I]** O sufixo "+" e os combos intermediários **não têm tooltip na demo** → pergunta aberta (confirmar com Alan/Márcio ou com dados reais). **Não inventar semântica.**
- **Colunas da tabela [C]:** Nº · Piloto · Arquivo · Decolagem · Pouso · Tempo de voo · Alt máx · SP(hora) · FP(hora) · TPs · HGs · TGs · T SP-FP · SP→FP(min) · Distância · Velocidade · **Decl FP · Voado FP · Erro FP** (FP como ponto de tempo) · Score TG bruto · **Penalidade · DQ** · Score TP · Score HG · Score TG · Score Vel · Soma · **Soma pós penalização** · **Score (1000)**.
- Ações: `PDF · CSV · Declarar tempos · Configurar prova · Penalidades`. "Penalidades: ON/OFF".

### Viewer (`/viewer`)
- **Leaflet.** Bases: OSM · Carto (claro) · **Esri (satélite)** · branco.
- Toggles: **Ver Pontos · Ver Raios · Ver Corredores** · Espaços aéreos **OpenAir**.
- Marcadores SP/FP/TP/HG/TG, trilha IGC com altitude, **seletor de múltiplos voos**, painel estatístico lateral, export CSV/PDF.
> "Ver Corredores" mostra que **corredor de prova tem precedente no paradigma** — embora nosso **N3 siga não-calibrado** (falta relatório real). **[C]**

### Competições (`/competicoes`)
- Lista: `ID · Nome · Criada em · Ações (Abrir/Excluir)` + botão `+ Criar`. Exemplos na demo: **Light · Paratrike · Paramotor · Gincana** (categorias). Board por competição não inspecionado (sem dados).
