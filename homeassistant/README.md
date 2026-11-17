# Home Assistant 侧配置（ESPectre Plus）

固件只上报**瞬时功率**（INA226 以 5 Hz 读取，节流为每 5 s 一次），不长期存电量。HA 这一侧负责：

1. 把 W 积分成 kWh（`integration`）；
2. 做日 / 月统计（`utility_meter`）；
3. 汇总两路功率、总电能，并按可充电价估算电费（`template` + `input_number`）；
4. 提供仪表板、手机 App / 语音入口，以及节点离线提醒。

目录：

```text
homeassistant/
├── packages/
│   └── espectre_plus.yaml        # 计量 + 统计 + 电费 + 离线提醒（复制到 HA 的 config/packages/）
├── dashboards/
│   └── lighting.yaml             # Lovelace YAML 仪表板示例（复制进“原始配置编辑器”）
└── README.md
```

本目录所有文件**不含任何真实 Wi-Fi、密码、token 或家庭地址**。本机 Docker 容器启动见 [local-ha.md](local-ha.md)。ESPHome 侧凭据请放在你自己的 `secrets.yaml`，本仓库只有 `firmware/rooms/secrets.example.yaml` 占位。

---

## 1. 前置条件

| 项 | 要求 |
|---|---|
| Home Assistant | 2023.6 以上即可，建议 2024.x 以上（写法只用长期稳定的 YAML 形式） |
| 节点 | ESPHome 节点 `espectre-plus-study` 已接入 HA（设置 → 设备与服务 → ESPHome 里能看到） |
| 实体 | 下表实体必须已经存在，命名与固件一致 |

| 实体 ID | 含义 | 备注 |
|---|---|---|
| `sensor.study_main_power` | 主灯瞬时功率 | 单位 W，`device_class: power`（INA226 默认由 ESPHome 自动设置） |
| `sensor.study_aux_power` | 辅灯瞬时功率 | 同上 |
| `sensor.study_illuminance` | 照度 | 仪表板用，package 不用 |
| `light.study_main_light` | 主灯 | 支持亮度 |
| `light.study_aux_light` | 辅灯 | 支持亮度 |
| `switch.study_auto_mode` | 自动模式 | 设备内策略的 AUTO/MANUAL 开关 |
| `binary_sensor.study_occupancy` | 占用 | 设备内策略输出 |

先到 **开发者工具 → 状态** 里搜一下 `study_`，确认这些实体都存在、功率单位是 `W`。单位不是 W 或缺少 `device_class: power` 时，`integration` 会拒绝这个源并在日志里报错。

---

## 2. 安装步骤

### 2.1 复制 package

把 `homeassistant/packages/espectre_plus.yaml` 复制到 HA 配置目录：

```text
config/packages/espectre_plus.yaml
```

（Samba / File editor / SSH add-on 都可以；Home Assistant OS 的配置目录通常是 `/config`。）

### 2.2 启用 packages

如果 `configuration.yaml` 里还没有 packages，加一段：

```yaml
homeassistant:
  packages: !include_dir_named packages
```

已经有 `homeassistant:` 段落的话，只把 `packages:` 那行合并进去即可（同一个键不要写两次）。

> 说明：`!include_dir_named packages` 会把 `packages/` 下每个 `.yaml` 当作一个 package 合并进配置。文件名随便，但不要和别的 package 用同一个文件名。

### 2.3 检查配置并重启

1. **开发者工具 → YAML → 检查配置**（必须显示“配置有效”）；
2. **设置 → 系统 → 右上角电源按钮 → 重启 Home Assistant**。

新增 `integration` / `utility_meter` / `template` 平台属于“新增实体”，一次完整重启最稳妥，单纯“重新加载 YAML”不一定能把它们建出来。

### 2.4 安装后应出现的实体

| 实体 ID | 说明 |
|---|---|
| `sensor.study_main_energy` | 主灯累计电能（kWh） |
| `sensor.study_aux_energy` | 辅灯累计电能（kWh） |
| `sensor.study_total_power` | 两路功率之和（W） |
| `sensor.study_total_energy` | 两路电能之和（kWh） |
| `sensor.study_main_energy_daily` / `_monthly` | 主灯今日 / 本月 |
| `sensor.study_aux_energy_daily` / `_monthly` | 辅灯今日 / 本月 |
| `sensor.study_total_energy_daily` / `_monthly` | 全房间今日 / 本月 |
| `sensor.study_daily_energy_cost` / `sensor.study_monthly_energy_cost` | 今日 / 本月电费（元） |
| `input_number.study_electricity_price` | 电价，默认 0.6 元/kWh |
| `automation.espectre_plus_study_node_offline` | 节点离线提醒 |

数量对不上时，先看 **设置 → 系统 → 日志**，最常见的原因是源实体名写错或功率单位不是 W。

### 2.5 改电价

`input_number.study_electricity_price`，默认 `0.6` 元/kWh，范围 0–5，步进 0.01。三种改法：

- 仪表板上的“电价”滑条/输入框（`dashboards/lighting.yaml` 里已包含）；
- 设置 → 设备与服务 → 辅助元素（Helpers）里找到它直接改；
- 开发者工具 → 动作（旧版叫“服务”）→ `input_number.set_value`。

改完以后电费模板传感器会立刻按新电价重算（见第 5 节“电价变化”的注意事项）。

### 2.6 把传感器加进能源仪表板

**设置 → 仪表板 → 能源**：

1. **单个设备（Individual devices）→ 添加设备**：
   - 想按整间房统计，就选 `sensor.study_total_energy`；
   - 想看主灯 / 辅灯分开，就分两次添加 `sensor.study_main_energy` 和 `sensor.study_aux_energy`。
   - 这两种方式只能选一种，别重复添加，否则会重复计入。
2. **电网（Grid）不用配**：本系统只测照明回路，没有全屋总表，硬加会得出错误的“电网用量”。
3. **成本**：可以在该设备的配置里填“固定电价”（0.6 元/kWh），也可以勾选“使用实体跟踪成本”并选我们的电费传感器。
   - 若提示单位不被识别，把 package 里电费传感器的 `unit_of_measurement` 从 `"元"` 改成 `"CNY"`（HA 的货币标准代码），并把 HA 的货币设置成 CNY。

能源仪表板的数据**从添加那一刻开始统计**，之前的历史不会补算。

### 2.7 导入 Lovelace 仪表板

任选一种：

- **已有仪表板**：打开仪表板 → 右上角铅笔（编辑）→ 再次点右上角三个点 → **原始配置编辑器** → 粘贴 `dashboards/lighting.yaml` 的内容 → 保存。
- **新建**：设置 → 仪表板 → 添加仪表板 → 标题 `智能照明` → URL 填 `lighting` → 创建后在“原始配置编辑器”里粘贴。
- **YAML 模式**（`lovelace: mode: yaml` 的高级用法）：把文件放到 `config/` 下再用 `!include` 引入，这类配置需要重启。

仪表板只用 HA 自带卡片（entities / gauge / history-graph / statistics-graph），不需要装 HACS 卡片。卡片里的 `max: 1000 lx`、`max: 100 W` 只是显示范围，按你实际灯具功率改。

---

## 3. 手机 App 与语音控制

### 3.1 Home Assistant Companion App

- 手机装官方 **Home Assistant** App（iOS / Android），填 HA 地址登录。地址可以是内网 IP（家里 Wi-Fi 下最稳），也可以是 Nabu Casa 云地址或你自己的 VPN —— 本仓库不写任何固定公网地址。
- 常用入口：
  - 把 `light.study_main_light` / `switch.study_auto_mode` 加到 **仪表板**，App 里直接就是控制页；
  - Android 可用桌面小组件（实体、按钮），iOS 可用“操作/快捷指令”；
  - 通知：`dashboards` / `packages` 里的离线提醒默认发 HA 持久通知。想推到手机，把自动化里
    `service: persistent_notification.create` 换成 `service: notify.mobile_app_<你的手机实体>`。
    手机实体名在 **开发者工具 → 动作** 里搜 `notify.mobile_app_` 就能看到，形如 `notify.mobile_app_pixel`。

### 3.2 语音（Assist）

1. **设置 → 语音助手 → 公开（Expose）**：勾选 `light.study_main_light`、`light.study_aux_light`、`switch.study_auto_mode`。（如果开启了“自动公开新实体”，新实体默认已被公开，需要的话取消勾选不想暴露的。）
2. 给实体加**别名**（中文名），例如“书房主灯”“书房辅灯”“书房自动模式”，语音识别更自然；同理也可以给房间加别名。
3. 之后用 HA 的 Assist（App 里的麦克风 / ESP32 语音卫星 / 浏览器）说：
   - “打开书房主灯” / “把书房主灯调到 40%”
   - “关掉书房辅灯”
   - “打开/关闭书房自动模式”

边界：

- Assist 内置意图主要覆盖**开关、亮度、温控、开关类模式**。问“书房现在多少瓦/多少度电/照度多少”这类数值查询，默认一般答不上来，需要在仪表板上看，或自己写自定义 intent。
- 语音/App 直接调灯，在固件里等同“人工干预”，会**退出自动模式进入 MANUAL**（手动优先的硬规则）。想恢复自动，用语音或按钮把 `switch.study_auto_mode` 打开。
- `switch.study_auto_mode` 的状态保存在设备内，HA 掉线不影响它。

---

## 4. 多房间扩展

### 4.1 推荐做法：复制 + 换前缀

1. 复制 `packages/espectre_plus.yaml` → `packages/espectre_plus_living.yaml`；
2. 把文件里的 `study` **全部**替换成新前缀（如 `living`）；
3. 逐个确认这几处都变了：
   - 所有实体 ID（`sensor.living_main_power`…）；
   - `integration` 的 `unique_id`（`living_main_energy` / `living_aux_energy`）—— **重复会直接报错或抢实体**；
   - `utility_meter` 的六个键名；
   - `input_number` 的键名；
   - 自动化 `id`（`espectre_plus_living_node_offline`）和 `alias`；
   - 模板里引用的实体名。
4. 固件侧房间 YAML（`firmware/rooms/<room>.yaml`）的 `room_name` 用同一个房间名（如 `Study`），HA 里才会生成 `study_` 前缀的实体；
5. 仪表板：在 `views:` 里再加一个房间的 view，或在一个 view 里堆多组卡片。

**电价建议只保留一份**：复制出来的 `living_electricity_price` 会和 `study_electricity_price` 变成两个独立电价。推荐只在一个 package 里留 `input_number`，其它房间的电费模板引用同一个 `input_number.study_electricity_price`（或换成中性的名字如 `electricity_price`）。

### 4.2 为什么不建议用 substitutions

HA 的 YAML **没有** Jinja/ESPHome 那种 `substitutions` 变量替换，`!include` 只能“整段复用同一个文件”，不能传入 `prefix: living` 之类的参数。所以：

- ESPHome 那种“一个包 + 每房间一份 substitutions”的做法在 HA 侧不成立；
- 可行替代：① 复制 + 文本替换（推荐，结果可读、可 review）；② 用一个本地脚本按模板生成 `packages/*.yaml`（生成物放 `config/packages/`，注意别让生成器和手改同时存在）；③ 引入 HACS 的 `auto-entities` 之类自定义卡片做“一个仪表板串多个房间”，但这类卡片要先装，本仓库不依赖。

另外，两个 package 里出现**同一个键**（比如都叫 `utility_meter: study_total_energy_daily`）会被当配置冲突/覆盖，所以复制后务必改全。

---

## 5. 报表、电价与数据保留

### 5.1 数据分三层

| 层 | 保留多久 | 谁在用 |
|---|---|---|
| 实体当前状态 | 只在内存里，重启由恢复机制带回来 | 界面、自动化 |
| recorder 明细历史 | 默认 `purge_keep_days: 10`（`configuration.yaml` 的 `recorder:` 可改） | history-graph、history 面板 |
| 长期统计（statistics） | 永久（按小时/天聚合，不会被 purge） | 能源仪表板、statistics-graph |

只有带 `state_class` 的实体才会进长期统计：本包里的 `sensor.*_energy*`（`total_increasing`）、`sensor.study_total_power`（`measurement`）、电费传感器（`total`）都符合条件。`utility_meter` 每天/每月归零不影响它的统计曲线，柱状图照样能看出每天用了多少。

### 5.2 电价与成本

- 电费模板的公式是 **当前电价 × 累积电量**。所以**改电价会重写历史**：今天的曲线、上周的数字都会按新电价重新算。这是模板传感器的固有限制。
- 想锁定历史成本，用**能源仪表板自己的成本设置**（固定费率或成本实体都是按当时数据记录），或录一份自己的统计。
- `2026 年起的阶梯电价/峰谷电价`：`input_number` 只有一个值，做不到分时。需要峰谷的话，改成两个 `input_number` + 一个 `template` 按当前小时选价，或用 HA 的 `utility_meter` `tariff` 功能（`tariffs:` 选项）。本包保持单电价，最简单也最不容易错。

### 5.3 精度与误差

- 采样 5 s，功率在采样点之间做梯形近似，灯具功率平稳时误差很小；频繁调光/开关的瞬间会有少量误差。
- INA226 在极小电流（灯关了但有待机）时分辨率有限，可能读 0，这部分电量就被丢掉。
- 节点离线、HA 停机期间**不会补算**（见下一节），电量会少计，不会多计。
- `integration` 的累计值存在 HA 的数据库里，重启后延续；它会随“重置/删除实体”一起丢，别随手删实体。

---

## 6. 断网 / 故障时的行为边界

| 场景 | 灯还能用吗 | HA 里看到什么 | 电量/电费 | 备注 |
|---|---|---|---|---|
| Wi-Fi 断 / 节点掉线 | **能**。感知、调光、按键都在设备内跑 | 该节点实体变 `unavailable`；离线自动化 10 分钟后发通知 | 不累计；恢复后从当前功率继续，中断期间不补算 | 仪表板会显示灰掉的实体 |
| HA 宕机或重启 | **能**。策略在 ESP32 上，HA 只是远程入口 | — | HA 停止期间不累计；重启后从恢复的累计值继续 | 手动优先状态由设备保留 |
| 路由器/局域网故障、互联网断 | 能（局域网内 HA 也可用） | 内网访问正常，外网/云访问不可用 | 正常 | 手机在外面就看不到 |
| 整户断电 | 不能（灯本身没电） | ESP32 与 HA 都需重新起来 | 停机期间不计量 | HA 历史数据仍在 |
| INA226 单路故障 | 能 | 该功率实体异常/不可用 | 该路电量停住 | 不参与开关灯判断，只影响报表 |
| 电价实体被改成 0 或不可用 | 能 | 电费显示 0 或 `unavailable` | 累计电量不受影响 | 兜底值见模板里的 `float(0.6)` |

一句话：**计量和报表是“尽力而为”，照明本身是本地优先**。断网期间灯照常工作，但用电曲线会有缺口。

---

## 7. 隐私与安全

- 本目录不含任何真实凭据。Wi-Fi 密码和 API 加密密钥请放在 ESPHome 的 `secrets.yaml` 里，不要提交；OTA 复用同一密钥。
- 不要把内网 IP、DDNS、Nabu Casa 地址、家庭住址写进仓库文件或截图。
- 对外暴露 HA（远程访问）优先用 Nabu Casa 或 VPN，不要在路由器上直接把 8123 端口映射到公网。

---

## 8. 排错清单

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 检查配置报 “Integration 'xxx' …” | 文件没放进 `config/packages/` 或 packages 没启用 | 检查 `configuration.yaml` 的 `packages:` 行与文件路径 |
| 没有 `sensor.study_main_energy` | 源实体名写错，或单位不是 W / 缺 `device_class: power` | 开发者工具 → 状态 里核对；日志里会有 `integration` 的报错 |
| `utility_meter` 一直 0 | 源传感器不是 `total_increasing`，或者源实体本身不涨 | 先确认 `sensor.study_main_energy` 在涨；确认 `study_total_energy` 有 `state_class` |
| 日统计在错误的时间归零 | HA 时区不是本地时区 | 设置 → 系统 → 常规 → 时区 |
| 仪表板某张卡片报“实体不存在” | 前缀没换全 / 实体还没生成 | 先确认实体在状态列表里，再改卡片 |
| `trapezoidal` 日志告警 | 新版 HA 把该方法标记为 deprecated | 功能正常，可忽略；需要消除告警就改 `method: left` |
| 能源仪表板里电量翻倍 | 同一路同时加了 `total_energy` 和 `main/aux_energy` | 二选一 |

---

## 9. 已知限制

- 只测照明回路，不含全屋家电；不要拿它当“家庭总电表”。
- 电费是估算值（单一电价 × 电量），不等于账单金额。
- 数据缺口无法回填：HA 或节点停机期间的用电不会补算。
- 电价变化会重写历史电费曲线（见 5.2）。
- 语音只能做开关/亮度类控制，数值查询与场景化语句需要自己写 intent 或脚本。
