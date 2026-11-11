#!/usr/bin/env python3
"""
Railway entrypoint for running one or more Honeygain instances routed through
proxychains4 using Railway environment variables (HONEYGAIN_EMAIL, HONEYGAIN_PASS,
PROXIES / PROXY, HONEYGAIN_DEVICE, PORT).
"""

import http.server
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse


STATE = {
    "status": "starting",
    "nodes": [],
    "warnings": [],
}


def parse_proxy_line(raw: str, index: int, default_prefix: str):
    line = raw.strip()
    if not line or line.startswith("#"):
        return None

    device = f"{default_prefix}-{index}"
    scheme = "socks5"
    user = ""
    password = ""

    if "://" in line:
        parsed = urlparse(line)
        scheme = "http" if parsed.scheme.startswith("http") else "socks5"
        host = parsed.hostname
        port = parsed.port
        user = parsed.username or ""
        password = parsed.password or ""
    else:
        parts = line.split(":")
        if len(parts) == 2:
            host, port = parts[0], int(parts[1])
        elif len(parts) == 4:
            host, port, user, password = parts[0], int(parts[1]), parts[2], parts[3]
        elif len(parts) >= 5:
            host, port, user, password = parts[0], int(parts[1]), parts[2], parts[3]
            custom = "-".join(parts[4:]).strip()
            if custom:
                device = custom
        else:
            raise ValueError(f"Invalid proxy format: {line}")

    if not host or not port:
        raise ValueError(f"Missing host/port in proxy: {line}")

    resolved_ip = socket.gethostbyname(host)
    return {
        "index": index,
        "scheme": scheme,
        "host": host,
        "ip": resolved_ip,
        "port": int(port),
        "user": user,
        "password": password,
        "device": device,
    }


def load_proxies():
    raw_proxies = os.environ.get("PROXIES") or os.environ.get("PROXY") or ""
    default_prefix = os.environ.get("HONEYGAIN_DEVICE", "Railway-Node").strip() or "Railway-Node"
    tokens = [t.strip() for t in re.split(r"[\r\n,;]+", raw_proxies) if t.strip()]

    proxies = []
    for idx, token in enumerate(tokens, start=1):
        try:
            parsed = parse_proxy_line(token, idx, default_prefix)
            if parsed:
                proxies.append(parsed)
        except Exception as exc:
            print(f"[WARN] Skipping proxy #{idx}: {exc}", flush=True)
            STATE["warnings"].append(f"Skipped proxy #{idx}: {exc}")
    return proxies


def write_proxychains_conf(proxy: dict) -> str:
    conf_path = f"/tmp/proxychains_{proxy['index']}.conf"
    auth = f" {proxy['user']} {proxy['password']}" if proxy["user"] else ""
    content = (
        "strict_chain\n"
        "proxy_dns\n"
        "remote_dns_subnet 224\n"
        "tcp_read_time_out 15000\n"
        "tcp_connect_time_out 8000\n"
        "[ProxyList]\n"
        f"{proxy['scheme']} {proxy['ip']} {proxy['port']}{auth}\n"
    )
    with open(conf_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return conf_path


def verify_proxy_ip(proxy: dict) -> str:
    scheme = "socks5h" if proxy["scheme"] == "socks5" else "http"
    auth = f"{proxy['user']}:{proxy['password']}@" if proxy["user"] else ""
    proxy_url = f"{scheme}://{auth}{proxy['host']}:{proxy['port']}"
    try:
        res = subprocess.run(
            ["curl", "-s", "--max-time", "10", "-x", proxy_url, "https://api.ipify.org"],
            capture_output=True,
            text=True,
            check=False,
        )
        ip_out = res.stdout.strip()
        if res.returncode == 0 and ip_out:
            return ip_out
        return f"check-failed (exit {res.returncode})"
    except Exception as exc:
        return f"check-error ({exc})"


def run_node_loop(proxy: dict, email: str, password: str, stop_event: threading.Event):
    conf_path = write_proxychains_conf(proxy)
    node_state = {
        "index": proxy["index"],
        "device": proxy["device"],
        "proxy": f"{proxy['scheme']}://{proxy['host']}:{proxy['port']}",
        "exit_ip": verify_proxy_ip(proxy),
        "running": False,
        "restarts": 0,
    }
    STATE["nodes"].append(node_state)
    print(
        f"[Node {proxy['index']}] Device={proxy['device']} Proxy={node_state['proxy']} ExitIP={node_state['exit_ip']}",
        flush=True,
    )

    cmd = [
        "proxychains4",
        "-q",
        "-f",
        conf_path,
        "/app/honeygain",
        "-tou-accept",
        "-email",
        email,
        "-pass",
        password,
        "-device",
        proxy["device"],
    ]

    while not stop_event.is_set():
        node_state["running"] = True
        proc = subprocess.Popen(
            cmd,
            cwd="/app",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if proc.stdout is not None:
            for line in proc.stdout:
                print(f"[Node {proxy['index']} | {proxy['device']}] {line.rstrip()}", flush=True)
                if stop_event.is_set():
                    break
        code = proc.wait()
        node_state["running"] = False
        if stop_event.is_set():
            break
        node_state["restarts"] += 1
        print(
            f"[Node {proxy['index']}] Exited with code {code}; restarting in 10s...",
            flush=True,
        )
        stop_event.wait(10)


class StatusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        payload = json.dumps(STATE, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


def main():
    port = int(os.environ.get("PORT", "5000"))
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), StatusHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Health/status server listening on 0.0.0.0:{port}", flush=True)

    email = os.environ.get("HONEYGAIN_EMAIL", "").strip()
    password = os.environ.get("HONEYGAIN_PASS", "").strip()
    proxies = load_proxies()

    if not email or not password:
        STATE["status"] = "missing_credentials"
        print("[ERROR] Set HONEYGAIN_EMAIL and HONEYGAIN_PASS in Railway Variables.", flush=True)
        while True:
            time.sleep(60)

    if not proxies:
        STATE["status"] = "missing_proxies"
        print(
            "[ERROR] Set PROXIES (or PROXY) in Railway Variables, e.g. IP:PORT:USER:PASS",
            flush=True,
        )
        while True:
            time.sleep(60)

    if not os.path.exists("/dev/net/tun"):
        msg = (
            "/dev/net/tun is not available in this container; running via proxychains4 "
            "(TCP only; UDP/QUIC is not tunneled by proxychains4)."
        )
        STATE["warnings"].append(msg)
        print(f"[WARN] {msg}", flush=True)

    stop_event = threading.Event()

    def handle_sig(signum, frame):
        stop_event.set()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sig)
    signal.signal(signal.SIGINT, handle_sig)

    STATE["status"] = "running"
    threads = []
    for proxy in proxies:
        t = threading.Thread(
            target=run_node_loop,
            args=(proxy, email, password, stop_event),
            daemon=True,
        )
        t.start()
        threads.append(t)

    while not stop_event.is_set():
        time.sleep(5)


if __name__ == "__main__":
    main()
