@echo off
echo ===================================================
echo Generating isolated per-IP stack from proxies.txt...
echo ===================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0generate-compose.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to generate docker-compose.yml from proxies.txt.
    pause
    exit /b 1
)

echo.
echo Starting Honeygain Multi-Proxy Stack...
docker compose up -d --remove-orphans
if %ERRORLEVEL% EQU 0 (
    echo.
    echo All Honeygain nodes and isolated proxy tunnels started successfully!
    echo Run check-ips.bat to verify each node's public IP, or logs.bat to view live status.
) else (
    echo.
    echo [ERROR] Failed to start containers. Make sure Docker Desktop is running.
)
pause
