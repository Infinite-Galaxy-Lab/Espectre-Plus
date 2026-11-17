// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ESPectre Plus contributors
//
// Host-side tests for the pure policy.

#include "lighting_policy.h"

#include <cmath>
#include <iostream>

using espectre_plus_policy::ControlMode;
using espectre_plus_policy::LightingPolicy;
using espectre_plus_policy::PolicyConfig;
using espectre_plus_policy::PolicyInputs;
using espectre_plus_policy::PolicyOutputs;

namespace {

int g_failures = 0;

void check(bool condition, const char *expression, int line) {
  if (!condition) {
    std::cerr << "FAIL line " << line << ": " << expression << "\n";
    ++g_failures;
  }
}

void check_near(float actual, float expected, float tolerance, const char *expression, int line) {
  if (std::fabs(actual - expected) > tolerance) {
    std::cerr << "FAIL line " << line << ": " << expression << " (actual=" << actual
              << ", expected=" << expected << ")\n";
    ++g_failures;
  }
}

#define CHECK(expr) check((expr), #expr, __LINE__)
#define CHECK_NEAR(actual, expected, tolerance) \
  check_near((actual), (expected), (tolerance), #actual " ~= " #expected, __LINE__)

PolicyInputs base_inputs() {
  PolicyInputs in;
  in.mmwave_configured = true;
  in.mmwave_valid = true;
  in.csi_configured = true;
  in.csi_valid = true;
  in.illuminance_valid = true;
  in.illuminance = 100.0f;
  in.auto_mode = true;
  return in;
}

void test_presence_confirmation() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 1000;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = true;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(!out.occupied);
  out = policy.update(in, 500);
  CHECK(!out.occupied);
  out = policy.update(in, 999);
  CHECK(!out.occupied);
  out = policy.update(in, 1000);
  CHECK(out.occupied);

  // A short dropout resets the confirmation window.
  LightingPolicy policy2;
  policy2.set_config(cfg);
  in.mmwave_present = true;
  policy2.update(in, 0);
  policy2.update(in, 500);
  in.mmwave_present = false;
  policy2.update(in, 600);
  in.mmwave_present = true;
  policy2.update(in, 700);
  out = policy2.update(in, 1400);
  CHECK(!out.occupied);
  out = policy2.update(in, 1700);
  CHECK(out.occupied);
}

void test_absence_timeout() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 0;
  cfg.absence_timeout_ms = 300000;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = true;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(out.occupied);

  // Keep presence alive until t=1000 so the absence window starts there.
  out = policy.update(in, 1000);
  CHECK(out.occupied);
  in.mmwave_present = false;
  out = policy.update(in, 1001);
  CHECK(out.occupied);
  out = policy.update(in, 300999);
  CHECK(out.occupied);
  out = policy.update(in, 301000);
  CHECK(!out.occupied);
}

void test_csi_hold_extends_presence() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 0;
  cfg.absence_timeout_ms = 100;
  cfg.csi_hold_ms = 5000;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = false;
  in.csi_motion = true;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(out.occupied);

  in.csi_motion = false;
  // CSI hold keeps raw presence true until 5000 ms.
  out = policy.update(in, 4000);
  CHECK(out.occupied);
  // The hold is still active at exactly 5000 ms.
  out = policy.update(in, 5000);
  CHECK(out.occupied);
  // After the hold expires, the 100 ms absence timeout applies.
  out = policy.update(in, 5050);
  CHECK(out.occupied);
  out = policy.update(in, 5150);
  CHECK(!out.occupied);
}

void test_lux_hysteresis_and_mapping() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 0;
  cfg.lux_on = 250.0f;
  cfg.lux_off = 350.0f;
  cfg.main_min_brightness = 0.2f;
  cfg.main_max_brightness = 1.0f;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = true;
  in.illuminance = 300.0f;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(out.occupied);
  CHECK(!out.main_on);  // in the stable band, never turned on

  in.illuminance = 240.0f;
  out = policy.update(in, 1000);
  CHECK(out.main_on);
  CHECK_NEAR(out.main_brightness, 0.232f, 0.01f);

  in.illuminance = 300.0f;
  out = policy.update(in, 2000);
  CHECK(out.main_on);  // hold in the hysteresis band
  CHECK_NEAR(out.main_brightness, 0.232f, 0.01f);

  in.illuminance = 400.0f;
  out = policy.update(in, 3000);
  CHECK(out.main_on);  // no immediate change
  out = policy.update(in, 63001);
  CHECK(out.main_on);
  CHECK(out.main_brightness < 0.232f);

  in.illuminance = 200.0f;
  out = policy.update(in, 64000);
  CHECK(out.main_on);
  CHECK_NEAR(out.main_brightness, 0.36f, 0.01f);
}

void test_aux_channel() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 0;
  cfg.aux_lux_threshold = 80.0f;
  cfg.aux_brightness = 0.4f;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = true;
  in.illuminance = 50.0f;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(out.aux_on);
  CHECK_NEAR(out.aux_brightness, 0.4f, 0.001f);

  in.illuminance = 100.0f;
  out = policy.update(in, 1000);
  CHECK(!out.aux_on);
  CHECK_NEAR(out.aux_brightness, 0.0f, 0.001f);
}

void test_manual_mode_holds_output() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 0;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = true;
  in.auto_mode = false;
  in.illuminance = 10.0f;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(out.occupied);
  CHECK(out.mode == ControlMode::MANUAL);
  CHECK(out.hold_output);
  CHECK(!out.main_on);
}

void test_sensor_fault_holds_output() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 0;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = true;
  in.illuminance = 10.0f;

  // A split-node deployment may have no CSI sensor. Its absence must not be
  // reported as a degraded sensor while the mmWave input is healthy.
  in.csi_configured = false;
  in.csi_valid = false;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(out.main_on);
  CHECK(!out.degraded);

  in.csi_configured = true;
  in.mmwave_valid = false;
  in.csi_valid = false;
  out = policy.update(in, 1000);
  CHECK(out.mode == ControlMode::SENSOR_FAULT);
  CHECK(out.hold_output);
  CHECK(out.degraded);
}

void test_invalid_lux_fallback() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 0;
  cfg.main_fallback_brightness = 0.6f;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = true;
  in.illuminance_valid = false;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(out.main_on);
  CHECK_NEAR(out.main_brightness, 0.6f, 0.001f);
  CHECK(out.degraded);

  // A NaN reading must take the same fallback path, not be treated as 0 lx.
  in.illuminance_valid = true;
  in.illuminance = std::nanf("");
  out = policy.update(in, 1000);
  CHECK(out.main_on);
  CHECK_NEAR(out.main_brightness, 0.6f, 0.001f);
  CHECK(out.degraded);
}

void test_absence_turns_lights_off() {
  LightingPolicy policy;
  PolicyConfig cfg;
  cfg.presence_confirm_ms = 0;
  cfg.absence_timeout_ms = 300000;
  policy.set_config(cfg);

  PolicyInputs in = base_inputs();
  in.mmwave_present = true;
  in.illuminance = 100.0f;
  PolicyOutputs out = policy.update(in, 0);
  CHECK(out.main_on);

  in.mmwave_present = false;
  out = policy.update(in, 299999);
  CHECK(out.main_on);  // still inside the absence window
  out = policy.update(in, 300000);
  CHECK(!out.occupied);
  CHECK(!out.main_on);
}

}  // namespace

int main() {
  test_presence_confirmation();
  test_absence_timeout();
  test_csi_hold_extends_presence();
  test_lux_hysteresis_and_mapping();
  test_aux_channel();
  test_manual_mode_holds_output();
  test_sensor_fault_holds_output();
  test_invalid_lux_fallback();
  test_absence_turns_lights_off();

  if (g_failures != 0) {
    std::cerr << g_failures << " test(s) failed\n";
    return 1;
  }
  std::cout << "All lighting policy tests passed\n";
  return 0;
}
