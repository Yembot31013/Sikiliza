#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — add GROQ_API_KEY (recommended) or OPENAI_API_KEY."
fi

if [[ ! -d .venv ]]; then
  python3.12 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip >/tmp/sikiliza-pip.log
python -m pip install fastapi "uvicorn[standard]" pydantic-settings httpx python-dotenv
export PYTHONPATH="$ROOT"

cd "$ROOT/web"
if [[ ! -d node_modules ]]; then
  npm install
fi

cd "$ROOT"
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "$ROOT/web"
npm run dev
