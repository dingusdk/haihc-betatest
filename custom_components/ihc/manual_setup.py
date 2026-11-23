"""Handle manual setup of ihc resources as entities in Home Assistant."""

import logging
from pathlib import Path

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.binary_sensor import DEVICE_CLASSES_SCHEMA
from homeassistant.config import load_yaml_config_file
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_NAME, CONF_TYPE, CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BINARY_SENSOR,
    CONF_DIMMABLE,
    CONF_INVERTING,
    CONF_LIGHT,
    CONF_NOTE,
    CONF_OFF_ID,
    CONF_ON_ID,
    CONF_POSITION,
    CONF_SENSOR,
    CONF_SWITCH,
    DOMAIN,
    IHC_PLATFORMS,
    MANUAL_SETUP_YAML,
    PRODUCT_RESOURCES,
)

_LOGGER = logging.getLogger(__name__)


def validate_name(config: dict) -> dict:
    """Validate the device name."""
    if CONF_NAME in config:
        return config
    ihcid = config[CONF_ID]
    name = f"ihc_{ihcid}"
    config[CONF_NAME] = name
    return config


DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID): cv.positive_int,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_NOTE): cv.string,
        vol.Optional(CONF_POSITION): cv.string,
    }
)

SWITCH_SCHEMA = DEVICE_SCHEMA.extend(
    {
        vol.Optional(CONF_OFF_ID, default=0): cv.positive_int,
        vol.Optional(CONF_ON_ID, default=0): cv.positive_int,
    }
)

BINARY_SENSOR_SCHEMA = DEVICE_SCHEMA.extend(
    {
        vol.Optional(CONF_INVERTING, default=False): cv.boolean,
        vol.Optional(CONF_TYPE): DEVICE_CLASSES_SCHEMA,
    }
)

LIGHT_SCHEMA = DEVICE_SCHEMA.extend(
    {
        vol.Optional(CONF_DIMMABLE, default=False): cv.boolean,
        vol.Optional(CONF_OFF_ID, default=0): cv.positive_int,
        vol.Optional(CONF_ON_ID, default=0): cv.positive_int,
    }
)

SENSOR_SCHEMA = DEVICE_SCHEMA.extend(
    {vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string}
)


MANUAL_SETUP_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            vol.All(
                cv.ensure_list,
                [
                    vol.Schema(
                        {
                            vol.Required("controller"): cv.string,
                            vol.Optional(CONF_BINARY_SENSOR, default=[]): vol.All(
                                cv.ensure_list,
                                [vol.All(BINARY_SENSOR_SCHEMA, validate_name)],
                            ),
                            vol.Optional(CONF_LIGHT, default=[]): vol.All(
                                cv.ensure_list, [vol.All(LIGHT_SCHEMA, validate_name)]
                            ),
                            vol.Optional(CONF_SENSOR, default=[]): vol.All(
                                cv.ensure_list, [vol.All(SENSOR_SCHEMA, validate_name)]
                            ),
                            vol.Optional(CONF_SWITCH, default=[]): vol.All(
                                cv.ensure_list, [vol.All(SWITCH_SCHEMA, validate_name)]
                            ),
                        }
                    )
                ],
            )
        )
    }
)


def remove_auto_setup_duplicates(
    hass: HomeAssistant, entry: ConfigEntry, controller_conf: dict
) -> None:
    """
    Remove auto setup devices that are also configured manually.

    Manual configuration overrides auto setup, so we remove any auto setup
    device using the same ihc resource id as a manually configured device,
    to avoid duplicate entities for the same resource.
    """
    manual_ids = {
        device_cfg[CONF_ID]
        for platform in IHC_PLATFORMS
        for device_cfg in controller_conf.get(platform, [])
    }
    controller_data = hass.data[DOMAIN][entry.entry_id]
    for platform in IHC_PLATFORMS:
        platform_data = controller_data.get(platform, {})
        for name in [
            name
            for name, device in platform_data.items()
            if device["ihc_id"] in manual_ids
        ]:
            _LOGGER.debug(
                "Manual configuration overrides auto setup for ihc id %s (%s)",
                platform_data[name]["ihc_id"],
                name,
            )
            del platform_data[name]


def warn_duplicate_ids(platform_setup: list, platform: str) -> None:
    """Warn about duplicate ihc ids in the manual configuration."""
    seen_ids: set[int] = set()
    for sensor_cfg in platform_setup:
        if sensor_cfg[CONF_ID] in seen_ids:
            _LOGGER.warning(
                "Duplicate ihc id %s in the manual %s configuration (%s). "
                "Only the first entity will be created",
                sensor_cfg[CONF_ID],
                platform,
                sensor_cfg[CONF_NAME],
            )
        seen_ids.add(sensor_cfg[CONF_ID])


def manual_setup(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Manual setup of IHC devices."""
    yaml_path = hass.config.path(MANUAL_SETUP_YAML)
    if not Path(yaml_path).is_file():
        return
    yaml = load_yaml_config_file(yaml_path)
    try:
        ihc_conf = MANUAL_SETUP_SCHEMA(yaml)[DOMAIN]
    except vol.Invalid:
        _LOGGER.exception("Invalid IHC manual setup data")
        return
    if entry.unique_id is None:
        msg = "Entry unique_id cannot be None"
        raise ValueError(msg)
    controller_id: str = entry.unique_id
    # Find the controller config for this controller
    controller_conf = None
    for conf in ihc_conf:
        if conf["controller"] == controller_id:
            controller_conf = conf
            break
    if controller_conf is None:
        return
    remove_auto_setup_duplicates(hass, entry, controller_conf)
    product_resources = hass.data[DOMAIN][entry.entry_id].get(PRODUCT_RESOURCES, {})
    # Get manual configuration for IHC devices
    for platform in IHC_PLATFORMS:
        discovery_info = {}
        if platform in controller_conf:
            platform_setup = controller_conf.get(platform, {})
            warn_duplicate_ids(platform_setup, platform)
            for sensor_cfg in platform_setup:
                name = sensor_cfg[CONF_NAME]
                # A resource that belongs to a product in the project (like a
                # button on a wireless push button) goes on that product's
                # device. The entity keeps the name from the configuration.
                product = product_resources.get(sensor_cfg[CONF_ID]) or {
                    "name": name,
                    "note": sensor_cfg.get(CONF_NOTE) or "",
                    "position": sensor_cfg.get(CONF_POSITION) or "",
                }
                device = {
                    "ihc_id": sensor_cfg[CONF_ID],
                    "ctrl_id": controller_id,
                    "product": product,
                    "product_cfg": {
                        "type": sensor_cfg.get(CONF_TYPE),
                        "inverting": sensor_cfg.get(CONF_INVERTING),
                        "off_id": sensor_cfg.get(CONF_OFF_ID),
                        "on_id": sensor_cfg.get(CONF_ON_ID),
                        "dimmable": sensor_cfg.get(CONF_DIMMABLE),
                        "unit_of_measurement": sensor_cfg.get(CONF_UNIT_OF_MEASUREMENT),
                    },
                }
                discovery_info[name] = device
        if discovery_info:
            if platform in hass.data[DOMAIN][entry.entry_id]:
                hass.data[DOMAIN][entry.entry_id][platform].update(discovery_info)
            else:
                hass.data[DOMAIN][entry.entry_id][platform] = discovery_info
