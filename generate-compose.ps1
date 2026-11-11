# Generates docker-compose.yml from proxies.txt so every proxy IP runs
# in a completely isolated network/identity container on the same Honeygain account.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$proxiesFile = Join-Path $scriptDir "proxies.txt"
$composeFile = Join-Path $scriptDir "docker-compose.yml"

if (-not (Test-Path $proxiesFile)) {
    Write-Error "proxies.txt not found at $proxiesFile"
    exit 1
}

$lines = Get-Content $proxiesFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith("#") }

if ($lines.Count -eq 0) {
    Write-Error "No proxies found in proxies.txt"
    exit 1
}

$services = New-Object System.Text.StringBuilder
$networks = New-Object System.Text.StringBuilder
$nodeNames = New-Object System.Collections.Generic.List[string]

$index = 0
foreach ($line in $lines) {
    $index++
    $customDevice = $null
    $proxyUrl = $null

    if ($line -match '^(socks5|socks4|http|https)://') {
        $proxyUrl = $line
    } else {
        $parts = $line -split ':'
        if ($parts.Count -eq 2) {
            $proxyUrl = "socks5://$($parts[0]):$($parts[1])"
        } elseif ($parts.Count -eq 4) {
            $proxyUrl = "socks5://$($parts[2]):$($parts[3])@$($parts[0]):$($parts[1])"
        } elseif ($parts.Count -ge 5) {
            $proxyUrl = "socks5://$($parts[2]):$($parts[3])@$($parts[0]):$($parts[1])"
            $customDevice = ($parts[4..($parts.Count - 1)] -join "-").Trim()
        } else {
            Write-Warning "Skipping invalid proxy line #$index : $line"
            continue
        }
    }

    $deviceName = if ($customDevice) { $customDevice } else { "Honeygain-Node-$index" }
    $hostname = ("DESKTOP-" + [BitConverter]::ToString([System.Security.Cryptography.MD5]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes("hg-$index-$proxyUrl"))).Replace("-", "").Substring(0, 7))
    $macOctet5 = "{0:x2}" -f ([int][Math]::Floor(($index - 1) / 250) + 1)
    $macOctet6 = "{0:x2}" -f ([int](($index - 1) % 250) + 1)
    $macAddress = "02:42:ac:18:${macOctet5}:${macOctet6}"
    $subnetOctet3 = 10 + $index
    $netName = "net_node_$index"
    $nodeNames.Add("honeygain-$index")

    [void]$services.AppendLine(@"
  # ==============================
  # Node $index ($deviceName)
  # ==============================
  tun2socks-${index}:
    image: xjasonlyu/tun2socks:latest
    container_name: tun2socks-$index
    hostname: $hostname
    mac_address: "$macAddress"
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun:/dev/net/tun
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.rp_filter=0
    dns:
      - 1.1.1.1
      - 8.8.8.8
    volumes:
      - ./resolv.conf:/etc/resolv.conf:ro
    environment:
      - LOGLEVEL=info
      - TUN=tun0
      - PROXY=$proxyUrl
    healthcheck:
      test: ["CMD-SHELL", "ip link show tun0 >/dev/null 2>&1 || exit 1"]
      interval: 3s
      timeout: 3s
      retries: 10
      start_period: 2s
    networks:
      - $netName

  honeygain-${index}:
    image: honeygain/honeygain:latest
    container_name: honeygain-$index
    restart: unless-stopped
    depends_on:
      tun2socks-${index}:
        condition: service_healthy
    network_mode: "service:tun2socks-$index"
    volumes:
      - ./resolv.conf:/etc/resolv.conf:ro
    environment:
      - TZ=`${HONEYGAIN_TZ:-America/New_York}
    command: -tou-accept -email `${HONEYGAIN_EMAIL} -pass `${HONEYGAIN_PASS} -device $deviceName

"@)

    [void]$networks.AppendLine(@"
  ${netName}:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.${subnetOctet3}.0/24
"@)
}

$composeContent = @"
# Auto-generated from proxies.txt by generate-compose.ps1
# Each node has its own isolated bridge network, MAC, hostname, DNS, and SOCKS5 tunnel.

services:
$($services.ToString().TrimEnd())

networks:
$($networks.ToString().TrimEnd())
"@

[System.IO.File]::WriteAllText($composeFile, $composeContent + "`n", (New-Object System.Text.UTF8Encoding $false))
Write-Host "Generated docker-compose.yml for $($nodeNames.Count) isolated proxy node(s)."
