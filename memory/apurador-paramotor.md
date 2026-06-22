---
name: apurador-paramotor
description: "App Flask de apuração de provas de navegação de paramotor (Aeronav) — ponteiros para a documentação canônica"
metadata: 
  node_type: memory
  type: project
  originSessionId: cbf4af43-051c-4164-91dc-18ceef3ad673
---

App **Flask** (`webapp/`) para apurar provas de navegação de paramotor, espelhando o paradigma **https://demo.paramotorpr.com.br/** (Apurador 2.x de Alan Braga). Dois pilares: **Criador de Mapas** (editor do organizador) + **Apurador de Provas** (scoring de IGC). Salas N1/N2 (calibradas) e N3 (corredor curvo, não-calibrado).

> Esta memória é só **ponteiro** — a fonte da verdade vive no repositório. Não duplicar calibrações aqui (para não contradizer). Em conflito, valem os arquivos abaixo.

- **Fonte da verdade:** `CLAUDE.md` (stack, calibrações sagradas, convenções, deploy).
- **Escopo / IA dos 4 módulos:** `docs/ESCOPO-PRODUTO.md` · **Backlog/DoD:** `docs/ROADMAP.md` · **Histórico:** `docs/EVOLUCAO.md` · **Eng. reversa do paradigma:** `docs/ARQUITETURA-PARADIGMA.md` · **Índice/hierarquia:** `docs/README.md`.

**Regra de ouro:** não quebrar as calibrações N1/N2 — rodar `cd webapp && python3 validate.py` (e `run_tests.py`) antes e depois de mexer no scoring. Os números sagrados (Emax 300, tol 5, raios, hit = aproximação máxima, referências Venet/Melk/Leandro) ficam **só** no `CLAUDE.md`.

> ⚠️ Histórico (não reintroduzir): o projeto começou como app **HTML single-file** (`apurador*.html`, já removidos → pivô para Flask) e o Emax foi calibrado de **180** (chute FAI inicial) para **300** (confirmado contra dados reais). Nem o single-file nem o Emax 180 voltam.
