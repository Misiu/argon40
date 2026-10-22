"""Local I2C fan control and libgpiod button input."""

import logging
from pathlib import Path
import time

import gpiod  # pylint: disable=import-error
from gpiod.line import Bias, Clock, Direction, Edge  # pylint: disable=import-error
from smbus import SMBus  # pylint: disable=import-error

from .const import BUTTON_GPIO, DEFAULT_SPEED, DEVICE_ONE, DOMAIN, I2C_ADDRESS, I2C_BUS

_LOGGER = logging.getLogger(__name__)
_I2C_UNAVAILABLE = "i2c_unavailable"
_FAN_UNAVAILABLE = "fan_unavailable"
_GPIO_UNAVAILABLE = "gpio_unavailable"
# Argon40Tech/Argon40case, src/scripts/argononed.py and
# src/scripts/argonpowerbutton-libgpiod.py: BCM4 encodes MCU actions as pulses.
_DOUBLE_CLICK_MIN_NS = 20_000_000
_DOUBLE_CLICK_MAX_NS = 30_000_000
_LONG_PRESS_MIN_NS = 40_000_000
_LONG_PRESS_MAX_NS = 50_000_000


class HardwareError(Exception):
    """A hardware error with a translatable config-flow error key."""

    def __init__(self, code: str) -> None:
        """Store the error key without exposing platform-specific error text."""
        super().__init__(code)
        self.code = code


class Argon40Hardware:
    """Own the I2C bus and, for ONE cases, the GPIO line request."""

    def __init__(self, device_type: str) -> None:
        """Initialize without opening hardware handles."""
        self._device_type = device_type
        self._bus: SMBus | None = None
        self._request: gpiod.LineRequest | None = None
        self._pulse_start: int | None = None
        self._last_edge: int | None = None

    def connect(self) -> None:
        """Open and validate hardware; call from an executor."""
        try:
            self._bus = SMBus(I2C_BUS)
        except OSError as err:
            raise HardwareError(_I2C_UNAVAILABLE) from err
        try:
            try:
                self.write_command(DEFAULT_SPEED)
            except OSError as err:
                raise HardwareError(_FAN_UNAVAILABLE) from err
            if self._device_type == DEVICE_ONE:
                self._request = self._request_button()
        except Exception:
            self.close()
            raise

    @staticmethod
    def _request_button() -> gpiod.LineRequest:
        """Find the Pi GPIO controller by label rather than a fixed chip number."""
        try:
            for path in sorted(Path("/dev").glob("gpiochip*")):
                with gpiod.Chip(str(path)) as chip:
                    if "pinctrl" not in chip.get_info().label:
                        continue
                    request = chip.request_lines(
                        consumer=DOMAIN,
                        config={
                            BUTTON_GPIO: gpiod.LineSettings(
                                direction=Direction.INPUT,
                                edge_detection=Edge.BOTH,
                                bias=Bias.PULL_DOWN,
                                event_clock=Clock.MONOTONIC,
                            )
                        },
                    )
                    _LOGGER.debug(
                        "Monitoring button GPIO%s on %s: both edges, monotonic clock, pull-down bias",
                        BUTTON_GPIO,
                        path,
                    )
                    return request
        except OSError as err:
            raise HardwareError(_GPIO_UNAVAILABLE) from err
        raise HardwareError(_GPIO_UNAVAILABLE)

    @property
    def button_fd(self) -> int | None:
        """Return the event descriptor, or None for Fan HAT hardware."""
        return self._request.fd if self._request is not None else None

    def read_button_events(self) -> list[str]:
        """Decode documented MCU pulses; call only when the descriptor is ready."""
        events: list[str] = []
        if self._request is None:
            return events
        for edge in self._request.read_edge_events():
            rising = edge.event_type == gpiod.EdgeEvent.Type.RISING_EDGE
            _LOGGER.debug(
                "Button GPIO%s edge=%s timestamp_ns=%s since_previous_ms=%s",
                BUTTON_GPIO,
                "rising" if rising else "falling",
                edge.timestamp_ns,
                (edge.timestamp_ns - self._last_edge) / 1_000_000
                if self._last_edge is not None
                else None,
            )
            self._last_edge = edge.timestamp_ns
            if rising:
                self._pulse_start = edge.timestamp_ns
            elif self._pulse_start is not None:
                duration = edge.timestamp_ns - self._pulse_start
                self._pulse_start = None
                event_type = None
                if _DOUBLE_CLICK_MIN_NS <= duration <= _DOUBLE_CLICK_MAX_NS:
                    event_type = "double"
                elif _LONG_PRESS_MIN_NS <= duration <= _LONG_PRESS_MAX_NS:
                    event_type = "hold"
                _LOGGER.debug(
                    "Button GPIO%s pulse duration_ms=%.3f decoded_event=%s",
                    BUTTON_GPIO,
                    duration / 1_000_000,
                    event_type or "unrecognized",
                )
                if event_type is not None:
                    events.append(event_type)
            else:
                _LOGGER.debug(
                    "Button GPIO%s falling edge without a preceding rising edge",
                    BUTTON_GPIO,
                )
        return events

    def write_command(self, speed: int) -> None:
        """Write a percentage to the MCU; call from an executor."""
        if self._bus is None:
            message = "I2C bus is closed"
            raise OSError(message)
        self._bus.write_byte(I2C_ADDRESS, speed)
        _LOGGER.debug(
            "I2C command sent: bus=%s address=0x%02x value=0x%02x (%s)",
            I2C_BUS,
            I2C_ADDRESS,
            speed,
            speed,
        )

    def close(self) -> None:
        """Release only this integration's handles; call from an executor."""
        request, self._request = self._request, None
        bus, self._bus = self._bus, None
        self._pulse_start = self._last_edge = None
        try:
            if request is not None:
                request.release()
        finally:
            if bus is not None:
                bus.close()


def test_hardware(device_type: str) -> None:
    """Run a short fan test, restore the startup speed and release all handles."""
    hardware = Argon40Hardware(device_type)
    try:
        hardware.connect()
        hardware.write_command(100)
        time.sleep(2)
        hardware.write_command(DEFAULT_SPEED)
    except OSError as err:
        raise HardwareError(_FAN_UNAVAILABLE) from err
    finally:
        hardware.close()
