@echo off
setlocal
for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

echo Starting the complete Cloudflare target stack...
echo This builds and starts the backend, frontend, demo portal, target WAF, bridge, and cloudflared.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\scripts\start_full_cloudflare_target.ps1" %*
set "exitCode=%ERRORLEVEL%"

echo.
if not "%exitCode%"=="0" (
    echo Stack startup failed with exit code %exitCode%.
) else (
    echo Stack startup completed.
)
pause
exit /b %exitCode%
