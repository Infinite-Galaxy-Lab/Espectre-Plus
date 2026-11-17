# Rooms

每个房间一份 YAML。复制 `example-room.yaml`，改 substitutions 即可。

## 必改项

| 项 | 说明 |
|---|---|
| `room_name` | 人类可读名称，用于实体名 |
| `node_name` | ESPHome 节点名，建议 `espectre-plus-<room>`，全屋唯一 |
| `main_gpio` / `aux_gpio` | 两路 PWM 引脚 |
| `button_*_gpio` | 三个按键引脚 |
| `i2c_sda` / `i2c_scl` | INA226 总线 |
| `ld2410_tx` / `ld2410_rx` | 雷达 UART |
| `lux_adc_pin` | 照度 ADC |
| `main_ina_address` / `aux_ina_address` | 0x40/0x41 |
| `main_shunt` / `aux_shunt` | 默认 0.01 Ω；必须与实物一致 |
| `main_max_current` / `aux_max_current` | 按灯具电流设置 |

## Secrets

`secrets.yaml` 放在本目录（`firmware/rooms/secrets.yaml`），不要提交。首次：

```powershell
Copy-Item secrets.example.yaml secrets.yaml
```

所有房间可以共用一个 `secrets.yaml`；如果每个房间要不同 API key，可以拆成多个目录，但 `!secret` 会优先找房间 YAML 所在目录，拆目录时要注意路径。
