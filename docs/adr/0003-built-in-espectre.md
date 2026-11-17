# ADR-0003: Use the built-in ESPHome `espectre` component

- Status: accepted for v0.1
- Date: 2026-11-16

## Context

ESPectre has an ESPHome external component and, since ESPHome 2026.10, a
built-in `espectre` component. The external component exposes more runtime
controls but is deprecated and will be removed in ESPectre 3.3. The lighting
controller only needs the CSI motion binary sensor.

## Decision

Use the built-in `espectre` component with ESPHome 2026.10.2 for v0.1.

## Consequences

- No external component source is fetched at build time; the firmware builds
  entirely from the ESPHome release and this repository.
- `binary_sensor` platform `espectre` with `motion` provides the CSI motion
  signal used by `LightingController`.
- `sensor` platform `espectre` with `movement` and `diagnostics.csi_occupancy`
  provide tuning and diagnostic data.
- If later firmware needs threshold/select/switch runtime controls, evaluate
  the external component at tag 3.2.0 or ESPHome 2026.11+, as documented in
  `docs/upstream-integration.md`.

## Verification

`esphome config` and `esphome compile` pass with ESPHome 2026.10.2 and ESP-IDF
5.5.6 on 2026-11-16.
