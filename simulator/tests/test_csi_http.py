"""Contract tests for the ESPectre V8 CSI transport and provider."""

from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from csi_http import CsiProtocolError, CsiSample, CsiStreamClient, FrameParser, normalize_csi_url
from fake_csi_device import FakeDeviceServer, build_frame
from wifi import EspCsiWifi


class CsiParserTests(unittest.TestCase):
    def test_split_frame_preserves_sample(self) -> None:
        frame = build_frame(1, 0.3)
        parser = FrameParser()
        samples = parser.feed(frame[:37])
        samples += parser.feed(frame[37:])
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].channel, 6)
        self.assertEqual(len(samples[0].amplitudes), 64)

    def test_rejects_non_increasing_sequence(self) -> None:
        parser = FrameParser()
        parser.feed(build_frame(2, 0.0))
        with self.assertRaises(CsiProtocolError):
            parser.feed(build_frame(2, 0.1))

    def test_normalizes_url(self) -> None:
        self.assertEqual(normalize_csi_url("http://192.0.2.10"), "http://192.0.2.10:62587/espectre/v1/csi")
        self.assertEqual(normalize_csi_url("http://192.0.2.10:62587/espectre/v1"), "http://192.0.2.10:62587/espectre/v1/csi")


class CsiClientTests(unittest.TestCase):
    def test_reads_chunked_stream(self) -> None:
        server = FakeDeviceServer(("127.0.0.1", 0), 0.02)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        received = threading.Event()
        client = CsiStreamClient(f"http://127.0.0.1:{server.server_address[1]}", timeout=2)
        client.set_callback(lambda sample: received.set())
        try:
            client.start()
            self.assertTrue(received.wait(2.0))
            self.assertEqual(server.last_origin, "https://espectre.dev")
            self.assertNotEqual(server.last_connection, "close")
        finally:
            client.close()
            server.shutdown()
            server.server_close()


class StubClient:
    connected = True

    def set_callback(self, callback):
        self.callback = callback

    def start(self) -> None:
        return

    def close(self) -> None:
        return


class EspCsiWifiTests(unittest.TestCase):
    def test_live_snapshot_shape(self) -> None:
        stub = StubClient()
        wifi = EspCsiWifi(client=stub)  # type: ignore[arg-type]
        wifi._on_sample(CsiSample(6, -48, -92, (2.0, 4.0, 0.0), time.monotonic(), 1))
        data = wifi.snapshot()
        self.assertEqual(data["source"], "espectre")
        self.assertEqual(data["status"], "streaming")
        self.assertEqual(len(data["subcarriers"]), 3)
        self.assertEqual(data["subcarriers"][1], 1.0)
        self.assertEqual(data["noise_dbm"], -92.0)

    def test_waiting_snapshot_has_no_fake_values(self) -> None:
        data = EspCsiWifi(client=StubClient()).snapshot()  # type: ignore[arg-type]
        self.assertEqual(data["status"], "waiting")
        self.assertEqual(data["subcarriers"], [])
        self.assertIsNone(data["rssi_dbm"])


if __name__ == "__main__":
    unittest.main()
