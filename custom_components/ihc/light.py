from __future__ import annotations

from typing import Any, Optional
from ihcsdk.ihccontroller import IHCController
from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import CONF_DIMMABLE, CONF_OFF_ID, CONF_ON_ID, DOMAIN, IHC_CONTROLLER
from .ihcdevice import IHCDevice
from .util import async_pulse, async_set_bool, async_set_int


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Load IHC lights based on a config entry."""
    controller_id: str = str(entry.unique_id)
    controller_data = hass.data[DOMAIN][controller_id]
    ihc_controller: IHCController = controller_data[IHC_CONTROLLER]
    lights = [
        IhcLight(
            ihc_controller,
            controller_id,
            name,
            device["ihc_id"],
            device["product_cfg"].get(CONF_OFF_ID),
            device["product_cfg"].get(CONF_ON_ID),
            device["product_cfg"].get(CONF_DIMMABLE, False),
            device["product"],
        )
        for name, device in controller_data.get("light", {}).items()
    ]
    async_add_entities(lights)


class IhcLight(IHCDevice, LightEntity):
    """Representation of a IHC light.
    For dimmable lights, the associated IHC resource should be a light
    level (integer). For non dimmable light the IHC resource should be
    an on/off (boolean) resource
    """

    def __init__(
        self,
        ihc_controller: IHCController,
        controller_id: str,
        name: str,
        ihc_id: int,
        ihc_off_id: Optional[int],
        ihc_on_id: Optional[int],
        dimmable: bool = False,
        product: Any = None,
    ) -> None:
        """Initialize the light."""
        super().__init__(ihc_controller, controller_id, name, ihc_id, product)
        self._ihc_off_id = ihc_off_id
        self._ihc_on_id = ihc_on_id
        self._brightness = 0
        self._dimmable = dimmable
        self._state = False
        self._attr_color_mode = (
            ColorMode.BRIGHTNESS if self._dimmable else ColorMode.ONOFF
        )
        self._attr_supported_color_modes = {self._attr_color_mode}

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            if (brightness := self._brightness) == 0:
                brightness = 255

        if self._dimmable:
            await async_set_int(
                self.hass, self.ihc_controller, self.ihc_id, int(brightness * 100 / 255)
            )
        else:
            if self._ihc_on_id:
                await async_pulse(self.hass, self.ihc_controller, self._ihc_on_id)
            else:
                await async_set_bool(self.hass, self.ihc_controller, self.ihc_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        if self._dimmable:
            await async_set_int(self.hass, self.ihc_controller, self.ihc_id, 0)
        else:
            if self._ihc_off_id:
                await async_pulse(self.hass, self.ihc_controller, self._ihc_off_id)
            else:
                await async_set_bool(self.hass, self.ihc_controller, self.ihc_id, False)

    def on_ihc_change(self, ihc_id, value):
        """Handle IHC notifications."""
        if isinstance(value, bool):
            self._dimmable = False
            self._state = value != 0
        else:
            self._dimmable = True
            self._state = value > 0
            if self._state:
                self._brightness = int(value * 255 / 100)
        self.schedule_update_ha_state()
