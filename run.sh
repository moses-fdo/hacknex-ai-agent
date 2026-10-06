#!/usr/bin/env bash
# ==============================================================================
# Aether-SWE: Autonomous Software Engineering Agent (Antigravity-Grade)
# 1-Click Launch Script
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "  ▲ AETHER-SWE · ANTIGRAVITY AUTONOMOUS CODING AGENT"
echo "========================================================================"

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "[SETUP] Initializing Python virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

echo "[START] Launching Aether-SWE Command Center on http://localhost:8080 ..."
echo "[START] Press Ctrl+C to terminate."
echo ""

exec .venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8080 --reload
