#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo
echo "============================================"
echo " copilot-azure-proxy — Init Environment"
echo "============================================"
echo

# ── Check Python ─────────────────────────────────────────────────────────────
PYTHON_BIN=""
if command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
elif command -v python &> /dev/null; then
    PYTHON_BIN="python"
else
    echo "[ERROR] Python not found. Please install Python 3.10+ and add it to PATH."
    echo "        https://www.python.org/downloads/"
    exit 1
fi

PY_VER=$("$PYTHON_BIN" --version 2>&1)
echo "[OK] $PY_VER detected."

# ── Create .venv ─────────────────────────────────────────────────────────────
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    echo "[SKIP] .venv already exists."
else
    echo "[INFO] Creating virtual environment..."
    if ! "$PYTHON_BIN" -m venv .venv; then
        echo "[ERROR] Failed to create .venv. See output above for details."
        exit 1
    fi
    echo "[OK] Virtual environment created."
fi

# ── Install dependencies ─────────────────────────────────────────────────────
VENV_PIP="$SCRIPT_DIR/.venv/bin/pip"

echo "[INFO] Installing dependencies from requirements.txt..."
if ! "$VENV_PIP" install -r requirements.txt --quiet; then
    echo "[ERROR] Failed to install dependencies. See output above for details."
    echo "        Try running manually: .venv/bin/pip install -r requirements.txt"
    exit 1
fi

echo "[OK] Dependencies installed."

echo
echo "============================================"
echo " Setup complete! You can now run:"
echo "   ./run.sh"
echo "============================================"
echo

