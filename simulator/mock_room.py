"""In-memory room scenario for the NAS preview."""

from __future__ import annotations

import threading
import time
from datetime import datetime

STAGES = [
    {"seconds": 8, "event": "空房间，灯灭", "occupied": False, "lux": 50,
     "main": (False, 0), "aux": (False, 0)},
    {"seconds": 8, "event": "有人进入：主灯 84%，辅灯 40%", "occupied": True, "lux": 50,
     "main": (True, 84), "aux": (True, 40)},
    {"seconds": 8, "event": "环境 300 lx：保持灯光", "occupied": True, "lux": 300,
     "main": (True, 84), "aux": (True, 40)},
    {"seconds": 4, "event": "环境 500 lx：开始延时降亮", "occupied": True, "lux": 500,
     "main": (True, 84), "aux": (True, 40)},
    {"seconds": 4, "event": "降亮到 64%", "occupied": True, "lux": 500,
     "main": (True, 64), "aux": (False, 0)},
    {"seconds": 4, "event": "降亮到 44%", "occupied": True, "lux": 500,
     "main": (True, 44), "aux": (False, 0)},
    {"seconds": 8, "event": "无人延时结束：关灯", "occupied": False, "lux": 500,
     "main": (False, 0), "aux": (False, 0)},
]


class MockRoom:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.mode = "auto"
            self.occupied = False
            self.lux = 50
            self.main_on = False
            self.main_brightness = 0
            self.aux_on = False
            self.aux_brightness = 0
            self.main_power = 0.0
            self.aux_power = 0.0
            self.energy_today = 0.142
            self.energy_month = 2.350
            self.price = 0.60
            self.demo = True
            self.stage = 0
            self.stage_started = time.monotonic()
            self.last_tick = self.stage_started
            self.events: list[dict[str, str]] = []
            self._log("模拟台架启动")
            self._apply_stage()

    def _log(self, text: str) -> None:
        self.events.append({"time": datetime.now().strftime("%H:%M:%S"), "text": text})
        self.events = self.events[-10:]

    def _apply_stage(self) -> None:
        stage = STAGES[self.stage]
        self.occupied = bool(stage["occupied"])
        self.lux = int(stage["lux"])
        self._set_light("main", *stage["main"])
        self._set_light("aux", *stage["aux"])
        self._log(str(stage["event"]))

    def _set_light(self, channel: str, on: bool, brightness: int) -> None:
        if channel == "main":
            self.main_on = on
            self.main_brightness = brightness if on else 0
        else:
            self.aux_on = on
            self.aux_brightness = brightness if on else 0
        self._recalc_power()

    def _recalc_power(self) -> None:
        self.main_power = round(24.0 * self.main_brightness / 100.0, 1) if self.main_on else 0.0
        self.aux_power = round(12.0 * self.aux_brightness / 100.0, 1) if self.aux_on else 0.0

    def tick(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_tick
            self.last_tick = now
            if elapsed > 5:
                elapsed = 1.0
            if self.demo and now - self.stage_started >= STAGES[self.stage]["seconds"]:
                self.stage = (self.stage + 1) % len(STAGES)
                self.stage_started = now
                self._apply_stage()
            total_w = self.main_power + self.aux_power
            self.energy_today += total_w * elapsed / 3_600_000.0
            self.energy_month += total_w * elapsed / 3_600_000.0

    def snapshot(self) -> dict:
        with self._lock:
            self.tick()
            total = round(self.main_power + self.aux_power, 1)
            return {
                "room": "Study",
                "demo": self.demo,
                "mode": self.mode,
                "occupancy": self.occupied,
                "lux": self.lux,
                "status": "auto" if self.mode == "auto" else "manual",
                "lights": {
                    "main": {"on": self.main_on, "brightness": self.main_brightness},
                    "aux": {"on": self.aux_on, "brightness": self.aux_brightness},
                },
                "power": {
                    "main": self.main_power,
                    "aux": self.aux_power,
                    "total": total,
                },
                "energy": {
                    "today_kwh": round(self.energy_today, 3),
                    "month_kwh": round(self.energy_month, 3),
                    "today_cost": round(self.energy_today * self.price, 2),
                    "month_cost": round(self.energy_month * self.price, 2),
                    "price": self.price,
                },
                "events": list(self.events),
                "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
            }

    def control(self, action: str, value=None) -> None:
        with self._lock:
            self.demo = False
            if action == "toggle_auto":
                self.mode = "manual" if self.mode == "auto" else "auto"
                self._log("自动模式切换为 " + self.mode)
            elif action == "toggle_main":
                self.mode = "manual"
                self._set_light("main", not self.main_on, 80 if not self.main_on else 0)
                self._log("主灯手动切换")
            elif action == "toggle_aux":
                self.mode = "manual"
                self._set_light("aux", not self.aux_on, 40 if not self.aux_on else 0)
                self._log("辅灯手动切换")
            elif action == "set_brightness" and isinstance(value, dict):
                channel = str(value.get("channel", ""))
                if channel not in ("main", "aux"):
                    raise ValueError("channel must be main or aux")
                brightness = max(0, min(100, int(value.get("brightness", 0))))
                self.mode = "manual"
                self._set_light(channel, brightness > 0, brightness)
                self._log(f"{'主灯' if channel == 'main' else '辅灯'}亮度 {brightness}%")
            elif action == "set_presence":
                self.occupied = bool(value)
                self._log("模拟占用：" + ("有人" if self.occupied else "无人"))
            elif action == "set_lux":
                self.lux = max(0, min(2000, int(value)))
                self._log(f"模拟照度：{self.lux} lx")
            elif action == "set_price":
                self.price = max(0.0, float(value))
                self._log(f"电价改为 {self.price:.2f} 元/kWh")
            elif action == "set_demo":
                self.demo = bool(value)
                if self.demo:
                    self.stage = 0
                    self.stage_started = time.monotonic()
                    self._apply_stage()
                self._log("演示模式：" + ("开启" if self.demo else "暂停"))
            elif action == "reset":
                self.reset()
                return
            else:
                raise ValueError(f"unknown action: {action}")
