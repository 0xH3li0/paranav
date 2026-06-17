# Funcionalidades — App "Mapas FAI" (gerador de mapas para provas de voo livre)

Lista de funcionalidades do software, organizada por módulo, com base na demonstração em vídeo.

**Legenda:** ✅ = já visível/funcionando no programa · 🔧 = a implementar/complementar

Contexto: aplicação web (aparentemente React, hospedada na Vercel; banco candidato: Supabase) para
gerar mapas de provas de voo livre / aerodesporto (FAI). Interface em português. Região de exemplo:
litoral sul de São Paulo (Itanhaém).

---

## 1. Criação e configuração do mapa
- ✅ Tela "Novo Mapa FAI" com pré-visualização ao lado e captura do recorte ao criar
- ✅ Campos: Nome do mapa, Escala (ex.: 1:50.000), Teto (m AMSL), Altitude mínima (m), Orientação (Paisagem/Retrato), Estilo
- ✅ Botão "Criar mapa" com estado de carregamento ("Capturando mapa…")
- 🔧 Validação de campos obrigatórios e mensagens de erro claras antes da captura
- 🔧 Presets/escalas pré-definidas (1:25.000, 1:50.000, 1:100.000) e cálculo automático da área coberta conforme escala
- 🔧 Seleção de formato/tamanho de saída (A4, A3, dimensões em px) e DPI
- 🔧 Salvar como rascunho e duplicar um mapa existente como modelo

## 2. Visualização e camadas
- ✅ Alternância Mapa / Satélite
- ✅ Camada de relevo topográfico (hipsometria/sombreamento)
- ✅ Marcadores (pins) sobre o mapa
- 🔧 Controle de camadas (ligar/desligar relevo, rodovias, hidrografia, áreas, satélite)
- 🔧 Curvas de nível e legenda de altitude
- 🔧 Busca por local/coordenadas e centralização rápida do mapa

## 3. Ferramentas de desenho e anotação
- ✅ Desenhar ponto, polígono, retângulo e círculo
- ✅ Desfazer / Refazer
- 🔧 Editar/mover/excluir geometrias já desenhadas
- 🔧 Medição de distância e área; raio de círculos (cilindros de prova) em metros/km
- 🔧 Rótulos e cores por tipo de geometria
- 🔧 Importar/exportar geometrias (GeoJSON/KML/GPX)

## 4. Pontos de voo, waypoints e prova (task)
- ✅ Bloco de seleção de pontos e definição da prova via retângulo/área
- 🔧 Cadastro de waypoints/turnpoints (nome, coordenada, raio, altitude)
- 🔧 Montagem da prova: ponto de decolagem, start, turnpoints (cilindros), ESS e goal
- 🔧 Cálculo da distância da prova e visualização da rota otimizada
- 🔧 Importar waypoints em formato padrão (.wpt, CompeGPS, FAI/CIVL)

## 5. Espaço aéreo e segurança
- ✅ Conceito de Teto (m AMSL) e referência a "áreas proibidas"
- 🔧 Camada de espaço aéreo (zonas proibidas/restritas/controladas) com cores e legenda
- 🔧 Alerta visual quando a prova ou um ponto invade espaço aéreo restrito
- 🔧 Atualização/importação da base de espaço aéreo (ex.: OpenAir/AIP)

## 6. Eventos e organização
- ✅ Bloco "EVENTO": Organizador, Título da prova, Data, Local
- 🔧 Cadastro completo de evento com várias provas/dias e listagem
- 🔧 Vincular cada mapa a um evento e a uma data específica
- 🔧 Papéis/permissões (organizador, piloto, administrador)

## 7. Exportação e saída
- ✅ Captura do recorte do mapa ao criar
- ✅ Painel "Dados do Mapa" com Rodapé, Logo, Pontos e Áreas (elementos do layout final)
- 🔧 Exportar em PNG/PDF de alta resolução com cabeçalho, rodapé, escala gráfica, norte e logo do evento
- 🔧 Inserção automática de metadados (escala, teto, data, organizador) no layout
- 🔧 Compartilhar via link e baixar/imprimir

## 8. Voos e Rankings
- ✅ Itens de menu "Voos" e "Rankings"
- 🔧 Upload de tracklogs (.igc) dos pilotos
- 🔧 Validação do voo contra a prova (cumprimento de cilindros, start/goal)
- 🔧 Pontuação automática e geração de ranking por prova e geral do evento
- 🔧 Página pública de resultados/leaderboard

## 9. Conta, dados e infraestrutura
- 🔧 Autenticação e perfil de usuário (o autocomplete sugere que hoje usa formulário simples)
- 🔧 Persistência dos mapas/eventos em banco (Supabase é bom candidato)
- 🔧 Histórico e versionamento de mapas
- 🔧 Responsividade e melhoria de usabilidade em telas menores

## 10. Qualidade e operação
- 🔧 Tratamento de erros na captura (o áudio sugere que "estava funcionando anteriormente" — vale logar falhas)
- 🔧 Testes da geração/captura de imagem
- 🔧 Métricas de uso e deploy automatizado (Vercel já conectado)
