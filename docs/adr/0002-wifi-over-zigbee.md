# ADR-0002: Wi-Fi over ZigBee for the lighting transport

- Status: accepted
- Date: 2026-11-16

## Context

The report compares Wi-Fi and ZigBee for a whole-home lighting system. The
existing ESPectre node and Home Assistant already use Wi-Fi. Lighting traffic is
small (commands, occupancy, 5 s power samples), but the system needs multi-room
coverage and local fallback.

## Decision

Use Wi-Fi + ESPHome Native API. Do not add a ZigBee coordinator in the first
version.

## Rationale

- Existing router, ESP32-S3 boards, and Home Assistant integration are reused.
- ESP32-S3 Wi-Fi 4 theoretical rate is 150 Mbit/s; lighting traffic is far
  below that.
- Nodes have fixed power, so Wi-Fi's higher idle power is acceptable.
- A battery-powered sensor would favor ZigBee; that is explicitly a future
  option, not the current requirement.

## Consequences

- Wi-Fi coverage must be verified room by room; add an access point or Ethernet
  backhaul where needed.
- The firmware disables Wi-Fi power save to keep CSI measurements stable.
- Local control does not depend on the internet or Home Assistant; only remote
  control and reporting do.
