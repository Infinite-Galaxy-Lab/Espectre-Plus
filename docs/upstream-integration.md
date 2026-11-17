# 上游 ESPectre 的 ESPHome 集成调研

> **本项目实际选择（2026-11-16）**：项目使用 ESPHome 2026.10.2 **内置 `espectre` 组件**，而不是外部组件。内置组件已提供本项目需要的 `binary_sensor` `motion`、`sensor` `movement` 和 `diagnostics.csi_occupancy`，且 `esphome config` / `esphome compile` 均已通过（见 `docs/adr/0003-built-in-espectre.md`）。本文下面的外部组件调研保留作为“需要阈值/select/switch 等高级运行时控制”时的备选方案。外部组件已弃用，3.3 将移除；若使用，固定 `ref: "3.2.0"`。
> 调研对象：`upstream-espectre/`（GitHub `francescopace/espectre`，main @ `062863f`，tag `3.2.0` @ `6284768`，GPLv3）。
> 调研日期：2026-11-16。本文只写能从仓库文件核实的结论；无法核实的放在“未确认项”。
> 引用格式：`文件:行号 @标签`，行号指该标签下文件的物理行。

---

## 1. 结论

1. **外部组件写法固定为 git 源 + `path` + `components` 列表**，本仓库可直接复用：
   `source.type: git`、`url: https://github.com/francescopace/espectre`、`path: src/cpp/frontend/esphome/components`、`components: [espectre]`。`ref` 可省略（跟随默认分支），但**省略即跟随 main，不可复现**（`README.md:279-290 @3.2.0`）。

2. **`3.2.0` 与 `main` 在 ESPHome 前端目录上完全一致**：`git diff --name-only 3.2.0 HEAD -- src/cpp/frontend/esphome` 为空，且 `README.md`、`components/espectre/__init__.py`、`examples/espectre-s3.yaml`、`examples/espectre-source-github.yaml` 四个文件在 3.2.0 与 main 的 git blob 哈希相同。差别只在仓库其它位置（web/docs），所以**用 `ref: "3.2.0"` 更稳**：同样是已验证的代码，但版本号固定、可复现，且与官方镜像发布版本对齐。

3. **外部组件已被上游标记为弃用**：构建时打印 `The ESPectre external component is deprecated and will be removed in ESPectre 3.3`（`components/espectre/__init__.py:470-475 @3.2.0`；`README.md:5`；`docs/CHANGELOG.md` 3.2.0 条目）。它现在仍可用，官方固件镜像也仍在用它，直到 3.3。

4. **ESPHome 自 2026.10 起自带 `espectre` 组件**（`README.md:224 @3.2.0`）。2026.10.2 的内置版本提供 `binary_sensor` 的 `motion`/`calibrating`，以及 `sensor` 的 `movement` 和 `diagnostics.csi_occupancy`；它没有 `number`/`select`/`switch`/`button` 等运行时阈值控制，也没有 Direct API，SDK 固定为 3.0.0。**这些实体已足够本项目使用（只需要 CSI motion），所以本项目选内置组件**；需要运行时调阈值/命中数时再看外部组件 3.2.0 或 ESPHome 2026.11+。

5. **最低版本**：ESPHome **2026.7.0**（所有示例 `esphome.min_version: 2026.7.0`；`CHANGELOG.md` 3.0.0/3.1.0 明确“ESPHome configurations still require 2026.7.0 or later”），ESP-IDF **≥ 5.5.3**（`src/cpp/idf_component.yml`；组件目录下 `idf_component.yml` 写 `>=5.5.0`，SDK 根目录要求更严的 5.5.3），框架**必须是 `esp-idf`**（组件用 `add_idf_component` / `add_idf_sdkconfig_option` 注册 IDF 组件，6 个官方示例全部是 `framework: type: esp-idf`）。

6. **许可证是硬约束**：ESPectre 第一方代码 `GPL-3.0-only`，**ESPHome 前端属于 GPL-only，商业许可不覆盖它**（`LICENSING.md`，`THIRD_PARTY_NOTICES.md` 中 “ESPHome C++ runtime … GPL-3.0-only；Not included in the commercial track”）。把 ESPectre 编译进固件并分发（包括烧到设备里）即视为单个组合作品，**整个组合必须以 GPLv3 授权并提供完整 Corresponding Source（含我们自己的集成代码）**。

7. **本项目采用的实际路径**：ESPHome `2026.10.2` 内置 `espectre`（构建时拉取 ESPectre SDK `3.0.0`），只使用 `binary_sensor` 的 `motion` 驱动本地照明策略；`esphome config` 与 `esphome compile` 已通过。`external_components` + `ref: "3.2.0"` 仅作为需要 `number`/`select`/`switch` 等运行时控制时的备选，且该外部组件在 3.3 将移除。

8. **校验记录**：本项目实际使用的内置 `espectre` 配置已在 ESPHome **2026.10.2** 下通过 `esphome config` 和 `esphome compile`；本文 §2 的外部组件片段仅做过本地 schema 校验，`type: git` 拉取路径未验证，见 §5。

---

## 2. 准确配置片段

### 2.1 上游原文（可核对的最小写法）

来源：`src/cpp/frontend/esphome/examples/espectre-source-github.yaml @3.2.0`（为 `espectre-s3.yaml` 等示例 include 的组件来源文件）：

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/francescopace/espectre
      ref: main
      path: src/cpp/frontend/esphome/components
    components: [ espectre ]
    refresh: always
```

同一写法的文档版本见 `README.md:279-286 @3.2.0`（省掉 `ref` 与 `refresh`）。要点：

- `path` 指向**仓库内的 `src/cpp/frontend/esphome/components`**，不是仓库根，也不是 `components/espectre`。
- `components` 只列 `espectre`（内置 Direct API 随组件编译；`espectre_direct` 是给 ESPHome 内置组件用的附加组件，当前不需要）。
- `refresh: always` 只在跟 main 时有意义；固定 `ref` 时可以去掉。
- **不能只复制 `components/espectre` 目录到本地**：组件在 `to_code` 里用 `_COMPONENT_ROOT.parents[3]` 推出 SDK 根（即 `src/cpp`）并 `add_idf_component(name="espectre", path=...)`（`__init__.py:543,550 @3.2.0`），必须是完整 checkout。

### 2.2 推荐用于 `firmware/packages/sensors.yaml` 的片段

来源：结构照搬 `examples/espectre-s3.yaml @3.2.0`（`min_version`、`esp32`、`psram`、`espectre:` 各行的取值都能在该文件对上），仅把 `ref` 从 `main` 改成 `3.2.0`、`direct_api` 改 `false`、给实体加 `id`：

```yaml
# firmware/packages/sensors.yaml —— ESPectre Wi-Fi CSI 人体存在（ESP32-S3）
esphome:
  min_version: 2026.7.0

esp32:
  variant: ESP32S3
  cpu_frequency: 240MHz
  framework:
    type: esp-idf

# S3 通常带 8MB Octal PSRAM（N16R8）；无 PSRAM 的板子删掉这一段并实测
psram:
  mode: octal
  speed: 80MHz

external_components:
  - source:
      type: git
      url: https://github.com/francescopace/espectre
      ref: "3.2.0"
      path: src/cpp/frontend/esphome/components
    components: [espectre]

espectre:
  id: espectre_csi
  detection_algorithm: lightweight      # lightweight(默认) | high_accuracy
  traffic_generator_mode: ping          # ping(默认) | dns | dns_tcp | wifi_raw | external
  evaluation_interval_ms: 250           # 10-10000，默认 250；检测与遥测节拍
  direct_api: false                     # 关掉 Direct HTTP/SSE/raw CSI/mDNS
  movement_sensor:
    id: espectre_movement
    name: "Movement Score"
    internal: true                      # 分数只留本机用，避免刷爆 HA recorder
  motion_sensor:
    id: espectre_motion
    name: "Motion Detected"
    on_press:
      - lambda: |-
          // 人体进入：此处接本地照明策略（示意，未实现）
    on_release:
      - lambda: |-
          // 人体离开：此处结束延时/降亮（示意，未实现）
  calibration_active_sensor:
    name: "Calibration Active"
    disabled_by_default: true
```

约束与注意：

- `espectre:` 的 `DEPENDENCIES = ["logger", "wifi"]`（`__init__.py:58`），所以 YAML 里必须有 `wifi:`（示例用 `wifi.ap` 做配网回退）和 `logger:`；`api:`、`ota:` 按主配置给即可。
- 实体 key 不写也会按默认名创建（`cv.Optional(..., default={"name": ...})`），全部传感器/控制都**默认存在**，不需要就显式 `internal: true` 或 `disabled_by_default: true`。
- 片段放在 package 里是安全的：ESPHome 合并 packages 时列表是**拼接**（`esphome/config_helpers.py` 的 `merge_config`：`if isinstance(new, list): return old + new`，2026.10.2 核对），根 YAML 里的 `external_components` 不会被覆盖。`esphome:` / `esp32:` 若主 YAML 已写，把这两段删掉只留 `external_components` + `espectre:` 更干净（重复的 `esp32.variant` 等要一致）。
- `esphome.project.version` 可省略：`ref` 是数字版本号（如 `3.2.0`）时组件自动用它当固件版本（`README.md:290`，`__init__.py:513-547`）。

### 2.3 `espectre:` 下的实体 id 写法

实体全部写成 `espectre:` 的**子键**（不是平台级 `sensor:`/`binary_sensor:`），每个子键接受标准 ESPHome 实体选项（`id`、`name`、`internal`、`icon`、`disabled_by_default`、`filters`、触发器）。

| 子键 | 类型 | 默认名 | 说明 |
|---|---|---|---|
| `movement_sensor` | sensor | Movement Score | 0–1 级运动分数，支持 `filters` |
| `motion_sensor` | binary_sensor | Motion Detected | 人体检测结果，支持 `on_press`/`on_release`（示例：`examples/espectre-s3-led.yaml`） |
| `calibration_active_sensor` | binary_sensor | Calibration Active | 标定进行中 |
| `threshold_number` | number | Threshold | 运行期阈值 |
| `motion_on_hits_number` / `motion_off_hits_number` | number | Motion On/Off Hits | 去抖命中数 |
| `detector_select` | select | Detection Profile | 运行期切换 lightweight / high_accuracy |
| `traffic_generator_mode_select` | select | CSI Traffic Source | 运行期切换流量源（含 external） |
| `csi_sample_spacing_select` | select | CSI Packet Spacing | half_slot / distinct |
| `sensing_switch` | switch | Sensing Enabled | 暂停/恢复感知 |
| `recalibrate_button` / `diagnostics_button` | button | Recalibrate / Refresh Diagnostics | 标定 / 拉取诊断 |
| `generator_rate_sensor`、`traffic_rate_sensor`、`traffic_rx_rate_sensor`、`csi_*_rate_sensor`、`csi_occupancy_sensor`、`wifi_channel_sensor`、`wifi_rssi_sensor` | sensor | 见 `README.md:78-108 @3.2.0` | 诊断用，默认随组件创建 |

写法示例（来源：`README.md:78-108 @3.2.0`，`examples/espectre-s3-led.yaml`）：

```yaml
espectre:
  movement_sensor:
    id: espectre_movement
    name: "Living Room Movement"
    internal: true
    icon: "mdi:sine-wave"
    filters:
      - multiply: 100
      - clamp:
          min_value: 0
          max_value: 100
      - round: 1
  motion_sensor:
    id: espectre_motion
    name: "Living Room Motion"
    icon: "mdi:motion-sensor"
```

给了 `id` 后即可在 lambda / 其它组件里 `id(espectre_motion).state`，也可在 YAML 里用 `on_press` 挂动作（`binary_sensor.new_binary_sensor(config[...])`，`__init__.py:637-641 @3.2.0`）。

### 2.4 关键选项（默认值与范围，来源 `components/espectre/__init__.py:220-280 @3.2.0` 与 `sensing_schema.py`）

| 选项 | 默认 | 取值/范围 | 说明 |
|---|---|---|---|
| `direct_api` | `true` | bool | 关掉后 Direct HTTP、SSE、raw CSI 采集、Direct mDNS 发现全部停用，ESPHome API 与实体不受影响。我们建议 `false`。 |
| `traffic_generator_mode` | `ping` | `ping` / `dns`(UDP) / `dns_tcp` / `wifi_raw` / `external` | `wifi_raw` 在 ESP32-C6 上被 schema 拒绝；`wifi_raw` 还要求 `csi_capture_profile` 为 `auto` 或 `lltf`（`FINAL_VALIDATE_SCHEMA`）。`external` 由 HA 侧 Traffic Generator add-on 发包。 |
| `evaluation_interval_ms` | `250` | 10–10000 | 检测器与实时遥测的节拍；示例注释建议 250–1000。 |
| `csi_target_pps` | `100` | 1–500 | 目标 CSI 包速率。 |
| `segmentation_window_size_ms` | `1000` | 1000–2000 | 检测窗口。 |
| `detection_algorithm` | `lightweight` | `lightweight` / `high_accuracy` | 起始配置；`detector_select` 可运行期改并持久化。 |
| `csi_capture_profile` | `auto` | `auto` / `lltf` / `ht-vht` | 只能改 YAML 后重编。 |
| `csi_sample_spacing` | `half_slot` | `half_slot` / `distinct` | 拥塞信道用 `distinct`。 |
| `motion_on_hits` / `motion_off_hits` | 见 schema | 1–20 | 去抖。 |
| `lowpass_enabled` / `lowpass_cutoff` | `false` / `11.0` | cutoff 5–20 | 低通滤波。 |
| `hampel_enabled` / `hampel_window` / `hampel_threshold` | `true` / `7` / `5.0` | window 3–11，threshold 1–10 | 异常值抑制，**默认开启**。 |
| `traffic_generator_target_ip` / `_target_mac` | `""` / `auto` | 单播 IPv4 / 单播 MAC 或 `auto` | 空 IP 用网关。 |
| `csi_traffic_multicast_group` | `239.255.0.1` | IPv4 组播 | `external` 模式使用。 |

### 2.5 ESP32-S3 推荐配置

全部来自 `examples/espectre-s3.yaml @3.2.0`：

- `esp32.variant: ESP32S3`、`cpu_frequency: 240MHz`、`framework.type: esp-idf`（行 29-33）
- `psram.mode: octal`、`speed: 80MHz`（行 36-38，注释说明“8MB on most S3 boards”，测试板为 ESP32-S3-DevKitC-1 / WROOM-1-N16R8）
- `esphome.name_add_mac_suffix: true`（行 24，同一镜像多设备时主机名唯一）
- `logger.level: INFO`，USB 直接接芯片时不要设 `hardware_uart`（行 60-63 注释）
- 固件 4MB flash 即可带 OTA，用 ESP-IDF 默认分区表（`README.md:331 @3.2.0`）
- 不用 BLE 配网：示例走 `improv_serial`；如同时跑 `bluetooth_proxy`，需要 `CONFIG_ESP_COEX_SW_COEXIST_ENABLE: n` 等额外设置，且会显著降低 CSI 占用率（`README.md:337-388 @3.2.0`）

### 2.6 本地校验记录（2026-11-16）

```powershell
# 用仓库自带 venv 的 ESPHome（2026.10.2）；系统 PATH 上的 esphome 是 2026.2.4，太旧，不要用
.\.venv\Scripts\esphome.exe config test-local.yaml
# => INFO ESPHome 2026.10.2 / INFO Configuration is valid!
```

- `type: local` + `path: D:/code/Espectre-Plus/upstream-espectre/src/cpp/frontend/esphome/components` 校验通过：§2.2 的选项名、实体子键和 `id` 写法在本版本 schema 下合法。
- 同一份 YAML 换成 `type: git` + `ref: "3.2.0"` 时，本机 `git clone https://github.com/francescopace/espectre` 被网络拦（`Failed to connect to github.com port 443`），属环境限制而非配置错误（上游示例本身就用 `type: git`）。
- **未做** `esphome compile`：需要 ESP-IDF 工具链和可访问 GitHub 的构建机。
- 离线/可复现构建两条路：① 构建机预置 ESPHome 的 external_components 缓存；② 把上游完整 checkout 固定到仓库内某路径，`external_components` 用 `type: local` 指向它（必须完整仓库，SDK 根在 `src/cpp`）。

---

## 3. 版本兼容

| ESPHome | 外部组件 `espectre:` | 内置 `espectre:` | 说明与依据 |
|---|---|---|---|
| ≤ 2026.6.x | ✗ | ✗ | 低于最低要求 `min_version: 2026.7.0`。 |
| 2026.7.x | ✓（上游最低基线） | ✗ | `examples/*.yaml` 的 `min_version: 2026.7.0`；`CHANGELOG.md` 3.0.0 起声明 “ESPHome configurations still require 2026.7.0 or later”。 |
| 2026.8.x–2026.9.x | ✓ | ✗ | 内置组件在 ESPHome `2026.10.0` 才出现（`esphome/components/espectre/__init__.py` 在 2026.9.1 不存在，在 2026.10.0 存在）。 |
| 2026.10.x（当前稳定，最新 2026.10.2） | ✓ 官方镜像即用此版本 + 外部组件 | ✓ 内置组件提供 `binary_sensor` 的 `motion`/`calibrating`、`sensor` 的 `movement` 和 `diagnostics.csi_occupancy`；无 number/select/switch/button，无 Direct API；SDK 固定 `3.0.0`。本项目用内置组件 | 本项目 `requirements.txt` 固定 `esphome==2026.10.2`；内置组件源码核对。外部组件在 2026.10.2 上仍可用（官方镜像构建即如此），组件名与内置同名不冲突。 |
| 2026.11.x | 未验证 | ✓ 扩展到 `number`/`select`/`switch`/`button`/`binary_sensor`，SDK 固定 `3.2.0`，选项改名 `window_size`、`evaluation_interval`、`lowpass_filter`、`hampel_filter` | 截至 2026-11-16 **只有预发布 tag `2026.11.0b1`–`b4`，无稳定版**（`git ls-remote --tags` 核对，esphome.io 当前文档版本为 2026.10.2）。`README.md:254,260 @3.2.0` 建议 2026.11+ 才迁到内置组件；b4 的文件清单已含上述平台文件、`__init__.py` 里 `esp32.add_idf_component(..., ref="3.2.0")`。 |
| ≥ ESPectre 3.3 | ✗ 将被移除 | ✓ 官方镜像迁到内置组件 | `CHANGELOG.md` 3.3.0（work in progress）+ `README.md:5`。 |

其它实测/文档化的差异点：

- **ESPHome 2026.8.2 + ESP-IDF 5.5.5**：`esp32_ble_tracker.software_coexistence: false` 单独使用无法关掉 IDF 共存，必须同时加 `CONFIG_ESP_COEX_SW_COEXIST_ENABLE: n` 并 Clean Build（`README.md:361-366 @3.2.0`）。与蓝牙代理共存时这条是关键。
- **mDNS 版本**：SDK 允许 `espressif/mdns` 1.12–1.15（`src/cpp/idf_component.yml`），3.2.0 放宽到 1.15 就是为了配合 ESPHome 2026.11 pin 的 1.15.0；2026.10 系列用 1.14.x 也落在范围内。
- **迁移到内置组件时的改名**（`README.md:260-274 @3.2.0`）：`segmentation_window_size_ms`→`window_size`、`evaluation_interval_ms`→`evaluation_interval`、`movement_sensor`→`sensor` 平台的 `movement`、`motion_sensor`→`binary_sensor` 平台的 `motion`、各 rate/occupancy/Wi-Fi 传感器→`sensor` 平台的 `diagnostics`、`direct_api`→`espectre_direct` 附加组件。内置版没有 admitted/filtered/stale/out-of-order rate，也没有 Wi-Fi channel。
- 官方镜像的 OTA 带签名校验，自编译固件会被官方固件拒绝（`README.md:220 @3.2.0`）；我们自建固件不要和官方镜像混用。

---

## 4. 许可证

### 4.1 事实

- 第一方代码统一 `GPL-3.0-only`：`LICENSE`（GPLv3 全文）、每个源文件头 `# SPDX-License-Identifier: GPL-3.0-only`（如 `components/espectre/__init__.py:1`）、`src/cpp/idf_component.yml` 的 `license: "GPL-3.0-only"`。
- `LICENSING.md`：可另购商业许可做闭源集成，**但 ESPHome 前端（`ESPHome` frontend）始终保持 GPLv3-only，商业许可不覆盖**；`THIRD_PARTY_NOTICES.md` 同口径（“ESPHome C++ runtime … GPL-3.0-only … Not included in the commercial track”）。
- `THIRD_PARTY_NOTICES.md` 记录随仓库分发的第三方材料（ESP-IDF Apache-2.0、mDNS Apache-2.0、esp_tinyusb/TinyUSB Apache-2.0+MIT、Arduino core LGPL-2.1 等），要求保留对应声明与许可证文本。
- 贡献规则（`LICENSING.md` / `CLA.md`）：DCO `Signed-off-by` + CLA，与我们无关但说明上游再许可路径。

### 4.2 对衍生项目意味着什么

- **用 ESPectre + ESPHome 做固件并分发（OTA 或烧到设备里都算 conveying）= 单个组合作品**，整个组合必须以 GPLv3 授权，并向接收者提供完整 Corresponding Source，**包括我们自己的集成代码**（`firmware/`、`firmware/packages/*.yaml`、自定义 C++ 组件、构建脚本）。
- 内部自用、不对外分发：不需要发布源码，也不需要商业许可（`LICENSING.md`：private use / internal modifications 不触发）。
- 卖硬件/卖服务可以，GPLv3 允许商业使用；但客户索要源码必须给。
- 想闭源分发：ESPHome 前端没有商业许可通道，所以**只要走 ESPHome 路线就必须 GPLv3**；商业许可只对 Native/Matter/Arduino 等前端有意义。
- 通过 MQTT/HTTP 与我们自己的 HA 侧代码交互不构成“组合作品”（`LICENSING.md` 明确），所以 `homeassistant/` 下的 YAML 包/自动化不必 GPLv3（但设备固件和其源码必须）。

### 4.3 仓库应保留的 NOTICE / 署名

1. 根目录 `LICENSE` = GPLv3 全文（本仓库对外发布固件源码时）。
2. 保留 `upstream-espectre/` 原样（含 `LICENSE`、`LICENSING.md`、`THIRD_PARTY_NOTICES.md`、`CLA.md`、所有文件头），不要删改 SPDX 头与 `Author:` 行。
3. 在 `docs/`（或 `NOTICE`/`THIRD_PARTY_NOTICES.md`）记录：上游项目名、仓库 URL、开发调研参考的 tag/commit（`3.2.0` @ `6284768`）、实际接入方式（ESPHome 2026.10.2 内置组件，构建 ESPectre SDK `3.0.0`），以及“本项目整体按 GPL-3.0 分发”。
4. 若将来 vendor 源码进本仓库：保留每个文件的 SPDX 头 + 上游 `LICENSE` + `THIRD_PARTY_NOTICES.md`；不要剥离 “Commercial licensing available under separate agreement” 那一行注释（它是上游文件的一部分）。
5. 若发布固件二进制：随附源码获取方式与许可证文本；如再叠加 ESP-IDF（Apache-2.0）等第三方，需保留其 NOTICE。
6. 不要使用 ESPectre / Matter 的名称、logo 暗示认证或背书（`THIRD_PARTY_NOTICES.md` “Trademarks, media, and external links”）。

---

## 5. 未确认项

1. **ESPHome 2026.11 尚无稳定版**（截至 2026-11-16 只有 `2026.11.0b1`–`b4`）。**外部组件在 2026.11 上是否仍能编译/运行未验证**；上游只在文档里建议 2026.11+ 改用内置组件。
2. **本项目构建已通过，外部组件路径未验证**：内置 `espectre` 配置在项目 `.venv` 的 ESPHome 2026.10.2 下通过 `config` 和 `compile`；本文研究的外部组件 `type: git` + `ref: "3.2.0"` 拉取路径未验证，需在有外网且可访问 GitHub 的构建机复验。系统 PATH 上的 `esphome` 是 2026.2.4（低于 2026.7.0），构建请用项目 `.venv`。
3. ESPHome 2026.7.x 自带的 ESP-IDF 具体版本未核实（要求 ≥5.5.3；能确认的是官方固件用 ESPHome 2026.10.2 + ESP-IDF 5.5.6，见 `CHANGELOG.md` 3.1.0）。
4. `firmware/packages/sensors.yaml` 已补齐并通过完整示例配置编译；外部组件片段若用于其它房间，仍需在实际主 YAML 再核对 `wifi:`/`logger:` 依赖、实体命名冲突和 GPIO 占用。
5. `psram` 是否必需未找到上游明文要求；片段按 N16R8 板给出，若目标板无 PSRAM 需删除并实测内存占用。
6. 低通/Hampel 等滤波参数默认值来自 `sensing_schema.py`（由 SDK 生成），实际调参建议按房间实测，本文不给推荐值。
7. ESPectre 3.3 的发布时间未公布（`CHANGELOG.md` 标为 work in progress），外部组件被移除的具体版本边界只能等发布。

---

## 附：核实方法（可复现）

```powershell
cd upstream-espectre
git log -1 --oneline                                   # 062863f
git rev-parse 3.2.0                                    # 6284768...
git diff --name-only 3.2.0 HEAD -- src/cpp/frontend/esphome   # 空 → 前端目录两版本一致
git rev-parse 3.2.0:src/cpp/frontend/esphome/examples/espectre-s3.yaml   # 与 HEAD: 同哈希
```
