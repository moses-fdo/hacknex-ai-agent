#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================="
echo " Starting Aether-SWE Command Center (Desktop & Web)"
echo "=========================================="

# Free port 8000 if lingering from previous run
if command -v fuser >/dev/null 2>&1; then
    fuser -k 8000/tcp 2>/dev/null || true
elif command -v lsof >/dev/null 2>&1; then
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

# Ensure Python venv exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

export PYTHONPATH="$DIR:$DIR/benchmarks/ecommerce_api"

# Check if user wants headless/web-only or Electron desktop
if [ "$1" == "--web" ] || [ -z "$DISPLAY" ]; then
    echo "Starting Web Server on http://127.0.0.1:8000..."
    exec .venv/bin/uvicorn backend.api.server:app --host 127.0.0.1 --port 8000 --reload
else
    echo "Starting Electron Desktop Application..."
    exec npm start
fi
