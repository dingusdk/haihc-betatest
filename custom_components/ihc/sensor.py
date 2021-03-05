"""Support for IHC sensors."""
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT
from homeassistant.helpers.entity import Entity

from .const import CONF_INFO, DOMAIN, IHC_CONTROLLER
from .ihcdevice import IHCDevice


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the IHC sensor platform."""
    if discovery_info is None:
        return
    devices = []
    for name, device in discovery_info.items():
        ihc_id = device["ihc_id"]
        product_cfg = device["product_cfg"]
        product = device["product"]
        # Find controller that corresponds with device id
        ctrl_id = device["ctrl_id"]
        ihc_key = f"ihc{ctrl_id}"
        info = hass.data[ihc_key][CONF_INFO]
        ihc_controller = hass.data[ihc_key][IHC_CONTROLLER]
        unit = product_cfg[CONF_UNIT_OF_MEASUREMENT]
        sensor = IHCSensor(ihc_controller, name, ihc_id, info, unit, product)
        devices.append(sensor)
    add_entities(devices)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Load IHC switches based on a config entry."""

    controller_id = config_entry.unique_id
    data = hass.data[DOMAIN][controller_id]
    ihc_controller = data[IHC_CONTROLLER]
    sensors = []
    if "sensor" in data and data["sensor"]:
        for name, device in data["sensor"].items():
            ihc_id = device["ihc_id"]
            product_cfg = device["product_cfg"]
            product = device["product"]
            unit = product_cfg[CONF_UNIT_OF_MEASUREMENT]
            sensor = IHCSensor(
                ihc_controller,
                controller_id,
                name,
                ihc_id,
                unit,
                product,
            )
            sensors.append(sensor)
        async_add_entities(sensors)


class IHCSensor(IHCDevice, Entity):
    """Implementation of the IHC sensor."""

    def __init__(
        self,
        ihc_controller,
        controller_id,
        name,
        ihc_id: int,
        unit,
        product=None,
    ) -> None:
        """Initialize the IHC sensor."""
        super().__init__(ihc_controller, controller_id, name, ihc_id, product)
        self._state = None
        self._unit_of_measurement = unit

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    def on_ihc_change(self, ihc_id, value):
        """Handle IHC resource change."""
        self._state = value
        self.schedule_update_ha_state()
