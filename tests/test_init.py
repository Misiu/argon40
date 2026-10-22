"""Exercise setup and public services through Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import voluptuous as vol

from homeassistant.setup import async_setup_component

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from homeassistant.core import Event, HomeAssistant


@pytest.mark.parametrize(("revision", "bus_number"), [(1, 0), (2, 1), (3, 1), (4, 0)])
async def test_setup(
    hass: HomeAssistant,
    hardware: tuple[MagicMock, MagicMock],
    revision: int,
    bus_number: int,
) -> None:
    """Select the hardware bus, initialize the fan and register public services."""
    gpio, bus_factory = hardware
    gpio.RPI_REVISION = revision

    assert await async_setup_component(hass, "argon40", {"argon40": {}})

    bus_factory.assert_called_once_with(bus_number)
    bus_factory.return_value.write_byte.assert_called_once_with(0x1A, 10)
    gpio.setup.assert_called_once_with(4, gpio.IN, pull_up_down=gpio.PUD_DOWN)
    assert hass.services.has_service("argon40", "set_fan_speed")
    assert hass.services.has_service("argon40", "set_mode")


@pytest.mark.parametrize("failure", ["open", "write"])
async def test_setup_io_error(
    hass: HomeAssistant,
    hardware: tuple[MagicMock, MagicMock],
    failure: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Fail setup cleanly without registering services when I2C is unavailable."""
    _, bus_factory = hardware
    target = bus_factory if failure == "open" else bus_factory.return_value.write_byte
    target.side_effect = OSError(5, "I2C unavailable")

    assert not await async_setup_component(hass, "argon40", {"argon40": {}})
    assert "I2C unavailable" in caplog.text
    assert not hass.services.has_service("argon40", "set_fan_speed")
    assert not hass.services.has_service("argon40", "set_mode")


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
    assert await async_setup_component(hass, "argon40", {"argon40": {}})
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
    assert await async_setup_component(hass, "argon40", {"argon40": {}})
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
    assert await async_setup_component(hass, "argon40", {"argon40": {}})
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
    assert await async_setup_component(hass, "argon40", {"argon40": {}})
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
    assert await async_setup_component(hass, "argon40", {"argon40": {}})
    hardware[1].return_value.write_byte.side_effect = OSError(5, "I2C unavailable")

    with pytest.raises(OSError, match="I2C unavailable"):
        await hass.services.async_call("argon40", service, data, blocking=True)

    await hass.async_block_till_done()
    assert not events
