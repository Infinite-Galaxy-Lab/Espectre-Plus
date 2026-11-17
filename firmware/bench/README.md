# 台架固件

这里放“只有一块 ESP32-S3、还没接全传感器”时用的验证配置。它们不是房间生产固件，也不替代整机台架和现场验收。

## 文件

| 文件 | 用途 |
|---|---|
| `common.yaml` | 板级、日志、I2C、调试公共配置 |
| `bench-smoke.yaml` | 串口日志、PSRAM、I2C 扫描、ADC GPIO1、GPIO4/5 的 5 kHz PWM 慢速扫描 |
| `bench-sim.yaml` | 模拟照度/存在/运动，复用生产 `actuators.yaml` 和 `control.yaml`，约 60 秒一轮 |
| `bench-csi.yaml` | CSI 专用：ESPectre sensing + Direct raw CSI :62587，不含照明执行器 |

## 默认接线

- USB 给 ESP32-S3 供电，串口 115200。
- GPIO4 / GPIO5：两路 PWM 输出，接逻辑电平 MOSFET 的栅极；不接灯时也可以只用万用表/示波器看引脚。
- GPIO6 / GPIO7 / GPIO15：主灯、辅灯、自动/手动按键，低电平有效，内部上拉。
- GPIO8 / GPIO9：I2C SDA/SCL，默认 100 kHz，启动时扫描地址。
- GPIO1：照度 ADC 输入，`bench-smoke` 只读电压。
- LD2410 的 UART 引脚是 GPIO17/18，但台架配置不启用雷达驱动；没接雷达也能跑。

## CSI 台架

`bench-csi.yaml` 只验证 CSI，不驱动灯。它复用 `packages/base.yaml` 的 Wi-Fi/API/OTA 和 `packages/csi.yaml` 的 ESPectre 配置，并使用本目录下被忽略的 `secrets.yaml`。首次运行先从 `rooms/secrets.example.yaml` 复制模板到 `bench/secrets.yaml`，填入可用的 **2.4 GHz** Wi-Fi；不要使用 5 GHz SSID。

```powershell
.\.venv\Scripts\esphome.exe config firmware/bench/bench-csi.yaml
.\.venv\Scripts\esphome.exe run firmware/bench/bench-csi.yaml --device COM3
```

启动后从日志或 mDNS 找到设备 IP，验证：

```text
GET http://<device-ip>:62587/espectre/v1/capabilities
GET http://<device-ip>:62587/espectre/v1/csi
```

第二条是持续二进制流，浏览器打开会一直下载；用 `simulator/csi_http.py` 或 NAS 预览页消费。CSI 采集期间设备会暂停派生运动事件，验证完关闭客户端即可恢复。没有 2.4 GHz 凭据时，可用 `simulator/fake_csi_device.py` 做协议联调，但页面必须标为模拟/联调数据。

## 运行

```powershell
# 只验证板子和 PWM 配置，不连 Wi-Fi
.\.venv\Scripts\esphome.exe run firmware/bench/bench-smoke.yaml --device COM3

# 模拟传感器 + 真实控制器 + 真实 PWM
.\.venv\Scripts\esphome.exe run firmware/bench/bench-sim.yaml --device COM3
```

`run` 会一直显示串口日志，按 `Ctrl+C` 退出。只想烧录不监视时用 `upload`。

## 预期现象

`bench-smoke` 启动后会打印：

- `PSRAM: Available: YES / Size: 8192 KB`
- `Results from bus scan: Found no devices`（当前没接 I2C 器件）
- `PWM Frequency: 5000.0 Hz`、`Bit depth: 13`
- 每 10 秒一行 `PWM sweep: main=... aux=...`

`bench-sim` 每 3 秒打印当前状态，并按脚本走完：

1. 空房间、50 lx：灯灭。
2. 有人进入、50 lx：主灯亮、辅灯亮。
3. 环境升到 300 lx：保持，不来回开关。
4. 环境升到 500 lx：延时后每 2 秒降 10%。
5. 人离开：CSI 保持结束后，按加速后的 8 秒无人延时关灯。
6. 手动按键/HA 调灯路径：进入 MANUAL；再切回 AUTO 后按当前状态恢复。

台架通过 substitutions 覆盖生产参数：无人 8 秒、CSI 保持 3 秒、高照度等待 5 秒、调光步进 2 秒；控制器逻辑与生产共用 `firmware/packages/control.yaml`。

## 安全边界

- 台架固件只输出 3.3 V 逻辑 PWM，不直接驱动 24 V 灯带。
- 接 MOSFET/灯带前，先确认驱动板支持 3.3 V 栅极、共地、栅极下拉、保险丝和续流/TVS 保护。
- 24 V 上电前按 `hardware/wiring.md` 和 `docs/testing.md` 的断电检查执行；不要用开发板 5 V/3.3 V 引脚给灯带供电。

## 已验证记录

2026-11-16，ESP32-S3 rev0.2、16 MB Flash、8 MB PSRAM、COM3：

- `bench-smoke` 启动成功，PSRAM 8192 KB，I2C 扫描无器件，ADC 初始化成功，LEDC 5 kHz / 13 bit。
- `bench-sim` 自动开灯、300 lx 保持、500 lx 延时降亮、无人关灯、手动/自动切换均通过。
- `bench-csi` 编译并烧录成功；2.4 GHz 信道 9，ESPectre 约 100 pps，Direct API 返回 64 子载波，NAS 页面连续接收。
- 联调发现并修复“自动命令被误判为手动”的适配层问题；修复后复测通过。

这些结果只证明单板、模拟输入和 PWM 配置可用，不代表 LD2410、INA226、照度、24 V 灯路或 HA 已验收。
