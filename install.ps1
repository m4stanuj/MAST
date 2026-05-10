# =============================================================================
#  MAST v1.0 — install.ps1
#  Merged: M4STCLAW v3 + OpenWork v12 + EIGENT v4.1
#  19 MCP servers | 10+ providers | NVIDIA NIM + Mistral + Grok
#
#  Run: powershell -ExecutionPolicy Bypass -File install.ps1
#  Safe to re-run: existing .env keys are preserved
# =============================================================================

$ErrorActionPreference = "Continue"
$cfg       = "$env:USERPROFILE\.config\opencode"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$username  = $env:USERNAME
$base      = "C:/Users/$username/.config/opencode"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   MAST v1.0 — Unified AI Stack Installer                    ║" -ForegroundColor Cyan
Write-Host "║   M4STCLAW v3 + OpenWork v12 + EIGENT v4.1                  ║" -ForegroundColor Green
Write-Host "║   19 MCP Servers | NVIDIA NIM | Mistral | Grok              ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$allOk = $true
$pythonExe = "python"

# ═══════════════════════════════════════════════════════════════════════
# STEP 1 — System check
# ═══════════════════════════════════════════════════════════════════════
Write-Host "[1/9] System check..." -ForegroundColor Yellow
$pythonOk = $false

try {
    $pyRaw = python --version 2>&1
    if (($pyRaw -join " ") -match "Python (\d+)\.(\d+)") {
        $maj = [int]$Matches[1]; $min = [int]$Matches[2]
        if ($maj -eq 3 -and $min -ge 9) {
            Write-Host "  ✅ Python $maj.$min" -ForegroundColor Green
            $pythonOk = $true
        } else {
            Write-Host "  ⚠️  Python $maj.$min — 3.9+ recommended" -ForegroundColor Yellow
            $pythonOk = $true
        }
    }
} catch {}

if (-not $pythonOk) {
    try { $pyRaw = python3 --version 2>&1; if ($pyRaw -match "Python") { $pythonExe = "python3"; $pythonOk = $true } } catch {}
}
if (-not $pythonOk) { Write-Host "  ❌ Python not found — install from python.org" -ForegroundColor Red; exit 1 }

try { $nv = node --version 2>&1; Write-Host "  ✅ Node: $nv" -ForegroundColor Green }
catch { Write-Host "  ⚠️  Node not found (playwright/firecrawl won't work)" -ForegroundColor Yellow }

try { $pv = pip --version 2>&1; Write-Host "  ✅ pip found" -ForegroundColor Green }
catch { Write-Host "  ⚠️  pip not found" -ForegroundColor Yellow }

# ═══════════════════════════════════════════════════════════════════════
# STEP 2 — Directories
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""; Write-Host "[2/9] Creating directories..." -ForegroundColor Yellow

$dirs = @(
    $cfg,
    "$cfg\mcp_servers",
    "$cfg\bridge_core",
    "$cfg\skills",
    "$cfg\config",
    "$cfg\data",
    "$cfg\agents",
    "$cfg\commands",
    "$cfg\authorized_targets"
)

foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
        Write-Host "  ✅ Created: $d" -ForegroundColor Green
    } else {
        Write-Host "  ✓  Exists:  $d" -ForegroundColor DarkGray
    }
}

# ═══════════════════════════════════════════════════════════════════════
# STEP 3 — Copy files
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""; Write-Host "[3/9] Copying MAST files..." -ForegroundColor Yellow

# MCP servers
$mcpSrc = Join-Path $scriptDir "mcp_servers"
if (Test-Path $mcpSrc) {
    Copy-Item "$mcpSrc\*.py" "$cfg\mcp_servers\" -Force
    Write-Host "  ✅ MCP servers copied ($(Get-ChildItem $mcpSrc -Filter *.py | Measure-Object).Count files)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  mcp_servers/ folder not found in script dir" -ForegroundColor Yellow
}

# Bridge core
$bridgeSrc = Join-Path $scriptDir "bridge_core"
if (Test-Path $bridgeSrc) {
    Copy-Item "$bridgeSrc\*.py" "$cfg\bridge_core\" -Force
    Write-Host "  ✅ Bridge core copied ($(Get-ChildItem $bridgeSrc -Filter *.py | Measure-Object).Count files)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  bridge_core/ folder not found" -ForegroundColor Yellow
}

# Skills
$skillsSrc = Join-Path $scriptDir "skills"
if (Test-Path $skillsSrc) {
    Copy-Item $skillsSrc "$cfg\" -Recurse -Force
    Write-Host "  ✅ Skills copied" -ForegroundColor Green
}

# SOUL file
$soulSrc = Join-Path $scriptDir "SOUL_MAST.md"
if (Test-Path $soulSrc) {
    Copy-Item $soulSrc "$cfg\SOUL_MAST.md" -Force
    Write-Host "  ✅ SOUL_MAST.md copied" -ForegroundColor Green
}

# Agents config
$agentsSrc = Join-Path $scriptDir "config\m4st_agents_config.json"
if (Test-Path $agentsSrc) {
    Copy-Item $agentsSrc "$cfg\config\m4st_agents_config.json" -Force
    Write-Host "  ✅ Agents config copied" -ForegroundColor Green
}

# ═══════════════════════════════════════════════════════════════════════
# STEP 4 — .env (preserve existing keys!)
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""; Write-Host "[4/9] Setting up .env..." -ForegroundColor Yellow

$envDst = "$cfg\config\.env"
$envSrc = Join-Path $scriptDir "config\.env"

if (Test-Path $envDst) {
    Write-Host "  ✓  .env already exists — keys preserved" -ForegroundColor DarkGray
    Write-Host "  💡 Add new keys manually: $envDst" -ForegroundColor Cyan
} else {
    if (Test-Path $envSrc) {
        Copy-Item $envSrc $envDst -Force
        Write-Host "  ✅ .env template created at $envDst" -ForegroundColor Green
        Write-Host "  ⚠️  Fill in your API keys before running!" -ForegroundColor Yellow
    }
}

# ═══════════════════════════════════════════════════════════════════════
# STEP 5 — opencode.json with path substitution
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""; Write-Host "[5/9] Installing opencode.json..." -ForegroundColor Yellow

$ocSrc = Join-Path $scriptDir "config\opencode.json"
$ocDst = "$cfg\opencode.json"

if (Test-Path $ocSrc) {
    $ocContent = Get-Content $ocSrc -Raw
    $mastDir   = $base.Replace("\", "/")
    $ocContent = $ocContent -replace '\$\{MAST_DIR\}', $mastDir
    # Strip comments (JSONC → JSON) for opencode compatibility
    $ocContent = $ocContent -replace '//[^\n]*', ''
    $ocContent | Set-Content $ocDst -Encoding UTF8
    Write-Host "  ✅ opencode.json installed (paths resolved for $username)" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  opencode.json not found in config/" -ForegroundColor Yellow
}

# Create authorized_targets.txt (pentest safety)
$authTargets = "$cfg\authorized_targets\authorized_targets.txt"
if (-not (Test-Path $authTargets)) {
    @"
# MAST — Authorized Pentest Targets
# =====================================
# Add your lab/authorized IPs/domains here, ONE PER LINE
# The pentest_mcp.py checks this file BEFORE any scan
# Blank file = nothing is authorized = all scans blocked
#
# Examples (uncomment to use):
# 192.168.1.100
# hackthebox.eu
# tryhackme.com
# 10.10.10.0/24
"@ | Set-Content $authTargets -Encoding UTF8
    Write-Host "  ✅ authorized_targets.txt created (add your lab IPs)" -ForegroundColor Green
}

# ═══════════════════════════════════════════════════════════════════════
# STEP 6 — Python dependencies
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""; Write-Host "[6/9] Installing Python packages..." -ForegroundColor Yellow

$pipPkgs = @(
    "requests",
    "mcp",
    "python-dotenv",
    "chromadb",
    "sentence-transformers",
    "duckduckgo-search",
    "beautifulsoup4",
    "APScheduler",
    "psutil"
)

foreach ($pkg in $pipPkgs) {
    try {
        & $pythonExe -m pip install $pkg --quiet --break-system-packages 2>&1 | Out-Null
        Write-Host "  ✅ $pkg" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  $pkg failed — try manually: pip install $pkg" -ForegroundColor Yellow
    }
}

# Optional (heavier) — comment out if you don't need them
$optPkgs = @(
    # "scrapling",          # advanced scraping
    # "langchain-openai",   # langchain compat
    # "cloakbrowser",       # privacy browser
    # "graphiti-core",      # T4 temporal memory (V2)
)
foreach ($pkg in $optPkgs) {
    Write-Host "  ℹ️  Optional (install manually if needed): pip install $pkg" -ForegroundColor DarkGray
}

# ═══════════════════════════════════════════════════════════════════════
# STEP 7 — OpenCode install
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""; Write-Host "[7/9] Checking OpenCode..." -ForegroundColor Yellow

$ocBin = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $ocBin) {
    Write-Host "  ⚠️  OpenCode not installed. Run:" -ForegroundColor Yellow
    Write-Host "      npm install -g opencode-ai" -ForegroundColor Cyan
    Write-Host "  Or: curl -fsSL https://opencode.ai/install | bash" -ForegroundColor Cyan
} else {
    Write-Host "  ✅ OpenCode found: $($ocBin.Source)" -ForegroundColor Green
}

# ═══════════════════════════════════════════════════════════════════════
# STEP 8 — Local LLM (optional)
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""; Write-Host "[8/9] Local LLM check (optional)..." -ForegroundColor Yellow

$ollamaBin = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaBin) {
    Write-Host "  ℹ️  Ollama not found — local model optional (cloud-first)" -ForegroundColor DarkGray
    Write-Host "      Install: https://ollama.ai  then: ollama pull qwen3.5:9b-instruct-q4_K_M" -ForegroundColor DarkGray
} else {
    Write-Host "  ✅ Ollama found. Local model: qwen3.5:9b-instruct-q4_K_M" -ForegroundColor Green
    Write-Host "  ℹ️  Pull if needed: ollama pull qwen3.5:9b-instruct-q4_K_M" -ForegroundColor DarkGray
}

# ═══════════════════════════════════════════════════════════════════════
# STEP 9 — Final summary
# ═══════════════════════════════════════════════════════════════════════
Write-Host ""; Write-Host "[9/9] Done!" -ForegroundColor Yellow
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   MAST v1.0 — Installation Complete                         ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  📁 Config:    $cfg" -ForegroundColor White
Write-Host "║  🔑 Add keys:  config\.env (fill in your API keys)          ║" -ForegroundColor White
Write-Host "║  🚀 Run:       opencode  (in any project folder)            ║" -ForegroundColor White
Write-Host "║  📖 SOUL file: SOUL_MAST.md (edit to change behavior)       ║" -ForegroundColor White
Write-Host "╠══════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  FREE providers to add first (no billing):                  ║" -ForegroundColor Cyan
Write-Host "║    Groq:    console.groq.com       (gsk_ prefix)            ║" -ForegroundColor Cyan
Write-Host "║    NVIDIA:  build.nvidia.com       (nvapi- prefix, 40 RPM) ║" -ForegroundColor Cyan
Write-Host "║    Gemini:  aistudio.google.com    (AIza prefix)            ║" -ForegroundColor Cyan
Write-Host "║    Mistral: console.mistral.ai     (msk- prefix, 1B/mo)    ║" -ForegroundColor Cyan
Write-Host "║    Cerebras: cloud.cerebras.ai     (csk- prefix)           ║" -ForegroundColor Cyan
Write-Host "║    OpenRouter: openrouter.ai       (sk-or- prefix)         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

if (-not $allOk) {
    Write-Host "⚠️  Some steps had warnings — check above and fix manually" -ForegroundColor Yellow
} else {
    Write-Host "✅ All steps completed. Open a terminal → cd <project> → opencode" -ForegroundColor Green
}
