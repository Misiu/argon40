"""Exercise entity setup, fan services, GPIO pulses and hardware cleanup."""

import logging
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import Event, HomeAssistant


@pytest.mark.parametrize("device_type", ["one_v2", "fan_hat"])
async def test_entities(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hardware: tuple[MagicMock, MagicMock],
    device_type: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Create one device with a fan and an optional button, without YAML."""
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, data={"device_type": device_type})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert {entity.domain for entity in entities} == (
        {"fan", "event"} if device_type == "one_v2" else {"fan"}
    )
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    assert {entity.device_id for entity in entities} == {devices[0].id}
    hardware[1].assert_called_once_with(1)
    hardware[1].return_value.write_byte.assert_called_once_with(0x1A, 10)
    if device_type == "fan_hat":
        hardware[0].Chip.assert_not_called()
    integration = await async_get_integration(hass, "argon40")
    assert f"Version: {integration.version}" in caplog.text


async def test_fan_actions(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hardware: tuple[MagicMock, MagicMock],
) -> None:
    """Keep native fan actions and legacy commands on the same state path."""
    registry = er.async_get(hass)
    fan_id = registry.async_get_entity_id("fan", "argon40", "argon40_fan")
    assert hass.states.get(fan_id).attributes["percentage"] == 10
    for service, data, expected in [
        ("set_percentage", {"percentage": 57}, 57),
        ("turn_off", {}, 0),
        ("turn_on", {}, 57),
        ("turn_on", {"percentage": 100}, 100),
    ]:
        await hass.services.async_call(
            "fan", service, {"entity_id": fan_id, **data}, blocking=True
        )
        await hass.async_block_till_done()
        assert hass.states.get(fan_id).attributes["percentage"] == expected
        hardware[1].return_value.write_byte.assert_called_with(0x1A, expected)
    assert setup_entry.runtime_data.percentage == 100


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (19, None),
        (20, "double"),
        (25, "double"),
        (30, "double"),
        (31, None),
        (40, "hold"),
        (45, "hold"),
        (50, "hold"),
        (51, None),
        (65, None),
    ],
)
async def test_button_pulses(  # noqa: PLR0913 - HA fixtures and pulse cases.
    *,
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hardware: tuple[MagicMock, MagicMock],
    events: list[Event],
    duration: int,
    expected: str | None,
) -> None:
    """Decode manufacturer pulse widths using kernel edge timestamps."""
    line = hardware[
        0
    ].Chip.return_value.__enter__.return_value.request_lines.return_value
    line.read_edge_events.return_value = [
        SimpleNamespace(event_type=2, timestamp_ns=1),
        SimpleNamespace(event_type=1, timestamp_ns=1_000_000_000),
        SimpleNamespace(
            event_type=2, timestamp_ns=1_000_000_000 + duration * 1_000_000
        ),
    ]
    setup_entry.runtime_data._async_button_ready()  # noqa: SLF001 - Exercise the registered fd callback.
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "event", "argon40", "argon40_button"
    )
    state = hass.states.get(entity_id)
    assert state.attributes["event_types"] == ["double", "hold"]
    assert state.attributes.get("event_type") == expected
    assert [event.data for event in events] == (
        [{"action": "double-tap" if expected == "double" else "long_press"}]
        if expected
        else []
    )


async def test_button_read_error(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hardware: tuple[MagicMock, MagicMock],
) -> None:
    """A GPIO failure marks the button unavailable without disabling the fan."""
    line = hardware[
        0
    ].Chip.return_value.__enter__.return_value.request_lines.return_value
    line.read_edge_events.side_effect = OSError(5, "GPIO read failed")
    setup_entry.runtime_data._async_button_ready()  # noqa: SLF001 - Exercise the registered fd callback.
    await hass.async_block_till_done()
    entities = er.async_entries_for_config_entry(
        er.async_get(hass), setup_entry.entry_id
    )
    states = {
        entity.domain: hass.states.get(entity.entity_id).state for entity in entities
    }
    assert states == {"fan": "on", "event": "unavailable"}


async def test_button_debug_logging(
    setup_entry: MockConfigEntry,
    hardware: tuple[MagicMock, MagicMock],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Keep raw edges and unknown pulses visible, including across read batches."""
    caplog.set_level(logging.DEBUG, logger="custom_components.argon40.hardware")
    line = hardware[
        0
    ].Chip.return_value.__enter__.return_value.request_lines.return_value
    line.read_edge_events.side_effect = [
        [
            SimpleNamespace(event_type=2, timestamp_ns=500_000_000),
            SimpleNamespace(event_type=1, timestamp_ns=1_000_000_000),
        ],
        [
            SimpleNamespace(event_type=2, timestamp_ns=1_025_000_000),
            SimpleNamespace(event_type=1, timestamp_ns=2_000_000_000),
            SimpleNamespace(event_type=2, timestamp_ns=2_075_000_000),
        ],
    ]
    driver = setup_entry.runtime_data.hardware
    assert driver.read_button_events() == []
    assert driver.read_button_events() == ["double"]
    assert (
        "Button GPIO4 edge=falling timestamp_ns=500000000 since_previous_ms=None"
        in caplog.messages
    )
    assert (
        "Button GPIO4 falling edge without a preceding rising edge" in caplog.messages
    )
    assert (
        "Button GPIO4 edge=rising timestamp_ns=1000000000 since_previous_ms=500.0"
        in caplog.messages
    )
    assert (
        "Button GPIO4 edge=falling timestamp_ns=1025000000 since_previous_ms=25.0"
        in caplog.messages
    )
    assert (
        "Button GPIO4 edge=rising timestamp_ns=2000000000 since_previous_ms=975.0"
        in caplog.messages
    )
    assert (
        "Button GPIO4 edge=falling timestamp_ns=2075000000 since_previous_ms=75.0"
        in caplog.messages
    )
    assert (
        "Button GPIO4 pulse duration_ms=25.000 decoded_event=double" in caplog.messages
    )
    assert (
        "Button GPIO4 pulse duration_ms=75.000 decoded_event=unrecognized"
        in caplog.messages
    )


async def test_unload(
    hass: HomeAssistant, entry: MockConfigEntry, hardware: tuple[MagicMock, MagicMock]
) -> None:
    """Remove the GPIO reader before releasing the line, and close handles once."""
    line = hardware[
        0
    ].Chip.return_value.__enter__.return_value.request_lines.return_value
    line.fd = 123
    entry.add_to_hass(hass)
    with (
        patch.object(hass.loop, "add_reader") as add_reader,
        patch.object(hass.loop, "remove_reader") as remove_reader,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        add_reader.assert_called_once_with(123, entry.runtime_data._async_button_ready)  # noqa: SLF001 - Verify fd registration.
        controller = entry.runtime_data
        assert await hass.config_entries.async_unload(entry.entry_id)
        remove_reader.assert_called_once_with(123)
        await controller.async_close()
    line.release.assert_called_once()
    hardware[1].return_value.close.assert_called_once()


async def test_failed_unload_keeps_hardware(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hardware: tuple[MagicMock, MagicMock],
) -> None:
    """Retain hardware after a failed unload, then release it at HA shutdown."""
    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=False
    ):
        assert not await hass.config_entries.async_unload(setup_entry.entry_id)
    hardware[1].return_value.close.assert_not_called()
    assert setup_entry.state is ConfigEntryState.FAILED_UNLOAD
    await hass.async_stop()
    hardware[1].return_value.close.assert_called_once()


async def test_service_after_unload(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hardware: tuple[MagicMock, MagicMock],
) -> None:
    """Reject commands after unloading instead of writing to a closed I2C bus."""
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    hardware[1].return_value.write_byte.reset_mock()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "argon40", "set_mode", {"always_on": True}, blocking=True
        )
    hardware[1].return_value.write_byte.assert_not_called()


async def test_fan_failure_and_recovery(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hardware: tuple[MagicMock, MagicMock],
) -> None:
    """Report I2C failure and restore availability on a successful legacy command."""
    fan_id = er.async_get(hass).async_get_entity_id("fan", "argon40", "argon40_fan")
    hardware[1].return_value.write_byte.side_effect = OSError(121, "I2C unavailable")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "argon40", "set_fan_speed", {"speed": 40}, blocking=True
        )
    await hass.async_block_till_done()
    assert hass.states.get(fan_id).state == "unavailable"
    assert setup_entry.runtime_data.percentage == 10
    hardware[1].return_value.write_byte.side_effect = None
    await hass.services.async_call(
        "argon40", "set_fan_speed", {"speed": 40}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(fan_id).state == "on"
    assert hass.states.get(fan_id).attributes["percentage"] == 40


async def test_retry_setup(
    hass: HomeAssistant, entry: MockConfigEntry, hardware: tuple[MagicMock, MagicMock]
) -> None:
    """Unavailable I2C schedules HA's native retry without leaking GPIO handles."""
    hardware[1].side_effect = OSError(2, "Missing I2C")
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    hardware[0].Chip.assert_not_called()


async def test_yaml_repair(
    hass: HomeAssistant, hardware: tuple[MagicMock, MagicMock]
) -> None:
    """Obsolete YAML creates HA's standard repair without opening hardware."""
    assert await async_setup_component(hass, "argon40", {"argon40": {}})
    assert ir.async_get(hass).async_get_issue(
        "homeassistant", "config_entry_only_argon40"
    )
    hardware[1].assert_not_called()
