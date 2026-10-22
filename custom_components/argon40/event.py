"""Expose the ONE case's hardware button events."""

from typing import TYPE_CHECKING

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import BUTTON_EVENTS, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import Argon40ConfigEntry
    from .controller import Argon40Controller


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: Argon40ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a button event entity only for ONE hardware."""
    async_add_entities([Argon40ButtonEvent(entry)])


class Argon40ButtonEvent(EventEntity):
    """Represent documented MCU button pulses without executing power actions."""

    _attr_has_entity_name = True
    _attr_translation_key = "button"
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_should_poll = False

    def __init__(self, entry: Argon40ConfigEntry) -> None:
        """Link the button to the same device as its fan."""
        self._attr_event_types = list(BUTTON_EVENTS)
        self._controller: Argon40Controller = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)}, manufacturer="Argon40", name=entry.title
        )

    @property
    def available(self) -> bool:
        """Report whether GPIO event monitoring is still active."""
        return self._controller.button_available

    async def async_added_to_hass(self) -> None:
        """Subscribe to decoded GPIO pulses."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._controller.signal_update, self.async_write_ha_state
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._controller.signal_button, self._async_button_event
            )
        )

    @callback
    def _async_button_event(self, event_type: str) -> None:
        """Publish a timestamped Home Assistant event entity update."""
        self._trigger_event(event_type)
        self.async_write_ha_state()
