#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  azure-ai-proxy  —  Linux/macOS Installation Script
# ─────────────────────────────────────────────────────────────────
#  This script will:
#  1. Check for Python 3.10+
#  2. Create a virtual environment
#  3. Install azure-ai-proxy and dependencies
#  4. Copy config.example.yaml to config.yaml
# ─────────────────────────────────────────────────────────────────

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Defaults
INSTALL_DIR="${INSTALL_DIR:-$HOME/.azure-ai-proxy}"
ADD_TO_PATH=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --add-to-path)
            ADD_TO_PATH=true
            shift
            ;;
        --help|-h)
            echo ""
            echo "azure-ai-proxy Installer for Linux/macOS"
            echo ""
            echo "Usage: ./install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --install-dir <path>    Installation directory (default: $HOME/.azure-ai-proxy)"
            echo "  --add-to-path           Add to PATH in shell profile"
            echo "  --help, -h              Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./install.sh"
            echo "  ./install.sh --install-dir /opt/azure-ai-proxy"
            echo "  ./install.sh --add-to-path"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo ""
echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}  azure-ai-proxy Installer for Linux/macOS${NC}"
echo -e "${CYAN}==============================================${NC}"
echo ""

# ── Check Python ───────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Checking Python installation...${NC}"

PYTHON_CMD=""
for cmd in python3 python py; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1)
        if [[ $version =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
            major="${BASH_REMATCH[1]}"
            minor="${BASH_REMATCH[2]}"
            if [[ $major -gt 3 ]] || [[ $major -eq 3 && $minor -ge 10 ]]; then
                PYTHON_CMD="$cmd"
                echo -e "  ${GREEN}Found: $version${NC}"
                break
            fi
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo -e "  ${RED}ERROR: Python 3.10+ is required but not found.${NC}"
    echo -e "  ${RED}Please install Python 3.10 or newer.${NC}"
    exit 1
fi

# ── Create installation directory ──────────────────────────────
echo -e "${YELLOW}[2/4] Creating installation directory...${NC}"
echo -e "  Location: $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"

# ── Create virtual environment and install ─────────────────────
echo -e "${YELLOW}[3/4] Installing azure-ai-proxy...${NC}"

VENV_PATH="$INSTALL_DIR/.venv"
if [[ ! -d "$VENV_PATH" ]]; then
    echo -e "  Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_PATH"
fi

# Detect venv directory structure (Scripts vs bin)
SCRIPTS_DIR=""
if [[ -d "$VENV_PATH/bin" ]]; then
    SCRIPTS_DIR="$VENV_PATH/bin"
elif [[ -d "$VENV_PATH/Scripts" ]]; then
    SCRIPTS_DIR="$VENV_PATH/Scripts"
else
    echo -e "  ${RED}ERROR: Failed to create virtual environment.${NC}"
    exit 1
fi

PIP_PATH="$SCRIPTS_DIR/pip"
if [[ ! -f "$PIP_PATH" ]]; then
    echo -e "  ${RED}ERROR: Failed to find pip in virtual environment.${NC}"
    exit 1
fi

echo -e "  Upgrading pip..."
"$PIP_PATH" install --upgrade pip &>/dev/null

echo -e "  Installing azure-ai-proxy from GitHub..."
"$PIP_PATH" install git+https://github.com/CarmJos/azure-ai-proxy.git
if [[ $? -ne 0 ]]; then
    echo -e "  ${RED}ERROR: Failed to install azure-ai-proxy.${NC}"
    exit 1
fi

# ── Copy config file ───────────────────────────────────────────
echo -e "${YELLOW}[4/4] Setting up configuration...${NC}"

CONFIG_PATH="$INSTALL_DIR/config.yaml"
if [[ ! -f "$CONFIG_PATH" ]]; then
    EXAMPLE_CONFIG="$VENV_PATH/lib/python*/site-packages/proxy/../config.example.yaml"
    EXAMPLE_CONFIG=$(ls $EXAMPLE_CONFIG 2>/dev/null | head -1)
    if [[ -f "$EXAMPLE_CONFIG" ]]; then
        cp "$EXAMPLE_CONFIG" "$CONFIG_PATH"
        echo -e "  ${GREEN}Created config.yaml from template${NC}"
    else
        cat > "$CONFIG_PATH" << 'EOF'
# azure-ai-proxy configuration
# See https://github.com/CarmJos/azure-ai-proxy for full documentation

general:
  host: "0.0.0.0"
  port: 4000
  timeout: 120
  debug: false
  api-key: ""
  log-level: "INFO"
  log-file: ""
  max-stream-timeout: 300
  keepalive-interval: 15

models:
  - model_name: deepseek-v4-pro
    litellm_params:
      model: openai/deepseek-v4-pro
      api_base: https://api.deepseek.com
      api_key: "YOUR_API_KEY_HERE"
      supports_function_calling: true
      supports_reasoning: true
      max_tokens: 384000
      max_input_tokens: 1000000
      max_output_tokens: 384000
EOF
        echo -e "  ${GREEN}Created config.yaml (template)${NC}"
    fi
else
    echo -e "  config.yaml already exists, skipping"
fi

# ── Add to PATH ────────────────────────────────────────────────
if [[ "$ADD_TO_PATH" == true ]]; then
    echo ""
    echo -e "${YELLOW}Adding to PATH...${NC}"
    SHELL_PROFILE=""
    if [[ -f "$HOME/.bashrc" ]]; then
        SHELL_PROFILE="$HOME/.bashrc"
    elif [[ -f "$HOME/.zshrc" ]]; then
        SHELL_PROFILE="$HOME/.zshrc"
    fi
    if [[ -n "$SHELL_PROFILE" ]]; then
        if ! grep -q "$SCRIPTS_DIR" "$SHELL_PROFILE"; then
            echo "" >> "$SHELL_PROFILE"
            echo "# azure-ai-proxy" >> "$SHELL_PROFILE"
            echo "export PATH=\"\$PATH:$SCRIPTS_DIR\"" >> "$SHELL_PROFILE"
            echo -e "  ${GREEN}Added to PATH in $SHELL_PROFILE${NC}"
        else
            echo -e "  Already in PATH"
        fi
    fi
fi

# ── Create run script ──────────────────────────────────────────
RUN_SCRIPT="$INSTALL_DIR/run.sh"
cat > "$RUN_SCRIPT" << EOF
#!/usr/bin/env bash
# azure-ai-proxy runner
VENV_PATH="$VENV_PATH"
SCRIPTS_DIR="$SCRIPTS_DIR"
CONFIG_PATH="$CONFIG_PATH"

"\$SCRIPTS_DIR/python" -m proxy.server --config "\$CONFIG_PATH" "\$@"
EOF
chmod +x "$RUN_SCRIPT"

# ── Done ───────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}==============================================${NC}"
echo ""
echo -e "  Installation directory: $INSTALL_DIR"
echo -e "  Configuration file:     $CONFIG_PATH"
echo -e "  Run script:             $RUN_SCRIPT"
echo ""
echo -e "  ${YELLOW}To start the proxy:${NC}"
echo -e "    Edit config.yaml with your model settings"
echo -e "    Run: $RUN_SCRIPT"
echo ""
echo -e "  ${YELLOW}Or activate the venv and run directly:${NC}"
echo -e "    source $SCRIPTS_DIR/activate"
echo -e "    python -m proxy.server --config $CONFIG_PATH"
echo ""
