# ESPectre Plus

**基于 ESP32-S3 + ESPectre 的全屋智能照明系统。** 用 Wi-Fi CSI 和毫米波雷达判断房间是否有人，结合照度自动调光，支持本地按键、Home Assistant 手机/语音控制和双路灯具用电统计。

> 当前状态：v0.3 单板台架 + 真实 CSI 通路。ESP32-S3 已实机验证启动、PSRAM、5 kHz PWM、模拟传感器控制，并通过 ESPectre Direct API 输出真实 64 子载波 CSI；NAS 预览页已切换为真实 CSI 数据源。LD2410、INA226、照度、24 V 灯路和 HA 实体仍未接入，详见 `docs/testing.md`。

## 这个项目解决什么问题

- 人走进房间、光线不足时自动开灯；人离开后延时关灯。
- 静坐时 Wi-Fi CSI 活动变少，用 LD2410 毫米波补足“是否有人”的判断。
- 主灯、辅灯两路独立 PWM 调光，5 kHz 开关频率，至少 12 位亮度分辨率。
- 两路 INA226 采集电压、电流、功率，Home Assistant 生成日/月用电报表。
- 断网时本地仍能自动照明和按键控制；网络恢复后状态自动同步。
- 一个房间一个节点，复制 YAML 改参数即可扩展到全屋。

## 目录

| 目录 | 内容 |
|---|---|
| `firmware/` | ESPHome 固件、房间配置、自定义 `lighting_controller` 组件、主机侧测试、单板台架配置 |
| `homeassistant/` | HA package、Energy Dashboard 配置、Lovelace 仪表板 |
| `hardware/` | BOM、接线、电源与驱动注意事项 |
| `docs/` | 架构、需求映射、测试、部署、ADR、开发交接记忆 |
| `simulator/` | NAS 预览页、mock 房间数据、真实 ESPectre CSI provider 和协议测试 |
| `tools/` | 配置检查、主机测试、构建脚本 |

## 快速开始

### 1. 准备环境

- Python 3.12+，推荐用 `uv` 管理虚拟环境；
- ESPHome 2026.10.2（`requirements.txt` 已固定；内置 `espectre` 组件要求 ESPHome ≥2026.10）；
- Git；
- 一块 ESP32-S3 开发板（8 MB PSRAM 推荐），以及报告中的传感器/驱动板。

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

### 2. 配置秘密

```powershell
Copy-Item firmware/rooms/secrets.example.yaml firmware/rooms/secrets.yaml
# 编辑 firmware/rooms/secrets.yaml，填入 Wi-Fi 和 API 加密 key（OTA 复用该 key）
```

`firmware/rooms/secrets.yaml` 已被 `.gitignore` 排除，**不要提交**。仓库里只保留 `firmware/rooms/secrets.example.yaml`。

### 3. 检查配置

```powershell
.\tools\validate.ps1
```

### 4. 编译/烧录

```powershell
.\.venv\Scripts\esphome.exe config firmware/rooms/example-room.yaml
.\.venv\Scripts\esphome.exe compile firmware/rooms/example-room.yaml
.\.venv\Scripts\esphome.exe run firmware/rooms/example-room.yaml
```

> 没有完整传感器时可以先做 `config`、主机侧单元测试和 `firmware/bench/` 的单板台架；`compile` 会下载 ESP-IDF 工具链，首次较慢。

### 5. 单板台架与模拟演示

只有一块 ESP32-S3、还没接传感器时，可以先用台架配置验证板子和控制逻辑：

```powershell
# 板级自检：串口、PSRAM、I2C 扫描、ADC、两路 5 kHz PWM
.\.venv\Scripts\esphome.exe run firmware/bench/bench-smoke.yaml --device COM3

# 模拟照度/存在/运动，真实运行照明控制器和 PWM
.\.venv\Scripts\esphome.exe run firmware/bench/bench-sim.yaml --device COM3

# 真实 CSI：ESPectre sensing + Direct API :62587
.\.venv\Scripts\esphome.exe run firmware/bench/bench-csi.yaml --device COM3
```

台架说明见 `firmware/bench/README.md`。台架输入是脚本模拟的，不能替代 LD2410/INA226/照度/24 V 灯路的实测。

### 6. NAS / HA 联调预览

没有 NAS 时，可以先看本地页面；默认 mock，设置 `ESPECTRE_CSI_URL` 后接真实设备：

```powershell
.\.venv\Scripts\python.exe simulator\server.py --port 8080
# 或者：$env:ESPECTRE_CSI_URL='http://<device-ip>:62587'
```

打开 <http://127.0.0.1:8080>。房间数据仍由 mock provider 提供；WiFi 可在 mock 与 ESPectre CSI 间切换，页面会标注来源。NAS 部署和 `/api/wifi` 说明见 `simulator/README.md`。

### 7. Home Assistant

把 `homeassistant/packages/espectre_plus.yaml` 放到 HA 的 `config/packages/`，重启后在 Energy Dashboard 添加两路电能传感器。详见 `homeassistant/README.md`。

## 硬件拓扑（报告基线）

```text
ESP32-S3 #1（现有）: ESPectre Wi-Fi CSI 活动检测 ──Wi-Fi──┐
                                                          ├── Home Assistant（NAS）
ESP32-S3 #2（本项目）: LD2410 + 照度 + 2x INA226 + 2x PWM ─┘
```

也支持**一体化节点**：把 ESPectre 和照明控制跑在同一块 ESP32-S3 上（推荐新房间），YAML 里保留 `espectre:` 即可；如果继续用报告里的两块板，照明节点只依赖 LD2410 做本地存在判断，ESPectre 的运动信号可由 HA 自动化叠加。

## 开源与许可

本项目是 [ESPectre](https://github.com/francescopace/espectre) 的衍生应用，遵循 **GPL-3.0**。上游版权与第三方声明见 `NOTICE` 和 `THIRD_PARTY_NOTICES.md`。仓库不包含任何密钥、API token、个人地址或家庭网络信息。

## 文档索引

- [架构设计](docs/architecture.md)
- [需求映射](docs/requirements.md)
- [硬件与接线](hardware/wiring.md)
- [固件说明](firmware/README.md)
- [Home Assistant 接入](homeassistant/README.md)
- [本地 HA 容器（开发）](homeassistant/local-ha.md)
- [测试计划](docs/testing.md)
- [代码质量与模块边界](docs/code-quality.md)
- [NAS/HA 联调模拟器](simulator/README.md)
- [部署说明](docs/deployment.md)
- [答辩材料（项目说明 / 40 组问答 / 讲述提纲）](docs/defense/README.md)
- [上游集成调研](docs/upstream-integration.md)
- [TODO / 路线图](TODO.md)
