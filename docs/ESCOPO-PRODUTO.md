# Escopo do Produto — fonte canônica de O QUE construir

> **Autoridade:** este documento é a **fonte da verdade do ESCOPO/IA** (o que o produto é e como se organiza). Fica **abaixo das calibrações sagradas** (que mandam no *scoring*) e manda em tudo que for *escopo*. Em conflito de escopo, vale este doc. Ver `docs/README.md`.
>
> **Origem:** alinhamento com **Márcio Aita** (piloto/instrutor de paramotor que co-desenha o produto) em **16/06/2026**. Substitui o enquadramento antigo de "apurador com construtor anexado".

## O que o produto é

**Dois pilares:**

1. **Criador de Mapas** — editor do organizador para produzir mapas de navegação (geometria + folha A3 impressa). **Não tem app de referência — está sendo construído do zero.**
2. **Apurador de Provas** — engine de scoring a partir da trilha GNSS (IGC), espelhando o paradigma **https://demo.paramotorpr.com.br/**.

## Arquitetura de informação — 4 módulos em sequência

A navegação principal segue **exatamente** esta ordem. Cada aba tem um escopo fechado; o que pertence a uma **não** vaza para a outra.

```
MAPA  →  PROVAS  →  COMPETIÇÕES  →  PILOTOS
```

### 1. MAPA
- Criar mapa (editor `/mapas`).
- Criar imagem dos pontos (folha A4 de recortes).
- Armazenar **todos** os mapas.
- **Regra de separação (Márcio):** aqui ficam **somente mapas crus e sempre editáveis**. **NENHUMA prova** aparece nesta aba — mapa que já virou prova (pronta ou em edição) vive na aba PROVAS. Misturar confunde.

### 2. PROVAS
- A aba mostra a **lista de provas** (prontas e em edição) + botão **"Nova Prova"**.
- **"Nova Prova" abre uma janela para escolher um Mapa** (não começa em branco — toda prova **puxa um mapa**).
- Depois de escolher o mapa: **selecionar tipo de prova** → **adicionar pontos** (SP, FP, TP, HG, TG…) → **definir tempos** → salvar.
- Armazenar **todas** as provas.

### 3. COMPETIÇÕES
- **Reservar o mapa** (para impressão).
- **Puxar o catálogo de pontos**.
- **Puxar as provas**.
- **Inscrever pilotos** (puxando do cadastro de pilotos).
- **Definir a data**.

### 4. PILOTOS
- **Cadastrar pilotos**.
- **Envio de IGCs para o logbook** (cada piloto tem seu histórico de voos).
- **Seleção de um IGC para a prova**.
- **Replay do voo** (reproduzir a trilha).
- **Informações do voo** (estatísticas: decolagem/pouso, tempo, altitude máx, etc.).

## Tipos de prova (salas) suportados

São independentes da IA acima — uma Prova tem um **tipo**. Estado calibrado manda; ver `CLAUDE.md`.

| Tipo | Nome (UI) | FAI Part 3 | Calibração |
|---|---|---|---|
| **N1** | Navegação Pura | 3.A1 Pure Navigation | ✅ sagrada |
| **N2** | Tempo Declarado | 3.A6 Known Circuit | ✅ sagrada |
| **N3** | Navegação em Curva | 3.A2 (corredor curvo) | ⚠️ não-calibrado |

## Estado atual × escopo — GAPS conhecidos (jun/2026)

A IA acima é o **alvo**; o app ainda não a reflete 100%. Os gaps abaixo são backlog (detalhe e DoD em `docs/ROADMAP.md`), **não** descrições do que já existe:

- **G1 — Aba PROVAS deve ser uma LISTA + "Nova Prova" (modal de escolha de mapa).** Hoje o link "Provas" abre o `/builder` direto. Falta a tela-lista e o modal.
- **G2 — Builder não pode mais desenhar geometria "modo legado" sem mapa.** Toda prova puxa um mapa (regra do Márcio). O caminho inline-sem-mapa deve ser aposentado.
- **G3 — Módulo PILOTOS de verdade.** Hoje só há "Enviar IGC" + pilotos em memória/BIB. Falta: cadastro, **logbook por piloto**, seleção de IGC para prova, **replay**, infos de voo numa tela própria.
- **G4 — COMPETIÇÕES com o conteúdo do Márcio.** Hoje a aba é rasa. Falta: reservar mapa (impressão), puxar catálogo de pontos, puxar provas, inscrever pilotos do cadastro, definir data.
- **G5 — Renomear a nav para a sequência canônica** `MAPA · PROVAS · COMPETIÇÕES · PILOTOS` (Scores vira uma visão de resultado dentro de Competições/Provas; "Enviar IGC" migra para PILOTOS).

> Ao fechar um gap, **não tocar nas calibrações N1/N2** (`validate.py` verde antes e depois) e atualizar este quadro + o ROADMAP.

## Pendências de regra — confirmar com o Márcio

Perguntas abertas (não-conflituosas; herdadas do briefing antigo, que foi removido). Resolver antes de implementar o item de backlog correspondente:

- **P1 — Pura (N1) tem HG?** Coerente com FAI 3.A1 (só coleta) é **não** ter. Modelar sem HG; confirmar.
- **P2 — Tolerância de tempo (N1):** faixas escalonadas (ex.: 60/65/70 min) **ou** penalidade linear por segundo (modelo FAI)? Hoje há a janela `window_min`. Confirmar o esquema.
- **P3 — Área vermelha (proibida):** hoje é **só visual**. Deve impactar a apuração (no FAI, voar em proibida zera a prova)? O campo de penalidade já fica previsto, desabilitado.
- **P4 — Pesos dos termos** (Qh/Qt/Qv): fixos para a competição ou **configuráveis por prova**? (recomendado: configuráveis — já são `w_hg/w_tg/w_vel`.)
- **P5 — Curve (N3) / desenho de curvas:** formato dos arcos (raio+ângulo, três pontos, Bézier?) e a tolerância espacial em metros equivalente à régua de papel.
- **P6 — App do Fabrício:** escopo da integração e contrato de API.

> **Backtracking** (penalidade parametrizável, ROADMAP B10): paramotor = **100%**, microleve = 50%. Não é "zera" universal.
