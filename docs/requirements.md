# 需求映射

> 来源：`智能照明系统方案设计报告 - 副本.docx`。本文把报告中的方案条目映射到可交付的代码/配置/文档。

| 编号 | 报告要求 | 实现位置 | 验收方式 |
|---|---|---|---|
| R1 | 根据光照和人体存在自动调光 | `firmware/components/lighting_controller/lighting_policy.cpp`；`firmware/packages/sensors.yaml` | 主机单元测试覆盖双阈值、有人/无人、延时 |
| R2 | 支持手机 APP、语音、按键控制 | ESPHome Native API + HA；`firmware/packages/actuators.yaml` 的 GPIO 按键 | HA 自动发现实体；按键事件进入 `MANUAL` |
| R3 | 采集单灯功率和用电量并生成报表 | 两路 INA226；`homeassistant/packages/espectre_plus.yaml` 的 `integration` + `utility_meter` | HA Energy Dashboard 显示日/月电量 |
| R4 | 系统框图：感知/传输/处理/执行层及信号流向 | `docs/architecture.md` 的 Mermaid 图；`hardware/wiring.md` | 文档评审 |
| R5 | 传输层 WiFi vs ZigBee 选型 | `docs/requirements.md` 第 2 节；`docs/adr/0002-wifi-over-zigbee.md` | 文档评审 |
| R6 | 2 个 A/D 环节、2 个 D/A/PWM 环节 | 照度 ADC + INA226 内部 ADC；两路 LEDC PWM；`docs/requirements.md` 第 3 节 | 配置核对 + 实测波形/读数 |
| R7 | 风险与容错 | `docs/architecture.md` 第 8 节；策略的 `SENSOR_FAULT` 降级；传感器超时失效 | 主机测试 + 断网/拔传感器演练 |
| R8 | 主灯/辅灯 24 V 直流 LED，两路独立 | `hardware/wiring.md`；`firmware/packages/actuators.yaml` | 台架通电测试 |
| R9 | 5 kHz、12 位 PWM；约 1 s 渐变 | LEDC `frequency: 5000Hz`；ESPHome 自动选择 ≥12 bit，单板启动日志显示 13 bit；`default_transition_length: 1s` | 示波器/逻辑分析仪 + 目视（波形待测） |
| R10 | 照度 0–2.5 V、12 位、20 Hz、5 次平均 | `firmware/packages/sensors.yaml` 的 ADC 配置 | 万用表/光照计标定 |
| R11 | 手动优先，直到重新选择自动 | `LightingController::set_manual_mode_()`；HA `switch` | 主机测试 + 手动操作 |
| R12 | 断网保留本地照明 | 策略在设备内运行；按键直接控制 light | 断网演练 |
| R13 | 多房间同结构扩展 | `firmware/rooms/` + `packages/`；一份 YAML 一个房间 | 复制配置检查 |
| R14 | 代码模块化、可维护、可复用 | 纯策略/适配层/配置包/HA 包分层；`docs/architecture.md` | 代码评审 + CI |
| R15 | 无隐私信息、密钥不进入版本库 | `.gitignore`；`secrets.example.yaml`；提交前仓库扫描 | 仓库扫描 |

## 1. 传输层选型

选择 **Wi-Fi**，理由：

- 现有 ESPectre 节点和 Home Assistant 已在 Wi-Fi 局域网内，不需要新增 ZigBee 协调器；
- ESP32-S3 的 Wi-Fi 4 理论速率 150 Mbit/s，照明指令和 5 s 一次的计量数据远远用不完；
- 家庭多房间覆盖可以用现有路由器/AP 扩展，成本低；
- 本方案节点固定供电，Wi-Fi 常在线不是瓶颈；如果未来做电池节点，再考虑 ZigBee。

对比表见报告表 1，代码侧对应 `docs/adr/0002-wifi-over-zigbee.md`。

## 2. 信号转换环节

| 环节 | 输入 → 输出 | 分辨率/频率 | 精度不足的影响 |
|---|---|---|---|
| 照度 A/D | 0–2.5 V → 数字照度 | 12 位；20 Hz；5 次平均 | 250/350 lx 阈值附近抖动，灯反复开关 |
| 电流 A/D | INA226 分流电阻电压 → 数字电流 | 16 位；5 Hz 读取；5 s 节流上报 | 小电流分辨不出，功率/电量偏低或偏高 |
| 主灯 PWM | 亮度指令 → 平均光输出 | ≥12 位；5 kHz；1 s 渐变 | 低亮度档位跳跃，调光不平滑 |
| 辅灯 PWM | 辅灯指令 → 平均光输出 | ≥12 位；5 kHz；1 s 渐变 | 夜间小夜灯无法细调 |

照度 ADC 的 ESPHome 配置会做 5 点滑动平均，对应报告的“连续 5 次取平均”。INA226 内部 16 位 ADC 由芯片完成；ESPHome 每 200 ms 读取（5 Hz），经 `throttle: 5s` 每 5 s 上报 HA。

## 3. 风险与容错

见 `docs/architecture.md` 第 8 节。优先级最高的三项：

1. CSI 误触发：1 s 确认 + 300 s 无人延时 + 毫米波持续存在补足（OR 融合，不是严格交叉验证）。
2. 网络/HA 中断：控制策略在设备内，按键直接驱动 light。
3. 照度自激振荡：双阈值 + 60 s 降亮延时 + 10% 步进。

## 4. 报告与实现的差异

- 报告写“另设一块 ESP32-S3 负责灯光控制”；本项目同时支持“两块板”和“一体化节点”。默认示例是一体化节点，因为新房间少一块板、少一个故障点；两块板模式在 `docs/deployment.md` 说明。
- 报告中的 24 W / 3 h = 0.072 kWh 是算例，不是实测；固件只上报功率，电量由 HA 积分。
- 报告中的阈值 250/350 lx、300 s、5 kHz 都是设计初值，现场需要按灯具和房间标定。
