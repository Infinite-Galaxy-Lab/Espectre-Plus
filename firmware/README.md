# Firmware

ESPHome 固件，目标芯片 ESP32-S3，框架 ESP-IDF。

## 目录

```text
firmware/
├── components/lighting_controller/   # 自定义照明 C++ 组件
├── components/espectre_direct/       # 上游 Direct API 适配器（GPL-3.0）
├── packages/                         # 可复用 YAML 包
├── rooms/                            # 每个房间一份入口 YAML + secrets
├── bench/                            # 单板自检 + 模拟传感器台架
├── tests/                            # 主机侧 C++ 测试
└── README.md
```

## 依赖

- ESPHome ≥ 2026.10（内置 `espectre` 组件）
- ESPectre SDK 3.2.0（`packages/csi.yaml` 固定，构建时下载/缓存）
- ESP-IDF 5.5.x（ESPHome 自动下载）
- Python 3.12+（建议用 `.venv`）

## 构建

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
Copy-Item firmware/rooms/secrets.example.yaml firmware/rooms/secrets.yaml
.\.venv\Scripts\esphome.exe config firmware/rooms/example-room.yaml
.\.venv\Scripts\esphome.exe compile firmware/rooms/example-room.yaml
```

## 台架固件

只有一块 ESP32-S3 时，用 `bench/` 下的配置先验证板子和控制逻辑：

- `bench-smoke.yaml`：串口日志、PSRAM、I2C 扫描、ADC、两路 5 kHz PWM 扫描。
- `bench-sim.yaml`：模拟照度/存在/CSI 输入，复用生产 `actuators.yaml` 和 `control.yaml`。
- `bench-csi.yaml`：CSI 专用，ESPectre + Direct API :62587，不含照明执行器。
- `common.yaml`：板级、日志、I2C 公共配置。

```powershell
.\.venv\Scripts\esphome.exe run firmware/bench/bench-smoke.yaml --device COM3
.\.venv\Scripts\esphome.exe run firmware/bench/bench-sim.yaml --device COM3
.\.venv\Scripts\esphome.exe run firmware/bench/bench-csi.yaml --device COM3
```

台架不是生产固件；接线和安全边界见 `firmware/bench/README.md`。

## 添加房间

1. 复制 `rooms/example-room.yaml` 为 `rooms/<room>.yaml`。
2. 改 `room_name`、`node_name`、GPIO、I2C 地址、分流电阻/最大电流。
3. 在 `secrets.yaml` 里准备 Wi-Fi 和 API 加密密钥（OTA 复用 API key；所有房间共用一个文件即可）。`bench-csi` 使用 `firmware/bench/secrets.yaml`，不要提交。
4. `esphome config` 校验，再 `esphome run` 烧录。
5. HA 侧复制 package，把 `study` 替换为新前缀。

## 默认引脚

| 功能 | GPIO |
|---|---|
| 主灯 PWM | 4 |
| 辅灯 PWM | 5 |
| 主灯按键 | 6 |
| 辅灯按键 | 7 |
| 模式按键 | 15 |
| I2C SDA/SCL | 8 / 9 |
| LD2410 TX/RX | 17 / 18 |
| 照度 ADC | 1 |

详见 `hardware/wiring.md`。

## 关键设计

- `lighting_policy` 是纯 C++，不包含 ESPHome 头文件；可在 PC 上运行 `tests/test_lighting_policy.cpp`。
- `lighting_controller` 是适配层：读传感器、调用 light、发布 occupancy/status。
- 自动模式在设备内运行；HA 只做远程入口和报表。
- 两路 PWM 用 LEDC 5 kHz；ESPHome 会根据频率自动选择 ≥12 bit 分辨率，当前单板启动日志为 13 bit。
- 照度 ADC 20 Hz 采样、5 点平均，再用 `calibrate_linear` 转 lx。
- 两路 INA226 以 5 Hz 读取，节流为每 5 s 上报一次；电量在 HA 侧积分，不写设备 Flash。

## 测试

```powershell
.\tools\test-host.ps1
```

覆盖存在确认、无人延时、CSI 保持、双阈值、调光、手动优先、传感器故障。详见 `docs/testing.md`。
