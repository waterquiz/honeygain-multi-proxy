@echo off
echo Regenerating docker-compose.yml from proxies.txt...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0generate-compose.ps1"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Applying updated containers...
    docker compose up -d --remove-orphans
)
pause
