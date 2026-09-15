@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   AKAAL Platform - Live Dev Server (wails dev)
echo ========================================================

set "NG_CLI_ANALYTICS=false"
set "NODE_OPTIONS=--max-old-space-size=4096"

cd /d "%~dp0"
wails dev
