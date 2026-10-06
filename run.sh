#!/usr/bin/env bash
# ==============================================================================
# Aether-SWE: Autonomous Software Engineering Agent (Antigravity-Grade)
# 1-Click Launch Script
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

echo "========================================================================"
echo "  ▲ AETHER-SWE · ANTIGRAVITY AUTONOMOUS CODING AGENT"
echo "========================================================================"

# Check if port is already occupied; if so, release it
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "[PORT] Port $PORT is currently in use. Freeing port $PORT..."
    fuser -k $PORT/tcp 2>/dev/null || kill -9 $(lsof -t -i:$PORT) 2>/dev/null || true
    sleep 1
fi

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "[SETUP] Initializing Python virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

echo "[START] Launching Aether-SWE Command Center on http://localhost:$PORT ..."
echo "[START] Press Ctrl+C to terminate."
echo ""

exec .venv/bin/uvicorn backend.app:app --host "$HOST" --port "$PORT"
