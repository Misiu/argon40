"""Support for Argon 40 cases and Argon Fan HAT"""
import logging
from typing import Any

from RPi import GPIO  # pylint: disable=import-error
from custom_components.argon40.const import (
    ATTR_NAME,
    DOMAIN,
    SERVICE_SET_FAN_SPEED,
    STARTUP_MESSAGE,
)
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceDataType
from smbus import SMBus
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_FAN_SPEED_SCHEMA = vol.Schema(
    {vol.Required(ATTR_NAME): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))}
)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up the Argon40 component."""

    _LOGGER.info(STARTUP_MESSAGE)

    try:
        rev = GPIO.RPI_REVISION
        if rev == 2 or rev == 3:
            bus = SMBus(1)
        else:
            bus = SMBus(0)

        @callback
        def cleanup_gpio(event: Any) -> None:
            """Stuff to do before stopping."""
            GPIO.cleanup()

        # not sure if @callback needed
        @callback
        def prepare_gpio(event: Any) -> None:
            """Stuff to do when Home Assistant starts."""
            hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, cleanup_gpio)

        hass.bus.listen_once(EVENT_HOMEASSISTANT_START, prepare_gpio)

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        shutdown_pin = 4
        GPIO.setup(shutdown_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        address = 0x1A
        bus.write_byte(address, 10)

    except IOError as err:
        _LOGGER.exception(
            "Error %d, %s accessing 0x%02X: Check your I2C address",
            err.errno,
            err.strerror,
            address,
        )
        pass

    async def set_fan_speed(service: ServiceDataType) -> None:
        value = service.data.get(ATTR_NAME)

        _LOGGER.debug("Set fan speed to %s", value)

        bus.write_byte(address, value)

        hass.bus.async_fire("argon40_event", {"speed": value})

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_SPEED,
        set_fan_speed,
        schema=SERVICE_SET_FAN_SPEED_SCHEMA,
    )

    return True
