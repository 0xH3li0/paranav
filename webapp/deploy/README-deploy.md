# Deploy no VPS (ubuntu-vinhedo) — Aeronav

Processo persistente: **gunicorn + systemd + nginx (ou Cloudflare Tunnel)**, com
estado em **SQLite** (sobrevive a restart). **Não derruba nenhum serviço existente**
do VPS — só adiciona um vhost/serviço/porta novos. O app escuta apenas em
`127.0.0.1:8050`; o proxy (nginx/cloudflared) é quem expõe ao mundo.

> Estado do VPS já levantado: nginx ativo (80/443), cloudflared (tunnel), gitea
> (:3000), redis (:6379), bind9 (:53), mediamtx (:8554/8888/8889). Porta local
> escolhida p/ o app: **8050** (livre). Python do sistema: 3.8 — usamos **venv**.

## 1. Código + venv

Origem do código = **GitHub privado** `git@github.com:0xH3li0/paranav.git` (intermediador
oficial dos deploys). O VPS clona esse repo em `/opt/aeronav/repo`.

```bash
sudo mkdir -p /opt/aeronav && sudo chown $USER /opt/aeronav
git clone git@github.com:0xH3li0/paranav.git /opt/aeronav/repo
ln -s /opt/aeronav/repo/webapp /opt/aeronav/webapp
python3 -m venv /opt/aeronav/venv
/opt/aeronav/venv/bin/pip install -r /opt/aeronav/webapp/requirements.txt
```

> **Estado/dados ficam FORA do repo** (`/opt/aeronav/data`, `aeronav.env`), então
> `git pull`/`reset` nunca tocam o SQLite vivo nem os segredos.

Se alguma lib de PDF (matplotlib/contextily) não instalar no Python 3.8 do sistema,
crie o venv com um Python mais novo (deadsnakes/pyenv) — **sem** mexer no python do
sistema, que outros serviços usam. O app em si (Flask + SQLite) roda no 3.8.

## 2. Configuração (segredos)

```bash
cp /opt/aeronav/webapp/deploy/aeronav.env.example /opt/aeronav/aeronav.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # gere APURADOR_SECRET
nano /opt/aeronav/aeronav.env                                   # edite secret/email/senha
mkdir -p /opt/aeronav/data
```

## 3. Migrar as provas para o SQLite

```bash
cd /opt/aeronav/webapp
APURADOR_DB=/opt/aeronav/data/aeronav.db /opt/aeronav/venv/bin/python -m apurador.repo.migrate
```

## 4. Serviço systemd

```bash
sudo cp /opt/aeronav/webapp/deploy/aeronav.service /etc/systemd/system/aeronav.service
# ajuste User= e os caminhos se necessário
sudo systemctl daemon-reload
sudo systemctl enable --now aeronav
sudo systemctl status aeronav        # deve estar "active (running)"
curl -s http://127.0.0.1:8050/ -o /dev/null -w "%{http_code}\n"   # 302 (redirect p/ login)
```

## 5. Expor (escolha UMA rota)

### A) Cloudflare Tunnel (já roda no VPS — provavelmente o caminho)
Adicione uma regra de ingress no config do cloudflared apontando o (sub)domínio
para `http://localhost:8050` e faça `cloudflared` recarregar. TLS é da Cloudflare
(sem certbot). **Confirme o config atual antes** (`/etc/cloudflared/`).

### B) nginx + certbot (se o acesso bate direto no nginx)
```bash
sudo cp /opt/aeronav/webapp/deploy/aeronav.nginx.conf /etc/nginx/sites-available/aeronav
# edite server_name p/ seu (sub)domínio
sudo ln -s /etc/nginx/sites-available/aeronav /etc/nginx/sites-enabled/aeronav
sudo nginx -t && sudo systemctl reload nginx          # reload, NUNCA restart
sudo certbot --nginx -d aeronav.SEU-DOMINIO.com       # HTTPS automático
```

## 6. Verificação

- `https://<seu-dominio>/` → tela de login do organizador.
- Login → Viewer/Scores. Salas N1, N2 e N3 aparecem.
- `/igcupload` → piloto envia IGC (com PIN, se configurado).
- `sudo systemctl restart aeronav` e confira que **tracks/competição continuam**
  (estado em SQLite).
- Serviços existentes (gitea/redis/bind9/mediamtx) **intactos**.

## Atualizar (deploy contínuo — via GitHub)

Fluxo oficial: **local → GitHub → VPS**. Nunca mais editar direto no VPS.

1. **Local** (máquina de dev): `git add -A && git commit -m "..." && git push`
2. **VPS**:
   ```bash
   cd /opt/aeronav/repo && git pull
   /opt/aeronav/venv/bin/pip install -r webapp/requirements.txt   # só se requirements mudou
   /opt/aeronav/venv/bin/python webapp/validate.py                # regressão ANTES de subir
   sudo systemctl restart aeronav
   ```
   Ou, da máquina local, em um passo: `ssh ubuntu-vinhedo 'bash -s' < webapp/deploy/update.sh`.

### Migração do deploy por rsync → GitHub (uma vez)

Se o `/opt/aeronav/repo` veio de um rsync (sem `.git`), converta-o em clone que
rastreia o GitHub — sem churn de arquivos (o conteúdo já bate com o que foi
empurrado):

```bash
cd /opt/aeronav/repo
git init && git remote add origin git@github.com:0xH3li0/paranav.git
git fetch origin && git reset --hard origin/main
git branch --set-upstream-to=origin/main main
```

## Regressão (rodar após mudanças)

```bash
cd /opt/aeronav/webapp && /opt/aeronav/venv/bin/python validate.py
# N1 Venet 11/18 TP + 01:00:47; N2 Melk HG 26 / Leandro 16; N3 cobertura 100%.
```
