@echo off
cd /d "%~dp0akaalSoftware"
call build.bat
exit /b %ERRORLEVEL%
