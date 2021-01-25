"""Support for IHC devices."""
import asyncio
import logging
import os.path
import yaml

from defusedxml import ElementTree
from ihcsdk.ihccontroller import IHCController
import voluptuous as vol

from homeassistant.components.binary_sensor import DEVICE_CLASSES_SCHEMA
from homeassistant.config import load_yaml_config_file
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ID,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TYPE,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_URL,
    CONF_USERNAME,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import HomeAssistantType

from .const import (
    ATTR_CONTROLLER_ID,
    ATTR_IHC_ID,
    ATTR_VALUE,
    CONF_AUTOSETUP,
    CONF_BINARY_SENSOR,
    CONF_DIMMABLE,
    CONF_INFO,
    CONF_INVERTING,
    CONF_LIGHT,
    CONF_NODE,
    CONF_NOTE,
    CONF_OFF_ID,
    CONF_ON_ID,
    CONF_POSITION,
    CONF_SENSOR,
    CONF_SWITCH,
    CONF_XPATH,
    SERVICE_PULSE,
    SERVICE_SET_RUNTIME_VALUE_BOOL,
    SERVICE_SET_RUNTIME_VALUE_FLOAT,
    SERVICE_SET_RUNTIME_VALUE_INT,
)
from .util import async_pulse, async_set_bool, async_set_int, async_set_float

_LOGGER = logging.getLogger(__name__)

AUTO_SETUP_YAML = "ihc_auto_setup.yaml"
MANUAL_SETUP_YAML = "ihc_manual_setup.yaml"
DOMAIN = "ihc"

IHC_CONTROLLER = "controller"
IHC_INFO = "info"
IHC_PLATFORMS = ("binary_sensor", "light", "sensor", "switch")


def validate_name(config):
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
    {vol.Optional(CONF_UNIT_OF_MEASUREMENT, default=TEMP_CELSIUS): cv.string}
)

IHC_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_URL): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_AUTOSETUP, default=True): cv.boolean,
        vol.Optional(CONF_BINARY_SENSOR, default=[]): vol.All(
            cv.ensure_list, [vol.All(BINARY_SENSOR_SCHEMA, validate_name)]
        ),
        vol.Optional(CONF_INFO, default=True): cv.boolean,
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

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(vol.All(cv.ensure_list, [IHC_SCHEMA]))}, extra=vol.ALLOW_EXTRA
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
                            vol.Optional(CONF_INFO, default=True): cv.boolean,
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


AUTO_SETUP_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_BINARY_SENSOR, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.All(
                    {
                        vol.Required(CONF_NODE): cv.string,
                        vol.Required(CONF_XPATH): cv.string,
                        vol.Optional(CONF_INVERTING, default=False): cv.boolean,
                        vol.Optional(CONF_TYPE): cv.string,
                    }
                )
            ],
        ),
        vol.Optional(CONF_LIGHT, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.All(
                    {
                        vol.Required(CONF_NODE): cv.string,
                        vol.Required(CONF_XPATH): cv.string,
                        vol.Optional(CONF_DIMMABLE, default=False): cv.boolean,
                    }
                )
            ],
        ),
        vol.Optional(CONF_SENSOR, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.All(
                    {
                        vol.Required(CONF_NODE): cv.string,
                        vol.Required(CONF_XPATH): cv.string,
                        vol.Optional(
                            CONF_UNIT_OF_MEASUREMENT, default=TEMP_CELSIUS
                        ): cv.string,
                    }
                )
            ],
        ),
        vol.Optional(CONF_SWITCH, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.All(
                    {
                        vol.Required(CONF_NODE): cv.string,
                        vol.Required(CONF_XPATH): cv.string,
                    }
                )
            ],
        ),
    }
)

SET_RUNTIME_VALUE_BOOL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Required(ATTR_VALUE): cv.boolean,
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)

SET_RUNTIME_VALUE_INT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Required(ATTR_VALUE): vol.Coerce(int),
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)

SET_RUNTIME_VALUE_FLOAT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)

PULSE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)


def setup(hass: HomeAssistant, config):
    """Set up the IHC integration."""
    conf = config.get(DOMAIN)
    if conf is not None:
        _LOGGER.error(
            """
            Setup of the IHC controller in configuration.yaml is no longer
            supported. See https://www.home-assistant.io/integrations/ihc/
            """
        )
        migrate_configuration(hass)
        return False

    setup_service_functions(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the IHC Controller from a config entry."""

    controller_id = entry.unique_id
    url = entry.data[CONF_URL]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    autosetup = entry.data[CONF_AUTOSETUP]
    info = get_options_value(entry, CONF_INFO, True)
    ihc_controller = IHCController(url, username, password)

    if not await hass.async_add_executor_job(ihc_controller.authenticate):
        _LOGGER.error("Unable to authenticate on IHC controller")
        return False
    system_info = await hass.async_add_executor_job(
        ihc_controller.client.get_system_info
    )
    if not system_info:
        _LOGGER.error("Unable to get system information from IHC controller")
        return False
    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, controller_id)},
        name=system_info["serial_number"],
        manufacturer="Schneider Electric",
        model=f"{system_info['brand']} {system_info['hw_revision']}",
        sw_version=system_info["version"],
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][controller_id] = {IHC_CONTROLLER: ihc_controller, IHC_INFO: info}

    if autosetup:
        await hass.async_add_executor_job(
            autosetup_ihc_products, hass, hass.config, ihc_controller, controller_id
        )
    await hass.async_add_executor_job(manual_setup, hass, controller_id)
    for component in IHC_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    entry.add_update_listener(async_update_options)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in IHC_PLATFORMS
            ]
        )
    )
    if not unload_ok:
        return False

    controller_id = config_entry.unique_id
    ihc_controller = hass.data[DOMAIN][controller_id][IHC_CONTROLLER]
    ihc_controller.disconnect()
    hass.data[DOMAIN].pop(controller_id)
    if hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


def manual_setup(hass, controller_id):
    """Manual setup of IHC devices."""
    yaml_path = hass.config.path(MANUAL_SETUP_YAML)
    if not os.path.isfile(yaml_path):
        return
    yaml = load_yaml_config_file(yaml_path)
    try:
        ihc_conf = MANUAL_SETUP_SCHEMA(yaml)[DOMAIN]
    except vol.Invalid as exception:
        _LOGGER.error("Invalid IHC manual setup data: %s", exception)
        return

    # Find the controller config for this controller
    controller_conf = None
    for x in ihc_conf:
        if x["controller"] == controller_id:
            controller_conf = x
            break
    if not controller_conf:
        return
    """Get manual configuration for IHC devices."""
    for component in IHC_PLATFORMS:
        discovery_info = {}
        if component in controller_conf:
            component_setup = controller_conf.get(component)
            for sensor_cfg in component_setup:
                name = sensor_cfg[CONF_NAME]
                device = {
                    "ihc_id": sensor_cfg[CONF_ID],
                    "ctrl_id": controller_id,
                    "product": {
                        "name": name,
                        "note": sensor_cfg.get(CONF_NOTE) or "",
                        "position": sensor_cfg.get(CONF_POSITION) or "",
                    },
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
            if component in hass.data[DOMAIN][controller_id]:
                hass.data[DOMAIN][controller_id][component].update(discovery_info)
            else:
                hass.data[DOMAIN][controller_id][component] = discovery_info


def autosetup_ihc_products(
    hass: HomeAssistantType, config, ihc_controller, controller_id
):
    """Auto setup of IHC products from the IHC project file."""

    project_xml = ihc_controller.get_project()
    if not project_xml:
        _LOGGER.error("Unable to read project from IHC controller")
        return False
    project = ElementTree.fromstring(project_xml)

    # If an auto setup file exist in the configuration it will override
    yaml_path = hass.config.path(AUTO_SETUP_YAML)
    if not os.path.isfile(yaml_path):
        yaml_path = os.path.join(os.path.dirname(__file__), AUTO_SETUP_YAML)
    yaml = load_yaml_config_file(yaml_path)
    try:
        auto_setup_conf = AUTO_SETUP_SCHEMA(yaml)
    except vol.Invalid as exception:
        _LOGGER.error("Invalid IHC auto setup data: %s", exception)
        return False
    groups = project.findall(".//group")
    for component in IHC_PLATFORMS:
        component_setup = auto_setup_conf[component]
        discovery_info = get_discovery_info(component_setup, groups, controller_id)
        if discovery_info:
            hass.data[DOMAIN][controller_id][component] = discovery_info
    return True


def get_discovery_info(component_setup, groups, controller_id):
    """Get discovery info for specified IHC component."""
    discovery_data = {}
    for group in groups:
        groupname = group.attrib["name"]
        for product_cfg in component_setup:
            products = group.findall(product_cfg[CONF_XPATH])
            for product in products:
                product_id = int(product.attrib["id"].strip("_"), 0)
                nodes = product.findall(product_cfg[CONF_NODE])
                for node in nodes:
                    if "setting" in node.attrib and node.attrib["setting"] == "yes":
                        continue
                    ihc_id = int(node.attrib["id"].strip("_"), 0)
                    name = f"{groupname}_{ihc_id}"
                    model = product.get("product_identifier") or ""
                    # make the model number look a bit nicer - strip leading _
                    if model.startswith("_"):
                        model = model[1::]
                    device = {
                        "ihc_id": ihc_id,
                        "ctrl_id": controller_id,
                        "product": {
                            "id": product_id,
                            "name": product.get("name") or "",
                            "note": product.get("note") or "",
                            "position": product.get("position") or "",
                            "model": model,
                        },
                        "product_cfg": product_cfg,
                        "group": groupname,
                    }
                    discovery_data[name] = device
    return discovery_data


def migrate_configuration(hass: HomeAssistant):
    """Migrate the old manual configuration from configuration.yaml
    to ihc_manual_setyp.yaml
    """
    yaml_manual_setup_path = hass.config.path(MANUAL_SETUP_YAML)
    if os.path.exists(yaml_manual_setup_path):
        _LOGGER.warning(
            f"The {yaml_manual_setup_path} already exist."
            "Migrating old configuration skipped"
        )
        return
    # We will load the configuration.yaml file to get the 'ihc' section
    # We do not want to use the config passed to setup because we do not
    # want the default values added by the config schema
    _LOGGER.debug("Migrating old IHC configuration")
    yaml_path = hass.config.path("configuration.yaml")
    conf = load_yaml_config_file(yaml_path)[DOMAIN]
    newconf = {DOMAIN: []}
    has_manual_config = False
    if not isinstance(conf, list):
        conf = [conf]
    for controllerconf in conf:
        serial = get_controller_serial(controllerconf)
        newcontrollerconf = {"controller": serial}
        for component in IHC_PLATFORMS:
            if component in controllerconf and len(controllerconf[component]) > 0:
                has_manual_config = True
                newcontrollerconf[component] = []
                i = -1
                for j in controllerconf[component]:
                    newcontrollerconf[component].append({})
                    i = i + 1
                    for key in j:
                        value = j[key]
                        newcontrollerconf[component][i][key] = value
        newconf[DOMAIN].append(newcontrollerconf)

    if not has_manual_config:
        _LOGGER.debug("No manual configuration in old IHC configuration")
        return
    with open(yaml_manual_setup_path, "w") as file:
        yaml.dump(newconf, file, default_flow_style=False, sort_keys=False)
    _LOGGER.warning(
        "Your old ihc configuration in configuration.yaml "
        f"file has been copied to the file {yaml_manual_setup_path} "
        "You can now delete the ihc section in configuration.yaml. "
        "Restart Home Assistant and add the IHC controller through the UI. "
        "See https://www.home-assistant.io/integrations/ihc/"
        " for more information"
    )
    return


def get_controller_serial(controllerconf):
    """Get the controller serial number. We use this as a controller id."""
    url = controllerconf[CONF_URL]
    username = controllerconf[CONF_USERNAME]
    password = controllerconf[CONF_PASSWORD]
    controller = IHCController(url, username, password)
    if not IHCController.is_ihc_controller(url):
        raise Exception("IHC controller not available at specified url")
    if not controller.authenticate():
        raise Exception("unable to authencitate on IHC controller")
    system_info = controller.client.get_system_info()
    _LOGGER.debug(f"IHC system info {system_info}")
    serial = system_info["serial_number"]
    controller.disconnect()
    return serial


def get_options_value(config_entry, key, default):
    """Get an options value and fall back to a default."""
    if config_entry.options:
        return config_entry.options.get(key, default)
    return default


def setup_service_functions(hass: HomeAssistantType):
    """Set up the IHC service functions."""

    def __get_controller(call):
        controller_id = call.data[ATTR_CONTROLLER_ID]
        # if no controller id is specified use the first one
        if controller_id == "":
            controller_id = next(iter(hass.data[DOMAIN]))
        return hass.data[DOMAIN][controller_id][IHC_CONTROLLER]

    async def async_set_runtime_value_bool(call):
        """Set a IHC runtime bool value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = __get_controller(call)
        await async_set_bool(hass, ihc_controller, ihc_id, value)

    async def async_set_runtime_value_int(call):
        """Set a IHC runtime integer value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = __get_controller(call)
        await async_set_int(hass, ihc_controller, ihc_id, value)

    async def async_set_runtime_value_float(call):
        """Set a IHC runtime float value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = __get_controller(call)
        await async_set_float(hass, ihc_controller, ihc_id, value)

    async def async_pulse_runtime_input(call):
        """Pulse a IHC controller input function."""
        ihc_id = call.data[ATTR_IHC_ID]
        ihc_controller = __get_controller(call)
        await async_pulse(hass, ihc_controller, ihc_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RUNTIME_VALUE_BOOL,
        async_set_runtime_value_bool,
        schema=SET_RUNTIME_VALUE_BOOL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RUNTIME_VALUE_INT,
        async_set_runtime_value_int,
        schema=SET_RUNTIME_VALUE_INT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RUNTIME_VALUE_FLOAT,
        async_set_runtime_value_float,
        schema=SET_RUNTIME_VALUE_FLOAT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PULSE, async_pulse_runtime_input, schema=PULSE_SCHEMA
    )
