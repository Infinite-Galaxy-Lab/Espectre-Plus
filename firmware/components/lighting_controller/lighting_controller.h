// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ESPectre Plus contributors

#pragma once

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/light/light_state.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/core/component.h"
#include "esphome/core/log.h"

#include "lighting_policy.h"

namespace esphome {
namespace espectre_plus {
using ::espectre_plus_policy::ControlMode;
using ::espectre_plus_policy::LightingPolicy;
using ::espectre_plus_policy::PolicyConfig;
using ::espectre_plus_policy::PolicyInputs;
using ::espectre_plus_policy::PolicyOutputs;

class LightingController : public Component, public light::LightRemoteValuesListener {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void set_illuminance_sensor(sensor::Sensor *sensor) { illuminance_sensor_ = sensor; }
  void set_presence_sensor(binary_sensor::BinarySensor *sensor) { presence_sensor_ = sensor; }
  void set_motion_sensor(binary_sensor::BinarySensor *sensor) { motion_sensor_ = sensor; }
  void set_main_light(light::LightState *light) { main_light_ = light; }
  void set_aux_light(light::LightState *light) { aux_light_ = light; }
  void set_occupancy_sensor(binary_sensor::BinarySensor *sensor) { occupancy_sensor_ = sensor; }
  void set_status_sensor(text_sensor::TextSensor *sensor) { status_sensor_ = sensor; }
  void set_auto_mode_switch(switch_::Switch *sw) { auto_mode_switch_ = sw; }

  void set_lux_on(float value) { config_.lux_on = value; policy_.set_config(config_); }
  void set_lux_off(float value) { config_.lux_off = value; policy_.set_config(config_); }
  void set_aux_lux_threshold(float value) { config_.aux_lux_threshold = value; policy_.set_config(config_); }
  void set_main_min_brightness(float value) { config_.main_min_brightness = value; policy_.set_config(config_); }
  void set_main_max_brightness(float value) { config_.main_max_brightness = value; policy_.set_config(config_); }
  void set_main_fallback_brightness(float value) { config_.main_fallback_brightness = value; policy_.set_config(config_); }
  void set_aux_brightness(float value) { config_.aux_brightness = value; policy_.set_config(config_); }
  void set_presence_confirm_ms(uint32_t value) { config_.presence_confirm_ms = value; policy_.set_config(config_); }
  void set_absence_timeout_ms(uint32_t value) { config_.absence_timeout_ms = value; policy_.set_config(config_); }
  void set_csi_hold_ms(uint32_t value) { config_.csi_hold_ms = value; policy_.set_config(config_); }
  void set_lux_reduce_delay_ms(uint32_t value) { config_.lux_reduce_delay_ms = value; policy_.set_config(config_); }
  void set_dim_step_interval_ms(uint32_t value) { config_.dim_step_interval_ms = value; policy_.set_config(config_); }
  void set_dim_step(float value) { config_.dim_step = value; policy_.set_config(config_); }
  void set_fade_ms(uint32_t value) { config_.fade_ms = value; policy_.set_config(config_); }

  // Public actions used by YAML buttons and the HA mode switch.
  void set_auto_mode(bool auto_mode);
  bool is_auto_mode() const { return auto_mode_; }
  void toggle_main();
  void toggle_aux();
  void toggle_auto_mode();

  // LightState listener: detects user changes made through HA or the web UI.
  void on_light_remote_values_update() override;

 protected:
  void apply_outputs_(const PolicyOutputs &outputs);
  void publish_outputs_(const PolicyOutputs &outputs);
  void command_light_(light::LightState *light, bool on, float brightness);
  void set_manual_mode_();
  bool light_matches_(light::LightState *light, bool expected_on, float expected_brightness) const;

  sensor::Sensor *illuminance_sensor_{nullptr};
  binary_sensor::BinarySensor *presence_sensor_{nullptr};
  binary_sensor::BinarySensor *motion_sensor_{nullptr};
  light::LightState *main_light_{nullptr};
  light::LightState *aux_light_{nullptr};
  binary_sensor::BinarySensor *occupancy_sensor_{nullptr};
  text_sensor::TextSensor *status_sensor_{nullptr};
  switch_::Switch *auto_mode_switch_{nullptr};

  PolicyConfig config_{};
  LightingPolicy policy_{};
  PolicyOutputs last_outputs_{};

  bool auto_mode_{true};
  bool auto_mode_initialized_{false};
  uint32_t last_loop_ms_{0};
  uint32_t last_command_ms_{0};

  bool expected_main_on_{false};
  float expected_main_brightness_{0.0f};
  bool expected_aux_on_{false};
  float expected_aux_brightness_{0.0f};

  bool last_applied_main_on_{false};
  float last_applied_main_brightness_{0.0f};
  bool last_applied_aux_on_{false};
  float last_applied_aux_brightness_{0.0f};

  // Ignore callbacks caused by our own automatic commands.
  bool applying_auto_command_{false};

  bool last_published_occupied_{false};
  bool has_published_occupied_{false};
  std::string last_published_status_;
};

}  // namespace espectre_plus
}  // namespace esphome
