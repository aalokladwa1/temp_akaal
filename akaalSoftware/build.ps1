# DevKros Desktop Production Build Script
Write-Host "1. Building Angular production frontend..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\frontend"
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "2. Compiling Go Windows GUI binary without terminal subsystem..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot"
Stop-Process -Name AKAAL -Force -ErrorAction SilentlyContinue
go build -tags "desktop,production" -ldflags "-H windowsgui -s -w" -o AKAAL.exe .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Go compilation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Build complete! AKAAL.exe is ready (pure GUI, no console window)." -ForegroundColor Green
