# TODO / 路线图

> 更新规则：完成一项勾选一项；新增工作写清验收标准。

## P0 项目基线（本次）

- [x] 读取报告，提炼功能/指标/风险
- [x] 建立目录结构与技术选型（ESPHome + C++ 纯策略）
- [x] 初始化项目文档、GPL-3.0 许可、NOTICE、隐私文件规则
- [x] 架构文档、需求映射、硬件接线、部署/测试文档
- [x] `lighting_controller` 纯策略 + ESPHome 适配层
- [x] 主机侧单元测试（存在确认/无人延时/双阈值/手动优先/传感器故障）
- [x] ESPHome YAML 配置包与示例房间
- [x] Home Assistant package + 仪表板
- [x] `esphome config` 校验通过
- [x] 首次 `esphome compile`（ESPHome 2026.10.2 + ESP-IDF 5.5.6）
- [x] 开发交接记忆更新
- [x] 答辩项目说明、40 组问答、5 分钟讲述提纲
- [x] 代码复用/注释/模块边界整理（`docs/code-quality.md`）

## P1 硬件台架（进行中）

### 2026-11-16 单板已完成

- [x] 识别板型：ESP32-S3 rev0.2，16 MB Flash，8 MB PSRAM；USB-UART `COM3`
- [x] 烧录 `bench-smoke`：启动、PSRAM、I2C 扫描、ADC、5 kHz PWM 配置通过
- [x] 烧录 `bench-sim`：模拟照度/存在/运动，真实控制器与两路 PWM 联调通过
- [x] 修复“自动命令被误判为手动”的适配层问题并复测
- [x] 更新台架说明、测试记录和开发交接文档

### 待接传感器与整机台架

- [x] `bench-csi`：ESP32-S3 + 2.4 GHz Wi-Fi + ESPectre Direct API 实机联通（64 子载波、约 100 pps）

- [ ] ESP32-S3 + 2x INA226 + LD2410 + 照度 + 2 路 MOSFET 接线检查
- [ ] 24 V 电源、保险丝、共地、反接保护检查
- [ ] 5 kHz PWM 波形/占空比实测（配置已为 13 bit）
- [ ] 照度 ADC 0–2.5 V 标定（照度计对照）
- [ ] INA226 0.01 Ω 分流/最大电流标定，与万用表对比
- [ ] LD2410 灵敏度/延时现场调试
- [ ] CSI 存在检测与 LD2410 融合参数调试
- [ ] 断网、拔传感器、I2C 掉线演练
- [ ] 两路满载 30 分钟温升/EMI 检查

## P2 NAS / HA 联调（进行中）

- [x] 本地 mock API（`simulator/server.py`）
- [x] WiFi CSI 干扰波形（模拟 provider + 前端频谱/趋势图）
- [x] 前端可视化预览页（`simulator/frontend/`）
- [x] API 契约与实体映射文档（`simulator/README.md`）
- [x] NAS 部署 mock 服务（`espectre-plus-sim.service`，8100，enable + active）
- [x] 模拟联调：页面、健康检查、房间控制、WiFi 脉冲、局域网访问
- [x] 启动/配置本地 HA（`espectre-plus-ha`，8123，onboarding 完成）
- [x] 接 ESPectre Direct API `/espectre/v1/csi` 的真实 CSI 波形（V8 解析、64 子载波、断线重连）
- [x] `bench-csi` 编译/烧录，真机验证真实 CSI 64 子载波
- [x] NAS 服务切换到真实 CSI，`/api/health` 返回 `mode=espectre`
- [ ] 真实 HA REST/WebSocket 适配器，替换 `MockRoom`
- [ ] NAS 上导入 `homeassistant/packages/espectre_plus.yaml`
- [ ] 导入 `homeassistant/dashboards/lighting.yaml`
- [ ] 验收 Energy Dashboard、离线通知和手机推送
- [ ] 现场验证 CSI 波动与人员走动/干扰源的相关性，调校显示阈值

### 前端与演示交付（下一轮）

- [ ] 前端视觉收敛：减少卡片数量和装饰层级，改成极简、专业、易扫读的仪表盘
- [ ] 保留真实 CSI 频谱、派生波动趋势、来源标识和断线状态；模拟房间数据继续明确标注
- [ ] 回到用户提供的 2.4 GHz 网络做一次实机复核；SSID/密码只写本机忽略的 `firmware/bench/secrets.yaml`，不进入 Git
- [ ] 复核真实 CSI 来自 ESPectre Direct API，而不是浏览器本地 mock 或虚构波形
- [ ] 答辩材料随最终实现同步更新，不把设计值或模拟值写成实测值
- [ ] 每次展示更新都重新生成独立演示目录和压缩包，不带构建产物、密钥或缓存

## P3 全屋扩展

- [ ] 第二房间节点复制与地址规划
- [ ] HA 跨房间场景（客厅-餐厅-走廊）
- [ ] 夜间最低亮度/观影/阅读场景
- [ ] 用电报表按房间/按日/按月
- [ ] OTA 批量升级流程
- [ ] 设备离线告警（HA package 已有持久通知，手机推送待接）

## P4 可选增强

- [ ] 闭环照度控制（PID/自适应）
- [ ] 电池供电节点评估（ZigBee/Thread）
- [ ] 本地 LCD/触摸屏状态显示
- [ ] 外壳/PCB/安规设计
- [ ] 运行时阈值调节（number/select 实体）

## 已知限制

- 当前只有一块 ESP32-S3 单板；LD2410、INA226、照度、MOSFET、24 V 灯路和真实 HA 都还没接入。单板模拟通过不等于整机验收。
- NAS 预览已接真实 ESPectre CSI；房间状态、功率和电量仍是 mock，NAS 没有 Home Assistant。
- `bench-sim` 的传感器是脚本模拟的，不能用来证明 CSI/雷达融合效果或计量精度。
- ESPectre 的 CSI 检测受路由器、墙体、人员走动影响，必须现场标定。
- 24 V 灯路涉及较大电流，必须由有经验的人接线并加保险丝。
