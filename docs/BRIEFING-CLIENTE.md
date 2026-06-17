# Briefing do Cliente — Visão de Produto (Navegação Aérea)

> ⚠️ **STATUS: documento de visão/requisitos (briefing Márcio/Fabrício, 14/06). NÃO é fonte de implementação.**
> **Hierarquia de autoridade:** `CLAUDE.md` (fonte da verdade) → docs de estado atual (`ARQUITETURA-PARADIGMA`, `EVOLUCAO`, `ROADMAP`) → este briefing. Em qualquer divergência, **vale o estado atual calibrado**, não este documento. Ver `docs/README.md`.
>
> **Conflitos conhecidos (não aplicar cegamente):**
> - **Emax:** este doc cita *default 180 s* (genérico do FAI). O valor **calibrado do projeto é 300 s** (confere com os dados reais N2). **NÃO** trocar o código para 180.
> - **Regulamento:** os códigos `2.A1`/`2.A2…` citados aqui são da **Part 2 (Microleves)**. Este apurador é de **paramotor → Part 3** (N1 = `3.A1` Pure Navigation, N2 = `3.A6` Navigation over a Known Circuit). **"Curve" (`2.A1`) é prova de microleve e não existe em paramotor** → pendência aberta (ver `docs/README.md`, P-Curve).
> - **Nomenclatura:** `PURA` ≡ **N1** · `DECLARADA` ≡ **N2**. Slugs em produção continuam `n1-navegacao-pura` / `n2-tempo-declarado`.
> - **Modelo de dados:** o esquema relacional proposto está em `MODELO-DADOS-PROPOSTO.md`; o estado atual é **em memória + JSON** e não deve ser migrado sem alinhamento (ver ROADMAP B6).

> Base normativa: **FAI Sporting Code, Section 10 (Microlights & Paramotors), Annex 4 — Task Catalogue, edição 01/01/2025.**
> Decisão do projeto: **seguir o Sporting Code à risca.**
> **Escopo do MVP (foco atual):** apenas as três provas de **navegação** — **Pura**, **Tempo Declarado** e **Curve** — incluindo **construtor de mapas** e **módulo de apuração**. As demais categorias (economia, precisão, ruído) ficam para evolução futura (ver Apêndice A).

---

## PARTE 0 — Escopo do MVP

Construir, para as três provas abaixo, o **construtor de mapas** (editor do organizador) e o **módulo de apuração** (scoring a partir da trilha GNSS).

| Prova | Elementos no mapa | Declaração do piloto | Termos de pontuação |
|---|---|---|---|
| **Pura** | SP + TPs + FP | Não | Coleta de pontos (ponderada por peso) e/ou distância |
| **Tempo Declarado** | SP + TG + TP (virada) + HG (oculto) + FP | Sim (tempos por gate) | Espacial (Qh) + Tempo (Qt) [+ Velocidade (Qv) se houver] |
| **Curve** | Curvas desenhadas + SP + TP e/ou TG + HG (oculto) + FP | Sim (tempos nas TG) | Espacial (Qh) + Tempo (Qt) [+ Velocidade (Qv)] |

Notas de composição (conforme alinhado com o Márcio, 14/06):

- **Pura:** só adicionar SP, TPs e FP no mapa, definir **tempo de prova** e **tolerância de tempo (se houver)**. Sem TG e sem declaração. (HG não foi citado para a Pura — modelar sem HG; ver pendência P1.)
- **Tempo Declarada:** SP → TG → TP (ponto de virada) → HG (oculto, só o organizador vê, para verificar precisão da rota) → FP.
- **Curve:** precisa permitir **desenhar as curvas no mapa** (a rota é uma linha curva arbitrária, não só pernas retas). Aceita SP, TP e/ou TG, HG (oculto) e FP.

---

## PARTE 1 — Correções às regras passadas inicialmente

Algumas regras do briefing inicial (WhatsApp) precisaram de ajuste para bater com o Annex 4. As corretas estão confirmadas; as incorretas, corrigidas.

### 1.1 TG vs TP vs HG (correção principal — confirmada pelo Márcio)

- **TP (Turn Point)** — ponto de virada/passagem. Validação essencialmente espacial. Símbolo: hexágono.
- **TG (Time Gate / Timing Gate)** — também chamado informalmente de "Turn Gate". Portão de controle nas provas de **navegação declarada** e **Curve** (NÃO de economia). Dupla função: (a) compara o **tempo declarado** pelo piloto contra o **tempo real** de cruzamento; e (b) **valida o sentido/direção da rota** — deve ser cruzado na **ordem e no sentido corretos**; cruzar ao contrário ou repetir invalida o gate. Símbolo: triângulo (△). SP/FP podem ser marcados com triângulo quando funcionam como time gate (SP△ / FP△).
  > Nomenclatura: usar **"Time Gate"** como nome oficial da entidade no código, para não colidir com "Turn **Point**" (TP). "Turn Gate" fica só como apelido.
- **HG (Hidden Gate)** — portão **invisível** ao piloto (não aparece no mapa), usado pelo organizador para verificar a precisão da rota. É o "ponto fantasma" do briefing inicial.

> Correção: o briefing inicial dizia "TG só em economia" — está **invertido**. TG é peça central das navegações declaradas; economia usa tempo total, não TG. → No software, o tipo do ponto (TP/TG/HG) é **atributo configurável e independente do tipo de prova**.

### 1.2 Backtracking — penalidade NÃO é sempre "zerar a prova"

O critério geométrico está certo (curva de mais de 90° saindo do corredor/rota, ou reentrar antes da saída), mas a **penalidade varia**:
- Navegação de microleve (S.10 4.24.5): **50%**.
- Navegação de paramotor: backtracking contra a direção ou cruzar HG ao contrário: **100%**.

→ Penalidade de backtracking **parametrizável por prova** (percentual ou pontos), não "zera" universal.

### 1.3 Pontuação relativa (1000 pts) — CORRETO, manter

`P = 1000 × Q / Qmax`. O melhor Q bruto da prova recebe **1000 pts** e define a escala dos demais. Provas de coleta/distância: `1000 × NBp/NBmax`. Manter exatamente.

### 1.4 Validação de ponto por entrar+sair do raio — CORRETO, com ajuste

Equivale à regra FAI: cruzado **uma vez, na ordem e no sentido corretos**; cruzar duas vezes **invalida**. Acrescentar ordem e sentido (o briefing inicial só citava a reentrada).

### 1.5 Critérios "Green" (pesos dos termos) — configuráveis, não fixos

A pontuação de navegação é a soma de termos normalizados: **Qh** (espacial/HG), **Qt** (tempo declarado vs real nas TG), **Qv** (velocidade). Os pesos (ex.: 25/50/25) são **escolha do organizador por prova**, não constante. Implementar como configuráveis.

### 1.6 Tolerância de tempo (ex-N1) — esclarecer

As faixas "60/65/70 min = 100/50/25%" **não constam do Annex 4** (que usa Tmax + penalidade por segundo) e havia contradição interna no briefing inicial. Tratar tolerância como **esquema configurável** e confirmar com o Márcio (ver pendência P2). Aplicável principalmente à **Pura** ("tempo de prova e tolerância se houver").

### 1.7 Banda morta de ±5s — configurável

Existe no FAI, mas valores variam (ANR ±1s e 3 pts/s; nav usa Emax típico 180s). Implementar banda morta e penalidade/segundo como **parâmetros**, com defaults por prova.

---

## PARTE 2 — Instruções de construção (MVP)

### 2.0 Princípio geral

Modelar **provas como composição de termos de pontuação configuráveis** e **tipos de ponto independentes do tipo de prova**. As três navegações compartilham os mesmos blocos; mudam apenas quais blocos/pontos estão ativos.

### 2.1 Construtor de mapas (editor do organizador)

Elementos a suportar no MVP:
- **SP / FP** — com opção de funcionar como time gate (SP△/FP△) e horário obrigatório de sobrevoo.
- **TP** — peso (1/2/3), valor em pontos, exige identificação por foto (opcional).
- **TG** — tempo declarado esperado, Emax (default 180s), banda morta, penalidade/segundo, sentido obrigatório.
- **HG** — invisível ao piloto; geometria raio ou linha; valor (Vh).
- **Curvas / rota desenhada** (essencial para a Curve) — polyline com segmentos retos e **arcos**, editável no mapa. Define a rota ativa para validação espacial. Se houver mais de uma track line ativa (ex.: cog wheel), todas são consideradas ativas.
- **Camadas:** montar pontos primeiro, depois sobrepor a elaboração da prova.

**Geometria de gates/raios:**
- HG e gates podem ser **raio (círculo)** ou **linha de comprimento definido**. Configurável por gate.
- A abertura/fechamento de tempo ocorre no **cruzamento do gate / passagem mais próxima do centro** do ponto.

**Áreas / polígonos coloridos (camada visual no MVP):**
- **Vermelho** = área proibida — **apenas visual/aviso por enquanto** (sem impacto na apuração no MVP; ver P3).
- **Amarelo** = atenção — visual/aviso.
- **Azul / Verde / Marrom** = ênfase de feições (rios e lagos / matas e plantações / desertos). Puramente visuais.
- Modelar como entidade de polígono com cor e rótulo; **deixar um campo de penalidade já previsto** (desabilitado por padrão) para quando/se a vermelha passar a valer na apuração.

### 2.2 Declaração do piloto (Declarada e Curve)

- Declaração **pré-decolagem** (lock ao decolar): tempos por gate (em segundos) e/ou sequência de pontos.
- Lógica sequencial: `SP-01, SP-02, … , SP-FP`.
- `Tmax` (tempo máximo SP→FP): nenhum tempo declarado pode ultrapassá-lo.

### 2.3 Módulo de apuração (engine)

**Detecção de cruzamentos (a partir da trilha GNSS):**
1. Gate/ponto só conta se cruzado **uma vez, na ordem e no sentido corretos**.
2. Cruzar o mesmo gate mais de uma vez (qualquer sentido) **invalida** aquele gate.
3. Se TG é cruzado mais de uma vez, o tempo vem do **primeiro** cruzamento.
4. Algoritmo de sequência fora de ordem (oficial): `1-2-4-3-5-6-5-7` → `1-2-4-6-7`.

**Termos de pontuação (somar os ativos, depois normalizar):**
- **Qh (espacial):** `Vh × Nh` ou, na Curve (2.A1), `1000 × H / Nh`.
- **Qt (tempo):** `Emax × Nt − Et` ou `Σ (Vt − Ei)`.
- **Qv (velocidade, se houver):** `Vs × S / Smax`.
- **Coleta/distância (Pura):** `1000 × NBp / NBmax`.
- **Normalização final:** `P = 1000 × Q / Qmax`.

**Penalidades (MVP):** backtracking (parametrizável), atraso para cruzar SP/FP, tempo excedido (por segundo). Quarentena e demais ficam disponíveis mas fora do foco inicial das três navegações.

### 2.4 Integração de tracking

- Apuração a partir de **trilha GNSS** carregada de gravadores (começar por importação de log; formato a definir).
- Arquitetar para aceitar também **stream em tempo real** (GSM/GPS) com plotagem da trilha — para evolução, não bloqueia o MVP.

---

## PARTE 3 — Pendências a confirmar com o Márcio

- **P1 — Pura tem HG?** O Márcio não citou HG na Pura (coerente com FAI 3.A1, que é só coleta). Modelar sem HG; confirmar.
- **P2 — Tolerância de tempo:** faixas escalonadas OU penalidade linear por segundo (modelo FAI)? Resolver a contradição "1h59s vs faixas".
- **P3 — Área vermelha:** hoje é só visual. Confirmar se em algum momento deve impactar a apuração (no FAI, voar em área proibida zera a prova). Campo de penalidade já fica previsto, desabilitado.
- **P4 — Pesos dos termos (Green):** fixos para a competição ou configuráveis por prova? (recomendado: configuráveis.)
- **P5 — Curve / desenho de curvas:** definir formato dos arcos (raio+ângulo, três pontos, Bézier?) e a tolerância espacial (em metros) equivalente à régua de mapa em papel.
- **P6 — App do Fabrício:** escopo da integração e contrato de API.

---

## Apêndice A — Evolução futura (fora do MVP)

Mantido como referência; **não implementar agora**.

- **Categoria A (demais navegações):** Precision Navigation (2.A2), Contract Navigation (2.A3), Navigation over Known Circuit (2.A4), Unknown Legs (2.A5), Turnpoint Hunt (2.A6), Circle (2.A7), ANR (2.A8).
- **Categoria B — Economia:** Pure Economy, Economy & Distance, Economy & Navigation, Economy & Precision, Speed Triangle. Usam tempo total (Tp/Tmax), seções (Lp/Lmax) e linhas de não-retorno; combustível limitado (15 kg solo / 22 kg biplace).
- **Categoria C — Precisão:** Spot Landing e variantes (deck 125×25 m, faixas 250→50, bônus de tempo), Precision Touchdown, alvos de paramotor, Four Sticks, Short Take-off, Fence, Fast/Slow, Bowling, Paraball, Wing Control. Entram como elementos integráveis com penalidade percentual limitada.
- **Categoria N — Ruído:** Noise in Climb, Minimum Noise in Level Flight (medição em dBA).
- **Operacional avançado:** quarentena (quebra = 100%), Le Mans start, gates ocultos secretos, identificação de fotos, limites de fotos por página/prova, penalidades de deck.
- **Área vermelha com efeito na apuração** (se P3 confirmar).
