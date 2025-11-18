<#
.SYNOPSIS
    Start the Foundit backend (uvicorn) with convenient environment variable setup.

USAGE
    From repository root (PowerShell):
      .\backend\start_backend.ps1 -OpenRouterKey "your-key" -GoogleClientId "..." -GoogleClientSecret "..."

    To allow firewall (Admin):
      .\backend\start_backend.ps1 -AllowFirewall

DESCRIPTION
    - Sets common environment variables for the backend process only
    - Installs Python requirements from backend/requirements.txt if missing
    - Optionally adds a Windows Firewall rule for port 8001 (requires Admin)
    - Starts uvicorn at 127.0.0.1:8001 with --reload

#>

[CmdletBinding()]
param(
    [string]$OpenRouterKey = "",
    [string]$OpenAIKey = "",
    [string]$AnthropicKey = "",
    [string]$GoogleClientId = "",
    [string]$GoogleClientSecret = "",
    [string]$JwtSecret = "",
    [string]$IndexPath = "",
    [switch]$AllowFirewall
)

function Write-Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m)  { Write-Host "[ERROR] $m" -ForegroundColor Red }

Set-Location -LiteralPath $PSScriptRoot

Write-Info "Starting Foundit backend helper (working dir: $PSScriptRoot)"

# Set environment variables for this process (not persistent)
if ($OpenRouterKey) { $env:OPENROUTER_API_KEY = $OpenRouterKey; Write-Info "Set OPENROUTER_API_KEY" }
if ($OpenAIKey)      { $env:OPENAI_API_KEY = $OpenAIKey; Write-Info "Set OPENAI_API_KEY" }
if ($AnthropicKey)   { $env:ANTHROPIC_API_KEY = $AnthropicKey; Write-Info "Set ANTHROPIC_API_KEY" }
if ($GoogleClientId)  { $env:GOOGLE_CLIENT_ID = $GoogleClientId; Write-Info "Set GOOGLE_CLIENT_ID" }
if ($GoogleClientSecret) { $env:GOOGLE_CLIENT_SECRET = $GoogleClientSecret; Write-Info "Set GOOGLE_CLIENT_SECRET" }
if ($JwtSecret)      { $env:JWT_SECRET_KEY = $JwtSecret; Write-Info "Set JWT_SECRET_KEY" }
if ($IndexPath)      { $env:FOUNDIT_INDEX_PATH = $IndexPath; Write-Info "Set FOUNDIT_INDEX_PATH = $IndexPath" }

# Ensure Python and pip are available
try {
    $python = Get-Command python -ErrorAction Stop
    Write-Info "Python found: $($python.Path)"
} catch {
    Write-Err "Python executable not found in PATH. Make sure Python 3.10+ is installed and 'python' is on PATH."
    exit 1
}

# Install requirements (best-effort)
if (Test-Path .\requirements.txt) {
    Write-Info "Installing Python requirements (this may take a moment)..."
    & python -m pip install -r .\requirements.txt
} else {
    Write-Warn "requirements.txt not found in backend folder. Skipping pip install."
}

# Optionally add firewall rule for port 8001
if ($AllowFirewall) {
    Write-Info "Attempting to add Windows Firewall rule for TCP port 8001 (requires Admin)..."
    try {
        New-NetFirewallRule -DisplayName "Foundit backend (uvicorn)" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow -Profile Any -ErrorAction Stop
        Write-Info "Firewall rule added."
    } catch {
        Write-Warn "Failed to add firewall rule. Run PowerShell as Administrator to add the rule."
    }
}

Write-Info "Launching uvicorn (127.0.0.1:8001)"
Write-Info "Endpoint: http://127.0.0.1:8001/health"

# Run uvicorn (blocking). Use --reload for development convenience.
& uvicorn app:app --host 127.0.0.1 --port 8001 --reload
