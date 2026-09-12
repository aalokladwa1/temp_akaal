@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   AKAAL Platform - Quick Build ^& Launch
echo ========================================================

set "NG_CLI_ANALYTICS=false"
set "NG_BUILD_MAX_WORKERS=1"
set "NG_BUILD_PARALLEL_TS=0"
set "NG_BUILD_TYPE_CHECK=0"
set "ESBUILD_WORKER_THREADS=1"

echo.
echo [1/4] Terminating running instances...
taskkill /F /IM AKAAL.exe >nul 2>&1
taskkill /F /IM akaalSoftware.exe >nul 2>&1

echo [2/4] Building Angular frontend...
cd /d "%~dp0frontend"
call npm run build:fast

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Frontend build failed with code %ERRORLEVEL%!
    exit /b %ERRORLEVEL%
)

echo.
echo [3/4] Clearing WebView2 cache...
if exist "%APPDATA%\AKAAL.exe\EBWebView" (
    rmdir /s /q "%APPDATA%\AKAAL.exe\EBWebView" >nul 2>&1
)
if exist "%APPDATA%\akaalSoftware.exe\EBWebView" (
    rmdir /s /q "%APPDATA%\akaalSoftware.exe\EBWebView" >nul 2>&1
)

echo.
echo [4/4] Compiling Go Wails GUI Binary...
cd /d "%~dp0"
go build -tags "desktop,production" -ldflags "-H windowsgui -s -w" -o AKAAL.exe .

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Go build failed with code %ERRORLEVEL%!
    exit /b %ERRORLEVEL%
)

copy /Y AKAAL.exe akaalSoftware.exe >nul

echo.
echo ========================================================
echo   BUILD SUCCESSFUL! Binaries are ready.
echo ========================================================