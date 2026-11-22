"""Support for IHC binary sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_TYPE
from homeassistant.util.enum import try_parse_enum

from .airlink import AirlinkCoordinator, AirlinkEntity, airlink_devices
from .const import CONF_INVERTING, DOMAIN, IHC_CONTROLLER
from .ihcdevice import IHCDevice

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from ihcsdk.ihccontroller import IHCController


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Load IHC binary sensors based on a config entry."""
    controller_id: str = str(entry.unique_id)
    controller_data = hass.data[DOMAIN][entry.entry_id]
    ihc_controller: IHCController = controller_data[IHC_CONTROLLER]
    sensors = []
    if controller_data.get("binary_sensor"):
        for name, device in controller_data["binary_sensor"].items():
            ihc_id = device["ihc_id"]
            product_cfg = device["product_cfg"]
            product = device["product"]
            sensor = IHCBinarySensor(
                ihc_controller,
                controller_id,
                name,
                ihc_id,
                product_cfg.get(CONF_TYPE),
                product_cfg[CONF_INVERTING],
                product,
            )
            sensors.append(sensor)
        async_add_entities(sensors)
    coordinator, airlink_products = airlink_devices(controller_data)
    if coordinator:
        async_add_entities(
            IHCAirlinkBatterySensor(coordinator, serial, device)
            for serial, device in airlink_products.items()
            if device["battery_powered"]
        )


class IHCBinarySensor(IHCDevice, BinarySensorEntity):
    """
    IHC Binary Sensor.

    The associated IHC resource can be any in or output from a IHC product
    or function block, but it must be a boolean ON/OFF resources.
    """

    def __init__(
        self,
        ihc_controller: IHCController,
        controller_id: str,
        name: str,
        ihc_id: int,
        sensor_type: str,
        inverting: bool,
        product=None,
    ) -> None:
        """Initialize the IHC binary sensor."""
        super().__init__(ihc_controller, controller_id, name, ihc_id, product)
        self._attr_device_class = try_parse_enum(BinarySensorDeviceClass, sensor_type)
        self.inverting = inverting

    def on_ihc_change(self, _ihc_id: int, value: Any) -> None:
        """IHC resource has changed."""
        if self.inverting:
            self._attr_is_on = not value
        else:
            self._attr_is_on = value
        self.schedule_update_ha_state()


class IHCAirlinkBatterySensor(AirlinkEntity, BinarySensorEntity):
    """Low battery on a battery powered wireless product."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(
        self, coordinator: AirlinkCoordinator, serial: int, device: dict
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, serial, device, "battery")

    @property
    def is_on(self) -> bool:
        """Return true when the battery is low."""
        return self.device_data["battery_level"] == 0
