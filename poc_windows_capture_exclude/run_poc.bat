@echo off
setlocal

echo ==============================================
echo Cheatly Windows Capture Exclusion POC Launcher
echo ==============================================
echo Script dir: %~dp0
echo.

set "LOGFILE=%~dp0poc_launcher.log"
set "POC_LOGFILE=%LOGFILE%"
if exist "%LOGFILE%" del /f /q "%LOGFILE%" >nul 2>&1

echo [INFO] Writing execution log to:
echo        %LOGFILE%
echo.
echo [INFO] Launcher started > "%LOGFILE%"
echo [INFO] Script dir: %~dp0 >> "%LOGFILE%"

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using launcher: py -3
    echo [INFO] Using launcher: py -3 >> "%LOGFILE%"
    py -3 "%~dp0poc_windows_capture_exclusion.py"
) else (
    echo Launcher 'py' not found. Trying 'python' from PATH.
    echo [INFO] Launcher 'py' not found. Trying 'python' from PATH. >> "%LOGFILE%"
    python "%~dp0poc_windows_capture_exclusion.py"
)

set EXITCODE=%ERRORLEVEL%
echo.
if NOT "%EXITCODE%"=="0" (
    echo [ERROR] POC exited with error code: %EXITCODE% >> "%LOGFILE%"
    echo POC exited with error code: %EXITCODE%
    echo.
    echo ----- Python output (root cause) -----
    type "%LOGFILE%"
    echo ----- End output -----
    echo.

    findstr /I /C:"No module named tkinter" "%LOGFILE%" >nul && (
        echo [ROOT CAUSE] Python was installed without tkinter.
        echo [FIX] Reinstall Python from python.org and enable tkinter/tcl-tk.
    )
    findstr /I /C:"'python' is not recognized" /C:"'py' is not recognized" "%LOGFILE%" >nul && (
        echo [ROOT CAUSE] Python is not installed or not in PATH.
        echo [FIX] Install Python and select "Add python.exe to PATH".
    )
    findstr /I /C:"SyntaxError" /C:"tuple[" "%LOGFILE%" >nul && (
        echo [ROOT CAUSE] Python version is too old for this script typing syntax.
        echo [FIX] Use Python 3.9+ (recommended 3.11+).
    )
    findstr /I /C:"This POC must be run on Windows" "%LOGFILE%" >nul && (
        echo [ROOT CAUSE] Script was launched outside Windows.
    )
    findstr /I /C:"Win32 error: 87" /C:"Win32 error=87" "%LOGFILE%" >nul && (
        echo [ROOT CAUSE] WDA_EXCLUDEFROMCAPTURE unsupported on this Windows build.
        echo [FIX] Use Windows 10 2004+ or Windows 11.
    )
) else (
    echo [INFO] POC exited successfully. >> "%LOGFILE%"
    echo POC exited successfully.
    if exist "%LOGFILE%" (
        echo.
        echo ----- Python output -----
        type "%LOGFILE%"
        echo ----- End output -----
    )
)

echo.
echo Press ENTER to close this window...
set /p __CLOSE_NOW__=

endlocal
