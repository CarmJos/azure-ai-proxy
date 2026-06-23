#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Free port 4000 ────────────────────────────────────────────────────────────
if command -v lsof &> /dev/null; then
    PID=$(lsof -ti :4000 2>/dev/null || true)
    if [ -n "$PID" ]; then
        echo "Killing existing process on port 4000 (PID $PID)..."
        kill -9 "$PID" 2>/dev/null || true
    fi
elif command -v fuser &> /dev/null; then
    fuser -k 4000/tcp 2>/dev/null || true
fi

# ── Check .venv ───────────────────────────────────────────────────────────────
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
VENV_PIP="$SCRIPT_DIR/.venv/bin/pip"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: .venv not found."
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/pip install aiohttp litellm pyyaml"
    exit 1
fi

# ── Ensure dependencies ───────────────────────────────────────────────────────
for pkg in aiohttp litellm yaml; do
    if ! "$VENV_PYTHON" -c "import $pkg" 2>/dev/null; then
        echo "Installing $pkg..."
        "$VENV_PIP" install "$pkg"
    fi
done

echo
echo "============================================"
echo " copilot-azure-proxy"
echo " Press Ctrl+C to stop."
echo "============================================"
echo

"$VENV_PYTHON" copilot_azure_proxy.py --config config.yaml

