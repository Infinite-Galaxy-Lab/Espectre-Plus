// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ESPectre Plus contributors

#include "lighting_controller.h"

#include <algorithm>
#include <cmath>
#include <string>

namespace esphome {
namespace espectre_plus {

static const char *const TAG = "espectre_plus.lighting";

namespace {
float clamp01(float value) { return std::max(0.0f, std::min(value, 1.0f)); }
}  // namespace

void LightingController::setup() {
  policy_.set_config(config_);
  policy_.reset(millis());

  if (main_light_ != nullptr) {
    main_light_->add_remote_values_listener(this);
  }
  if (aux_light_ != nullptr) {
    aux_light_->add_remote_values_listener(this);
  }

  // The actual mode is read from the restored switch state on the first loop.
  auto_mode_ = true;
  auto_mode_initialized_ = false;
  last_command_ms_ = millis();
  ESP_LOGCONFIG(TAG, "Lighting controller initialized");
}

void LightingController::loop() {
  const uint32_t now = millis();

  if (!auto_mode_initialized_) {
    if (auto_mode_switch_ != nullptr) {
      auto_mode_ = auto_mode_switch_->state;
    }
    auto_mode_initialized_ = true;
  }

  if (last_loop_ms_ != 0 && static_cast<uint32_t>(now - last_loop_ms_) < 500) {
    return;
  }
  last_loop_ms_ = now;

  PolicyInputs inputs;
  if (illuminance_sensor_ != nullptr) {
    const bool valid = illuminance_sensor_->has_state() && std::isfinite(illuminance_sensor_->state);
    inputs.illuminance_valid = valid;
    inputs.illuminance = valid ? illuminance_sensor_->state : 0.0f;
  }
  if (presence_sensor_ != nullptr) {
    inputs.mmwave_configured = true;
    inputs.mmwave_valid = presence_sensor_->has_state();
    inputs.mmwave_present = inputs.mmwave_valid && presence_sensor_->state;
  }
  if (motion_sensor_ != nullptr) {
    inputs.csi_configured = true;
    inputs.csi_valid = motion_sensor_->has_state();
    inputs.csi_motion = inputs.csi_valid && motion_sensor_->state;
  }
  inputs.auto_mode = auto_mode_;

  last_outputs_ = policy_.update(inputs, now);

  if (last_outputs_.mode == ControlMode::AUTO && !last_outputs_.hold_output) {
    apply_outputs_(last_outputs_);
  }
  publish_outputs_(last_outputs_);
}

void LightingController::apply_outputs_(const PolicyOutputs &outputs) {
  const bool main_changed =
      outputs.main_on != last_applied_main_on_ ||
      (outputs.main_on && std::fabs(outputs.main_brightness - last_applied_main_brightness_) > 0.01f);
  const bool aux_changed =
      outputs.aux_on != last_applied_aux_on_ ||
      (outputs.aux_on && std::fabs(outputs.aux_brightness - last_applied_aux_brightness_) > 0.01f);

  // Set both targets before calling perform().
  if (main_changed) {
    expected_main_on_ = outputs.main_on;
    expected_main_brightness_ = outputs.main_brightness;
  }
  if (aux_changed) {
    expected_aux_on_ = outputs.aux_on;
    expected_aux_brightness_ = outputs.aux_brightness;
  }

  // Ignore callbacks until both channels have been commanded.
  applying_auto_command_ = true;
  if (main_changed) {
    command_light_(main_light_, outputs.main_on, outputs.main_brightness);
    last_applied_main_on_ = outputs.main_on;
    last_applied_main_brightness_ = outputs.main_brightness;
  }
  if (aux_changed) {
    command_light_(aux_light_, outputs.aux_on, outputs.aux_brightness);
    last_applied_aux_on_ = outputs.aux_on;
    last_applied_aux_brightness_ = outputs.aux_brightness;
  }
  applying_auto_command_ = false;
}

void LightingController::command_light_(light::LightState *light, bool on, float brightness) {
  if (light == nullptr) {
    return;
  }
  last_command_ms_ = millis();
  auto call = light->make_call();
  call.set_state(on);
  if (on) {
    call.set_brightness(clamp01(brightness));
  }
  call.set_transition_length(config_.fade_ms);
  call.perform();
}

void LightingController::publish_outputs_(const PolicyOutputs &outputs) {
  if (occupancy_sensor_ != nullptr) {
    if (!has_published_occupied_ || outputs.occupied != last_published_occupied_) {
      occupancy_sensor_->publish_state(outputs.occupied);
      last_published_occupied_ = outputs.occupied;
      has_published_occupied_ = true;
    }
  }

  if (status_sensor_ != nullptr) {
    std::string status;
    if (outputs.mode == ControlMode::SENSOR_FAULT) {
      status = "sensor_fault";
    } else if (outputs.mode == ControlMode::MANUAL) {
      status = "manual";
    } else if (outputs.degraded) {
      status = "auto_degraded";
    } else {
      status = "auto";
    }
    if (status != last_published_status_) {
      status_sensor_->publish_state(status);
      last_published_status_ = status;
    }
  }
}

void LightingController::set_auto_mode(bool auto_mode) {
  if (auto_mode_ == auto_mode) {
    return;
  }
  auto_mode_ = auto_mode;
  if (auto_mode_switch_ != nullptr && auto_mode_switch_->state != auto_mode) {
    auto_mode_switch_->publish_state(auto_mode);
  }

  // Force the next automatic decision to apply after manual mode.
  last_applied_main_on_ = false;
  last_applied_main_brightness_ = 0.0f;
  last_applied_aux_on_ = false;
  last_applied_aux_brightness_ = 0.0f;
  last_command_ms_ = millis();
  ESP_LOGI(TAG, "Mode changed to %s", auto_mode ? "auto" : "manual");
}

void LightingController::set_manual_mode_() {
  if (!auto_mode_) {
    return;
  }
  ESP_LOGW(TAG, "Manual light change detected, switching to manual mode");
  set_auto_mode(false);
}

void LightingController::toggle_main() {
  if (auto_mode_) {
    set_auto_mode(false);
  }
  if (main_light_ == nullptr) {
    return;
  }
  const bool on = main_light_->remote_values.is_on();
  const bool target_on = !on;
  const float target_brightness = target_on ? 0.8f : 0.0f;
  expected_main_on_ = target_on;
  expected_main_brightness_ = target_brightness;
  last_command_ms_ = millis();
  command_light_(main_light_, target_on, target_brightness);
  last_applied_main_on_ = target_on;
  last_applied_main_brightness_ = target_brightness;
}

void LightingController::toggle_aux() {
  if (auto_mode_) {
    set_auto_mode(false);
  }
  if (aux_light_ == nullptr) {
    return;
  }
  const bool on = aux_light_->remote_values.is_on();
  const bool target_on = !on;
  const float target_brightness = target_on ? 0.4f : 0.0f;
  expected_aux_on_ = target_on;
  expected_aux_brightness_ = target_brightness;
  last_command_ms_ = millis();
  command_light_(aux_light_, target_on, target_brightness);
  last_applied_aux_on_ = target_on;
  last_applied_aux_brightness_ = target_brightness;
}

void LightingController::toggle_auto_mode() { set_auto_mode(!auto_mode_); }

bool LightingController::light_matches_(light::LightState *light, bool expected_on,
                                        float expected_brightness) const {
  if (light == nullptr) {
    return true;
  }
  if (light->remote_values.is_on() != expected_on) {
    return false;
  }
  if (!expected_on) {
    return true;
  }
  return std::fabs(light->remote_values.get_brightness() - expected_brightness) <= 0.03f;
}

void LightingController::on_light_remote_values_update() {
  if (!auto_mode_ || applying_auto_command_) {
    return;
  }
  const uint32_t now = millis();
  if (last_command_ms_ != 0 && static_cast<uint32_t>(now - last_command_ms_) < 1500 &&
      light_matches_(main_light_, expected_main_on_, expected_main_brightness_) &&
      light_matches_(aux_light_, expected_aux_on_, expected_aux_brightness_)) {
    return;
  }
  set_manual_mode_();
}

void LightingController::dump_config() {
  ESP_LOGCONFIG(TAG, "ESPectre Plus lighting controller:");
  ESP_LOGCONFIG(TAG, "  Lux on: %.1f lx", config_.lux_on);
  ESP_LOGCONFIG(TAG, "  Lux off: %.1f lx", config_.lux_off);
  ESP_LOGCONFIG(TAG, "  Aux lux threshold: %.1f lx", config_.aux_lux_threshold);
  ESP_LOGCONFIG(TAG, "  Presence confirm: %u ms", config_.presence_confirm_ms);
  ESP_LOGCONFIG(TAG, "  Absence timeout: %u ms", config_.absence_timeout_ms);
  ESP_LOGCONFIG(TAG, "  CSI hold: %u ms", config_.csi_hold_ms);
  ESP_LOGCONFIG(TAG, "  Fade: %u ms", config_.fade_ms);
}

}  // namespace espectre_plus
}  // namespace esphome
