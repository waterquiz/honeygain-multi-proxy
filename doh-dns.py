#!/usr/bin/env python3
"""Minimal UDP+TCP DNS forwarder on 127.0.0.1:53 -> DoH (port 443) for TCP-only proxies."""

import socket
import struct
import threading
import urllib.request

DOH_ENDPOINTS = (
    "https://1.1.1.1/dns-query",
    "https://8.8.8.8/dns-query",
)


def query_doh(packet: bytes) -> bytes:
    for url in DOH_ENDPOINTS:
        try:
            req = urllib.request.Request(
                url,
                data=packet,
                method="POST",
                headers={
                    "Content-Type": "application/dns-message",
                    "Accept": "application/dns-message",
                },
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception:
            continue
    return b""


def handle_udp(sock: socket.socket, data: bytes, addr):
    reply = query_doh(data)
    if reply:
        sock.sendto(reply, addr)


def serve_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 53))
    while True:
        data, addr = sock.recvfrom(4096)
        threading.Thread(target=handle_udp, args=(sock, data, addr), daemon=True).start()


def handle_tcp(conn: socket.socket):
    try:
        hdr = conn.recv(2)
        if len(hdr) < 2:
            return
        (length,) = struct.unpack("!H", hdr)
        buf = b""
        while len(buf) < length:
            chunk = conn.recv(length - len(buf))
            if not chunk:
                return
            buf += chunk
        reply = query_doh(buf)
        if reply:
            conn.sendall(struct.pack("!H", len(reply)) + reply)
    finally:
        conn.close()


def serve_tcp():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 53))
    srv.listen(64)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle_tcp, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    threading.Thread(target=serve_tcp, daemon=True).start()
    serve_udp()
