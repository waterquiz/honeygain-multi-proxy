# Honeygain Multi-Proxy Isolated Docker Setup

Run multiple Honeygain nodes on **one single Honeygain account**, where **every proxy IP** runs inside its own isolated virtual machine/network identity so Honeygain sees each IP as a completely separate device and person.

---

## 🔒 How Per-IP Isolation Works

Every proxy in `proxies.txt` gets its own dedicated pair of containers (`tun2socks-N` + `honeygain-N`):

1. **Separate Isolated Bridge Network (`net_node_N`)**: Each node runs on its own private `/24` Docker subnet (`172.28.11.0/24`, `172.28.12.0/24`, ...). Nodes cannot see or communicate with each other.
2. **Unique Hardware/Network Identity**: Each node receives its own unique `hostname` (`DESKTOP-...`) and unique `mac_address` (`02:42:ac:18:...`).
3. **Zero DNS Leak (`resolv.conf`)**: Both `tun2socks` and `honeygain` use [`resolv.conf`](resolv.conf) (`1.1.1.1` / `8.8.8.8`) routed through the proxy tunnel instead of your PC's ISP DNS.
4. **Startup Kill-Switch (`service_healthy`)**: `honeygain-N` will not start until `tun2socks-N` has brought up `tun0`, preventing any accidental connection over your home IP.
5. **Unique Device Name**: Each IP registers with its own distinct `-device` name on your Honeygain dashboard.

---

## ⚙️ Initial Setup

1. Copy [`.env.example`](.env.example) to `.env` and fill in your Honeygain email and password:
   ```env
   HONEYGAIN_EMAIL=your_email@example.com
   HONEYGAIN_PASS=your_password
   HONEYGAIN_TZ=America/New_York
   ```
2. Copy [`proxies.example.txt`](proxies.example.txt) to `proxies.txt` and add one proxy per line:
   ```text
   1.2.3.4:50100:username:password:Device-01
   5.6.7.8:50100:username:password:Device-02
   ```
   Supported formats:
   - `IP:PORT:USER:PASS:CustomDeviceName`
   - `IP:PORT:USER:PASS`
   - `IP:PORT`
   - `socks5://USER:PASS@IP:PORT` or `http://USER:PASS@IP:PORT`

---

## 🌐 Adding or Changing Any IP / Proxy

Edit `proxies.txt` and double-click [`update-proxies.bat`](update-proxies.bat) (or [`start.bat`](start.bat)) to regenerate `docker-compose.yml` and apply the changes.

---

## 🚀 Usage

1. Make sure **Docker Desktop** is open and running.
2. Double-click [`start.bat`](start.bat) to generate `docker-compose.yml` and start all isolated nodes.
3. Double-click [`check-ips.bat`](check-ips.bat) to verify the exact public IP each tunnel is using.
4. Double-click [`logs.bat`](logs.bat) to watch live Honeygain connection and earning logs.
5. Double-click [`stop.bat`](stop.bat) to stop all containers.
