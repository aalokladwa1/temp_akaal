@echo off
title Akaal Enterprise Software
echo ===================================================
echo     AKAAL ENTERPRISE MIGRATION PLATFORM
echo ===================================================
echo Starting AKAAL Python Engine...
cd /d "c:\Users\LENOVO\Downloads\temp_akaal-main"
start "Akaal Engine" /min py main.py --ipc

echo Starting AKAAL Software Desktop Service...
cd /d "c:\Users\LENOVO\Downloads\temp_akaal-main\akaal_software"
start "Akaal Desktop UI" /min npx vite preview --port 4173

ping 127.0.0.1 -n 4 >nul
echo Launching AKAAL Desktop Application Window...
start "" "msedge.exe" --app=http://localhost:4173 --window-size=1280,800
