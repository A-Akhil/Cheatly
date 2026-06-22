@echo off
setlocal enableextensions

rem Launches two CMD windows:
rem 1) FastAPI backend
rem 2) Avalonia frontend

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

call :run_backend
call :run_frontend
exit /b 0

:run_backend
start "Cheatly Backend" cmd /k "cd /d "%REPO_ROOT%" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765"
exit /b 0

:run_frontend
start "Cheatly Frontend" cmd /k "cd /d "%REPO_ROOT%\avalonia\Cheatly.Avalonia" && dotnet run"
exit /b 0
