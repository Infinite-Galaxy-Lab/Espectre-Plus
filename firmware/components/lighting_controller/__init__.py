import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor, light, sensor, switch as switch_, text_sensor
from esphome.const import CONF_ID

AUTO_LOAD = ["binary_sensor", "light", "sensor", "switch", "text_sensor"]

CONF_ILLUMINANCE = "illuminance"
CONF_PRESENCE = "presence"
CONF_MOTION = "motion"
CONF_MAIN_LIGHT = "main_light"
CONF_AUX_LIGHT = "aux_light"
CONF_OCCUPANCY = "occupancy"
CONF_STATUS = "status"
CONF_AUTO_MODE_SWITCH = "auto_mode_switch"

CONF_LUX_ON = "lux_on"
CONF_LUX_OFF = "lux_off"
CONF_AUX_LUX_THRESHOLD = "aux_lux_threshold"
CONF_MAIN_MIN_BRIGHTNESS = "main_min_brightness"
CONF_MAIN_MAX_BRIGHTNESS = "main_max_brightness"
CONF_MAIN_FALLBACK_BRIGHTNESS = "main_fallback_brightness"
CONF_AUX_BRIGHTNESS = "aux_brightness"
CONF_PRESENCE_CONFIRM = "presence_confirm"
CONF_ABSENCE_TIMEOUT = "absence_timeout"
CONF_CSI_HOLD = "csi_hold"
CONF_LUX_REDUCE_DELAY = "lux_reduce_delay"
CONF_DIM_STEP_INTERVAL = "dim_step_interval"
CONF_DIM_STEP = "dim_step"
CONF_FADE = "fade"

espectre_plus_ns = cg.esphome_ns.namespace("espectre_plus")
LightingController = espectre_plus_ns.class_("LightingController", cg.Component)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(LightingController),
        cv.Required(CONF_ILLUMINANCE): cv.use_id(sensor.Sensor),
        cv.Optional(CONF_PRESENCE): cv.use_id(binary_sensor.BinarySensor),
        cv.Optional(CONF_MOTION): cv.use_id(binary_sensor.BinarySensor),
        cv.Required(CONF_MAIN_LIGHT): cv.use_id(light.LightState),
        cv.Required(CONF_AUX_LIGHT): cv.use_id(light.LightState),
        cv.Optional(CONF_OCCUPANCY): binary_sensor.binary_sensor_schema(),
        cv.Optional(CONF_STATUS): text_sensor.text_sensor_schema(),
        cv.Optional(CONF_AUTO_MODE_SWITCH): cv.use_id(switch_.Switch),
        cv.Optional(CONF_LUX_ON, default=250.0): cv.positive_float,
        cv.Optional(CONF_LUX_OFF, default=350.0): cv.positive_float,
        cv.Optional(CONF_AUX_LUX_THRESHOLD, default=80.0): cv.positive_float,
        cv.Optional(CONF_MAIN_MIN_BRIGHTNESS, default=0.20): cv.percentage,
        cv.Optional(CONF_MAIN_MAX_BRIGHTNESS, default=1.00): cv.percentage,
        cv.Optional(CONF_MAIN_FALLBACK_BRIGHTNESS, default=0.60): cv.percentage,
        cv.Optional(CONF_AUX_BRIGHTNESS, default=0.40): cv.percentage,
        cv.Optional(CONF_PRESENCE_CONFIRM, default="1s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_ABSENCE_TIMEOUT, default="300s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_CSI_HOLD, default="60s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_LUX_REDUCE_DELAY, default="60s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_DIM_STEP_INTERVAL, default="10s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_DIM_STEP, default=0.10): cv.percentage,
        cv.Optional(CONF_FADE, default="1s"): cv.positive_time_period_milliseconds,
    }
).extend(cv.COMPONENT_SCHEMA)


def _validate_config(config):
    if config[CONF_LUX_OFF] <= config[CONF_LUX_ON]:
        raise cv.Invalid(f"{CONF_LUX_OFF} must be greater than {CONF_LUX_ON}")
    if config[CONF_MAIN_MIN_BRIGHTNESS] > config[CONF_MAIN_MAX_BRIGHTNESS]:
        raise cv.Invalid(f"{CONF_MAIN_MIN_BRIGHTNESS} must not exceed {CONF_MAIN_MAX_BRIGHTNESS}")
    return config


CONFIG_SCHEMA = CONFIG_SCHEMA.add_extra(_validate_config)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    cg.add(var.set_illuminance_sensor(await cg.get_variable(config[CONF_ILLUMINANCE])))
    if CONF_PRESENCE in config:
        cg.add(var.set_presence_sensor(await cg.get_variable(config[CONF_PRESENCE])))
    if CONF_MOTION in config:
        cg.add(var.set_motion_sensor(await cg.get_variable(config[CONF_MOTION])))
    cg.add(var.set_main_light(await cg.get_variable(config[CONF_MAIN_LIGHT])))
    cg.add(var.set_aux_light(await cg.get_variable(config[CONF_AUX_LIGHT])))

    if CONF_OCCUPANCY in config:
        occupancy = await binary_sensor.new_binary_sensor(config[CONF_OCCUPANCY])
        cg.add(var.set_occupancy_sensor(occupancy))
    if CONF_STATUS in config:
        status = await text_sensor.new_text_sensor(config[CONF_STATUS])
        cg.add(var.set_status_sensor(status))
    if CONF_AUTO_MODE_SWITCH in config:
        cg.add(var.set_auto_mode_switch(await cg.get_variable(config[CONF_AUTO_MODE_SWITCH])))

    cg.add(var.set_lux_on(config[CONF_LUX_ON]))
    cg.add(var.set_lux_off(config[CONF_LUX_OFF]))
    cg.add(var.set_aux_lux_threshold(config[CONF_AUX_LUX_THRESHOLD]))
    cg.add(var.set_main_min_brightness(config[CONF_MAIN_MIN_BRIGHTNESS]))
    cg.add(var.set_main_max_brightness(config[CONF_MAIN_MAX_BRIGHTNESS]))
    cg.add(var.set_main_fallback_brightness(config[CONF_MAIN_FALLBACK_BRIGHTNESS]))
    cg.add(var.set_aux_brightness(config[CONF_AUX_BRIGHTNESS]))
    cg.add(var.set_presence_confirm_ms(config[CONF_PRESENCE_CONFIRM].total_milliseconds))
    cg.add(var.set_absence_timeout_ms(config[CONF_ABSENCE_TIMEOUT].total_milliseconds))
    cg.add(var.set_csi_hold_ms(config[CONF_CSI_HOLD].total_milliseconds))
    cg.add(var.set_lux_reduce_delay_ms(config[CONF_LUX_REDUCE_DELAY].total_milliseconds))
    cg.add(var.set_dim_step_interval_ms(config[CONF_DIM_STEP_INTERVAL].total_milliseconds))
    cg.add(var.set_dim_step(config[CONF_DIM_STEP]))
    cg.add(var.set_fade_ms(config[CONF_FADE].total_milliseconds))
