"""Support for IHC switches."""
import logging
from homeassistant.components.switch import SwitchEntity

from .const import CONF_INFO, CONF_OFF_ID, CONF_ON_ID, DOMAIN, IHC_CONTROLLER
from .ihcdevice import IHCDevice
from .util import async_pulse, async_set_bool

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the IHC switch platform."""
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
        ihc_off_id = product_cfg.get(CONF_OFF_ID)
        ihc_on_id = product_cfg.get(CONF_ON_ID)
        switch = IHCSwitch(
            ihc_controller, name, ihc_id, ihc_off_id, ihc_on_id, info, product
        )
        devices.append(switch)
    add_entities(devices)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Load IHC switches based on a config entry."""

    controller_id = config_entry.unique_id
    data = hass.data[DOMAIN][controller_id]
    ihc_controller = data[IHC_CONTROLLER]
    switches = []
    if "switch" in data and data["switch"]:
        for name, device in data["switch"].items():
            ihc_id = device["ihc_id"]
            product_cfg = device["product_cfg"]
            product = device["product"]
            ihc_off_id = product_cfg.get(CONF_OFF_ID)
            ihc_on_id = product_cfg.get(CONF_ON_ID)
            switch = IHCSwitch(
                ihc_controller,
                controller_id,
                name,
                ihc_id,
                ihc_off_id,
                ihc_on_id,
                product,
            )
            switches.append(switch)
        async_add_entities(switches)


class IHCSwitch(IHCDevice, SwitchEntity):
    """Representation of an IHC switch."""

    def __init__(
        self,
        ihc_controller,
        controller_id,
        name: str,
        ihc_id: int,
        ihc_off_id: int,
        ihc_on_id: int,
        product=None,
    ) -> None:
        """Initialize the IHC switch."""
        super().__init__(ihc_controller, controller_id, name, ihc_id, product)
        self._ihc_off_id = ihc_off_id
        self._ihc_on_id = ihc_on_id
        self._state = False

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        if self._ihc_on_id:
            await async_pulse(self.hass, self.ihc_controller, self._ihc_on_id)
        else:
            await async_set_bool(self.hass, self.ihc_controller, self.ihc_id, True)

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        if self._ihc_off_id:
            await async_pulse(self.hass, self.ihc_controller, self._ihc_off_id)
        else:
            await async_set_bool(self.hass, self.ihc_controller, self.ihc_id, False)

    def on_ihc_change(self, ihc_id, value):
        """Handle IHC resource change."""
        self._state = value
        self.schedule_update_ha_state()
