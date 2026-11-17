"""HTTP integration checks for the live CSI preview provider."""

from __future__ import annotations

import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fake_csi_device import FakeDeviceServer
from mock_room import MockRoom
from server import PreviewServer
from wifi import EspCsiWifi


class LivePreviewTests(unittest.TestCase):
    def test_live_wifi_endpoint_and_static_text(self) -> None:
        fake = FakeDeviceServer(("127.0.0.1", 0), 0.02)
        threading.Thread(target=fake.serve_forever, daemon=True).start()
        wifi = EspCsiWifi(f"http://127.0.0.1:{fake.server_address[1]}")
        preview = PreviewServer(("127.0.0.1", 0), MockRoom(), wifi)
        threading.Thread(target=preview.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{preview.server_address[1]}"
        try:
            deadline = time.monotonic() + 2.0
            while wifi.snapshot()["status"] != "streaming" and time.monotonic() < deadline:
                time.sleep(0.02)
            with urllib.request.urlopen(f"{base}/api/wifi", timeout=2) as response:
                data = json.load(response)
            self.assertEqual(data["source"], "espectre")
            self.assertEqual(data["status"], "streaming")
            self.assertEqual(len(data["subcarriers"]), 64)
            with urllib.request.urlopen(f"{base}/", timeout=2) as response:
                html = response.read().decode("utf-8")
            self.assertIn('id="wifiFineprint"', html)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(urllib.request.Request(f"{base}/api/wifi/burst", method="POST"), timeout=2)
            self.assertEqual(error.exception.code, 409)
        finally:
            preview.shutdown()
            preview.server_close()
            wifi.close()
            fake.shutdown()
            fake.server_close()


if __name__ == "__main__":
    unittest.main()
