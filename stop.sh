#!/bin/bash
# Stop CodeArena servers on ports 8000 and 5173.
# Usage: bash stop.sh

BACKEND_PORT=8000
FRONTEND_PORT=5173

find_pid_on_port() {
  local port="$1"
  netstat -ano 2>/dev/null \
    | awk -v p=":$port" '$2 ~ p"$" && $4 == "LISTENING" { print $5 }' \
    | head -n 1
}

kill_pid() {
  local pid="$1" port="$2"
  if [ -z "$pid" ]; then
    echo "  port $port: nothing listening"
    return
  fi
  if command -v taskkill >/dev/null 2>&1; then
    if taskkill //F //T //PID "$pid" >/dev/null 2>&1; then
      echo "  port $port: killed PID $pid"
    else
      echo "  port $port: failed to kill PID $pid"
    fi
  else
    kill -TERM "$pid" 2>/dev/null && echo "  port $port: sent TERM to $pid"
  fi
}

echo "Stopping CodeArena..."
kill_pid "$(find_pid_on_port $BACKEND_PORT)" "$BACKEND_PORT"
kill_pid "$(find_pid_on_port $FRONTEND_PORT)" "$FRONTEND_PORT"
echo "Done."
