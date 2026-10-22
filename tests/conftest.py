"""Fixtures for real Home Assistant setup with only GPIO and I2C mocked."""

from pathlib import Path
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import custom_components
import pytest

from homeassistant.core import callback

try:
    from pytest_homeassistant.common import MockConfigEntry
except ModuleNotFoundError:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

_REPO_ROOT = Path(__file__).resolve().parents[1]

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from homeassistant.core import Event, HomeAssistant


@pytest.fixture(autouse=True)
async def hardware(
    monkeypatch: pytest.MonkeyPatch,
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> AsyncGenerator[tuple[MagicMock, MagicMock]]:
    """Provide isolated hardware handles and unload entries before restoring mocks."""
    _ = enable_custom_integrations
    hass.config.skip_pip = True
    monkeypatch.setattr(
        custom_components,
        "__path__",
        [str(_REPO_ROOT / "custom_components")],
    )
    gpio = MagicMock(name="gpiod")
    gpio.EdgeEvent.Type.RISING_EDGE = 1
    gpio.EdgeEvent.Type.FALLING_EDGE = 2
    line = gpio.Chip.return_value.__enter__.return_value.request_lines.return_value
    line.fd = None
    gpio.Chip.return_value.__enter__.return_value.get_info.return_value = (
        SimpleNamespace(label="pinctrl-bcm2711")
    )
    smbus = MagicMock(name="smbus")
    monkeypatch.setitem(sys.modules, "gpiod", gpio)
    monkeypatch.setitem(sys.modules, "gpiod.line", MagicMock())
    monkeypatch.setitem(sys.modules, "smbus", smbus)
    from custom_components.argon40 import hardware as driver  # noqa: PLC0415 - Import after hardware stubs.

    monkeypatch.setattr(driver, "gpiod", gpio)
    monkeypatch.setattr(driver, "SMBus", smbus.SMBus)
    paths = MagicMock()
    paths.glob.return_value = [Path("/dev/gpiochip0")]
    monkeypatch.setattr(driver, "Path", MagicMock(return_value=paths))
    monkeypatch.setattr(driver, "time", MagicMock())
    yield gpio, smbus.SMBus
    for entry in hass.config_entries.async_loaded_entries("argon40"):
        await hass.config_entries.async_unload(entry.entry_id)


@pytest.fixture
def entry() -> MockConfigEntry:
    """Return an unregistered ONE case config entry."""
    return MockConfigEntry(
        domain="argon40",
        unique_id="argon40",
        title="Argon ONE V2",
        data={"device_type": "one_v2"},
    )


@pytest.fixture
async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> MockConfigEntry:
    """Load the integration and its real fan and event platforms."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
def events(hass: HomeAssistant) -> list[Event]:
    """Capture public legacy events on the real HA event bus."""
    captured: list[Event] = []

    @callback
    def capture(event: Event) -> None:
        captured.append(event)

    hass.bus.async_listen("argon40_event", capture)
    return captured
