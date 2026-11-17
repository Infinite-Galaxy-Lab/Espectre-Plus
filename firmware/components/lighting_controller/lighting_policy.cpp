// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ESPectre Plus contributors

#include "lighting_policy.h"

#include <algorithm>
#include <cmath>

namespace espectre_plus_policy {

void LightingPolicy::set_config(const PolicyConfig &config) { config_ = config; }

void LightingPolicy::reset(uint32_t now_ms) {
  initialized_ = true;
  occupied_ = false;
  presence_candidate_ = false;
  presence_since_ms_ = now_ms;
  last_present_ms_ = now_ms;
  last_csi_ms_ = now_ms;
  csi_seen_ = false;
  csi_hold_active_ = false;

  lux_high_ = false;
  lux_high_since_ms_ = now_ms;
  last_dim_ms_ = now_ms;
  dim_scale_ = 1.0f;
  base_brightness_ = 0.0f;

  last_main_on_ = false;
  last_main_brightness_ = 0.0f;
  last_aux_on_ = false;
  last_aux_brightness_ = 0.0f;
  mode_ = ControlMode::AUTO;
}

bool LightingPolicy::elapsed(uint32_t now_ms, uint32_t since_ms, uint32_t interval_ms) {
  if (interval_ms == 0) {
    return true;
  }
  return static_cast<uint32_t>(now_ms - since_ms) >= interval_ms;
}

float LightingPolicy::clamp01(float value) { return clampf(value, 0.0f, 1.0f); }

float LightingPolicy::clampf(float value, float low, float high) {
  return std::max(low, std::min(value, high));
}

PolicyOutputs LightingPolicy::update(const PolicyInputs &inputs, uint32_t now_ms) {
  if (!initialized_) {
    reset(now_ms);
  }

  // Keep CSI motion alive for csi_hold_ms.
  if (inputs.csi_valid && inputs.csi_motion) {
    last_csi_ms_ = now_ms;
    csi_seen_ = true;
  }
  csi_hold_active_ = inputs.csi_valid && csi_seen_ && static_cast<uint32_t>(now_ms - last_csi_ms_) <= config_.csi_hold_ms;

  const bool raw_present = (inputs.mmwave_valid && inputs.mmwave_present) || csi_hold_active_;
  const bool presence_available =
      (inputs.mmwave_configured && inputs.mmwave_valid) || (inputs.csi_configured && inputs.csi_valid);

  if (presence_available) {
    if (raw_present) {
      if (!occupied_) {
        if (!presence_candidate_) {
          presence_candidate_ = true;
          presence_since_ms_ = now_ms;
        }
        if (elapsed(now_ms, presence_since_ms_, config_.presence_confirm_ms)) {
          occupied_ = true;
          presence_candidate_ = false;
        }
      }
      last_present_ms_ = now_ms;
    } else {
      presence_candidate_ = false;
      if (occupied_ && elapsed(now_ms, last_present_ms_, config_.absence_timeout_ms)) {
        occupied_ = false;
      }
    }
  }

  const bool illuminance_valid = inputs.illuminance_valid && std::isfinite(inputs.illuminance);

  PolicyOutputs out;
  out.occupied = occupied_;
  out.degraded = (inputs.mmwave_configured && !inputs.mmwave_valid) ||
                 (inputs.csi_configured && !inputs.csi_valid) || !illuminance_valid;

  // Hold outputs when no presence input is usable.
  if (!presence_available) {
    mode_ = ControlMode::SENSOR_FAULT;
    out.mode = mode_;
    out.hold_output = true;
    return out;
  }

  // Track presence, but do not command lights in manual mode.
  if (!inputs.auto_mode) {
    mode_ = ControlMode::MANUAL;
    out.mode = mode_;
    out.hold_output = true;
    return out;
  }

  mode_ = ControlMode::AUTO;
  out.mode = mode_;

  if (!occupied_) {
    dim_scale_ = 1.0f;
    lux_high_ = false;
    base_brightness_ = 0.0f;
    last_main_on_ = false;
    last_main_brightness_ = 0.0f;
    last_aux_on_ = false;
    last_aux_brightness_ = 0.0f;
  } else if (!illuminance_valid) {
    // Missing lux: use a safe output and report degraded.
    dim_scale_ = 1.0f;
    lux_high_ = false;
    last_main_on_ = true;
    last_main_brightness_ = config_.main_fallback_brightness;
    last_aux_on_ = false;
    last_aux_brightness_ = 0.0f;
  } else {
    const float lux = std::max(0.0f, inputs.illuminance);

    if (lux < config_.lux_on) {
      lux_high_ = false;
      dim_scale_ = 1.0f;

      const float span = std::max(1.0f, config_.lux_on);
      const float deficit = clamp01((config_.lux_on - lux) / span);
      const float target =
          config_.main_min_brightness + deficit * (config_.main_max_brightness - config_.main_min_brightness);
      base_brightness_ = target;

      last_main_on_ = target > 0.01f;
      last_main_brightness_ = target;
      last_aux_on_ = lux < config_.aux_lux_threshold;
      last_aux_brightness_ = last_aux_on_ ? config_.aux_brightness : 0.0f;
    } else if (lux > config_.lux_off) {
      if (!lux_high_) {
        lux_high_ = true;
        lux_high_since_ms_ = now_ms;
        last_dim_ms_ = now_ms;
      }

      if (elapsed(now_ms, lux_high_since_ms_, config_.lux_reduce_delay_ms)) {
        if (elapsed(now_ms, last_dim_ms_, config_.dim_step_interval_ms)) {
          dim_scale_ = clamp01(dim_scale_ - config_.dim_step);
          last_dim_ms_ = now_ms;
        }

        if (dim_scale_ <= 0.001f) {
          last_main_on_ = false;
          last_main_brightness_ = 0.0f;
          last_aux_on_ = false;
          last_aux_brightness_ = 0.0f;
        } else {
          const float target = base_brightness_ * dim_scale_;
          last_main_on_ = target > 0.01f;
          last_main_brightness_ = target;
          last_aux_on_ = false;
          last_aux_brightness_ = 0.0f;
        }
      }
    } else {
      // Hysteresis band: keep the current output.
      lux_high_ = false;
    }
  }

  out.main_on = last_main_on_;
  out.main_brightness = last_main_brightness_;
  out.aux_on = last_aux_on_;
  out.aux_brightness = last_aux_brightness_;
  return out;
}

}  // namespace espectre_plus_policy
