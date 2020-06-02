"""Support for Argon 40 cases and Argon Fan HAT"""
import logging

from RPi import GPIO  # pylint: disable=import-error
from custom_components.argon40.const import (
    ATTR_NAME,
    DOMAIN,
    SERVICE_SET_FAN_SPEED,
    STARTUP_MESSAGE,
)
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceDataType
import smbus  # pylint: disable=import-error
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
            bus = smbus.SMBus(1)
        else:
            bus = smbus.SMBus(0)

        def cleanup_gpio(event):
            """Stuff to do before stopping."""
            GPIO.cleanup()

        def prepare_gpio(event):
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

        hass.bus.async_fire("argon_one_event", {"speed": value})

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_SPEED,
        set_fan_speed,
        schema=SERVICE_SET_FAN_SPEED_SCHEMA,
    )

    return True


# """
# Custom integration to integrate Argon ONE cases and Arfon Fan HAT with Home Assistant.

# For more details about this integration, please refer to
# https://github.com/Misiu/argon_one
# """
# import asyncio
# from datetime import timedelta
# import logging

# from homeassistant.config_entries import ConfigEntry
# from homeassistant.core import Config, HomeAssistant
# from homeassistant.exceptions import ConfigEntryNotReady
# from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
# from sampleclient.client import Client

# from custom_components.argon_one.const import (
#     CONF_PASSWORD,
#     CONF_USERNAME,
#     DOMAIN,
#     PLATFORMS,
#     STARTUP_MESSAGE,
# )

# SCAN_INTERVAL = timedelta(seconds=30)

# _LOGGER = logging.getLogger(__name__)


# async def async_setup(hass: HomeAssistant, config: Config):
#     """Set up this integration using YAML is not supported."""
#     return True


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
#     """Set up this integration using UI."""
#     if hass.data.get(DOMAIN) is None:
#         hass.data.setdefault(DOMAIN, {})
#         _LOGGER.info(STARTUP_MESSAGE)

#     username = entry.data.get(CONF_USERNAME)
#     password = entry.data.get(CONF_PASSWORD)

#     coordinator = BlueprintDataUpdateCoordinator(
#         hass, username=username, password=password
#     )
#     await coordinator.async_refresh()

#     if not coordinator.last_update_success:
#         raise ConfigEntryNotReady

#     hass.data[DOMAIN][entry.entry_id] = coordinator

#     for platform in PLATFORMS:
#         if entry.options.get(platform, True):
#             coordinator.platforms.append(platform)
#             hass.async_add_job(
#                 hass.config_entries.async_forward_entry_setup(entry, platform)
#             )

#     entry.add_update_listener(async_reload_entry)
#     return True


# class BlueprintDataUpdateCoordinator(DataUpdateCoordinator):
#     """Class to manage fetching data from the API."""

#     def __init__(self, hass, username, password):
#         """Initialize."""
#         self.api = Client(username, password)
#         self.platforms = []

#         super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

#     async def _async_update_data(self):
#         """Update data via library."""
#         try:
#             data = await self.api.async_get_data()
#             return data.get("data", {})
#         except Exception as exception:
#             raise UpdateFailed(exception)


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
#     """Handle removal of an entry."""
#     coordinator = hass.data[DOMAIN][entry.entry_id]
#     unloaded = all(
#         await asyncio.gather(
#             *[
#                 hass.config_entries.async_forward_entry_unload(entry, platform)
#                 for platform in PLATFORMS
#                 if platform in coordinator.platforms
#             ]
#         )
#     )
#     if unloaded:
#         hass.data[DOMAIN].pop(entry.entry_id)

#     return unloaded


# async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
#     """Reload config entry."""
#     await async_unload_entry(hass, entry)
#     await async_setup_entry(hass, entry)
