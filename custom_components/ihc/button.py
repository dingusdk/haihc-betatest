"""Support for IHC buttons."""
import logging

from ihcsdk.ihccontroller import IHCController

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from typing import Any

from .const import DOMAIN, IHC_CONTROLLER
from .ihcdevice import IHCDevice
from .util import async_pulse

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Load IHC buttons based on a config entry."""
    controller_id: str = str(config_entry.unique_id)
    controller_data = hass.data[DOMAIN][controller_id]
    ihc_controller: IHCController = controller_data[IHC_CONTROLLER]
    buttons = []
    if "button" in controller_data and controller_data["button"]:
        for name, device in controller_data["button"].items():
            ihc_id = device["ihc_id"]
            product = device["product"]
            switch = IHCButton(
                ihc_controller,
                controller_id,
                name,
                ihc_id,
                product,
            )
            buttons.append(switch)
        async_add_entities(buttons)


class IHCButton(IHCDevice, ButtonEntity):
    """Representation of an IHC stateless button."""

    def __init__(
        self,
        ihc_controller: IHCController,
        controller_id: str,
        name: str,
        ihc_id: int,
        product=None,
    ) -> None:
        """Initialize the IHC button."""
        super().__init__(ihc_controller, controller_id, name, ihc_id, product)
        self._state = False

    async def async_press(self) -> None:
        """Send button pulse to IHC."""
        await async_pulse(self.hass, self.ihc_controller, self.ihc_id)

    def on_ihc_change(self, ihc_id, value):
        """Handle IHC resource change."""
        self._state = value
        self.schedule_update_ha_state()
