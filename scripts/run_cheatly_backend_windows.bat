@echo off
setlocal enableextensions

rem Launches only the backend in a new CMD window.

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

start "Cheatly Backend" cmd /k "cd /d "%REPO_ROOT%" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765"
exit /b 0
