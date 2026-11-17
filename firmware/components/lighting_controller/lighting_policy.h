// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ESPectre Plus contributors
//
// Pure control policy; no ESPHome dependencies, host-testable.

#pragma once

#include <cstdint>

namespace espectre_plus_policy {

enum class ControlMode : uint8_t {
  AUTO = 0,
  MANUAL = 1,
  SENSOR_FAULT = 2,
};

struct PolicyConfig {
  float lux_on{250.0f};
  float lux_off{350.0f};
  float aux_lux_threshold{80.0f};
  float main_min_brightness{0.20f};
  float main_max_brightness{1.00f};
  float main_fallback_brightness{0.60f};
  float aux_brightness{0.40f};

  uint32_t presence_confirm_ms{1000};
  uint32_t absence_timeout_ms{300000};
  uint32_t csi_hold_ms{60000};
  uint32_t lux_reduce_delay_ms{60000};
  uint32_t dim_step_interval_ms{10000};
  float dim_step{0.10f};
  uint32_t fade_ms{1000};
};

struct PolicyInputs {
  bool mmwave_configured{false};
  bool mmwave_present{false};
  bool mmwave_valid{false};
  bool csi_configured{false};
  bool csi_motion{false};
  bool csi_valid{false};
  float illuminance{0.0f};
  bool illuminance_valid{false};
  bool auto_mode{true};
};

struct PolicyOutputs {
  bool occupied{false};
  ControlMode mode{ControlMode::AUTO};
  bool main_on{false};
  float main_brightness{0.0f};
  bool aux_on{false};
  float aux_brightness{0.0f};
  bool degraded{false};
  bool hold_output{false};
};

class LightingPolicy {
 public:
  void set_config(const PolicyConfig &config);
  const PolicyConfig &config() const { return config_; }

  void reset(uint32_t now_ms);
  PolicyOutputs update(const PolicyInputs &inputs, uint32_t now_ms);

  bool occupied() const { return occupied_; }
  ControlMode mode() const { return mode_; }

 private:
  static bool elapsed(uint32_t now_ms, uint32_t since_ms, uint32_t interval_ms);
  static float clamp01(float value);
  static float clampf(float value, float low, float high);

  PolicyConfig config_{};
  bool initialized_{false};
  bool occupied_{false};
  bool presence_candidate_{false};
  uint32_t presence_since_ms_{0};
  uint32_t last_present_ms_{0};
  uint32_t last_csi_ms_{0};
  bool csi_seen_{false};
  bool csi_hold_active_{false};

  bool lux_high_{false};
  uint32_t lux_high_since_ms_{0};
  uint32_t last_dim_ms_{0};
  float dim_scale_{1.0f};
  float base_brightness_{0.0f};

  bool last_main_on_{false};
  float last_main_brightness_{0.0f};
  bool last_aux_on_{false};
  float last_aux_brightness_{0.0f};

  ControlMode mode_{ControlMode::AUTO};
};

}  // namespace espectre_plus_policy
