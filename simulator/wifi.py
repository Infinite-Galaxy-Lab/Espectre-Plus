"""WiFi CSI providers for the preview API."""

from __future__ import annotations

import math
import random
import threading
import time
from datetime import datetime

from csi_http import CsiSample, CsiStreamClient

SUB_CARRIERS = 64
CHANNEL = 6
CENTER_MHZ = 2437


def _center_mhz(channel: int) -> int:
    if channel == 14:
        return 2484
    return 2412 + (channel - 1) * 5


def _normalize(values: tuple[float, ...]) -> list[float]:
    peak = max(values, default=0.0)
    if peak <= 0:
        return [0.0 for _ in values]
    return [round(min(1.0, value / peak), 3) for value in values]


def _percent(value: float) -> int:
    # Square-root compression keeps small real CSI changes visible without claiming power units.
    return int(round(100.0 * math.sqrt(max(0.0, min(1.0, value)))))


def _shape_change(previous: list[float], current: list[float]) -> float:
    if len(previous) != len(current) or not previous:
        return 0.0
    dot = sum(a * b for a, b in zip(previous, current))
    norm_a = math.sqrt(sum(a * a for a in previous))
    norm_b = math.sqrt(sum(b * b for b in current))
    cosine = 1.0 - dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
    mean_delta = sum(abs(a - b) for a, b in zip(previous, current)) / len(current)
    return max(0.0, min(1.0, 0.6 * cosine + 0.4 * mean_delta))


class MockWifi:
    """Stable scripted CSI, used when no device URL is configured."""

    source = "mock"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rng = random.Random(20261116)
        self._phase = 0.0
        self._last = time.monotonic()
        self._burst_until = 0.0

    def burst(self, seconds: float = 2.5) -> None:
        with self._lock:
            self._burst_until = max(self._burst_until, time.monotonic() + seconds)

    def close(self) -> None:
        return

    def _advance(self) -> float:
        now = time.monotonic()
        elapsed = min(max(now - self._last, 0.0), 1.5)
        self._last = now
        self._phase = (self._phase + elapsed) % 3600.0
        return now

    def _subcarriers(self, interference: float, burst: bool) -> list[float]:
        values: list[float] = []
        source_position = 8.0 + (self._phase * 2.2) % 46.0
        for index in range(SUB_CARRIERS):
            base = 0.64
            notch_a = 0.20 * math.exp(-((index - 21) / 3.4) ** 2)
            notch_b = 0.13 * math.exp(-((index - 49) / 2.8) ** 2)
            ripple = 0.055 * math.sin(index * 0.63 + self._phase * 1.5)
            slow = 0.030 * math.sin(index * 0.19 - self._phase * 0.8)
            peak = 0.045 + interference / 100.0 * 0.34 + (0.25 if burst else 0.0)
            source = peak * math.exp(-((index - source_position) / 3.1) ** 2)
            noise = self._rng.uniform(-0.018, 0.018)
            values.append(round(max(0.06, min(1.0, base - notch_a - notch_b + ripple + slow + source + noise)), 3))
        return values

    def snapshot(self) -> dict:
        with self._lock:
            now = self._advance()
            burst = now < self._burst_until
            wave = 0.5 + 0.5 * math.sin(self._phase * 0.42)
            pulse = 8.0 * (0.5 + 0.5 * math.sin(self._phase * 1.7))
            interference = 18.0 + 11.0 * wave + pulse + (46.0 if burst else 0.0)
            interference = int(max(3.0, min(96.0, interference + self._rng.uniform(-1.5, 1.5))))
            rssi = round(-47.0 - interference * 0.06 + 1.1 * math.sin(self._phase * 0.7), 1)
            noise = round(-93.0 + interference * 0.045, 1)
            quality = int(max(28, min(99, round(100 - interference * 0.55))))
            return {
                "source": "mock",
                "source_label": "模拟 CSI",
                "simulated": True,
                "status": "streaming",
                "metric_label": "干扰强度",
                "channel": CHANNEL,
                "band": "2.4 GHz",
                "center_mhz": CENTER_MHZ,
                "rssi_dbm": rssi,
                "noise_dbm": noise,
                "interference_pct": interference,
                "fluctuation_pct": interference,
                "quality_pct": quality,
                "burst": burst,
                "subcarriers": self._subcarriers(interference, burst),
                "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
            }


class EspCsiWifi:
    """Live provider backed by ESPectre Direct HTTP raw CSI."""

    source = "espectre"

    def __init__(self, url: str | None = None, *, client: CsiStreamClient | None = None) -> None:
        self._lock = threading.RLock()
        self._latest: dict | None = None
        self._last_received = 0.0
        self._last_amplitudes: list[float] | None = None
        self._fluctuation = 0.0
        self._frames = 0
        self._client = client or CsiStreamClient(url or "")
        self._client.set_callback(self._on_sample)
        self._client.start()

    def _on_sample(self, sample: CsiSample) -> None:
        current = _normalize(sample.amplitudes)
        with self._lock:
            if self._last_amplitudes is not None:
                change = _shape_change(self._last_amplitudes, current)
                self._fluctuation = 0.72 * self._fluctuation + 0.28 * change
            self._last_amplitudes = current
            self._last_received = sample.received_at
            self._frames += 1
            fluctuation = _percent(self._fluctuation)
            rssi_quality = max(0.0, min(100.0, (sample.rssi_dbm + 95.0) / 45.0 * 100.0))
            quality = int(round(0.7 * rssi_quality + 0.3 * (100 - fluctuation)))
            self._latest = {
                "source": "espectre",
                "source_label": "ESPectre CSI",
                "simulated": False,
                "status": "streaming",
                "metric_label": "CSI 波动",
                "channel": sample.channel,
                "band": "2.4 GHz",
                "center_mhz": _center_mhz(sample.channel),
                "rssi_dbm": float(sample.rssi_dbm),
                "noise_dbm": None if sample.noise_floor_dbm is None else float(sample.noise_floor_dbm),
                "interference_pct": fluctuation,
                "fluctuation_pct": fluctuation,
                "quality_pct": quality,
                "burst": False,
                "subcarriers": current,
                "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
                "frames": self._frames,
            }

    def burst(self, seconds: float = 2.5) -> None:
        return

    def close(self) -> None:
        self._client.close()

    def snapshot(self) -> dict:
        with self._lock:
            if self._latest is None:
                status = "waiting" if self._client.connected else "offline"
                return {
                    "source": "espectre",
                    "source_label": "ESPectre CSI",
                    "simulated": False,
                    "status": status,
                    "metric_label": "CSI 波动",
                    "channel": None,
                    "band": "2.4 GHz",
                    "center_mhz": None,
                    "rssi_dbm": None,
                    "noise_dbm": None,
                    "interference_pct": None,
                    "fluctuation_pct": None,
                    "quality_pct": None,
                    "burst": False,
                    "subcarriers": [],
                    "updated": None,
                }
            snapshot = dict(self._latest)
            snapshot["subcarriers"] = list(snapshot["subcarriers"])
            if time.monotonic() - self._last_received > 5.0:
                snapshot["status"] = "stale"
            snapshot["connected"] = self._client.connected
            return snapshot
