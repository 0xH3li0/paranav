# Aeronav — Apuração de navegação (paramotor)

Aplicação web para **apurar provas de navegação de paramotor** a partir dos tracks IGC dos pilotos. Stack: Python + **Flask + Jinja2**, **Bootstrap 5.3.3**, **Leaflet 1.9.4**. Persistência **plugável** (arquivos JSON + memória, ou **SQLite**). Salas: **N1 (Navegação Pura, 3.A1)**, **N2 (Tempo Declarado, 3.A6)** e **N3 (Curve Navigation / Rota de Precisão — corredor curvo, 3.A2)**, seguindo o FAI Section 10 Annex 4.

## Rodar

```bash
cd webapp
pip install -r requirements.txt
python run.py
# abra http://localhost:5050
```

Login do organizador (dev): **admin@apurador.local / admin** (configurável por variáveis de ambiente `APURADOR_EMAIL`, `APURADOR_PASSWORD`, `APURADOR_SECRET`, `APURADOR_PIN`).

### Persistência (backends)

Selecionada por `APURADOR_BACKEND`:
- **`files`** (default): provas em `data/provas/*.json` + pilotos **em memória**. Usado em dev e na validação.
- **`sqlite`**: provas + competições + pilotos/tracks em `data/aeronav.db` (`APURADOR_DB`). **Sobrevive a restart.** Migrar do JSON: `python3 -m apurador.repo.migrate`.

### Deploy (produção)

VPS dedicado com **gunicorn + systemd + nginx** (ou Cloudflare Tunnel), backend `sqlite`. Passo a passo e templates em [`deploy/`](deploy/README-deploy.md).

### Regressão

`python3 validate.py` — confere os invariantes sagrados (N1 Venet 11/18 TP + 01:00:47; N2 Melk HG 26 / Leandro 16) e o invariante N3. Rodar antes/depois de mexer no scoring.

## Como usar

1. **Provas**: ficam em `data/provas/*.json` (já vêm a N1 e a N2 de referência). O slug vem do nome do arquivo (`prova-N1-navegacao-pura.json` → `n1-navegacao-pura`).
2. **Enviar IGC (piloto)**: página pública `/igcupload` — escolhe a Sala, informa BIB+PIN, envia `.igc` (com prévia no mapa).
3. **Carregar Tracks (organizador)**: `/upload/tracks` — vários `.igc` de uma vez.
4. **Scores**: `/scores?sala=<slug>` — apuração automática (N1 por TP válidos; N2 = HG+TG+Vel).
5. **Relatório**: por piloto, com estatísticas de voo + tabela de pontos (botão PDF via impressão).

## Estrutura

```
webapp/
  run.py                      ponto de entrada (dev)
  requirements.txt
  apurador/
    __init__.py               create_app (Flask factory, filtros Jinja)
    state.py                  fachada de pilotos por sala (delega ao repo)
    storage.py                fachada de provas/competições (delega ao repo)
    repo/                     backends plugáveis: files_backend, sqlite_backend, migrate, base
    core/
      geo.py                  Haversine + geometria de corredor (N3)
      igc.py                  parser IGC (offsets fixos 1–34; ignora I-record do Gaggle)
      models.py               Prova (com route N3), Point, Pilot + mapdata()
      scoring.py              evaluate() + pontuação N1/N2/N3
      timefmt.py              clock/dur (UTC -> local)
    routes/
      auth.py                 login/logout (sessão por cookie)
      api.py                  /api/sala/<slug>/mapdata, /trackdata, /state/reset
      main.py                 igcupload, viewer, scores, upload/tracks, relatorio
    templates/                Jinja2 (Bootstrap + Leaflet)
    static/                   css + js (igcupload, viewer)
  data/provas/                provas em JSON
```

## API

| Endpoint | Método | Retorno |
|---|---|---|
| `/api/sala/<slug>/mapdata` | GET | `{ok,has_prova,center,wpts[],airspaces,route}` (`route` só na N3) |
| `/api/sala/<slug>/trackdata` | GET | trajetos dos pilotos (viewer) |
| `/api/state/reset` | POST | zera o estado em memória |

## Validação

`python3 validate.py` — harness de regressão. Valores sagrados (não regredir):
- **Venet (N1):** 11/18 TP, tempo SP→FP **01:00:47**, horários de hit ao segundo.
- **Melk (N2):** HG 26, erros TG/FP **19/6/57/116**. **Leandro (N2):** HG 16, erros **190/70**.
- **Ranking N2:** Melk 1000 · Leandro 314 · Paulo 0.
- Estatísticas de voo (decolagem/pouso/tempo/altitude) idênticas ao paradigma.

## Pendências / próximos passos

Ver `docs/ROADMAP.md` (backlog priorizado). Construtor (B0–B4), produção de mapa (A3/A4), persistência SQLite e deploy VPS estão **concluídos**. Resumo do que falta:
- **B5:** calibrar Score Vel (e o modelo N3) quando houver dado real.
- **B8:** autenticação de piloto por BIB/PIN.
- Opcionais: fundo de satélite no mapa A3; rotação dos recortes A4 pelo ângulo da folha.

### Mapas × Provas (separados)
- **Mapa** = geometria reutilizável (pontos, áreas, rota, folha A3, escala, teto/altura, logo). Editor em **`/mapas`** com **Leaflet-Geoman** (polígono auto-fechável p/ áreas verde/vermelho/amarelo, edição de vértices), fluxo em 2 etapas (escala+folha → desenho).
- **Prova** = puxa um mapa (`map_slug`) + scoring. `get_prova()` hidrata a geometria do mapa, então scoring/PDFs não mudaram. Migração: `python3 -m apurador.repo.migrate --split`.

### Construtor de prova (`/builder`)
Editor sobre satélite com **ferramentas que mudam conforme o tipo** (N1/N2/N3), **seletor "próximo ponto"** (SP/TP/FP…), **rascunho automático** (não perde trabalho no refresh), **Salvar** / **Salvar como nova**, e validação ao salvar (exige SP/FP; N3 exige rota). Exporta KML/JSON.

### Produção de mapa (organizador)
- **Mapa A3 (PDF) em escala fiel:** `/prova/<slug>/mapa.pdf` — link em Scores. 1 km = 2 cm em 1:50.000; rosa dos ventos orientada.
- **Folha A4 de imagens dos pontos:** `/prova/<slug>/pontos.pdf` — recorte de satélite por ponto.
