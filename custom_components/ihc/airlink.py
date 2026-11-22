"""
Airlink (wireless) diagnostics for IHC products.

The controller keeps the battery level and the last received signal strength
of every wireless product. They are read with
AirlinkManagementService.getDetectedDeviceList and matched to the products in
the project file by serial number.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, IHC_CONTROLLER_DEVICE_ID, IHC_CONTROLLER_ID

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from ihcsdk.ihccontroller import IHCController

_LOGGER = logging.getLogger(__name__)

AIRLINK_PRODUCTS = "airlink_products"
AIRLINK_COORDINATOR = "airlink_coordinator"
AIRLINK_UPDATE_INTERVAL = timedelta(minutes=10)

# Battery powered wireless products (push buttons and key rings). Mains
# powered products also report a battery level, but it means nothing there.
BATTERY_PRODUCT_PREFIX = "0x41"


def _local(tag: str) -> str:
    """Return the tag name without the namespace."""
    return tag.rsplit("}", 1)[-1]


def get_airlink_products(groups: list[Element], controller_id: str) -> dict:
    """Return the wireless products in the project, keyed by serial number."""
    products = {}
    for group in groups:
        groupname = group.attrib["name"]
        for product in group.iter("product_airlink"):
            serial = product.get("serialnumber", "").strip("_")
            if not serial:
                continue
            model = product.get("product_identifier", "").lstrip("_")
            products[int(serial, 0)] = {
                "ctrl_id": controller_id,
                "product": {
                    "id": int(product.attrib["id"].strip("_"), 0),
                    "name": product.get("name") or "",
                    "note": product.get("note") or "",
                    "position": product.get("position") or "",
                    "model": model,
                    "group": groupname,
                },
                "battery_powered": model.startswith(BATTERY_PRODUCT_PREFIX),
            }
    return products


def read_detected_devices(ihc_controller: IHCController) -> dict[int, dict] | None:
    """Read the wireless devices the controller knows, keyed by serial number."""
    xdoc = ihc_controller.client.connection.soap_action(
        "/ws/AirlinkManagementService", "getDetectedDeviceList", ""
    )
    if xdoc is False:
        return None
    devices = {}
    for item in xdoc.iter():
        if _local(item.tag) != "arrayItem":
            continue
        values = {_local(child.tag): child.text for child in item}
        try:
            devices[int(values["serialNumber"])] = {
                "battery_level": int(values["batteryLevel"]),
                "signal_strength": int(values["signalStrength"]),
                "detected": values.get("detected") == "true",
            }
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug("Skipping unreadable airlink device: %s", values)
    return devices


class AirlinkCoordinator(DataUpdateCoordinator[dict[int, dict]]):
    """Poll the controller for wireless device diagnostics."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, ihc_controller: IHCController
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="IHC airlink",
            update_interval=AIRLINK_UPDATE_INTERVAL,
        )
        self.ihc_controller = ihc_controller

    async def _async_update_data(self) -> dict[int, dict]:
        devices = await self.hass.async_add_executor_job(
            read_detected_devices, self.ihc_controller
        )
        if devices is None:
            msg = "Unable to read airlink devices from the IHC controller"
            raise UpdateFailed(msg)
        return devices


class AirlinkEntity(CoordinatorEntity[AirlinkCoordinator]):
    """Base for diagnostic entities on a wireless IHC product."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: AirlinkCoordinator, serial: int, device: dict, key: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.serial = serial
        self.controller_id = device["ctrl_id"]
        product = device["product"]
        self._attr_unique_id = f"{self.controller_id}-airlink-{serial}-{key}"
        # Same device as the light/switch entities of the product, so the
        # diagnostics show up next to them.
        device_name = product["name"]
        if product["position"]:
            device_name += f" ({product['position']})"
        self._device = {
            "identifiers": {(DOMAIN, f"{self.controller_id}_{product['id']}")},
            "name": device_name,
            "manufacturer": "Schneider Electric",
            "suggested_area": product["group"],
            "model": product["model"],
            "serial_number": f"{serial:x}",
        }

    @property
    def device_info(self) -> dict:
        """Return the device info."""
        return {**self._device, "via_device_id": self._controller_device_id()}

    def _controller_device_id(self) -> str | None:
        for data in self.hass.data[DOMAIN].values():
            if data[IHC_CONTROLLER_ID] == self.controller_id:
                return data.get(IHC_CONTROLLER_DEVICE_ID)
        return None

    @property
    def available(self) -> bool:
        """Return if the controller knows the device."""
        return super().available and self.serial in self.coordinator.data

    @property
    def device_data(self) -> dict[str, Any]:
        """Return the latest data for this device."""
        return self.coordinator.data[self.serial]


def airlink_devices(controller_data: dict) -> tuple[AirlinkCoordinator | None, dict]:
    """Return the airlink coordinator and products for a controller."""
    return (
        controller_data.get(AIRLINK_COORDINATOR),
        controller_data.get(AIRLINK_PRODUCTS, {}),
    )
