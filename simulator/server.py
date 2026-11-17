#!/usr/bin/env python3
"""NAS preview server: room state plus mock or live ESPectre CSI."""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from mock_room import MockRoom
from wifi import EspCsiWifi, MockWifi

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], room: MockRoom, wifi: MockWifi | EspCsiWifi) -> None:
        super().__init__(address, Handler)
        self.room = room
        self.wifi = wifi


class Handler(BaseHTTPRequestHandler):
    server_version = "ESPectrePlusPreview/0.3"

    @property
    def preview(self) -> PreviewServer:
        return self.server  # type: ignore[return-value]

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self._send_json(self.preview.room.snapshot())
        elif path == "/api/wifi":
            self._send_json(self.preview.wifi.snapshot())
        elif path == "/api/health":
            wifi = self.preview.wifi.snapshot()
            self._send_json({
                "ok": True,
                "mode": "espectre" if self.preview.wifi.source == "espectre" else "mock",
                "wifi_status": wifi.get("status"),
                "features": ["room", "wifi"],
            })
        else:
            self._serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/wifi/burst":
            if self.preview.wifi.source != "mock":
                self._send_json({"error": "burst injection is only available in mock mode"}, 409)
                return
            self.preview.wifi.burst()
            self._send_json(self.preview.wifi.snapshot())
            return
        if path != "/api/control":
            self._send_json({"error": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            self.preview.room.control(str(payload.get("action", "")), payload.get("value"))
            self._send_json(self.preview.room.snapshot())
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, 400)

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (FRONTEND / rel).resolve()
        if not target.is_relative_to(FRONTEND):
            self._send_json({"error": "forbidden"}, 403)
            return
        if not target.is_file():
            self._send_json({"error": "not found"}, 404)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def run() -> None:
    parser = argparse.ArgumentParser(description="ESPectre Plus NAS preview")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--csi-url", default=os.environ.get("ESPECTRE_CSI_URL", "").strip(),
                        help="ESPectre base URL or raw CSI URL; empty keeps mock mode")
    args = parser.parse_args()

    room = MockRoom()
    try:
        wifi = EspCsiWifi(args.csi_url) if args.csi_url else MockWifi()
    except ValueError as exc:
        parser.error(str(exc))

    def ticker() -> None:
        while True:
            time.sleep(1)
            room.tick()

    threading.Thread(target=ticker, daemon=True).start()
    server = PreviewServer((args.host, args.port), room, wifi)
    print(f"ESPectre Plus preview: http://{args.host}:{args.port}")
    print(f"WiFi source: {wifi.source}")
    if wifi.source == "mock":
        print("Mock CSI; set ESPECTRE_CSI_URL or --csi-url for a device stream.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        wifi.close()


if __name__ == "__main__":
    run()
