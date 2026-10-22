"""Configure local Argon40 hardware through Home Assistant."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import CONF_DEVICE_TYPE, DEVICE_FAN_HAT, DEVICE_ONE, DOMAIN, I2C_HELP_URL
from .hardware import HardwareError, test_hardware


class Argon40ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Validate hardware and create a single local config entry."""

    VERSION = 1

    def __init__(self) -> None:
        """Keep the tested model until the user confirms the fan test."""
        self._device_type = DEVICE_ONE
        self._tested = False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Check I2C, the controller and the GPIO line before creating an entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            try:
                await self.hass.async_add_executor_job(test_hardware, self._device_type)
            except HardwareError as err:
                errors["base"] = err.code
            else:
                self._tested = True
                return await self.async_step_confirm()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_TYPE, default=self._device_type
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[DEVICE_ONE, DEVICE_FAN_HAT],
                            translation_key="device_type",
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders={"i2c_help_url": I2C_HELP_URL},
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to verify rotation: this MCU provides no RPM feedback."""
        self._abort_if_unique_id_configured()
        if not self._tested:
            return await self.async_step_user()
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input["fan_working"]:
                return self.async_create_entry(
                    title="Argon ONE V2"
                    if self._device_type == DEVICE_ONE
                    else "Argon Fan HAT",
                    data={CONF_DEVICE_TYPE: self._device_type},
                )
            errors["base"] = "fan_not_running"
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({vol.Required("fan_working", default=True): bool}),
            errors=errors,
        )
