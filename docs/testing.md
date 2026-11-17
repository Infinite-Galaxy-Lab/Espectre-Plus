# 测试计划与记录

## 1. 当前已验证

日期：2026-11-16；环境：Windows 11，Python 3.12.11，ESPHome 2026.10.2，ESP-IDF 5.5.6。

### 1.1 无硬件基线

| 检查 | 命令 | 结果 |
|---|---|---|
| 纯策略单元测试 | `.\tools\test-host.ps1` | 通过（9 组测试） |
| ESPHome 配置校验 | `.\.venv\Scripts\esphome.exe config firmware/rooms/example-room.yaml` | `Configuration is valid!` |
| 固件编译 | `.\.venv\Scripts\esphome.exe compile firmware/rooms/example-room.yaml` | 成功；Flash 14.2%（1,154,663 / 8,126,464 bytes），RAM 34.6%（118,091 / 341,760 bytes） |

编译产物：`firmware/rooms/.esphome/build/espectre-plus-study/build/firmware.factory.bin`（本地生成，不提交）。

### 1.2 单板实物台架

板卡：ESP32-S3 rev0.2，16 MB Flash、8 MB PSRAM；USB-UART 为 CH343（当前 `COM3`）。这一节只代表单板，不等于整机验收。

| 检查 | 命令 | 结果 |
|---|---|---|
| 芯片/存储识别 | `.\.venv\Scripts\esptool.exe --port COM3 chip-id`、`flash-id` | ESP32-S3 rev0.2；16 MB Flash；8 MB PSRAM |
| 板级自检 | `.\.venv\Scripts\esphome.exe run firmware/bench/bench-smoke.yaml --device COM3` | 启动成功；PSRAM 8192 KB；I2C 扫描 0 个器件；ADC 初始化 OK；LEDC 5 kHz / 13 bit |
| 模拟传感器联调 | `.\.venv\Scripts\esphome.exe run firmware/bench/bench-sim.yaml --device COM3` | 自动开灯、300 lx 保持、500 lx 延时降亮、无人 8 s 关灯、手动/自动切换均通过 |
| 适配层回归 | 同上 | 发现“自动命令被误判为手动”；加命令下发保护后复测通过 |

注意：以上只用 USB 供电和模拟输入，未接 LD2410、INA226、照度分压、MOSFET、24 V 灯带或 HA；PWM 只确认了 LEDC 配置和 GPIO 输出，没有示波器波形/占空比数据。

### 1.3 NAS 模拟联调（2026-11-16）

- NAS 上部署 `espectre-plus-sim.service`，监听 `8100`，`enable` + `active`；项目目录在 NAS 数据盘。
- 从本机验证页面 HTTP 200、`/api/health`、`/api/state`、`/api/wifi` 均正常；局域网访问通过。
- 房间控制 `toggle_main`、`set_brightness`、`set_price`、`set_lux` 可用；WiFi 脉冲接口可把模拟干扰从约 30% 抬到 70%+。
- 前端页面用 Edge headless 桌面 1280 px 和手机 390 px 宽度渲染检查；状态、灯光、功率、电量、事件流和 WiFi 频谱/趋势图正常。
- `simulator/tests/test_preview.py` 4 项 provider 契约测试通过。
- 本机 Docker Desktop 另有本地 HA 容器 `espectre-plus-ha`（2026.3.0，8123，onboarding 完成，API 正常）；它还没有 ESPHome/ESPectre 实体，不能替代设备联调。
- NAS 没有 Home Assistant；这是 NAS 上的 mock 服务联调，不是 HA 整机、真实 ESPectre CSI 或设备联调。

### 1.4 真实 CSI 通路（2026-11-16）

- `firmware/packages/csi.yaml` 已接入本地 vendored `espectre_direct`，`esphome config` 对 `bench-csi.yaml` 和 `example-room.yaml` 均通过；Direct API 端口为 62587，raw CSI 默认开启。
- `simulator/csi_http.py` 已按 ESPectre V8 协议解析 HTTP 前缀和 CSI 记录，校验 magic、版本、记录长度、session 和 stream sequence；`sqrt(I² + Q²)` 生成幅值。
- `simulator/wifi.py` 的 `EspCsiWifi` 已完成真实 provider、64 子载波归一化、相邻帧 CSI 形状变化和断线重连；无数据时返回 `null`/`[]`，不填假值。
- `simulator/fake_csi_device.py` 能生成本地 V8 chunked 流；`simulator/tests/` 的解析器、chunk 分片、序号校验、HTTP client 和 `/api/wifi` 集成测试均通过。
- `simulator/server.py --csi-url ...` 已验证 `/api/wifi` 返回 `source=espectre`、`status=streaming`、64 个子载波；真实模式 `POST /api/wifi/burst` 返回 409，页面隐藏模拟按钮。
- 2026-11-16 真机验证：`bench-csi` 编译成功（Flash 13.6%，RAM 32.8%），烧录后连接 2.4 GHz 信道 9，ESPectre 约 100 pps，`capabilities.features.csi=true`；解析器取得 64 子载波、RSSI 约 -28 dBm、底噪约 -94 dBm。
- NAS 服务从 `EnvironmentFile` 读取设备地址后，`/api/health` 返回 `mode=espectre`、`wifi_status=streaming`，页面来源显示 `ESPectre CSI`；已用 headless Chromium 检查桌面布局。
- Direct HTTP 必须带 `Origin: https://espectre.dev`，且 raw `/csi` 不能发 `Connection: close`。修正后本地连续 20 s 收到约 1885 个样本（约 100 pps），状态保持 `streaming`。
- 以上证明真实 CSI 数据链路可用，但还没有做人员走动、干扰源、距离/穿墙和长时间稳定性验收，不能写成现场感知效果验收。

## 2. 主机侧单元测试

`firmware/tests/test_lighting_policy.cpp` 覆盖：

1. 人体存在 1 s 连续确认；中途短时丢失会重新计时。
2. 无人 300 s 延时关灯。
3. CSI 60 s 保持，保持结束后再计无人延时。
4. 250/350 lx 双阈值滞回；中间区间保持；高照度延时后逐步降亮。
5. 照度—亮度映射：越暗越亮，接近 250 lx 时降到最低亮度。
6. 辅灯在 80 lx 以下开启，以上关闭。
7. 手动模式不覆盖用户操作。
8. 两路存在传感器都失效时进入 `SENSOR_FAULT` 并保持输出；没有 CSI 的两块板模式不会误报降级。
9. 照度传感器失效或读到 NaN 时回退到 60% 亮度并标记降级。

命令：

```powershell
.\tools\test-host.ps1
```

## 3. 配置与编译检查

```powershell
Copy-Item firmware/rooms/secrets.example.yaml firmware/rooms/secrets.yaml
.\.venv\Scripts\esphome.exe config firmware/rooms/example-room.yaml
.\.venv\Scripts\esphome.exe compile firmware/rooms/example-room.yaml
```

`config` 不需要硬件；`compile` 首次会下载 ESP-IDF 工具链，之后增量编译较快。

YAML 还配置了失效检测：照度 1 s、毫米波 5 s、INA226 10 s 无更新后标记为不可用。控制器会把非有限照度值当作无效，避免 NaN 被误判为 0 lx。

## 4. 硬件台架测试（进行中）

### 4.0 单板已完成（2026-11-16）

- [x] 确认板型、Flash/PSRAM 和串口。
- [x] 烧录 `bench-smoke`，确认启动、PSRAM、I2C 扫描、ADC 和 PWM 配置。
- [x] 烧录 `bench-sim`，用模拟输入验证控制器与两路 PWM。
- [x] 修复自动命令误判手动的问题并复测。

### 4.1 上电前

- [ ] 万用表确认 24 V 电源极性、保险丝、共地。
- [ ] 检查 MOSFET 栅极下拉、栅极电阻、灯带极性。
- [ ] 检查 INA226 分流电阻值（0.01 Ω）和 I2C 地址（0x40/0x41）。
- [ ] 检查 LD2410 TX/RX 交叉、5 V 供电、逻辑电平。
- [ ] 检查照度分压节点不超过 2.5 V。

### 4.2 上电顺序

1. 只接 ESP32 + USB，确认串口日志；配好 `secrets.yaml` 后再确认 Wi-Fi 和 HA 发现。
2. 接 I2C，扫描到 0x40/0x41；读电压、电流、功率。
3. 接 LD2410，确认 `has_target` 随人员移动变化。
4. 接照度电路，用照度计记录至少 4 个点，更新 `calibrate_linear`。
5. 接一路 LED + MOSFET，示波器/逻辑分析仪测 GPIO4：5 kHz，占空比随亮度变化。
6. 接第二路，重复。
7. 两路同时满载 30 分钟，检查 MOSFET/线缆/电源温升。

### 4.3 功能验收

| 编号 | 场景 | 预期 |
|---|---|---|
| T1 | 人进入，照度 <250 lx | 连续 1 s 确认后主灯亮；<80 lx 时辅灯亮 |
| T2 | 人静坐 5 分钟 | 灯保持，不因 CSI 活动减少而误关 |
| T3 | 人离开 5 分钟 | 300 s 后两路渐灭 |
| T4 | 照度从 240 升到 300 lx | 灯保持，不反复开关 |
| T5 | 照度 >350 lx 持续 60 s | 逐步降亮，不立即关灯 |
| T6 | 按主灯键 | 进入 MANUAL，主灯切换，自动逻辑不再抢灯 |
| T7 | HA 调主灯亮度 | 进入 MANUAL，HA 状态与设备一致 |
| T8 | 按模式键/HA 开关回 AUTO | 按当前 occupancy/lux 重新决策 |
| T9 | 拔掉 LD2410 | 降级为 CSI-only，状态显示 `auto_degraded` |
| T10 | 拔掉两路存在传感器 | `sensor_fault`，保持当前灯光，HA 告警 |
| T11 | 断网/HA 停机 | 本地自动和按键继续工作；恢复后状态同步 |
| T12 | INA226 掉线 | 照明不受影响；功率实体 unavailable |
| T13 | 两路满载 | 功率读数与万用表偏差在可接受范围；电量报表累计 |
| T14 | 自动开灯/调光 | 控制器不得把自己的命令误判为手动；`bench-sim` 已验证，整机复测待做 |

## 5. 现场标定

- 照度：至少 0、250、500、1000 lx 四点；记录 ADC 电压，更新 `calibrate_linear`。
- 存在：LD2410 灵敏度和无人延时；内置 `espectre` 的 `motion_on_hits`/`motion_off_hits` 可在 YAML 中改，但要重新编译，不是运行时实体。
- 调光：记录 10%、30%、50%、100% 亮度下的照度和功率，确认低亮度不闪烁。
- 计量：用万用表/功率计对比 0.2 A、0.5 A、1 A、1.5 A 四点；必要时修正分流电阻值。

## 6. 尚未验证

- LD2410、INA226、照度分压、MOSFET 和 24 V 灯路的整机接线与读数。
- 实际 Wi-Fi CSI 检测距离、穿墙、误报率、不同干扰源的相关性和长时间稳定性。
- LD2410 与 CSI 的融合效果。
- 照度传感器的实际线性度和现场标定。
- INA226 与万用表/功率计的计量偏差。
- 5 kHz PWM 的实际波形、占空比和低亮度闪烁。
- 24 V 灯路满载温升和 EMI。
- HA 仪表板、Energy Dashboard 和离线通知的实际效果（未接 HA 实例）。
- NAS 的 WiFi provider 已接真实 ESPectre 流；房间状态、功率和电量仍是 mock。
