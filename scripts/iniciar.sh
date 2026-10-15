#!/bin/sh
# Starts the app for local use. Called by iniciar.bat (through WSL) or directly: sh scripts/iniciar.sh
# Env: CONTROLE_DB (default app.db), PORT (default 8000), NO_BROWSER=1 to skip opening the browser.
cd "$(dirname "$0")/.." || exit 1

if [ ! -f .venv/bin/activate ]; then
  echo "Ambiente virtual .venv nao encontrado. Crie com:"
  echo "  python3 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'"
  exit 1
fi
. .venv/bin/activate

DB="${CONTROLE_DB:-app.db}"
PORT="${PORT:-8000}"
export CONTROLE_DB="$DB"

# Se a porta ja estiver ocupada por um processo antigo do controle-atendimento, encerra antes de subir.
if command -v fuser >/dev/null 2>&1; then
  fuser -k -n tcp "$PORT" >/dev/null 2>&1 || true
elif command -v lsof >/dev/null 2>&1; then
  PID=$(lsof -ti tcp:"$PORT" 2>/dev/null)
  if [ -n "$PID" ]; then
    kill -9 $PID >/dev/null 2>&1 || true
  fi
fi
sleep 1

HAS_OWNER=$(python3 - "$DB" <<'EOF'
import sqlite3, sys
try:
    conn = sqlite3.connect(sys.argv[1])
    print(conn.execute("SELECT COUNT(*) FROM owners").fetchone()[0])
except sqlite3.Error:
    print(0)
EOF
)

if [ "$HAS_OWNER" = "0" ]; then
  echo "Primeiro uso: vamos criar o dono da agenda."
  printf "Endereco do negocio (slug, ex: barbearia-do-ze): "
  read -r SLUG
  printf "Nome do negocio: "
  read -r NAME
  printf "E-mail de login: "
  read -r EMAIL
  PYTHONPATH=. python scripts/create_owner.py --db "$DB" --slug "$SLUG" --name "$NAME" --email "$EMAIL" || exit 1
fi

URL="http://localhost:$PORT"
echo
echo "Servidor em $URL  (Ctrl+C para parar)"
if [ -z "$NO_BROWSER" ] && command -v cmd.exe >/dev/null 2>&1; then
  (sleep 3 && cmd.exe /c start "" "$URL" >/dev/null 2>&1) &
fi
exec uvicorn --factory web.app:default_app --host 127.0.0.1 --port "$PORT" --reload --reload-dir web --reload-dir domain --reload-dir adapters --reload-dir ports
