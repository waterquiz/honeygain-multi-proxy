# Honeygain Multi-Proxy Docker Setup

Run multiple Honeygain nodes on **one single Honeygain account**, where each proxy IP runs with its own device identity.

---

## ☁️ Option 1: Deploy on Railway (via Variables)

This repository includes [`Dockerfile`](Dockerfile) and [`railway.json`](railway.json) for Railway deployment.

1. Connect `waterquiz/honeygain-multi-proxy` in Railway and deploy.
2. Open **Service → Variables** in Railway and add:
   - `HONEYGAIN_EMAIL` = your Honeygain email
   - `HONEYGAIN_PASS` = your Honeygain password
   - `PROXIES` = one or more proxies separated by newlines or commas:
     ```text
     1.2.3.4:50100:username:password:Device-01
     5.6.7.8:50100:username:password:Device-02
     ```
   - *(Optional)* `HONEYGAIN_DEVICE` = default device prefix (defaults to `Railway-Node`)
3. Redeploy and check **Deploy Logs** (or visit the service URL to see JSON node status).

> **Note on Railway limitations:** Railway does not provide `/dev/net/tun` or `NET_ADMIN`, so on Railway this container uses `proxychains4` (TCP-only proxying). If Honeygain requires UDP/QUIC (`libmsquic.so`) on your proxies, use Option 2 (Docker Desktop / Linux VPS with `tun2socks`) for full TCP + UDP tunneling.

---

## 💻 Option 2: Local Windows Docker Desktop / Linux VPS (`tun2socks` Full Isolation)

Every proxy in `proxies.txt` gets its own dedicated pair of containers (`tun2socks-N` + `honeygain-N`):

1. **Separate Isolated Bridge Network (`net_node_N`)**: Each node runs on its own private `/24` Docker subnet.
2. **Unique Hostname & MAC Address**: Each tunnel node receives a unique `hostname` and `mac_address`.
3. **Zero DNS Leak (`resolv.conf`)**: Uses [`resolv.conf`](resolv.conf) (`1.1.1.1` / `8.8.8.8`) through the proxy tunnel.
4. **Startup Kill-Switch (`service_healthy`)**: `honeygain-N` waits until `tun0` is active before starting.

### Initial Setup
1. Copy [`.env.example`](.env.example) to `.env` and fill in your Honeygain email and password.
2. Copy [`proxies.example.txt`](proxies.example.txt) to `proxies.txt` and add one proxy per line:
   ```text
   1.2.3.4:50100:username:password:Device-01
   5.6.7.8:50100:username:password:Device-02
   ```
3. Make sure **Docker Desktop** is running, then double-click [`start.bat`](start.bat).
4. Use [`check-ips.bat`](check-ips.bat), [`logs.bat`](logs.bat), [`update-proxies.bat`](update-proxies.bat), and [`stop.bat`](stop.bat) to manage your nodes.
