import logging
import os.path

from defusedxml import ElementTree
import voluptuous as vol

from homeassistant.config import load_yaml_config_file
import homeassistant.helpers.config_validation as cv

from homeassistant.const import (
    CONF_TYPE,
    CONF_UNIT_OF_MEASUREMENT,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant

from .const import (
    AUTO_SETUP_YAML,
    CONF_BINARY_SENSOR,
    CONF_DIMMABLE,
    CONF_INVERTING,
    CONF_LIGHT,
    CONF_NODE,
    CONF_SENSOR,
    CONF_SWITCH,
    CONF_XPATH,
    DOMAIN,
    IHC_PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


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


def autosetup_ihc_products(
    hass: HomeAssistant, ihc_controller, controller_id, use_groups: bool
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
        discovery_info = get_discovery_info(
            component_setup, groups, controller_id, use_groups
        )
        if discovery_info:
            hass.data[DOMAIN][controller_id][component] = discovery_info
    return True


def get_discovery_info(component_setup, groups, controller_id, use_groups: bool):
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
                    }
                    if use_groups:
                        device["product"]["group"] = groupname
                    discovery_data[name] = device
    return discovery_data