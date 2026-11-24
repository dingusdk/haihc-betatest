"""Handle auto setup of IHC products from the ihc project file."""

import logging
from pathlib import Path
from xml.etree.ElementTree import Element

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from defusedxml import ElementTree
from homeassistant.config import load_yaml_config_file
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE, CONF_UNIT_OF_MEASUREMENT, UnitOfTemperature
from homeassistant.core import HomeAssistant
from ihcsdk.ihccontroller import IHCController

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
    PRODUCT_RESOURCES,
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
                            CONF_UNIT_OF_MEASUREMENT, default=UnitOfTemperature.CELSIUS
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
    hass: HomeAssistant, ihc_controller: IHCController, entry: ConfigEntry
) -> bool:
    """Auto setup of IHC products from the IHC project file."""
    if not (project_xml := ihc_controller.get_project()):
        _LOGGER.error("Unable to read project from IHC controller")
        return False
    # The ihcsdk decodes the project as ISO-8859-1. Some projects contain
    # UTF-8 bytes even though the xml declares ISO-8859-1, garbling special
    # characters (like the danish æøå). If the raw bytes are valid UTF-8 we
    # use that instead - text with special characters that validates as
    # UTF-8 is very unlikely to actually be ISO-8859-1.
    _LOGGER.debug("IHC project header: %r", project_xml[:120])
    try:
        project_xml = project_xml.encode("ISO-8859-1").decode("UTF-8")
    except UnicodeDecodeError:
        _LOGGER.debug("IHC project is not UTF-8, keeping the ISO-8859-1 decoding")
    project = ElementTree.fromstring(project_xml)

    # If an auto setup file exist in the configuration it will override
    yaml_path = hass.config.path(AUTO_SETUP_YAML)
    if not Path(yaml_path).is_file():
        yaml_path = str(Path(__file__).parent / AUTO_SETUP_YAML)
    yaml = load_yaml_config_file(yaml_path)
    try:
        auto_setup_conf = AUTO_SETUP_SCHEMA(yaml)
    except vol.Invalid:
        # A broken auto setup file is a permanent error, so we do not want
        # to fail the setup (that would make Home Assistant retry forever).
        # Log the problem and continue without auto setup entities.
        _LOGGER.exception("Invalid IHC auto setup data")
        return True
    if entry.unique_id is None:
        msg = "unique id not set"
        raise ValueError(msg)
    controller_id: str = entry.unique_id
    groups = project.findall(".//group")
    if groups:
        _LOGGER.debug("First IHC group name: %r", groups[0].attrib.get("name", ""))
    for platform in IHC_PLATFORMS:
        platform_setup = auto_setup_conf[platform]
        discovery_info = get_discovery_info(platform_setup, groups, controller_id)
        if discovery_info:
            hass.data[DOMAIN][entry.entry_id][platform] = discovery_info
    hass.data[DOMAIN][entry.entry_id][PRODUCT_RESOURCES] = get_product_resources(groups)
    return True


def get_product_info(product: Element, groupname: str) -> dict:
    """Return the device information for a product in the project."""
    return {
        "id": int(product.attrib["id"].strip("_"), 0),
        "name": product.get("name") or "",
        "note": product.get("note") or "",
        "position": product.get("position") or "",
        # make the model number look a bit nicer - strip leading _
        "model": product.get("product_identifier", "").lstrip("_"),
        "group": groupname,
    }


def get_product_resources(groups: list) -> dict[int, dict]:
    """Return the product of every resource in the project, by resource id."""
    resources = {}
    for group in groups:
        groupname = group.attrib["name"]
        for product in group.iter():
            if not product.tag.startswith("product_") or "id" not in product.attrib:
                continue
            info = get_product_info(product, groupname)
            for node in product.iter():
                if node is product or "id" not in node.attrib:
                    continue
                try:
                    resources[int(node.attrib["id"].strip("_"), 0)] = info
                except ValueError:
                    continue
    return resources


def get_discovery_info(platform_setup: dict, groups: list, controller_id: str) -> dict:
    """Get discovery info for specified IHC platform."""
    discovery_data = {}
    for group in groups:
        groupname = group.attrib["name"]
        for product_cfg in platform_setup:
            products = group.findall(product_cfg[CONF_XPATH])
            for product in products:
                nodes = product.findall(product_cfg[CONF_NODE])
                for node in nodes:
                    if "setting" in node.attrib and node.attrib["setting"] == "yes":
                        continue
                    ihc_id = int(node.attrib["id"].strip("_"), 0)
                    name = f"{groupname}_{ihc_id}"
                    device = {
                        "ihc_id": ihc_id,
                        "ctrl_id": controller_id,
                        "product": get_product_info(product, groupname),
                        "product_cfg": product_cfg,
                    }
                    discovery_data[name] = device
    return discovery_data
