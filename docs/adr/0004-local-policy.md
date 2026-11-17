# ADR-0004: Keep the control policy on the device

- Status: accepted
- Date: 2026-11-16

## Context

Lighting decisions could run in Home Assistant automations or on the ESP32.
The report requires basic lighting to keep working when the network or platform
is unavailable, and the thresholds need to be testable.

## Decision

Implement the decision logic as a pure C++ state machine on the ESP32. Home
Assistant only provides remote controls, cross-room scenes, and reporting.

## Consequences

- Basic automatic lighting and local buttons survive a Home Assistant or
  internet outage.
- The same behavior is covered by host-side unit tests without hardware.
- HA automations must not duplicate the device policy; they should only send
  explicit user intent or coordinate multiple rooms.
- Changing a threshold requires a firmware rebuild (v0.1). Runtime tuning can
  be added later with number entities.
