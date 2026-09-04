@echo off
setlocal
cd /d "%~dp0"

echo Starting the complete Cloudflare target stack...
echo This builds and starts the backend, frontend, demo portal, target WAF, bridge, and cloudflared.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_full_cloudflare_target.ps1"
set "exitCode=%ERRORLEVEL%"

echo.
if not "%exitCode%"=="0" (
    echo Stack startup failed with exit code %exitCode%.
) else (
    echo Stack startup completed.
)
pause
exit /b %exitCode%
