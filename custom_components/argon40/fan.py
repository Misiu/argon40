"""Expose the Argon40 fan as a standard Home Assistant fan entity."""

from typing import TYPE_CHECKING, Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DEFAULT_SPEED, DOMAIN

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
    """Add one fan linked to the controller's device."""
    async_add_entities([Argon40Fan(entry)])


class Argon40Fan(FanEntity):
    """Report the last successfully commanded speed, without claiming RPM feedback."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_speed_count = 100
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
    )

    def __init__(self, entry: Argon40ConfigEntry) -> None:
        """Link the fan to the shared runtime and stable device identifier."""
        self._controller: Argon40Controller = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)}, manufacturer="Argon40", name=entry.title
        )

    @property
    def available(self) -> bool:
        """Indicate whether the last I2C command succeeded."""
        return self._controller.available

    @property
    def percentage(self) -> int:
        """Return the commanded percentage."""
        return self._controller.percentage

    @property
    def is_on(self) -> bool:
        """Return whether a nonzero speed was requested."""
        return self.percentage > 0

    async def async_added_to_hass(self) -> None:
        """Subscribe to successful entity and legacy service commands."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._controller.signal_update, self.async_write_ha_state
            )
        )

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed through the shared command path."""
        await self._controller.async_set_speed(percentage)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,  # noqa: ARG002 - Standard fan API.
        **kwargs: Any,  # noqa: ARG002 - Standard fan API.
    ) -> None:
        """Use an explicit percentage or the previous nonzero speed."""
        await self.async_set_percentage(
            percentage
            if percentage is not None
            else self._controller.last_speed or DEFAULT_SPEED
        )

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002 - Standard fan API.
        """Stop the fan."""
        await self.async_set_percentage(0)
