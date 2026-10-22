"""Constants for Argon40."""

NAME = "Argon40"
DOMAIN = "argon40"
CONF_DEVICE_TYPE = "device_type"
DEVICE_ONE = "one_v2"
DEVICE_FAN_HAT = "fan_hat"
I2C_ADDRESS = 0x1A
I2C_BUS = 1
BUTTON_GPIO = 4
DEFAULT_SPEED = 10
BUTTON_EVENTS = ("double", "hold")
I2C_HELP_URL = (
    "https://community.home-assistant.io/t/add-on-hassos-i2c-configurator/264167"
)

ATTR_SPEED_NAME = "speed"
SERVICE_SET_FAN_SPEED = "set_fan_speed"

ATTR_ALWAYS_ON_NAME = "always_on"
SERVICE_SET_MODE = "set_mode"

ISSUE_URL = "https://github.com/Misiu/argon40/issues"
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: %s
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
