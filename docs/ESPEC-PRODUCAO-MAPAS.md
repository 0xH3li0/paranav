# Especificação — Produção de Mapas de Competição

Requisitos passados por instrutor/competidor (orientações para gerar o mapa da prova, hoje feito manualmente no Google Earth + QGIS). Objetivo: automatizar no app.

## 1. Folha de impressão (mapa)

- **Formato: A3.**
- **Escala (legenda de tamanho), opções:**
  - 1:50.000 → **2 cm = 1 km**
  - 1:100.000 → **1 cm = 1 km**
  - 1:150.000 (≈ 0,67 cm = 1 km)  *(obs.: a nota "0,5 cm = 1 km" equivale a 1:200.000; manter as três escalas listadas como padrão)*
- A folha precisa de uma **faixa de informações** contendo:
  - **Logo**
  - **Rosa dos ventos orientada** (alinhada ao norte; se a folha for inclinada, a rosa indica o norte real)
  - **Informações da prova**

### Principais informações que devem constar na folha
- Legenda da escala/tamanho
- Rosa dos ventos orientada
- Altitudes de voo (teto / altura mínima)
- Informações da prova

## 2. Cadastro de Mapas (modelo de dados)

- **Tamanho (escala):** 1:50.000 / 1:100.000 / 1:150.000
- **Pontos (clicável no mapa):** Nome, Raio
- **Áreas Proibidas e de Atenção (desenhável):** exibir em **vermelho** (proibida) ou **amarelo** (atenção)
- **Teto:** definir se houver
- **Altura mínima:** definir se houver
- **Imagens dos Pontos:** foto/recorte de cada ponto, em tamanho que **caibam vários numa folha A4** e que **cubra área maior que o raio**

## 3. Folha de Imagens dos Pontos (A4)

- Recorte (satélite) de cada ponto, enquadrando **área maior que o raio**.
- Vários pontos por folha A4 (grade).
- **Alinhados com a rosa dos ventos** (mesma orientação do mapa).
- Identificar nome/raio de cada um.

## Lembretes do autor
- Mapa **e** imagens dos pontos devem estar **alinhados com a rosa dos ventos**.
- Mapa fornecido em **A3** com espaço para logotipo e informações do mapa/prova.

---

## Plano de implementação proposto (fases)

**Fase 1 — Construtor de Prova (dados / "Cadastro de Mapas")**
Editor no app (Leaflet + satélite Esri World Imagery, grátis): pontos clicáveis (nome, tipo, raio; no N1 com anéis de peso), áreas proibidas/atenção desenháveis (vermelho/amarelo), campos Teto e Altura mínima, dados da prova. Salva como prova (JSON) e exporta KML. **Base de tudo.**
> **Atualização (jun/2026):** além do acima, o construtor agora desenha **rota/corredor curvo (N3)** — modo "Rota (N3)", vértices arrastáveis, largura do corredor, render do buffer; salva em `prova.route` e exporta como LineString no KML.

**Fase 2 — Exportação do Mapa A3 (PDF)** ✅ (jun/2026)
Página A3 na escala escolhida (escala fiel ao papel), com a faixa de informações: logo/marca, rosa dos ventos orientada, legenda de escala, teto/altura mínima, info da prova; pontos com raio, áreas e corredor N3 desenhados. Implementado em `apurador/mappdf.py` → rota `/prova/<slug>/mapa.pdf` (link em Scores). Verificado: 1 km = 20,00 mm em 1:50.000. Pendente opcional: fundo de satélite (raster) sob o vetor.

**Fase 3 — Folha de Imagens dos Pontos (A4)** ✅ (jun/2026)
Recorte de satélite (Esri) por ponto (vizinhança > raio), anel do raio + norte, grade na A4, nome/raio. Implementado em `apurador/pointspdf.py` → rota `/prova/<slug>/pontos.pdf` (link em Scores). Recortes north-up; pendente opcional: rotacionar pelo ângulo da folha.

As três fases estão entregues. (Fase 1: dados/builder; Fase 2: mapa A3 PDF; Fase 3: imagens A4.)
