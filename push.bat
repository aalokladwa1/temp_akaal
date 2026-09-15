@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   AKAAL Platform - Git Commit ^& Push
echo ========================================================

cd /d "%~dp0"

echo [1/3] Staging changes...
git add .

echo [2/3] Committing changes...
git commit -m "fix(migration): restore native Step 2 & Step 3 Migration UX with full capability parity"

echo [3/3] Pushing to remote origin main...
git push origin main

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Git push failed with code %ERRORLEVEL%!
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo   PUSH SUCCESSFUL!
echo ========================================================
