# Argon ONE Pi 3 & 4 Cases and Fan HAT support for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![GitHub CRON Workflow Status][cron-build-shield]][cron-build]
[![GitHub PUSH Workflow Status][push-build-shield]][push-build]

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]


_Component supports:_ [Argon ONE Raspberry Pi 4 Case][argon_one_pi4], [Argon ONE Raspberry Pi 3 Case][argon_one_pi3], [Argon Fan HAT][argon_fan_hat].

![example][exampleimg]

## Requirements and installation

Requires Home Assistant 2025.1 or newer and direct access to the Raspberry Pi's
GPIO and I2C hardware. Enable I2C before installing the integration; see the
[Home Assistant OS instructions](https://www.home-assistant.io/common-tasks/os#enable-i2c-via-home-assistant-operating-system-terminal).

Add `Misiu/argon40` as a custom repository in HACS (category: Integration), then
install Argon40. Alternatively, copy the entire `custom_components/argon40`
directory from this repository into your Home Assistant configuration directory.
Include all files and the `brand` directory. The resulting layout should include:

```text
custom_components/argon40/__init__.py
custom_components/argon40/const.py
custom_components/argon40/manifest.json
custom_components/argon40/services.yaml
custom_components/argon40/brand/
```

Add this entry to `configuration.yaml`, then restart Home Assistant:

```yaml
argon40:
```

Configuration uses YAML; there is no setup flow in the UI. If setup fails, check
Home Assistant's logs for the I2C error and verify that the hardware is accessible
from your Home Assistant installation.

## Fan control

The integration sets the initial fan speed to 10% and exposes two actions:

| Action | Required data | Effect |
| --- | --- | --- |
| `argon40.set_fan_speed` | `speed`: integer from 0 to 100 | Send a fan speed command; 0 stops the fan. |
| `argon40.set_mode` | `always_on`: boolean | Select always-on mode (`true`) or the default mode (`false`). |

For example, use Developer Tools > Actions:

```yaml
action: argon40.set_fan_speed
data:
  speed: 40
```

```yaml
action: argon40.set_mode
data:
  always_on: true
```

Temperature control requires your own automation. You can get a temperature
sensor from the [System monitor integration](https://www.home-assistant.io/integrations/systemmonitor/#processor-temperature),
or configure a command-line sensor:

```yaml
command_line:
  - sensor:
      name: CPU Temp
      unique_id: cpu_temp
      command: "cat /sys/class/thermal/thermal_zone0/temp"
      unit_of_measurement: "°C"
      value_template: "{{ value | multiply(0.001) | round(1) }}"
```

This example sets the fan to 40% after the temperature stays above 50°C for one
minute. Add your own cooling and startup rules as needed; this example does not
turn the fan down again or restore a speed after restarting Home Assistant.

```yaml
automation:
  - alias: "Set fan speed"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.cpu_temp
        above: 50
        for:
          minutes: 1
    actions:
      - action: argon40.set_fan_speed
        data:
          speed: 40
```

After a successful command, the integration fires `argon40_event` with either
`speed` or `always_on` in its event data. These events describe the command sent;
they do not report measured fan speed. Button double-tap detection is not
implemented.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[argon_one_pi4]: https://www.argon40.com/argon-one-raspberry-pi-4-case.html
[argon_one_pi3]: https://www.argon40.com/argon-one-raspberry-pi-3-case.html
[argon_fan_hat]: https://www.argon40.com/argon-fan-hat-for-raspberry-pi-4-raspberry-pi-3b-and-raspberry-pi-3-b.html

[buymecoffee]: https://www.buymeacoffee.com/Misiu
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge

[commits]: https://github.com/Misiu/argon40/commits/main
[commits-shield]: https://img.shields.io/github/commit-activity/y/Misiu/argon40.svg?style=for-the-badge

[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge

[exampleimg]: example.png

[license-shield]: https://img.shields.io/github/license/Misiu/argon40.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40Misiu-blue.svg?style=for-the-badge

[releases-shield]: https://img.shields.io/github/release/Misiu/argon40.svg?style=for-the-badge
[releases]: https://github.com/Misiu/argon40/releases

[cron-build-shield]: https://img.shields.io/github/actions/workflow/status/Misiu/argon40/cron.yml?label=CRON&style=for-the-badge
[cron-build]: https://github.com/Misiu/argon40/actions/workflows/cron.yml

[push-build-shield]: https://img.shields.io/github/actions/workflow/status/Misiu/argon40/pull_and_push.yml?label=PULL%20%26%20PUSH&style=for-the-badge
[push-build]: https://github.com/Misiu/argon40/actions/workflows/pull_and_push.yml
