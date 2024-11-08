"""Support for Argon 40 cases and Argon Fan HAT"""
import logging
from typing import Any

from custom_components.argon40.const import (
    ATTR_ALWAYS_ON_NAME,
    ATTR_SPEED_NAME,
    DOMAIN,
    SERVICE_SET_FAN_SPEED,
    SERVICE_SET_MODE,
    STARTUP_MESSAGE,
)
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback, HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType, ServiceDataType
from smbus2 import SMBus
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_FAN_SPEED_SCHEMA = vol.Schema(
    {vol.Required(ATTR_SPEED_NAME): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))}
)

#I2C addresses
ARGONONE_FAN_ADDRESS=0x1a

#ArgonOne Reg Addresses
ADDR_ARGONONEREG_DUTYCYCLE=0x80

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Argon40 component."""

    _LOGGER.info(STARTUP_MESSAGE)

    try:
        bus = SMBus(1)
        
        bus.write_byte_data(ARGONONE_FAN_ADDRESS, ADDR_ARGONONEREG_DUTYCYCLE, 10)

        # Run check support function on startup
        if argonregister_checksupport(bus):
            _LOGGER.info("Argon case detected and supported.")
        else:
            _LOGGER.error("Argon case not detected or not supported.")

    except IOError as err:
        _LOGGER.exception(
            "Error %d, %s accessing 0x%02X: Check your I2C address",
            err.errno,
            err.strerror,
            ARGONONE_FAN_ADDRESS,
        )
        return False

    async def set_fan_speed(service: ServiceDataType) -> None:
        value = service.data.get(ATTR_SPEED_NAME)
        _LOGGER.error("Set fan speed to %s", value)
        bus.write_byte_data(ARGONONE_FAN_ADDRESS, ADDR_ARGONONEREG_DUTYCYCLE, value)
        hass.bus.async_fire("argon40_event", {"speed": value})

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_SPEED,
        set_fan_speed,
        schema=SERVICE_SET_FAN_SPEED_SCHEMA,
    )

    return True
    
def argonregister_checksupport(bus: SMBus) -> bool:
    """Check if Argon case is supported."""
    if bus is None:
        return False
    try:
        oldval = argonregister_getbyte(bus, ADDR_ARGONONEREG_DUTYCYCLE)
        _LOGGER.debug("old value %s", oldval)
        newval = oldval + 1
        if newval >= 100:
            newval = 98
        argonregister_setbyte(bus, ADDR_ARGONONEREG_DUTYCYCLE, newval)
        read_back_val = argonregister_getbyte(bus, ADDR_ARGONONEREG_DUTYCYCLE)
        
        # Restore original value
        argonregister_setbyte(bus, ADDR_ARGONONEREG_DUTYCYCLE, oldval)
        
        return read_back_val != oldval
    except Exception as e:
        _LOGGER.error("Error checking Argon support: %s", e)
        return False
        
def argonregister_getbyte(bus, address: int) -> int:
    """Read a single byte from a specific register address."""
    if bus is None:
        return 0
    return bus.read_byte_data(ARGONONE_FAN_ADDRESS, address)

def argonregister_setbyte(bus, address: int, bytevalue: int) -> None:
    """Write a single byte to a specific register address, with a delay for stability."""
    if bus is None:
        return
    bus.write_byte_data(ARGONONE_FAN_ADDRESS, address, bytevalue)
