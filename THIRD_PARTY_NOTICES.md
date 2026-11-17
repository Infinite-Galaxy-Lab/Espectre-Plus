# Third-party notices

ESPectre Plus is a GPL-3.0 application built on the ESPectre project and the
ESPHome firmware framework. This file records the upstream projects and the
license terms that apply when the firmware is distributed.

## ESPectre

- Project: ESPectre
- Upstream: https://github.com/francescopace/espectre
- Reference used during development: commit `062863f0625c0055a0add9680ebb9d0dbc48b195` (main, 2026-11-12); release tag `3.2.0`.
- License: GPL-3.0-only for first-party code and the ESPHome frontend. The
  commercial license offered by upstream does not cover the ESPHome frontend.
- Use in this project: the ESPHome built-in `espectre` component (ESPHome
  2026.10+) provides Wi-Fi CSI sensing. The small `espectre_direct` ESPHome
  adapter from the upstream repository is vendored at
  `firmware/components/espectre_direct/` under GPL-3.0-only to expose the raw
  CSI endpoint. The full upstream repository is otherwise kept locally as a
  development reference and excluded by `.gitignore`.

If you distribute a firmware image built from this repository, the whole
combined work is distributed under GPL-3.0. You must provide the complete
corresponding source, including this repository's `firmware/` directory,
custom components, YAML packages, and build scripts. The upstream GPL text is
in `LICENSE`; the upstream project's own notices are in its repository.

## ESPHome

- Project: ESPHome
- Upstream: https://github.com/esphome/esphome
- License: GPL-3.0 for the C++ runtime; MIT for the Python build tooling.
- Use in this project: firmware framework and ESP32-S3 toolchain integration.

## ESP-IDF

- Project: Espressif IoT Development Framework
- Upstream: https://github.com/espressif/esp-idf
- License: Apache-2.0 with bundled permissive third-party components.
- Use in this project: downloaded by ESPHome at build time; not vendored.

## Home Assistant

- Project: Home Assistant
- Upstream: https://www.home-assistant.io/
- License: Apache-2.0.
- Use in this project: optional dashboard/package YAML in `homeassistant/`.
  These YAML files are configuration examples, not a fork of Home Assistant.

## Hardware datasheets and trademarks

ESP32, ESP32-S3, ESP-IDF, and ESPHome are trademarks or products of their
respective owners. INA226 is a product of Texas Instruments. LD2410 is a
product of Hi-Link. This project is not endorsed by any of these vendors.
