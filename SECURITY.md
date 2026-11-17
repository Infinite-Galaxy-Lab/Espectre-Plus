# Security policy

## Reporting

Please report security issues privately to the maintainers rather than opening
a public issue with exploit details. If the repository has no private channel
configured yet, open a minimal public issue asking for a private contact.

## Secrets

- Never commit `firmware/rooms/secrets.yaml`, `.env`, API encryption keys (also used for OTA),
  Wi-Fi credentials, tokens, or personal network addresses.
- The repository contains only placeholder values in
  `firmware/rooms/secrets.example.yaml`.
- If a secret was committed, rotate it immediately and remove it from history;
  deleting the file in a later commit is not enough.

## Firmware exposure

- The ESPHome API uses an encryption key; do not expose the device directly to
  the public internet.
- OTA reuses the API encryption key in the example. Use a unique key per device.
- Home Assistant should be reached through a VPN or a properly secured remote
  access solution, not by port-forwarding the device API.

## Physical safety

The 24 V LED wiring is low-voltage but can still carry several amperes. Use a
fused supply, correct wire gauge, and a common ground between the ESP32 and the
MOSFET driver board. Do not work on energized wiring.
