"""Share fan commands and GPIO events between entities and legacy services."""

import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DEFAULT_SPEED, DOMAIN
from .hardware import Argon40Hardware

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class Argon40Controller:  # pylint: disable=too-many-instance-attributes
    """Own one local controller and serialize its blocking I2C operations."""

    def __init__(self, hass: HomeAssistant, entry_id: str, device_type: str) -> None:
        """Prepare the runtime without opening hardware."""
        self.hass = hass
        self.hardware = Argon40Hardware(device_type)
        self.percentage = DEFAULT_SPEED
        self.last_speed = DEFAULT_SPEED
        self.available = True
        self.button_available = True
        self.signal_update = f"{DOMAIN}_{entry_id}_update"
        self.signal_button = f"{DOMAIN}_{entry_id}_button"
        self._lock = asyncio.Lock()
        self._closed = False
        self._button_fd: int | None = None

    async def async_connect(self) -> None:
        """Open hardware off the event loop and start listening for GPIO edges."""
        await self.hass.async_add_executor_job(self.hardware.connect)
        try:
            self._button_fd = self.hardware.button_fd
            if self._button_fd is not None:
                self.hass.loop.add_reader(self._button_fd, self._async_button_ready)
        except Exception:
            await self.hass.async_add_executor_job(self.hardware.close)
            raise

    @callback
    def _async_button_ready(self) -> None:
        """Drain ready GPIO events without polling or waiting for an edge."""
        try:
            events = self.hardware.read_button_events()
        except OSError:
            _LOGGER.exception("Unable to read Argon40 button events")
            self.button_available = False
            async_dispatcher_send(self.hass, self.signal_update)
            if self._button_fd is not None:
                self.hass.loop.remove_reader(self._button_fd)
                self._button_fd = None
            return
        for event in events:
            async_dispatcher_send(self.hass, self.signal_button, event)
            self.hass.bus.async_fire(
                "argon40_event",
                {"action": "double-tap" if event == "double" else "long_press"},
            )

    async def async_set_speed(self, speed: int) -> None:
        """Apply a fan command and publish only successful state changes."""
        async with self._lock:
            await self._async_write(speed)
            self.percentage = speed
            if speed:
                self.last_speed = speed
            async_dispatcher_send(self.hass, self.signal_update)
            self.hass.bus.async_fire("argon40_event", {"speed": speed})

    async def async_set_mode(self, *, always_on: bool) -> None:
        """Preserve the legacy power-mode service without adding an options UI."""
        async with self._lock:
            await self._async_write(254 if always_on else 253)
            async_dispatcher_send(self.hass, self.signal_update)
            self.hass.bus.async_fire("argon40_event", {"always_on": always_on})

    async def _async_write(self, value: int) -> None:
        """Write off-loop and expose hardware failures to the caller."""
        if self._closed:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="not_configured"
            )
        try:
            await self.hass.async_add_executor_job(self.hardware.write_command, value)
        except OSError as err:
            self.available = False
            async_dispatcher_send(self.hass, self.signal_update)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="communication_error"
            ) from err
        self.available = True

    async def async_close(self) -> None:
        """Stop GPIO callbacks before releasing hardware, including at shutdown."""
        async with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._button_fd is not None:
                self.hass.loop.remove_reader(self._button_fd)
                self._button_fd = None
            await self.hass.async_add_executor_job(self.hardware.close)
