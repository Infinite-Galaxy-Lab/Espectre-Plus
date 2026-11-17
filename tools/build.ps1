# Build the example room firmware (no hardware required).
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
& $esphome compile $Room
if ($LASTEXITCODE -ne 0) { throw "Firmware build failed." }
