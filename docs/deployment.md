# 部署说明

## 1. 两种拓扑

### 1.1 一体化节点（推荐新房间）

一块 ESP32-S3 同时运行 ESPectre CSI、LD2410、照度、两路 INA226 和两路 PWM。优点是本地联动不依赖 Wi-Fi 的另一块板，少一个故障点。`firmware/rooms/example-room.yaml` 就是这种布局。

### 1.2 两块板（报告基线）

如果保留现有 ESPectre 节点，只新增一块照明节点：

- 照明节点保留 `firmware/packages/sensors.yaml` 中的 LD2410、照度、INA226，删除 `espectre:` 和 `binary_sensor/sensor` 里 `platform: espectre` 的条目；
- 本地自动逻辑只依赖 LD2410（`presence` 输入），`motion` 输入可以留空；
- ESPectre 的运动信号由 HA 自动化叠加（例如把 CSI motion 作为额外条件），但断网时这部分增强不可用；
- 如果希望断网时也保留 CSI，建议直接用一体化节点，把现有 S3 刷成本项目固件。

## 2. 首次烧录

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
Copy-Item firmware/rooms/secrets.example.yaml firmware/rooms/secrets.yaml
# 编辑 secrets.yaml：Wi-Fi、fallback AP 密码、API 加密 key（OTA 复用该 key）
.\.venv\Scripts\esphome.exe run firmware/rooms/example-room.yaml
```

首次用 USB 连接；ESPHome 会编译并询问串口。后续 OTA 使用同一 YAML。

## 3. 密钥与隐私

- `firmware/rooms/secrets.yaml` 不提交，`.gitignore` 和 `firmware/rooms/.gitignore` 都排除它。
- API encryption key 用 `openssl rand -base64 32` 生成；每个房间最好用不同 key。
- OTA 复用 API 加密 key，不再单独设置 OTA 密码；API key 不要复用路由器密码。
- 不要在 YAML 里写固定公网 IP、DDNS、家庭地址、手机号。
- 仓库扫描：`git grep -n -i -E 'password|token|api_key|secret'` 只应看到占位符和文档示例。

## 4. Home Assistant

1. 把 `homeassistant/packages/espectre_plus.yaml` 放到 HA 的 `config/packages/`。
2. 在 `configuration.yaml` 里启用 `homeassistant: packages: !include_dir_named packages`。
3. 重启 HA，确认 ESPHome 发现节点。
4. 在 Energy Dashboard 添加 `sensor.study_total_energy`（或分路电能）。
5. 导入 `homeassistant/dashboards/lighting.yaml` 作为 Lovelace 原始配置。

多房间：复制 package，把 `study` 全替换成新前缀；复制 `firmware/rooms/example-room.yaml`，改 `room_name`、`node_name`、GPIO、INA226 地址。建议每房间用不同 I2C 地址组合，避免总线冲突（同一总线只有两个 INA226 时通常 0x40/0x41）。

## 5. OTA 与回滚

- OTA 前确认设备在线、Wi-Fi RSSI 稳定、电源不会断。
- 保留上一版 `firmware.factory.bin` 和 YAML；OTA 失败时用 USB 重新烧录。
- 大批量升级建议一次一个房间，观察 10 分钟后再下一个。
- 设备刷入本项目的固件后，不要与 ESPectre 官方签名镜像混用 OTA。

## 6. 故障排查

| 现象 | 先查 |
|---|---|
| 配置校验失败 | `secrets.yaml` 位置（`firmware/rooms/`）、I2C 地址、YAML 缩进 |
| 编译失败 | ESPHome 版本 ≥2026.10、ESP-IDF 5.5.x、网络能下载工具链 |
| I2C 扫不到设备 | 供电、SDA/SCL 上拉、地址跳线、共地 |
| 照度一直是 0/满量程 | ADC 引脚、分压、`calibrate_linear`、attenuation |
| 灯不亮 | MOSFET 栅极、共地、灯带极性、PWM 频率 |
| 灯闪 | 电源功率不足、PWM 频率/滤波、Wi-Fi 干扰、接地 |
| 自动逻辑不动作 | `switch.*_auto_mode` 是否 ON、occupancy 状态、日志级别调到 DEBUG |
| 功率读数不对 | 分流电阻值、`max_current`、INA226 地址、校准 |
| HA 实体 unavailable | 节点在线状态、API key、Wi-Fi、HA 日志 |
