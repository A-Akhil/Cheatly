@echo off
setlocal enableextensions

rem Launches only the Avalonia frontend in a new CMD window.

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

start "Cheatly Frontend" cmd /k "cd /d "%REPO_ROOT%\avalonia\Cheatly.Avalonia" && dotnet run"
exit /b 0
