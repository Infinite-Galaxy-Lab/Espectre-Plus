# Contributing

Thanks for improving ESPectre Plus.

## Before you start

- Read `docs/architecture.md` and `docs/requirements.md`.
- Do not commit `firmware/rooms/secrets.yaml`, `.venv/`, `.esphome/`, or any
  API key, token, Wi-Fi password, or personal address.
- This project is GPL-3.0. By contributing you agree that your contribution is
  licensed under GPL-3.0.

## Development workflow

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
Copy-Item firmware/rooms/secrets.example.yaml firmware/rooms/secrets.yaml
.\tools\validate.ps1
.\tools\build.ps1
```

- Keep the pure policy (`lighting_policy.*`) free of ESPHome headers.
- Add a host test for every behavior change in the policy.
- Keep YAML packages room-agnostic; room-specific values belong in
  `firmware/rooms/<room>.yaml`.
- Update the relevant documentation under `docs/` when behavior changes.

## Commit style

Use short, imperative summaries, for example:

- `feat(firmware): add lighting policy state machine`
- `fix(ha): correct utility meter source`
- `docs: record wiring and calibration steps`

## Pull requests

Include:

1. What changed and why.
2. How it was tested (`tools/test-host.ps1`, `esphome config`, `esphome compile`).
3. Any hardware-dependent behavior that could not be verified.
