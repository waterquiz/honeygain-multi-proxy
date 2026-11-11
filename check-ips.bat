@echo off
echo Checking live public IP seen by each Honeygain tunnel...
echo.
for /f "tokens=*" %%C in ('docker ps --filter "name=tun2socks-" --format "{{.Names}}"') do (
    echo|set /p="%%C -> "
    docker run --rm --network container:%%C curlimages/curl:latest -s --max-time 10 https://api.ipify.org
    echo.
)
echo.
pause
