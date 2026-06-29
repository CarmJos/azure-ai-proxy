#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  Azure AI Proxy — Linux/macOS launcher
# ─────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

CONFIG="${1:-config.yaml}"

if [ ! -f "$CONFIG" ]; then
    echo "ERROR: Config file not found: $CONFIG"
    echo "Usage: ./run.sh [config.yaml]"
    exit 1
fi

python -m proxy.server --config "$CONFIG"
