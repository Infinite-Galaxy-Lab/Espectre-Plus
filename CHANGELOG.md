# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog and the project uses semantic versioning once firmware is
released.

## [Unreleased]

### Added

- Local NAS/HA mock (`simulator/server.py`) with `/api/state`, `/api/control`
  and `/api/health`.
- Local dashboard preview (`simulator/frontend/`) for room state, lights,
  power, energy and event log.
- Mock WiFi CSI provider (`simulator/wifi.py`): 64 subcarriers, RSSI, noise
  floor, interference trend and burst injection through `/api/wifi`.
- NAS preview deployed as `espectre-plus-sim.service` on port 8100; real CSI is enabled through a private `EnvironmentFile`. Home Assistant is not installed on the NAS.
- Simulator provider tests in `simulator/tests/`.
- Local Home Assistant development container and setup notes (`homeassistant/local-ha.md`); credentials stay outside the repository.
- `docs/code-quality.md` with layering, reuse and comment rules.
- Real ESPectre CSI provider: `simulator/csi_http.py` V8 frame parser and Direct HTTP client, `EspCsiWifi` provider, 64-subcarrier normalization and reconnect handling.
- `simulator/fake_csi_device.py` synthetic V8 stream for protocol tests without hardware.
- `firmware/bench/bench-csi.yaml` CSI-only bench profile; `firmware/packages/csi.yaml` shared ESPectre + Direct API config.
- Vendored `firmware/components/espectre_direct/` adapter (GPL-3.0-only) to expose `/espectre/v1/csi` without a runtime GitHub clone.
- Real CSI now deployed on NAS; device address comes from `/etc/espectre-plus-sim.env`, not the repository.

### Changed

- Bench configs share `firmware/bench/common.yaml`; `bench-sim` reuses
  `packages/actuators.yaml` and `packages/control.yaml`.
- `control.yaml` thresholds/timings are substitutions so production and bench
  use one controller definition.
- Trimmed long comments/banners in firmware YAML, C++ and HA dashboard files.
- Split simulator HTTP routing from room and WiFi providers; `tools/validate.ps1`
  now runs simulator tests and frontend syntax checks.
- Frontend source labels, footer and fineprint are provider-aware; real mode hides burst injection and labels the derived metric as CSI fluctuation.

### Verified

- `bench-csi` compiled (Flash 13.6%, RAM 32.8%), flashed to ESP32-S3, and streamed 64 real CSI subcarriers over Direct HTTP at about 100 pps on 2.4 GHz channel 9.
- NAS preview returned `mode=espectre` and `wifi_status=streaming` with real CSI.

## [0.2.0] - 2026-11-16

### Added

- `firmware/bench/bench-smoke.yaml`: single-board boot, PSRAM, I2C scan, ADC
  and two-channel 5 kHz PWM self-test.
- `firmware/bench/bench-sim.yaml`: scripted illuminance/presence/motion inputs
  driving the real `lighting_controller` and PWM outputs.
- Bench README and single-board test records.

### Fixed

- Automatic light commands no longer trip the manual-override listener when
  `LightState` fires synchronous remote-value callbacks. Added
  `applying_auto_command_` guard in `LightingController`.

### Verified

- ESP32-S3 rev0.2, 16 MB flash, 8 MB PSRAM: `bench-smoke` passes; PSRAM
  8192 KB; I2C scan finds no devices; LEDC reports 5 kHz / 13 bit.
- `bench-sim`: auto-on, 300 lx hold, 500 lx delayed dimming, absence off and
  manual/auto recovery pass after the fix.

### Known limitations

- Only one bare board has been tested. LD2410, INA226, illuminance divider,
  MOSFET board, 24 V load and Home Assistant are not connected.
- Physical PWM waveform, sensor accuracy, RF performance, thermal rise and
  EMI remain unverified.

## [0.1.0] - 2026-11-16

### Added

- Project skeleton, GPL-3.0 license, upstream notice, privacy rules.
- `lighting_controller` ESPHome component with a pure C++ policy:
  - 1 s presence confirmation, 300 s absence timeout, 60 s CSI hold.
  - 250/350 lx dual-threshold hysteresis and 1 s fade.
  - 10% dimming steps after a 60 s high-lux delay.
  - manual override and sensor-fault hold.
- Host-side policy tests covering presence, absence, CSI hold, hysteresis,
  manual mode, sensor fault, invalid lux/NaN, optional CSI, and aux channel
  behavior.
- Sensor availability timeouts: illuminance 1 s, mmWave 5 s, INA226 10 s.
- ESPHome room package for ESP32-S3 with built-in `espectre`, LD2410, ADC
  illuminance, two INA226 sensors, two 5 kHz LEDC channels, and local buttons.
- Home Assistant package for energy integration, utility meters, cost estimate,
  and offline notification; Lovelace dashboard example.
- `esphome config` and `esphome compile` pass on ESPHome 2026.10.2 with
  ESP-IDF 5.5.6.
- Chinese defense pack: project overview, 40-question Q&A, and a 5-minute
  presentation outline.

### Known limitations

- No physical hardware has been connected yet; RF, sensor, and power
  measurements are not validated.
- Thresholds and calibration points are initial values and must be tuned on
  site.
