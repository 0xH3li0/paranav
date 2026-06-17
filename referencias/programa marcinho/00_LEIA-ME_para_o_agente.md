# Capturas de tela — App "Mapas FAI" (gerador de mapas para provas de voo livre)

Estas 7 imagens foram extraídas de dois vídeos de demonstração do software (gravações de
tela filmadas com celular, daí o leve ruído/moiré). Servem como referência visual da
interface para reconstrução, documentação ou continuação do desenvolvimento.

Contexto: aplicação web (aparentemente em React, hospedada na Vercel) para gerar mapas de
provas de **voo livre / aerodesporto (FAI)**. A região exibida é o litoral sul de São Paulo
(Itanhaém). Interface em português.

## Índice das imagens

1. **01_form_novo_mapa.png** — Tela "Novo Mapa FAI". Formulário de configuração à esquerda
   (Nome do mapa, Escala ex. 1:50.000, Orientação = Paisagem, Teto em m AMSL = 1500,
   Alt. mínima (m) = 50, bloco EVENTO, botão "Criar mapa →") e preview do mapa de relevo à direita.

2. **02_form_data_evento.png** — Mesmo formulário com o seletor de **Data** (calendário) aberto
   e o bloco **EVENTO** (Organizador, Título da prova, Local).

3. **03_mapa_itanhaem_capturando.png** — Mapa de relevo da região de **Itanhaém (SP)** com
   rótulos de cidade; botão em estado de carregamento "Capturando mapa…".

4. **04_layout_completo.png** — Visão completa do app: **barra de ferramentas de desenho** no
   topo (Adicionar ponto / Desenhar polígono / Desenhar retângulo / Desenhar círculo /
   Desfazer / Refazer), mapa central e **painel "Dados do Mapa"** à direita.

5. **05_painel_dados_mapa.png** — Detalhe do painel direito "Dados do Mapa": Nome, Escala
   (1:50.000), Orientação, Estilo, Teto (1500), Altitude (50), Rodapé, Logo, Pontos, Áreas;
   e a alternância **Mapa / Satélite** no canto do mapa.

6. **06_mapa_com_marcadores.png** — Mapa topográfico com **marcadores (pontos azuis)** sobre
   o terreno e as ferramentas "Desenhar polígono / retângulo" visíveis.

7. **07_vista_satelite.png** — Mesma área em **vista de satélite** (faixa de praia / estrutura
   tipo píer), demonstrando a troca de camada base.

## Elementos de UI observados (para fidelidade na reconstrução)
- Navegação superior com itens: **Voos**, **Rankings**.
- Toggle de camada base: **Mapa / Satélite**.
- Ferramentas de desenho geoespacial: ponto, polígono, retângulo, círculo, desfazer, refazer.
- Campos de domínio aeronáutico: **Teto (m AMSL)**, **Altitude mínima (m)**, **Escala**.
- Painel de propriedades do mapa com Rodapé, Logo, contadores de **Pontos** e **Áreas**.
- Bloco de evento/prova: Organizador, Título da prova, Data, Local.
