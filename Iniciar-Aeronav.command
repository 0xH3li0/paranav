#!/bin/bash
# ============================================================
#  Aeronav — iniciar o app (duplo-clique neste arquivo)
#  Na 1ª vez instala as dependências (pode levar alguns minutos).
#  Depois é rápido. Para PARAR o app: feche esta janela ou Ctrl+C.
# ============================================================
cd "$(dirname "$0")/webapp" || { echo "Pasta webapp não encontrada"; read -r; exit 1; }

echo "🪂  Aeronav — preparando..."

# Python 3
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 não encontrado. Instale em https://www.python.org/downloads/ e tente de novo."
  read -r; exit 1
fi

# ambiente isolado (.venv) para não bagunçar o sistema
if [ ! -d ".venv" ]; then
  echo "📦  Criando ambiente (1ª vez)..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -q --upgrade pip >/dev/null 2>&1
echo "📦  Instalando o essencial (Flask)..."
python -m pip install -q flask >/dev/null 2>&1
echo "📦  Instalando recursos de relatório/mapa (opcional)..."
python -m pip install -q reportlab matplotlib contextily Pillow staticmap >/dev/null 2>&1 || \
  echo "   (alguns recursos de PDF podem ficar indisponíveis — o app funciona mesmo assim)"

# escolhe uma porta livre (a 5000 costuma estar ocupada pelo AirPlay do macOS)
PORT=5050
for p in 5050 5001 5002 8000 8080; do
  if ! lsof -i ":$p" >/dev/null 2>&1; then PORT=$p; break; fi
done
export APURADOR_PORT=$PORT

# abre o navegador depois de 3s
( sleep 3; open "http://localhost:$PORT" ) &

echo ""
echo "✅  Pronto! Abrindo http://localhost:$PORT no navegador."
echo "    Login: admin@apurador.local   Senha: admin"
echo "    (Para parar o app, feche esta janela.)"
echo ""
python run.py
