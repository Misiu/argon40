"""Validate the real config flow against mocked local hardware."""

from typing import TYPE_CHECKING
from unittest.mock import call

import pytest

from homeassistant.data_entry_flow import FlowResultType

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.core import HomeAssistant


@pytest.mark.parametrize("device_type", ["one_v2", "fan_hat"])
async def test_create_entry(
    hass: HomeAssistant, hardware: tuple[MagicMock, MagicMock], device_type: str
) -> None:
    """Require a successful bus test and physical fan confirmation."""
    result = await hass.config_entries.flow.async_init(
        "argon40", context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_type": device_type}
    )
    assert result["step_id"] == "confirm"
    assert not hass.config_entries.async_entries("argon40")
    bus = hardware[1].return_value
    assert bus.write_byte.call_args_list == [
        call(0x1A, 10),
        call(0x1A, 100),
        call(0x1A, 10),
    ]
    bus.close.assert_called_once()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fan_working": False}
    )
    assert result["errors"] == {"base": "fan_not_running"}
    assert not hass.config_entries.async_entries("argon40")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"fan_working": True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"device_type": device_type}
    assert result["result"].unique_id == "argon40"
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        ("open", "i2c_unavailable"),
        ("write", "fan_unavailable"),
        ("gpio", "gpio_unavailable"),
        ("test", "fan_unavailable"),
    ],
)
async def test_hardware_failure(
    hass: HomeAssistant,
    hardware: tuple[MagicMock, MagicMock],
    failure: str,
    error: str,
) -> None:
    """Present actionable errors and release partially opened hardware."""
    gpio, factory = hardware
    if failure == "open":
        factory.side_effect = OSError(2, "Missing I2C bus")
    elif failure == "write":
        factory.return_value.write_byte.side_effect = OSError(121, "No response")
    elif failure == "test":
        factory.return_value.write_byte.side_effect = [
            None,
            OSError(121, "No response"),
        ]
    else:
        gpio.Chip.side_effect = OSError(16, "GPIO busy")
    result = await hass.config_entries.flow.async_init(
        "argon40", context={"source": "user"}, data={"device_type": "one_v2"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert result["description_placeholders"]["i2c_help_url"].startswith(
        "https://community.home-assistant.io/"
    )
    assert not hass.config_entries.async_entries("argon40")
    if failure != "open":
        factory.return_value.close.assert_called_once()


async def test_single_instance(
    hass: HomeAssistant, entry: MockConfigEntry, hardware: tuple[MagicMock, MagicMock]
) -> None:
    """Reject a duplicate before touching a running controller."""
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "argon40", context={"source": "user"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    hardware[1].assert_not_called()
