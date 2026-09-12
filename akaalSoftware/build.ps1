$env:NG_CLI_ANALYTICS = "false"
$env:NODE_OPTIONS = "--max-old-space-size=4096"
$env:NG_BUILD_MAX_WORKERS = "1"
$env:NG_BUILD_PARALLEL_TS = "0"
$env:NG_BUILD_TYPE_CHECK = "0"
$env:ESBUILD_WORKER_THREADS = "1"

Write-Host "1. Building Angular production frontend (4096MB heap)..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\frontend"
node --max-old-space-size=4096 ./node_modules/@angular/cli/bin/ng build --base-href ./

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "2. Compiling Go Windows GUI binary..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot"
Stop-Process -Name AKAAL -Force -ErrorAction SilentlyContinue
Stop-Process -Name akaalSoftware -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Remove-Item -Path "$env:APPDATA\AKAAL.exe\EBWebView" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:APPDATA\akaalSoftware.exe\EBWebView" -Recurse -Force -ErrorAction SilentlyContinue

go build -tags "desktop,production" -ldflags "-H windowsgui -s -w" -o AKAAL.exe .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Go compilation failed!" -ForegroundColor Red
    exit 1
}

Copy-Item -Path "$PSScriptRoot\AKAAL.exe" -Destination "$PSScriptRoot\akaalSoftware.exe" -Force

Write-Host "Build complete! AKAAL.exe and akaalSoftware.exe are ready." -ForegroundColor Green
