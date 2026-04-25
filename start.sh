#!/bin/bash
# Start both backend and frontend servers
# Usage: bash start.sh

set -u

BACKEND_PORT=8000
FRONTEND_PORT=5173

echo "Starting CodeArena Contest Platform..."
echo ""

# Pick a Python that actually has uvicorn installed.
PY=""
if [ -n "${PYTHON_CMD:-}" ]; then
  PY="$PYTHON_CMD"
else
  for cand in python.exe python py python3 /usr/bin/python3; do
    if command -v "$cand" >/dev/null 2>&1; then
      if "$cand" -c "import uvicorn" >/dev/null 2>&1; then
        PY="$cand"
        break
      fi
    fi
  done
fi

if [ -z "$PY" ]; then
  echo "Error: no Python with 'uvicorn' installed was found on PATH."
  echo "Install backend dependencies with one of:"
  echo "  python.exe -m pip install -r backend/requirements.txt"
  echo "  py -m pip install -r backend/requirements.txt"
  echo "Or set PYTHON_CMD to the interpreter you want to use:"
  echo "  PYTHON_CMD=/c/path/to/python.exe bash start.sh"
  exit 1
fi
echo "[Backend] Using Python: $PY ($($PY --version 2>&1))"

# Find the real Windows PID listening on a given port (handles MSYS PID mismatch).
find_pid_on_port() {
  local port="$1"
  if command -v netstat >/dev/null 2>&1; then
    netstat -ano 2>/dev/null \
      | awk -v p=":$port" '$2 ~ p"$" && $4 == "LISTENING" { print $5 }' \
      | head -n 1
  fi
}

kill_pid() {
  local pid="$1"
  [ -z "$pid" ] && return 0
  if command -v taskkill >/dev/null 2>&1; then
    # //F force, //T kill tree (needed for uvicorn --reload child process)
    taskkill //F //T //PID "$pid" >/dev/null 2>&1 || true
  else
    kill -TERM "$pid" 2>/dev/null || true
  fi
}

cleanup() {
  echo ""
  echo "Shutting down..."
  # Kill by port — reliable across MSYS/Windows PID mismatch.
  for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    pid=$(find_pid_on_port "$port")
    kill_pid "$pid"
  done
  # Also try the bash-tracked PIDs (no-op on Windows, useful elsewhere).
  kill_pid "${BACKEND_PID:-}"
  kill_pid "${FRONTEND_PID:-}"
  exit 0
}

trap cleanup INT TERM

# Start backend
echo "[Backend] Starting FastAPI on http://localhost:$BACKEND_PORT"
cd "$(dirname "$0")"
$PY -m uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!

# Start frontend
echo "[Frontend] Starting Vite dev server on http://localhost:$FRONTEND_PORT"
cd frontend
npm run dev -- --port "$FRONTEND_PORT" --strictPort &
FRONTEND_PID=$!
cd ..

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║          CodeArena is running!                   ║"
echo "║                                                  ║"
echo "║  Frontend:  http://localhost:$FRONTEND_PORT                 ║"
echo "║  Backend:   http://localhost:$BACKEND_PORT                 ║"
echo "║  API Docs:  http://localhost:$BACKEND_PORT/docs            ║"
echo "║                                                  ║"
echo "║  Press Ctrl+C to stop both servers               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

wait
