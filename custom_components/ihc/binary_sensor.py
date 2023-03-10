"""Support for IHC binary sensors."""

from __future__ import annotations

from typing import List, Union

from ihcsdk.ihccontroller import IHCController

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_INVERTING, DOMAIN, IHC_CONTROLLER
from .ihcdevice import IHCDevice


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Load IHC binary sensors based on a config entry."""
    controller_id: str = str(entry.unique_id)
    controller_data = hass.data[DOMAIN][controller_id]
    ihc_controller: IHCController = controller_data[IHC_CONTROLLER]
    sensors: List[IHCBinarySensor] = [
        IHCBinarySensor(
            ihc_controller,
            controller_id,
            name,
            device["ihc_id"],
            device["product_cfg"].get(CONF_TYPE),
            device["product_cfg"].get(CONF_INVERTING),
            device["product"]
        )
        for name, device in controller_data.get("binary_sensor", {}).items()
    ]
    async_add_entities(sensors)


class IHCBinarySensor(IHCDevice, BinarySensorEntity):
    """IHC Binary Sensor.
    The associated IHC resource can be any in or output from a IHC product
    or function block, but it must be a boolean ON/OFF resources.
    """

    def __init__(
        self,
        ihc_controller: IHCController,
        controller_id: str,
        name: str,
        ihc_id: int,
        sensor_type: str | None,
        inverting: bool | None,
        product: Union[None, str] = None,
    ) -> None:
        """Initialize the IHC binary sensor."""
        super().__init__(ihc_controller, controller_id, name, ihc_id, product)
        self._state: bool | None = None
        self._sensor_type: str | None = sensor_type
        self.inverting: bool = bool(inverting)

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of this sensor."""
        return (
            BinarySensorDeviceClass(self._sensor_type)
            if self._sensor_type in DEVICE_CLASSES
            else None
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on/open."""
        return self._state

    def on_ihc_change(self, ihc_id: int, value: bool) -> None:
        """IHC resource has changed."""
        self._state = not value if self.inverting else value
        self.schedule_update_ha_state()
