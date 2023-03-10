"""Support for IHC devices."""
import voluptuous as vol

from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_CONTROLLER_ID,
    ATTR_IHC_ID,
    ATTR_VALUE,
    DOMAIN,
    IHC_CONTROLLER,
    SERVICE_PULSE,
    SERVICE_SET_RUNTIME_VALUE_BOOL,
    SERVICE_SET_RUNTIME_VALUE_FLOAT,
    SERVICE_SET_RUNTIME_VALUE_INT,
)
from .util import async_pulse, async_set_bool, async_set_float, async_set_int

SET_RUNTIME_VALUE_BOOL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Required(ATTR_VALUE): cv.boolean,
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)

SET_RUNTIME_VALUE_INT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Required(ATTR_VALUE): vol.Coerce(int),
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)

SET_RUNTIME_VALUE_FLOAT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)

PULSE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)


def setup_service_functions(hass: HomeAssistant) -> None:
    """Set up the IHC service functions."""

    def _get_controller(call):
        controller_id = call.data[ATTR_CONTROLLER_ID]
        # if no controller id is specified use the first one
        if controller_id == "":
            controller_id = next(iter(hass.data[DOMAIN]))
        return hass.data[DOMAIN][controller_id][IHC_CONTROLLER]

    async def async_set_runtime_value_bool(call):
        """Set a IHC runtime bool value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = _get_controller(call)
        await async_set_bool(hass, ihc_controller, ihc_id, value)

    async def async_set_runtime_value_int(call):
        """Set a IHC runtime integer value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = _get_controller(call)
        await async_set_int(hass, ihc_controller, ihc_id, value)

    async def async_set_runtime_value_float(call):
        """Set a IHC runtime float value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = _get_controller(call)
        await async_set_float(hass, ihc_controller, ihc_id, value)

    async def async_pulse_runtime_input(call):
        """Pulse a IHC controller input function."""
        ihc_id = call.data[ATTR_IHC_ID]
        ihc_controller = _get_controller(call)
        await async_pulse(hass, ihc_controller, ihc_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RUNTIME_VALUE_BOOL,
        async_set_runtime_value_bool,
        schema=SET_RUNTIME_VALUE_BOOL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RUNTIME_VALUE_INT,
        async_set_runtime_value_int,
        schema=SET_RUNTIME_VALUE_INT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RUNTIME_VALUE_FLOAT,
        async_set_runtime_value_float,
        schema=SET_RUNTIME_VALUE_FLOAT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PULSE, async_pulse_runtime_input, schema=PULSE_SCHEMA
    )
