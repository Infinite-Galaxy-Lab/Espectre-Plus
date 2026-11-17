# 代码质量与模块边界

## 分层

| 层 | 位置 | 职责 | 允许依赖 |
|---|---|---|---|
| 纯策略 | `firmware/components/lighting_controller/lighting_policy.*` | 存在、照度、手动、故障状态机 | 仅 C++ 标准库 |
| ESPHome 适配 | `firmware/components/lighting_controller/lighting_controller.*` | 读实体、驱动灯、发布状态 | ESPHome、纯策略 |
| 房间配置 | `firmware/packages/`、`firmware/rooms/` | 引脚、传感器、控制器参数 | 组件与 YAML 包 |
| 台架 | `firmware/bench/` | 单板验证、模拟输入 | 房间配置包 |
| HA 报表 | `homeassistant/` | 计量、统计、仪表板、离线提醒 | ESPHome 实体 |
| 联调模拟 | `simulator/` | mock/真实 CSI provider、HTTP 路由、前端预览 | 只依赖 HTTP 契约 |
| 上游适配 | `firmware/components/espectre_direct/` | 暴露 ESPectre Direct API | ESPectre SDK、GPL-3.0 |

## 复用规则

- 新房间复制 `firmware/rooms/example-room.yaml`，只改 substitutions；不要复制 C++ 组件。
- 公共硬件/传感器/执行器/控制配置分别在 `firmware/packages/{base,sensors,actuators,control}.yaml`。
- `control.yaml` 的阈值和时间由 substitutions 提供，生产房间和 `bench-sim` 共用同一份控制器配置。
- `firmware/bench/common.yaml` 统一板级、日志、I2C 和调试配置；台架只写差异。
- `simulator/server.py` 只管 HTTP；`mock_room.py` 和 `wifi.py` 是独立 provider。真实 CSI 的二进制解析在 `csi_http.py`，`wifi.py` 只做归一化和展示映射。
- `csi_http.py` 不依赖 Flask/前端；`fake_csi_device.py` 仅用于协议联调，不进入生产路径。
- `firmware/packages/csi.yaml` 只放 ESPectre/Direct 相关配置，生产房间和 `bench-csi` 复用。

## 代码约定

- 注释只解释“为什么”或关键边界，一行能说清就不写三行；不放装饰性 banner。
- `lighting_policy` 不得 include ESPHome 头文件；适配层不得包含具体房间/引脚常量。
- 房间入口只做 substitutions 和 package include，不堆业务逻辑。
- 新增台架或模拟器时先确认是否可复用现有 package，避免复制 YAML。
- 密钥、Wi-Fi、token、设备 MAC 不进入仓库；示例文件只保留占位值。

## 本次整理

- `bench-smoke` / `bench-sim` 的重复板级配置收拢到 `bench/common.yaml`。
- `bench-sim` 复用 `packages/actuators.yaml` 和 `packages/control.yaml`。
- `control.yaml` 的生产参数改为 substitutions，避免台架复制控制器逻辑。
- 精简 C++、固件 YAML、HA package 和 Lovelace 仪表板的长注释与装饰横幅。
