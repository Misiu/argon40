"""Set up Argon40 through a Home Assistant config entry."""

import logging
from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.loader import async_get_integration

from .const import (
    ATTR_ALWAYS_ON_NAME,
    ATTR_SPEED_NAME,
    CONF_DEVICE_TYPE,
    DEVICE_ONE,
    DOMAIN,
    SERVICE_SET_FAN_SPEED,
    SERVICE_SET_MODE,
    STARTUP_MESSAGE,
)
from .controller import Argon40Controller
from .hardware import HardwareError

if TYPE_CHECKING:
    from homeassistant.core import Event, HomeAssistant, ServiceCall
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)
_PLATFORMS = [Platform.FAN, Platform.EVENT]

type Argon40ConfigEntry = ConfigEntry[Argon40Controller]

SERVICE_SET_FAN_SPEED_SCHEMA = vol.Schema(
    {vol.Required(ATTR_SPEED_NAME): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))}
)
SERVICE_SET_MODE_SCHEMA = vol.Schema({vol.Required(ATTR_ALWAYS_ON_NAME): cv.boolean})
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)  # pylint: disable=invalid-name


# Home Assistant requires this signature; CONFIG_SCHEMA handles obsolete YAML.
# pylint: disable-next=unused-argument
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Register the existing services without opening hardware from YAML."""

    async def handle_service(call: ServiceCall) -> None:
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="not_configured"
            )
        controller = entries[0].runtime_data
        if call.service == SERVICE_SET_FAN_SPEED:
            await controller.async_set_speed(call.data[ATTR_SPEED_NAME])
        else:
            await controller.async_set_mode(always_on=call.data[ATTR_ALWAYS_ON_NAME])

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_SPEED,
        handle_service,
        schema=SERVICE_SET_FAN_SPEED_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_MODE, handle_service, schema=SERVICE_SET_MODE_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: Argon40ConfigEntry) -> bool:
    """Open the local hardware and forward its fan and optional button entity."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP_MESSAGE, integration.version)
    controller = Argon40Controller(hass, entry.entry_id, entry.data[CONF_DEVICE_TYPE])
    try:
        await controller.async_connect()
    except HardwareError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key=err.code
        ) from err
    entry.runtime_data = controller
    platforms = (
        _PLATFORMS if entry.data[CONF_DEVICE_TYPE] == DEVICE_ONE else [Platform.FAN]
    )
    try:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)
    except Exception:
        await controller.async_close()
        raise

    async def stop_hardware(_event: Event) -> None:
        await controller.async_close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hardware)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Argon40ConfigEntry) -> bool:
    """Unload entities and release the I2C and GPIO handles."""
    platforms = (
        _PLATFORMS if entry.data[CONF_DEVICE_TYPE] == DEVICE_ONE else [Platform.FAN]
    )
    if not await hass.config_entries.async_unload_platforms(entry, platforms):
        return False
    await entry.runtime_data.async_close()
    return True
