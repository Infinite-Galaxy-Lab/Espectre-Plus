# ADR-0001: Use ESPHome instead of a bare ESP-IDF application

- Status: accepted
- Date: 2026-11-16

## Context

The project needs Wi-Fi provisioning, OTA, Home Assistant discovery, sensor
drivers, PWM outputs, and a maintainable configuration per room. ESPectre ships
an ESPHome component and a native SDK. A bare ESP-IDF application would give
more control but would also require reimplementing networking, provisioning,
entity publishing, and OTA.

## Decision

Use ESPHome 2026.10+ with the ESP-IDF framework as the firmware foundation.

## Consequences

- Fast path to Home Assistant entities and OTA.
- YAML packages make multi-room copies cheap.
- The pure control policy remains C++ and is not tied to ESPHome, so it can be
  reused by a future native frontend.
- ESPHome firmware is GPL-3.0; this project is GPL-3.0 as well.
