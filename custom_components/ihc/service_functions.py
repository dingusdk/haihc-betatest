"""Support for IHC devices."""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from ihcsdk.ihccontroller import IHCController

from .const import (
    ATTR_CONTROLLER_ID,
    ATTR_IHC_ID,
    ATTR_VALUE,
    ATTR_VALUE_HOUR,
    ATTR_VALUE_MINUTE,
    ATTR_VALUE_SECOND,
    DOMAIN,
    IHC_CONTROLLER,
    IHC_CONTROLLER_ID,
    SERVICE_PULSE,
    SERVICE_SET_RUNTIME_VALUE_BOOL,
    SERVICE_SET_RUNTIME_VALUE_FLOAT,
    SERVICE_SET_RUNTIME_VALUE_INT,
    SERVICE_SET_RUNTIME_VALUE_TIME,
    SERVICE_SET_RUNTIME_VALUE_TIMER,
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

SET_RUNTIME_VALUE_TIMER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        vol.Required(ATTR_VALUE): vol.Coerce(int),
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)

SET_RUNTIME_VALUE_TIME_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IHC_ID): cv.positive_int,
        # hour must be an integer in [0,23]
        vol.Optional(ATTR_VALUE_HOUR, default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=23)
        ),
        # minute/second coerced to int and bounded to typical ranges
        vol.Optional(ATTR_VALUE_MINUTE, default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=59)
        ),
        vol.Optional(ATTR_VALUE_SECOND, default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=59)
        ),
        vol.Optional(ATTR_CONTROLLER_ID, default=""): cv.string,
    }
)


def setup_service_functions(hass: HomeAssistant) -> None:
    """Set up the IHC service functions."""

    def _get_controller(call: ServiceCall) -> IHCController:
        controller_id = call.data[ATTR_CONTROLLER_ID]
        if controller_id != "":
            for data in hass.data[DOMAIN].values():
                if data[IHC_CONTROLLER_ID] == controller_id:
                    return data[IHC_CONTROLLER]
        # if the controller id was not found or specified we use the first one
        entry_id = next(iter(hass.data[DOMAIN]))
        return hass.data[DOMAIN][entry_id][IHC_CONTROLLER]

    async def async_set_runtime_value_bool(call: ServiceCall) -> None:
        """Set a IHC runtime bool value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = _get_controller(call)
        await async_set_bool(hass, ihc_controller, ihc_id, value)

    async def async_set_runtime_value_int(call: ServiceCall) -> None:
        """Set a IHC runtime integer value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = _get_controller(call)
        await async_set_int(hass, ihc_controller, ihc_id, value)

    async def async_set_runtime_value_float(call: ServiceCall) -> None:
        """Set a IHC runtime float value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = _get_controller(call)
        await async_set_float(hass, ihc_controller, ihc_id, value)

    async def async_pulse_runtime_input(call: ServiceCall) -> None:
        """Pulse a IHC controller input function."""
        ihc_id = call.data[ATTR_IHC_ID]
        ihc_controller = _get_controller(call)
        await async_pulse(hass, ihc_controller, ihc_id)

    async def async_set_runtime_value_timer(call: ServiceCall) -> None:
        """Set a IHC runtime integer value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value = call.data[ATTR_VALUE]
        ihc_controller = _get_controller(call)
        await hass.async_add_executor_job(
            ihc_controller.set_runtime_value_timer, ihc_id, value
        )

    async def async_set_runtime_value_time(call: ServiceCall) -> None:
        """Set a IHC runtime integer value service function."""
        ihc_id = call.data[ATTR_IHC_ID]
        value_hour = call.data[ATTR_VALUE_HOUR]
        value_minute = call.data[ATTR_VALUE_MINUTE]
        value_second = call.data[ATTR_VALUE_SECOND]
        ihc_controller = _get_controller(call)
        await hass.async_add_executor_job(
            ihc_controller.set_runtime_value_time,
            ihc_id,
            value_hour,
            value_minute,
            value_second,
        )

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
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RUNTIME_VALUE_TIMER,
        async_set_runtime_value_timer,
        schema=SET_RUNTIME_VALUE_TIMER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RUNTIME_VALUE_TIME,
        async_set_runtime_value_time,
        schema=SET_RUNTIME_VALUE_TIME_SCHEMA,
    )
