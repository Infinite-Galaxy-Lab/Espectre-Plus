# Validate ESPHome YAML and run host-side tests.
param(
    [string]$Room = "firmware/rooms/example-room.yaml"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$esphome = Join-Path $root ".venv/Scripts/esphome.exe"
if (-not (Test-Path $esphome)) {
    throw "ESPHome not found at $esphome. Create .venv and install requirements first."
}

Write-Host "==> esphome config $Room"
& $esphome config $Room
if ($LASTEXITCODE -ne 0) { throw "ESPHome config validation failed." }

Write-Host "==> host tests"
& (Join-Path $root "tools/test-host.ps1")
if ($LASTEXITCODE -ne 0) { throw "Host tests failed." }

Write-Host "==> simulator syntax"
$python = Join-Path $root ".venv/Scripts/python.exe"
& $python -m py_compile simulator/server.py simulator/mock_room.py simulator/wifi.py simulator/csi_http.py simulator/fake_csi_device.py
if ($LASTEXITCODE -ne 0) { throw "Simulator syntax check failed." }

Write-Host "==> simulator tests"
& $python -m unittest discover -s simulator/tests
if ($LASTEXITCODE -ne 0) { throw "Simulator tests failed." }

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    Write-Host "==> frontend syntax"
    & $node.Source --check simulator/frontend/app.js
    if ($LASTEXITCODE -ne 0) { throw "Frontend syntax check failed." }
}
if ($LASTEXITCODE -ne 0) { throw "Simulator syntax check failed." }
