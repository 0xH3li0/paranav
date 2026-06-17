#!/usr/bin/env bash
# Deploy contínuo no VPS via GitHub. Rodar no VPS (ou: ssh ubuntu-vinhedo 'bash -s' < update.sh).
# Puxa do GitHub, reinstala deps se mudaram, roda a regressão sagrada e só então reinicia.
set -euo pipefail

REPO=/opt/aeronav/repo
VENV=/opt/aeronav/venv

cd "$REPO"
echo "==> git pull"
BEFORE=$(git rev-parse HEAD)
git pull --ff-only
AFTER=$(git rev-parse HEAD)

if git diff --name-only "$BEFORE" "$AFTER" | grep -q 'webapp/requirements.txt'; then
  echo "==> requirements mudou — reinstalando"
  "$VENV/bin/pip" install -r webapp/requirements.txt
fi

echo "==> regressão (invariantes sagrados N1/N2/N3)"
( cd webapp && "$VENV/bin/python" validate.py )

echo "==> restart do serviço (reload, sem derrubar vizinhos)"
sudo systemctl restart aeronav
sudo systemctl --no-pager --lines=0 status aeronav
curl -s http://127.0.0.1:8050/ -o /dev/null -w "health: %{http_code}\n" || true
echo "==> OK ($BEFORE -> $AFTER)"
