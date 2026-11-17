#!/usr/bin/env python3
"""Synthetic ESPectre V8 CSI endpoint for protocol-level preview tests.

This is not a real device. It emits frames with the same binary layout as
ESPectre Direct HTTP so the NAS client can be exercised without a 2.4 GHz node.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PREFIX = struct.Struct("<IBBH16sQHHQQQ")
RECORD = struct.Struct("<HBBBBIHHQQIQBbbQIIBBB")
SESSION = bytes.fromhex("00112233445566778899aabbccddeeff")
DEVICE_ID = 0x1122334455667788


def build_frame(sequence: int, phase: float) -> bytes:
    amplitudes: list[float] = []
    source_position = 10.0 + (phase * 9.0) % 44.0
    for index in range(64):
        base = 0.62 + 0.05 * math.sin(index * 0.22 + phase * 1.1)
        notch = 0.18 * math.exp(-((index - 22) / 3.2) ** 2)
        notch += 0.11 * math.exp(-((index - 50) / 2.8) ** 2)
        interference = (0.22 + 0.13 * math.sin(phase * 1.8)) * math.exp(-((index - source_position) / 3.8) ** 2)
        amplitudes.append(max(0.06, min(1.0, base - notch + interference + 0.015 * math.sin(index * 1.7))))

    payload = bytearray()
    for index, amplitude in enumerate(amplitudes):
        angle = phase * 1.4 + index * 0.31
        q = int(round(amplitude * 82.0 * math.cos(angle)))
        i = int(round(amplitude * 82.0 * math.sin(angle)))
        payload.extend((q & 0xFF, i & 0xFF))

    record = RECORD.pack(
        0x4353,
        8,
        64,
        3,
        3,
        sequence & 0xFFFFFFFF,
        64,
        len(payload),
        DEVICE_ID,
        int(phase * 1_000_000) & 0xFFFFFFFFFFFFFFFF,
        int(phase * 1_000_000) & 0xFFFFFFFF,
        0,
        6,
        -48,
        -92,
        0,
        sequence & 0xFFFFFFFFFFFFFFFF,
        sequence & 0xFFFFFFFF,
        2,
        2,
        1,
    ) + bytes(payload)
    prefix = PREFIX.pack(
        0x52505345,
        1,
        8,
        60,
        SESSION,
        sequence & 0xFFFFFFFFFFFFFFFF,
        len(record),
        0,
        sequence & 0xFFFFFFFFFFFFFFFF,
        0,
        0,
    )
    return prefix + record


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.server.last_origin = self.headers.get("Origin")  # type: ignore[attr-defined]
        self.server.last_connection = self.headers.get("Connection")  # type: ignore[attr-defined]
        if self.path == "/espectre/v1/capabilities":
            self._json({
                "protocol_version": "1.0",
                "resources": ["device", "wifi", "csi"],
                "features": {"csi": True},
            })
            return
        if self.path == "/espectre/v1/wifi":
            self._json({"configured": True, "connected": True, "band": "2g", "channel": 6, "rssi_dbm": -48})
            return
        if self.path != "/espectre/v1/csi":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            sequence = 0
            started = time.monotonic()
            while True:
                frame = build_frame(sequence, time.monotonic() - started)
                self.wfile.write(f"{len(frame):X}\r\n".encode("ascii"))
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
                sequence += 1
                time.sleep(self.server.interval)  # type: ignore[attr-defined]
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def log_message(self, format: str, *args) -> None:
        return


class FakeDeviceServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], interval: float) -> None:
        super().__init__(address, Handler)
        self.interval = interval
        self.last_origin: str | None = None
        self.last_connection: str | None = None


def run() -> None:
    parser = argparse.ArgumentParser(description="Synthetic ESPectre V8 CSI stream")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=62587)
    parser.add_argument("--interval", type=float, default=0.1)
    args = parser.parse_args()
    server = FakeDeviceServer((args.host, args.port), args.interval)
    print(f"Synthetic ESPectre CSI: http://{args.host}:{args.port}/espectre/v1/csi")
    print("Protocol test only; these frames are generated locally.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
