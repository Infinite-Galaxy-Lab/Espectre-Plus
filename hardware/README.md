# Hardware

- [Wiring and safety notes](wiring.md)
- [BOM](bom.csv)

## Design summary

| Block | Part | Why |
|---|---|---|
| Controller | ESP32-S3 DevKitC-1 | Wi-Fi CSI support, dual LEDC, ADC, UART, I2C |
| Presence | LD2410C | Static presence; complements CSI motion |
| Energy | 2x INA226 | Per-channel bus voltage/current/power |
| Light driver | 2x logic-level N-MOSFET | 24 V low-side PWM, common ground |
| Lux | GL5528 divider | Matches the report's 0-2.5 V analog A/D analysis |
| Local input | 3 push buttons | Main, aux, auto/manual |

## Before ordering

1. Confirm the ESP32-S3 board has the PSRAM option you need. The example uses
   octal PSRAM; remove the `psram:` block if your board has none.
2. Confirm INA226 shunt value. A 0.1 ohm module cannot measure 2 A; use 0.01 ohm
   or a module with a suitable shunt.
3. Confirm LED strip voltage and current. The example assumes 24 V, about 1 A
   per 24 W channel.
4. Confirm the MOSFET is logic-level at 3.3 V gate drive.
