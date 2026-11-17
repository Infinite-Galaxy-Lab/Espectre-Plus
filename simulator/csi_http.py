"""ESPectre Direct HTTP raw CSI transport and V8 frame parser."""

from __future__ import annotations

import http.client
import math
import struct
import threading
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

CSI_PREFIX = struct.Struct("<IBBH16sQHHQQQ")
CSI_RECORD = struct.Struct("<HBBBBIHHQQIQBbbQIIBBB")
PREFIX_MAGIC = 0x52505345
RECORD_MAGIC = 0x4353
RECORD_VERSION = 8
PREFIX_VERSION = 1
PREFIX_LEN = 60
DEFAULT_PORT = 62587
ALLOWED_ORIGIN = "https://espectre.dev"
RAW_CSI_PATH = "/espectre/v1/csi"
MAX_RECORD_BYTES = 576


class CsiProtocolError(ValueError):
    """Raised when the device stream does not match the V8 CSI contract."""


@dataclass(frozen=True)
class CsiSample:
    channel: int
    rssi_dbm: int
    noise_floor_dbm: int | None
    amplitudes: tuple[float, ...]
    received_at: float
    seq_num: int


def normalize_csi_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("CSI URL must be an http(s) URL")
    path = parsed.path.rstrip("/")
    if not path:
        path = RAW_CSI_PATH
    elif path.endswith("/espectre/v1"):
        path += "/csi"
    port = parsed.port or DEFAULT_PORT
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"{parsed.scheme}://{host}:{port}{path}"


def _int8(value: int) -> int:
    return value - 256 if value >= 128 else value


def _parse_record(record: bytes) -> CsiSample:
    if len(record) < CSI_RECORD.size:
        raise CsiProtocolError("CSI record header is truncated")
    fields = CSI_RECORD.unpack_from(record)
    (
        magic,
        version,
        header_len,
        _chip,
        _flags,
        seq_num,
        num_sc,
        csi_len,
        _device_id,
        _device_ticks,
        _rx_ts,
        _rx_start_ts,
        channel,
        rssi,
        noise,
        _transport_total,
        _fresh_total,
        _request_total,
        _phy,
        _ltf,
        _width,
    ) = fields
    if magic != RECORD_MAGIC or version != RECORD_VERSION:
        raise CsiProtocolError("unexpected CSI record magic or version")
    if header_len < CSI_RECORD.size:
        raise CsiProtocolError("CSI record header length is invalid")
    if num_sc == 0 or csi_len != num_sc * 2 or header_len + csi_len != len(record):
        raise CsiProtocolError("CSI record length does not match its payload")
    payload = record[header_len:]
    amplitudes = tuple(
        math.hypot(_int8(payload[index + 1]), _int8(payload[index]))
        for index in range(0, len(payload), 2)
    )
    return CsiSample(
        channel=int(channel),
        rssi_dbm=int(rssi),
        noise_floor_dbm=None if int(noise) == -128 else int(noise),
        amplitudes=amplitudes,
        received_at=time.monotonic(),
        seq_num=int(seq_num),
    )


class FrameParser:
    """Incrementally split an HTTP byte stream into validated CSI samples."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._session: bytes | None = None
        self._sequence: int | None = None

    def feed(self, chunk: bytes) -> list[CsiSample]:
        self._buffer.extend(chunk)
        samples: list[CsiSample] = []
        while len(self._buffer) >= PREFIX_LEN:
            (
                magic,
                version,
                record_version,
                header_len,
                session,
                sequence,
                record_len,
                _flags,
                _fresh_total,
                _drop_total,
                _backpressure_total,
            ) = CSI_PREFIX.unpack_from(self._buffer)
            if magic != PREFIX_MAGIC or version != PREFIX_VERSION:
                raise CsiProtocolError("unexpected CSI HTTP frame header")
            if record_version != RECORD_VERSION or header_len != PREFIX_LEN:
                raise CsiProtocolError("unsupported CSI stream version")
            if record_len < CSI_RECORD.size or record_len > MAX_RECORD_BYTES:
                raise CsiProtocolError("invalid CSI record length")
            if len(self._buffer) < PREFIX_LEN + record_len:
                break
            if self._session is None:
                self._session = bytes(session)
            elif bytes(session) != self._session:
                raise CsiProtocolError("CSI session changed without a reconnect")
            if self._sequence is not None and sequence <= self._sequence:
                raise CsiProtocolError("CSI stream sequence is not increasing")
            frame = bytes(self._buffer[: PREFIX_LEN + record_len])
            del self._buffer[: PREFIX_LEN + record_len]
            self._sequence = int(sequence)
            samples.append(_parse_record(frame[PREFIX_LEN:]))
        return samples


class CsiStreamClient:
    """Read the ESPectre Direct raw CSI endpoint and reconnect on failure."""

    def __init__(self, url: str, *, timeout: float = 5.0, reconnect_delay: float = 3.0) -> None:
        self.url = normalize_csi_url(url)
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.connected = False
        self.last_error: str | None = None
        self._callback: Callable[[CsiSample], None] | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def set_callback(self, callback: Callable[[CsiSample], None]) -> None:
        self._callback = callback

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="espectre-csi", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._stream_once()
            except Exception as exc:  # Keep the preview usable while the device reconnects.
                self.last_error = f"{type(exc).__name__}: {exc}"
                self.connected = False
                self._stop.wait(self.reconnect_delay)

    def _stream_once(self) -> None:
        parsed = urlparse(self.url)
        connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        connection = connection_type(parsed.hostname, parsed.port, timeout=self.timeout)
        try:
            connection.request(
                "GET",
                parsed.path or RAW_CSI_PATH,
                headers={
                    "Accept": "application/octet-stream",
                    "Origin": ALLOWED_ORIGIN,
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise CsiProtocolError(f"CSI endpoint returned HTTP {response.status}")
            self.connected = True
            self.last_error = None
            parser = FrameParser()
            while not self._stop.is_set():
                read = getattr(response, "read1", response.read)
                chunk = read(4096)
                if not chunk:
                    raise ConnectionError("CSI stream ended")
                for sample in parser.feed(chunk):
                    if self._callback is not None:
                        self._callback(sample)
        finally:
            self.connected = False
            connection.close()
