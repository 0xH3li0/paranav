# Plano completo — Construtor de Prova

Plano de evolução do Construtor, baseado nas provas de **navegação de paramotor** do FAI Section 10 Annex 4 (2025), Part 3 (tasks 3.A1–3.A7), e na especificação de produção de mapa (`ESPEC-PRODUCAO-MAPAS.md`).

## A. Camada compartilhada (toda prova usa)

1. **Região + Folha A3** *(passo 1 — em construção)*
   - Buscar/navegar até a região; escolher **escala** (1:50.000 = 2 cm/km · 1:100.000 = 1 cm/km · 1:150.000).
   - Posicionar um **retângulo A3** com o tamanho real de solo correspondente à escala, **rotacionável** (folha inclinada, como o tutorial do Alan) e arrastável. Tamanhos de solo (A3 = 420×297 mm):
     - 1:50.000 → **21 × 14,85 km**
     - 1:100.000 → 42 × 29,7 km
     - 1:150.000 → 63 × 44,55 km
   - O ângulo da folha define a orientação da **rosa dos ventos** e o alinhamento das imagens dos pontos.
2. **Faixa de informações** (reservada na folha): logo, rosa dos ventos orientada, legenda de escala, altitudes (teto/altura mínima), dados da prova.
3. **Áreas proibidas (vermelho) / atenção (amarelo)** — desenháveis.
4. **Teto** e **altura mínima** de voo.
5. **Imagens dos pontos** (recorte de satélite por ponto, área > raio, alinhadas ao norte da folha).

## B. Por tipo de prova (o que o construtor precisa + scoring do regulamento)

| Prova | O que montar no construtor | Scoring (FAI) |
|---|---|---|
| **3.A1 Navegação Pura (N1)** | SP, FP, **array de turnpoints** (peso por faixa de distância — 2 anéis centrados no ponto médio SP–FP que dividem a prova em 3 faixas iguais até a borda da folha A3; raios derivados da folha; peso 1·2·3 cresce com a distância), **janela de tempo** | `1000 × NBp/NBmax` (turnpoints coletados ÷ melhor); DQ fora da janela. *Obs.: peso é anotação no mapa; o score atual não pondera por peso (calibrado).* |
| **3.A2 Navegação c/ rota de precisão** | SP/FP + array de TP + gates intermediários; corredor | navegação + erro de trajeto `Dp` |
| **3.A3 Navegação, Precisão e Velocidade** | TPs (coletar no tempo) + marcadores de pouso | `NBp/NBmax` + bônus decolagem/pouso |
| **3.A4 Navegação / Velocidade estimada** | TPs/gates com **tempos declarados** | `NBp/NBmax` + termo de tempo `T` (cap 300/250) |
| **3.A5 + Precisão** | + marcadores de pouso | idem 3.A4 + pousos |
| **3.A6 Navegação sobre circuito conhecido (≈ N2 Tempo Declarado)** | SP/FP, **hidden gates** (auto-interpolados nas pernas), **time gates** (tempos declarados), marcadores/fotos, opcional velocidade | **Q = Qh + Qt + Qv** · `Qh = Vh·Nh` · `Qt = Σ(Vt−Ei)` · **`Qv = Vs·S/Smax`** · `P = 1000·Q/Qmax` |
| **3.A7 Navegação com pernas desconhecidas** | rumos/instruções seladas, hidden gates, troca de perna por marcador | idem 3.A6 |

> O **Score Vel** que faltava confirmar É regulamentar: `Qv = Vs × S/Smax` (3.A6/3.A7) — velocidade relativa à maior. Bate com a nossa implementação (`w_vel × melhor_tempo/tempo`).
> Penalidades comuns: backtracking 100%, cruzar hidden gate ao contrário 100%, cruzar duas vezes invalida o gate, decolagem/pouso fora 20%.

## C. Saídas (produção de mapa)

- **KML/JSON** da prova (compatível com paradigma/GE). *(ok)*
- **Mapa A3 (PDF)** na escala, com faixa de informações + rosa dos ventos. *(Fase 2)*
- **Folha A4 de imagens dos pontos**, alinhadas ao norte. *(Fase 3)*

## D. Ordem de construção (passos)

1. **Região + retângulo A3** (escala, rotação, arrastar) ← começando agora
2. Colocação de pontos por tipo + tabela (já existe; melhorar UX: snap, numeração, peso por anel)
3. Áreas proibidas/atenção (já existe; melhorar edição de vértices)
4. Geração de hidden gates por perna (N2/3.A6) e anéis de peso (N1/3.A1) — já existe; refinar
5. Marcadores de pouso / fotos de ponto (3.A3/3.A5/3.A6)
6. Exportar **Mapa A3 PDF** (Fase 2) + **A4 de imagens** (Fase 3)
7. Salvar/recarregar prova com a folha e orientação
