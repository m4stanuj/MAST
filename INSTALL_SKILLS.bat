@echo off
REM MAST Skills Installer v1.0
REM Installs skills/, agents/, commands/ into OpenCode config folder
REM
REM HOW TO USE:
REM 1. Extract this ZIP file
REM 2. Double-click INSTALL_SKILLS.bat  (or run install.ps1 for full setup)
REM
REM For full installation (MCP servers + all packages): run install.ps1

echo.
echo ============================================================
echo    MAST v1.0 — Skills Installer
echo    M4STCLAW v3 + OpenWork v12 + EIGENT v4.1
echo ============================================================
echo.

REM Find config dir
set MAST_PATH=

if exist "%USERPROFILE%\.config\opencode" (
    set MAST_PATH=%USERPROFILE%\.config\opencode
    goto :found
)

if exist ".opencode" (
    set MAST_PATH=.opencode
    goto :found
)

if exist "C:\workk\.opencode" (
    set MAST_PATH=C:\workk\.opencode
    goto :found
)

:found
if not defined MAST_PATH (
    echo ERROR: .config\opencode not found!
    echo Run install.ps1 first to create the config directory.
    pause
    exit /b 1
)

echo Installing to: %MAST_PATH%
echo.

REM Install skills (28 skills)
if exist "skills" (
    echo [1/3] Installing skills...
    if not exist "%MAST_PATH%\skills" mkdir "%MAST_PATH%\skills"
    xcopy /E /Y skills\* "%MAST_PATH%\skills\" >nul 2>&1
    echo       Done! ^(28 skills^)
)

REM Install agents
if exist "agents" (
    echo [2/3] Installing agents config...
    if not exist "%MAST_PATH%\agents" mkdir "%MAST_PATH%\agents"
    xcopy /E /Y agents\* "%MAST_PATH%\agents\" >nul 2>&1
    echo       Done!
)

REM Install commands
if exist "commands" (
    echo [3/3] Installing commands...
    if not exist "%MAST_PATH%\commands" mkdir "%MAST_PATH%\commands"
    xcopy /E /Y commands\* "%MAST_PATH%\commands\" >nul 2>&1
    echo       Done!
)

echo.
echo ============================================================
echo    Skills Installed! Restart OpenCode to activate.
echo ============================================================
echo.
echo Skills: aivector-memory, asset-gen-local, chrome-devtools,
echo         context7-docs, env-guardian, excel-full, gui,
echo         image-processing, m4st-hinglish-brain, m4st-pentest-cai,
echo         m4st-scheduler, mcp-arch, multi-agent-omo, music-gen,
echo         palot-gui, persistent-memory, playwright-mcp,
echo         research-doc, safety-net, screenpipe, session-handoff,
echo         superpowers, telegram, token-optimizer, video-gen,
echo         vision-gui, web-search-exa, workspace-guide
echo.
echo For full setup with MCP servers: run install.ps1
echo.
pause
