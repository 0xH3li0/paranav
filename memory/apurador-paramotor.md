---
name: apurador-paramotor
description: "Projeto do app de apuração de provas de navegação de paramotor (réplica do \"Apurador 2.1\" de Alan Braga)"
metadata: 
  node_type: memory
  type: project
  originSessionId: cbf4af43-051c-4164-91dc-18ceef3ad673
---

Helio está construindo um app para apurar provas de navegação de paramotor, espelhando o "Apurador 2.1 / Paradigma" (cursoaita.alanbraga.app.br) de Alan Braga.

Pasta do projeto: "Programa de apuração de navegação de provas paramotor".
- `apurador.html` — versão completa inicial (4 tipos de prova). Substituída pelo foco em navegação.
- `apurador-navegacao.html` — versão focada em navegação (entregável principal).

Decisões: app web single-file (offline + publicável), em português. Foco em NAVEGAÇÃO primeiro.

Modelo do paradigma (engenharia reversa dos relatórios reais):
- Tipos de ponto: **SP** (largada), **FP** (chegada), **TP** (turnpoint), **HG** (hidden gate, valida trajeto), **TG** (time gate, confere tempo). Raio e peso por ponto (SP/FP 200m, demais 150m).
- Salas: **N1 Navegação Pura** (posição/sequência) e **N2 Tempo declarado**.
- **Score HG = 400 × HG_piloto / melhor_HG** (CONFIRMADO exato).
- Score N2 = Score HG (máx 400) + Score TG (máx 200) + Score Vel (máx 400) = 1000.
- Corte de validade: sem cruzar SP/FP/TP → score 0 mesmo com HGs.
- Fórmulas exatas de Score TG e Score Vel NÃO recuperadas a partir dos dados; implementadas em formato FAI (Emax=180) — precisam de calibração contra a fonte/regulamento.
- Relatórios são gerados em PDF (voo por piloto + tabela de scores).

Regulamento: Helio tinha o FAI Section 10 Annex 4 de 2020; a versão atual é 2025 (em vigor 01/01/2025).

Parser IGC validado com arquivos reais (Venet, Leandro) — tempos batem exatamente com o paradigma. IGC do Gaggle tem I-record (extensões) após posição 35; parser lê offsets fixos 1-34 corretamente.
