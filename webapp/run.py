"""Ponto de entrada — desenvolvimento.

    pip install -r requirements.txt
    python run.py
Porta padrão 5050 (evita o AirPlay Receiver do macOS, que ocupa a 5000).
Defina APURADOR_PORT para escolher outra; se ocupada, busca a próxima livre.
Login: admin@apurador.local / admin
"""
import os
import socket
from apurador import create_app

app = create_app()


def _free_port(preferred):
    candidates = [preferred, 5050, 5001, 5002, 8000, 8080, 0]
    for p in candidates:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", p))
            port = s.getsockname()[1]
            s.close()
            return port
        except OSError:
            continue
    return preferred


if __name__ == "__main__":
    port = _free_port(int(os.environ.get("APURADOR_PORT", 5050)))
    print(f"\n  Aeronav rodando em:  http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
