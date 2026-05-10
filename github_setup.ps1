# =============================================================================
#  MAST — GitHub Setup Script
#  Run this ONCE to create repo + push everything to GitHub
#
#  Prerequisites:
#    1. GitHub account: github.com/mastjarvis-cmyk  (ya jo bhi handle ho)
#    2. Git installed: git --version
#    3. GitHub CLI (optional but easier): gh auth login
#       OR Personal Access Token: github.com/settings/tokens
#
#  Run: powershell -ExecutionPolicy Bypass -File github_setup.ps1
# =============================================================================

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   MAST v1.0 — GitHub Setup                                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Config — CHANGE THESE ────────────────────────────────────────────
$GITHUB_USERNAME = "mastjarvis-cmyk"       # <- tera GitHub handle
$REPO_NAME       = "MAST"                  # <- repo name
$REPO_DESC       = "Unified AI operator — 21 MCP servers, 11 providers, NVIDIA NIM + Mistral. M4STCLAW v3 + OpenWork v12 + EIGENT v4.1"
$REPO_PRIVATE    = $false                  # $true = private, $false = public
$MAST_DIR        = Split-Path -Parent $MyInvocation.MyCommand.Path
# ─────────────────────────────────────────────────────────────────────

Set-Location $MAST_DIR

# Step 1: Git check
Write-Host "[1/5] Checking git..." -ForegroundColor Yellow
try {
    $gv = git --version 2>&1
    Write-Host "  ✅ $gv" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Git not found. Install: git-scm.com" -ForegroundColor Red
    exit 1
}

# Step 2: Init repo
Write-Host "[2/5] Initializing repo..." -ForegroundColor Yellow
if (-not (Test-Path ".git")) {
    git init
    Write-Host "  ✅ git init done" -ForegroundColor Green
} else {
    Write-Host "  ✓  Already a git repo" -ForegroundColor DarkGray
}

# Set default branch to main
git branch -M main 2>&1 | Out-Null

# Step 3: Safety check — make sure .env is not being committed
Write-Host "[3/5] Safety check (no secrets in commit)..." -ForegroundColor Yellow
$envFile = "config\.env"
if (Test-Path $envFile) {
    $inGitignore = (Get-Content ".gitignore" -ErrorAction SilentlyContinue) -match "config/\.env"
    if ($inGitignore) {
        Write-Host "  ✅ config/.env is in .gitignore — safe" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Adding config/.env to .gitignore..." -ForegroundColor Yellow
        Add-Content ".gitignore" "`nconfig/.env"
    }
}
# Double-check: remove .env from tracking if accidentally staged
git rm --cached config/.env 2>&1 | Out-Null
git rm --cached .env 2>&1 | Out-Null

# Step 4: First commit
Write-Host "[4/5] Creating first commit..." -ForegroundColor Yellow
git add .
git status --short | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
git commit -m "feat: MAST v1.0 — Unified AI stack (M4STCLAW v3 + OpenWork v12 + EIGENT v4.1)

- 21 MCP servers (pentest, agents, scheduler, task-router + 17 core)
- 11 providers: Groq, Cerebras, Gemini, OpenRouter, SambaNova, DeepSeek,
  Together, NVIDIA NIM, Mistral, xAI/Grok, HuggingFace
- 11 task chains incl. pentest (NVIDIA primary) + hinglish (Sarvam-M)
- Zero hardcoded keys — all env-based with SMART_KEY auto-detect
- bridge_core: recon, vuln, agents, scheduler, memory (from M4STCLAW v3)
- 28 skills, SOUL_MAST.md hot-reload identity
- Windows installer (install.ps1) with dynamic path substitution" 2>&1
Write-Host "  ✅ Commit created" -ForegroundColor Green

# Step 5: Push to GitHub
Write-Host "[5/5] Pushing to GitHub..." -ForegroundColor Yellow
Write-Host ""

# Try GitHub CLI first (easiest)
$ghCli = Get-Command gh -ErrorAction SilentlyContinue
if ($ghCli) {
    Write-Host "  GitHub CLI found — creating repo automatically..." -ForegroundColor Cyan
    $visibility = if ($REPO_PRIVATE) { "--private" } else { "--public" }
    gh repo create "$GITHUB_USERNAME/$REPO_NAME" $visibility --description $REPO_DESC --push --source . 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "  ✅ Repo live: https://github.com/$GITHUB_USERNAME/$REPO_NAME" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  gh CLI failed — try manual steps below" -ForegroundColor Yellow
        goto :manual
    }
} else {
    :manual
    Write-Host "  GitHub CLI not found. Manual steps:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Go to: https://github.com/new" -ForegroundColor White
    Write-Host "  2. Repo name: $REPO_NAME" -ForegroundColor White
    Write-Host "  3. Description: $REPO_DESC" -ForegroundColor White
    Write-Host "  4. Set: $(if ($REPO_PRIVATE) {'Private'} else {'Public'})" -ForegroundColor White
    Write-Host "  5. DON'T add README/gitignore (we have them)" -ForegroundColor White
    Write-Host "  6. Create repo, then run:" -ForegroundColor White
    Write-Host ""
    Write-Host "     git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git" -ForegroundColor Cyan
    Write-Host "     git push -u origin main" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Optional — install GitHub CLI for next time:" -ForegroundColor DarkGray
    Write-Host "     winget install GitHub.cli" -ForegroundColor DarkGray
    Write-Host "     gh auth login" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Done! Repo: github.com/$GITHUB_USERNAME/$REPO_NAME" -ForegroundColor Green
Write-Host "║  Pin it on your profile for max visibility 📌               ║" -ForegroundColor Green  
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
