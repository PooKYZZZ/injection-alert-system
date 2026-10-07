@echo off
setlocal
for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

echo Starting the complete local Injection Alert System stack...
echo This rebuilds and starts backend, frontend, technical WAF, bridge, and demo target.
echo Docker volumes are preserved.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\scripts\rebuild_full_local_stack.ps1"
set "exitCode=%ERRORLEVEL%"

echo.
if not "%exitCode%"=="0" (
    echo Stack startup failed with exit code %exitCode%.
) else (
    echo Stack startup completed.
)
pause
exit /b %exitCode%
