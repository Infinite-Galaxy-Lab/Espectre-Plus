# Host-side build/test helpers for ESPectre Plus.
param(
    [string]$BuildDir = "build-host"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root "firmware/components/lighting_controller"
$test = Join-Path $root "firmware/tests/test_lighting_policy.cpp"
$out = Join-Path $root $BuildDir
New-Item -ItemType Directory -Force -Path $out | Out-Null

$gxx = (Get-Command g++ -ErrorAction Stop).Source
& $gxx -std=c++17 -Wall -Wextra -Werror -O2 -I $src `
    $test (Join-Path $src "lighting_policy.cpp") `
    -o (Join-Path $out "test_lighting_policy.exe")
if ($LASTEXITCODE -ne 0) { throw "Host tests failed to compile." }
& (Join-Path $out "test_lighting_policy.exe")
if ($LASTEXITCODE -ne 0) { throw "Host tests failed." }
