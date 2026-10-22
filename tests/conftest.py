"""Fixtures for testing Argon40 with Home Assistant and mocked hardware."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import custom_components
import pytest

from homeassistant.core import callback

if TYPE_CHECKING:
    from homeassistant.core import Event, HomeAssistant


@pytest.fixture(autouse=True)
def hardware(
    monkeypatch: pytest.MonkeyPatch,
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> tuple[MagicMock, MagicMock]:
    """Mock only hardware modules and skip installing their native dependencies."""
    _ = enable_custom_integrations
    hass.config.skip_pip = True
    # The harness also supplies example custom integrations; scan our checkout.
    monkeypatch.setattr(
        custom_components,
        "__path__",
        [str(Path(__file__).resolve().parents[1] / "custom_components")],
    )
    gpio = MagicMock(name="GPIO")
    gpio.RPI_REVISION = 3
    smbus = MagicMock(name="smbus")
    monkeypatch.setitem(sys.modules, "RPi", MagicMock(GPIO=gpio))
    monkeypatch.setitem(sys.modules, "smbus", smbus)
    if integration := sys.modules.get("custom_components.argon40"):
        monkeypatch.setattr(integration, "GPIO", gpio)
        monkeypatch.setattr(integration, "SMBus", smbus.SMBus)
    return gpio, smbus.SMBus


@pytest.fixture
def events(hass: HomeAssistant) -> list[Event]:
    """Capture the integration's public events on the real HA event bus."""
    captured: list[Event] = []

    @callback
    def capture(event: Event) -> None:
        captured.append(event)

    hass.bus.async_listen("argon40_event", capture)
    return captured
