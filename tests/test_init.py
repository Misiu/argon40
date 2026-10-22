"""Exercise setup and public services through Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from homeassistant.core import Event, HomeAssistant


pytestmark = pytest.mark.usefixtures("setup_entry")


@pytest.mark.parametrize(
    ("speed", "expected"), [(0, 0), (40, 40), (100, 100), ("50", 50)]
)
async def test_fan_speed(
    hass: HomeAssistant,
    hardware: tuple[MagicMock, MagicMock],
    events: list[Event],
    speed: int | str,
    expected: int,
) -> None:
    """Validate service data, write the fan command and emit its public event."""
    bus = hardware[1].return_value
    bus.write_byte.reset_mock()

    await hass.services.async_call(
        "argon40", "set_fan_speed", {"speed": speed}, blocking=True
    )
    await hass.async_block_till_done()

    bus.write_byte.assert_called_once_with(0x1A, expected)
    assert [event.data for event in events] == [{"speed": expected}]


@pytest.mark.parametrize(
    "data", [{}, {"speed": -1}, {"speed": 101}, {"speed": "invalid"}, {"speed": None}]
)
async def test_invalid_fan_speed(
    hass: HomeAssistant,
    hardware: tuple[MagicMock, MagicMock],
    events: list[Event],
    data: dict[str, object],
) -> None:
    """Reject invalid service data before touching the device."""
    bus = hardware[1].return_value
    bus.write_byte.reset_mock()

    with pytest.raises(vol.Invalid):
        await hass.services.async_call("argon40", "set_fan_speed", data, blocking=True)

    await hass.async_block_till_done()
    bus.write_byte.assert_not_called()
    assert not events


@pytest.mark.parametrize(
    ("enabled", "expected"),
    [
        (True, (True, 254)),
        (False, (False, 253)),
        ("on", (True, 254)),
        ("off", (False, 253)),
    ],
)
async def test_mode(
    *,
    hass: HomeAssistant,
    hardware: tuple[MagicMock, MagicMock],
    events: list[Event],
    enabled: bool | str,
    expected: tuple[bool, int],
) -> None:
    """Validate mode input, send the device command and emit its public event."""
    bus = hardware[1].return_value
    bus.write_byte.reset_mock()

    await hass.services.async_call(
        "argon40", "set_mode", {"always_on": enabled}, blocking=True
    )
    await hass.async_block_till_done()

    bus.write_byte.assert_called_once_with(0x1A, expected[1])
    assert [event.data for event in events] == [{"always_on": expected[0]}]


@pytest.mark.parametrize("data", [{}, {"always_on": "invalid"}, {"always_on": None}])
async def test_invalid_mode(
    hass: HomeAssistant,
    hardware: tuple[MagicMock, MagicMock],
    data: dict[str, object],
) -> None:
    """Reject missing or invalid mode values without issuing I2C commands."""
    bus = hardware[1].return_value
    bus.write_byte.reset_mock()

    with pytest.raises(vol.Invalid):
        await hass.services.async_call("argon40", "set_mode", data, blocking=True)

    bus.write_byte.assert_not_called()


@pytest.mark.parametrize(
    ("service", "data"),
    [("set_fan_speed", {"speed": 40}), ("set_mode", {"always_on": True})],
)
async def test_service_io_error(
    hass: HomeAssistant,
    hardware: tuple[MagicMock, MagicMock],
    events: list[Event],
    service: str,
    data: dict[str, object],
) -> None:
    """Surface a failed hardware command without emitting a success event."""
    hardware[1].return_value.write_byte.side_effect = OSError(5, "I2C unavailable")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("argon40", service, data, blocking=True)

    await hass.async_block_till_done()
    assert not events
