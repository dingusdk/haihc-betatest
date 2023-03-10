"""Useful functions for the IHC component."""

import asyncio

from ihcsdk.ihccontroller import IHCController

from homeassistant.core import callback


async def async_pulse(hass, ihc_controller, ihc_id: int):
    """Send a short on/off pulse to an IHC controller resource."""
    await async_set_bool(hass, ihc_controller, ihc_id, True)
    await asyncio.sleep(0.1)
    await async_set_bool(hass, ihc_controller, ihc_id, False)


async def async_set_bool(hass, ihc_controller, ihc_id: int, value: bool):
    """Set a bool value on an IHC controller resource."""
    return await hass.async_add_executor_job(
        ihc_controller.set_runtime_value_bool, ihc_id, value
    )


async def async_set_int(hass, ihc_controller, ihc_id: int, value: int):
    """Set a int value on an IHC controller resource."""
    return await hass.async_add_executor_job(
        ihc_controller.set_runtime_value_int, ihc_id, value
    )


async def async_set_float(hass, ihc_controller, ihc_id: int, value: float):
    """Set a float value on an IHC controller resource."""
    return await hass.async_add_executor_job(
        ihc_controller.set_runtime_value_float, ihc_id, value
    )


def get_controller_serial(ihc_controller: IHCController) -> str:
    """Get the controller serial number.
    Having the function makes it easier to patch for testing
    """
    info = ihc_controller.client.get_system_info()
    return info["serial_number"]
