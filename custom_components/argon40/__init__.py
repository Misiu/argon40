"""Support for Argon 40 cases and Argon Fan HAT."""

import logging
from typing import TYPE_CHECKING

# Hardware libraries are installed by Home Assistant on the Raspberry Pi.
from RPi import GPIO  # pylint: disable=import-error
from smbus import SMBus  # pylint: disable=import-error
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.loader import async_get_integration

from .const import (
    ATTR_ALWAYS_ON_NAME,
    ATTR_SPEED_NAME,
    DOMAIN,
    SERVICE_SET_FAN_SPEED,
    SERVICE_SET_MODE,
    STARTUP_MESSAGE,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_FAN_SPEED_SCHEMA = vol.Schema(
    {vol.Required(ATTR_SPEED_NAME): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))}
)

SERVICE_SET_MODE_SCHEMA = vol.Schema({vol.Required(ATTR_ALWAYS_ON_NAME): cv.boolean})

I2C_ADDRESS = 0x1A


# Home Assistant requires this setup signature, including the unused config.
# pylint: disable-next=unused-argument
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001 - HA setup signature
    """Set up the Argon40 component."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP_MESSAGE, integration.version)

    try:
        rev = GPIO.RPI_REVISION
        if rev in (2, 3):
            bus = SMBus(1)
        else:
            bus = SMBus(0)

        GPIO.setwarnings(False)  # noqa: FBT003 - RPi.GPIO's external API
        GPIO.setmode(GPIO.BCM)
        shutdown_pin = 4
        GPIO.setup(shutdown_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        bus.write_byte(I2C_ADDRESS, 10)

    except OSError as err:
        _LOGGER.exception(
            "Error %d, %s accessing 0x%02X: Check your I2C address",
            err.errno,
            err.strerror,
            I2C_ADDRESS,
        )
        return False

    async def set_fan_speed(service: ServiceCall) -> None:
        value = service.data.get(ATTR_SPEED_NAME)
        _LOGGER.debug("Set fan speed to %s", value)
        bus.write_byte(I2C_ADDRESS, value)
        hass.bus.async_fire("argon40_event", {"speed": value})

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_SPEED,
        set_fan_speed,
        schema=SERVICE_SET_FAN_SPEED_SCHEMA,
    )

    async def set_mode(service: ServiceCall) -> None:
        value = service.data.get(ATTR_ALWAYS_ON_NAME)
        _LOGGER.debug("Set always on mode to %s", value)
        if value:
            bus.write_byte(I2C_ADDRESS, 254)  # 0xfe - always on mode
        else:
            bus.write_byte(I2C_ADDRESS, 253)  # 0xfd - the default mode

        hass.bus.async_fire("argon40_event", {"always_on": value})

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MODE,
        set_mode,
        schema=SERVICE_SET_MODE_SCHEMA,
    )

    return True
