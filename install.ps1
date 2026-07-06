# ─────────────────────────────────────────────────────────────────
#  azure-ai-proxy  —  Windows Installation Script
# ─────────────────────────────────────────────────────────────────
#  This script will:
#  1. Check for Python 3.10+
#  2. Create a virtual environment
#  3. Install azure-ai-proxy and dependencies
#  4. Copy config.example.yaml to config.yaml
# ─────────────────────────────────────────────────────────────────

param(
    [switch]$Help,
    [string]$InstallDir = "$env:USERPROFILE\.azure-ai-proxy",
    [switch]$AddToPath
)

if ($Help) {
    Write-Host @"
azure-ai-proxy Installer for Windows

Usage: .\install.ps1 [Options]

Options:
    -InstallDir <path>    Installation directory (default: $env:USERPROFILE\.azure-ai-proxy)
    -AddToPath            Add to user PATH environment variable
    -Help                 Show this help message

Examples:
    .\install.ps1
    .\install.ps1 -InstallDir "C:\Tools\azure-ai-proxy"
    .\install.ps1 -AddToPath
"@
    exit 0
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  azure-ai-proxy Installer for Windows" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ── Check Python ───────────────────────────────────────────────
Write-Host "[1/4] Checking Python installation..." -ForegroundColor Yellow

$pythonCmd = $null
foreach ($cmd in @("python", "py", "python3")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                $pythonCmd = $cmd
                Write-Host "  Found: $version" -ForegroundColor Green
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $pythonCmd) {
    Write-Host "  ERROR: Python 3.10+ is required but not found." -ForegroundColor Red
    Write-Host "  Please install Python from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Red
    exit 1
}

# ── Create installation directory ──────────────────────────────
Write-Host "[2/4] Creating installation directory..." -ForegroundColor Yellow
Write-Host "  Location: $InstallDir"

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# ── Create virtual environment and install ─────────────────────
Write-Host "[3/4] Installing azure-ai-proxy..." -ForegroundColor Yellow

$venvPath = Join-Path $InstallDir ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "  Creating virtual environment..."
    & $pythonCmd -m venv $venvPath
}

# Detect venv directory structure (Scripts vs Bin)
$scriptsDir = $null
if (Test-Path (Join-Path $venvPath "Scripts")) {
    $scriptsDir = Join-Path $venvPath "Scripts"
} elseif (Test-Path (Join-Path $venvPath "bin")) {
    $scriptsDir = Join-Path $venvPath "bin"
} else {
    Write-Host "  ERROR: Failed to create virtual environment." -ForegroundColor Red
    exit 1
}

$pipPath = Join-Path $scriptsDir "pip.exe"
if (-not (Test-Path $pipPath)) {
    $pipPath = Join-Path $scriptsDir "pip"
}
if (-not (Test-Path $pipPath)) {
    Write-Host "  ERROR: Failed to find pip in virtual environment." -ForegroundColor Red
    exit 1
}

Write-Host "  Upgrading pip..."
& $pipPath install --upgrade pip | Out-Null

Write-Host "  Installing azure-ai-proxy from PyPI..."
& $pipPath install azure-ai-proxy
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Failed to install azure-ai-proxy." -ForegroundColor Red
    exit 1
}

# ── Copy config file ───────────────────────────────────────────
Write-Host "[4/4] Setting up configuration..." -ForegroundColor Yellow

$configPath = Join-Path $InstallDir "config.yaml"
if (-not (Test-Path $configPath)) {
    $exampleConfig = Join-Path $venvPath "Lib\site-packages\proxy\..\config.example.yaml"
    if (Test-Path $exampleConfig) {
        Copy-Item $exampleConfig $configPath
        Write-Host "  Created config.yaml from template" -ForegroundColor Green
    } else {
        # Create a minimal config
        @"
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
"@ | Set-Content $configPath -Encoding UTF8
        Write-Host "  Created config.yaml (template)" -ForegroundColor Green
    }
} else {
    Write-Host "  config.yaml already exists, skipping" -ForegroundColor DarkGray
}

# ── Add to PATH ────────────────────────────────────────────────
if ($AddToPath) {
    Write-Host ""
    Write-Host "Adding to user PATH..." -ForegroundColor Yellow
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$scriptsDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$scriptsDir", "User")
        $env:Path = "$env:Path;$scriptsDir"
        Write-Host "  Added to PATH: $scriptsDir" -ForegroundColor Green
    } else {
        Write-Host "  Already in PATH" -ForegroundColor DarkGray
    }
}

# ── Create run script ──────────────────────────────────────────
$runScript = Join-Path $InstallDir "run.ps1"
$pythonExe = if (Test-Path (Join-Path $scriptsDir "python.exe")) { "python.exe" } else { "python" }
$activateScript = if (Test-Path (Join-Path $scriptsDir "Activate.ps1")) { "Activate.ps1" } else { "activate" }

@"
# azure-ai-proxy runner
`$venvPath = "$venvPath"
`$scriptsDir = "$scriptsDir"
`$configPath = "$configPath"

& "`$scriptsDir\$pythonExe" -m proxy.server --config "`$configPath" @args
"@ | Set-Content $runScript -Encoding UTF8

# ── Done ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Installation directory: $InstallDir"
Write-Host "  Configuration file:     $configPath"
Write-Host "  Run script:             $runScript"
Write-Host ""
Write-Host "  To start the proxy:" -ForegroundColor Yellow
Write-Host "    Edit config.yaml with your model settings"
Write-Host "    Run: & '$runScript'"
Write-Host ""
Write-Host "  Or activate the venv and run directly:" -ForegroundColor Yellow
Write-Host "    & '$scriptsDir\$activateScript'"
Write-Host "    python -m proxy.server --config '$configPath'"
Write-Host ""
