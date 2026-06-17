# Índice da documentação — Apurador de Navegação (Aeronav)

Guia de leitura da pasta `docs/`. **Comece sempre pelo `CLAUDE.md` na raiz** (fonte da verdade), depois use este índice.

## Hierarquia de autoridade (em caso de conflito, vale o de cima)

1. **`/CLAUDE.md`** — fonte da verdade do projeto (stack, calibrações, convenções).
2. **Estado atual** (descrevem o que está construído e calibrado):
   - `ARQUITETURA-PARADIGMA.md` — engenharia reversa do app de referência.
   - `EVOLUCAO.md` — histórico/decisões (Fases 0–8).
   - `ROADMAP.md` — regras de trabalho com IA + backlog (DoD por item).
3. **Especificações de produção** (construtor de mapas):
   - `CONSTRUTOR-PLANO.md` — plano do construtor por tipo de prova.
   - `ESPEC-PRODUCAO-MAPAS.md` — requisitos de mapa A3/A4.
4. **Visão de produto / briefing** (NÃO sobrescrevem o estado atual nem as calibrações):
   - `BRIEFING-CLIENTE.md` — briefing do Márcio/Fabrício (14/06): escopo amplo, 3 navegações, modelo genérico.
   - `MODELO-DADOS-PROPOSTO.md` — esquema relacional idealizado (alvo futuro, não implementado).

> Os documentos de nível 4 foram escritos em nível *greenfield* e contêm defaults genéricos do FAI que **divergem** das calibrações reais. Tratá-los como **direção de futuro**, nunca como instrução de código.

## Glossário (briefing × projeto)

| Briefing (nível 4) | Projeto (em produção) | Regulamento (paramotor, Part 3) |
|---|---|---|
| `PURA` | **N1** · slug `n1-navegacao-pura` | `3.A1` Pure Navigation |
| `DECLARADA` | **N2** · slug `n2-tempo-declarado` | `3.A6` Navigation over a Known Circuit |
| `CURVE` | — (não existe) | **sem equivalente em paramotor** (`2.A1` é microleve, Part 2) |

## Calibrações sagradas (não regredir — repetidas aqui por segurança)

- `Emax = 300 s` (briefing diz 180 — ignorar). Banda morta `tol = 5 s`. Score TG sobre **TG + FP**.
- Hit = **aproximação máxima ao centro**. Raios N2: SP/FP 200 m, intermediários 150 m.
- Referências: Venet N1 11/18 TP, SP→FP 01:00:47 · Melk N2 19/6/57/116 · Ranking N2 Melk 1000 / Leandro 314 / Paulo 0.

## Pendências abertas (confirmar com o cliente)

- **P-Curve** — o briefing pede uma 3ª prova "Curve", mas **`Curve Navigation` (2.A1) é prova de MICROLEVE (Part 2)**; em paramotor (Part 3) não há prova Curve. Confirmar com o Márcio: (a) quer mesmo microleve? (b) ou um equivalente paramotor com rota desenhada — mais próximo de `3.A2` (precision route) / `3.A7` (unknown legs)?
- **P1–P6** — pendências de regra listadas no fim de `BRIEFING-CLIENTE.md` (HG na Pura, tolerância de tempo, área vermelha, pesos dos termos, formato de arcos, API do app do Fabrício).

> Resolvido nesta revisão: **paramotor = FAI Section 10 Annex 4, Part 3** (`3.A1–3.A7`). Confirmado no PDF em `Regulamento/`. Os códigos `2.A1/2.A2…` do briefing são da Part 2 (Microleves) e foram anotados como erro de citação.
