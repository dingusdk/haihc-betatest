import logging

from ihcsdk.ihccontroller import IHCController
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IHCDevice(Entity):
    """Base class for all IHC devices."""

    _attr_should_poll = False

    def __init__(
        self,
        ihc_controller: IHCController,
        controller_id: str,
        name: str,
        ihc_id: int,
        product=None,
    ) -> None:
        """Initialize IHC attributes."""
        self.ihc_controller = ihc_controller
        self._name = name
        self.ihc_id = ihc_id
        self.controller_id = controller_id
        self.device_id = None
        self.suggested_area = None

        if product:
            self.ihc_name, self.ihc_note, self.ihc_position = (
                product["name"],
                product["note"],
                product["position"],
            )
            self.suggested_area = product.get("group")
            self.device_id = f"{controller_id}_{product.get('id')}"
            self.device_name = f"{product['name']} ({product.get('position', '')})"
            self.device_model = product["model"]
        else:
            self.ihc_name = self.ihc_note = self.ihc_position = ""

    async def async_added_to_hass(self):
        """Add callback for IHC changes."""
        _LOGGER.debug("Adding IHC entity notify event: %s", self.ihc_id)
        self.ihc_controller.add_notify_event(self.ihc_id, self.on_ihc_change, True)

    @property
    def name(self):
        """Return the device name."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.controller_id}-{self.ihc_id}"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = {
            "ihc_id": self.ihc_id,
            "ihc_name": self.ihc_name,
            "ihc_note": self.ihc_note,
            "ihc_position": self.ihc_position,
        }
        if len(self.hass.data[DOMAIN]) > 1:
            attributes["ihc_controller"] = self.controller_id
        return attributes

    def on_ihc_change(self, ihc_id, value):
        """Handle IHC resource change."""
        raise NotImplementedError

    @property
    def device_info(self):
        """Return the device info."""
        if not self.device_id:
            return None
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.device_name,
            "manufacturer": "Schneider Electric",
            "suggested_area": self.suggested_area,
            "model": self.device_model,
            "sw_version": "",
            "via_device": (DOMAIN, self.controller_id),
        }
