# lighting_controller

ESPHome 自定义组件：把照度、存在、CSI 运动、两路灯和本地按键组合成一个本地照明控制器。

## 文件

| 文件 | 作用 |
|---|---|
| `lighting_policy.{h,cpp}` | 纯 C++ 状态机，无 ESPHome 依赖，可在 PC 上测试 |
| `lighting_controller.{h,cpp}` | ESPHome 适配：读传感器、驱动 `light::LightState`、发布状态 |
| `__init__.py` | YAML schema 与代码生成 |

## YAML 用法

```yaml
lighting_controller:
  id: lighting
  illuminance: illuminance
  presence: mmwave_presence
  motion: csi_motion          # 可选；没有 CSI 时只靠毫米波
  main_light: main_light
  aux_light: aux_light
  auto_mode_switch: auto_mode
  occupancy:
    id: occupancy
    name: "Room Occupancy"
    device_class: occupancy
  status:
    id: control_state
    name: "Room Control State"
  lux_on: 250
  lux_off: 350
  aux_lux_threshold: 80
  main_min_brightness: 20%
  main_max_brightness: 100%
  main_fallback_brightness: 60%
  aux_brightness: 40%
  presence_confirm: 1s
  absence_timeout: 300s
  csi_hold: 60s
  lux_reduce_delay: 60s
  dim_step_interval: 10s
  dim_step: 10%
  fade: 1s
```

## 行为

- 存在：毫米波 `has_target` 或 CSI 运动保持；连续 `presence_confirm` 后确认有人；无人 `absence_timeout` 后关灯。
- 光照：低于 `lux_on` 开灯/增亮；高于 `lux_off` 持续 `lux_reduce_delay` 后按 `dim_step` 逐步降亮；中间保持。
- 手动：用户按灯键或 HA 直接调灯 → MANUAL；直到 HA 开关或模式键回 AUTO。
- 故障：两路存在传感器都无效 → `SENSOR_FAULT`，保持当前输出；照度无效 → 回退到 `main_fallback_brightness`。
- 调光：所有命令带 `fade` 过渡，默认 1 s。

## 测试

```powershell
.\tools\test-host.ps1
```

测试只编译 `lighting_policy.*`，不需要 ESPHome/ESP32。
