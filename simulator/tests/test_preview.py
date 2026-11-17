"""Contract tests for the preview providers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mock_room import MockRoom
from wifi import MockWifi


class MockWifiTests(unittest.TestCase):
    def test_snapshot_shape(self) -> None:
        wifi = MockWifi()
        data = wifi.snapshot()
        self.assertEqual(data["source"], "mock")
        self.assertEqual(data["channel"], 6)
        self.assertEqual(len(data["subcarriers"]), 64)
        self.assertTrue(all(0.0 <= value <= 1.0 for value in data["subcarriers"]))
        self.assertGreaterEqual(data["interference_pct"], 0)
        self.assertLessEqual(data["interference_pct"], 100)

    def test_burst_raises_interference(self) -> None:
        wifi = MockWifi()
        before = wifi.snapshot()["interference_pct"]
        wifi.burst()
        after = wifi.snapshot()["interference_pct"]
        self.assertGreater(after, before)


class MockRoomTests(unittest.TestCase):
    def test_manual_light_switches_mode(self) -> None:
        room = MockRoom()
        room.control("toggle_main")
        self.assertEqual(room.mode, "manual")
        self.assertTrue(room.main_on)

    def test_reset_returns_to_auto(self) -> None:
        room = MockRoom()
        room.control("toggle_main")
        room.control("reset")
        self.assertEqual(room.mode, "auto")
        self.assertFalse(room.main_on)


if __name__ == "__main__":
    unittest.main()
