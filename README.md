# Argon ONE V2 and Fan HAT support for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![GitHub CRON Workflow Status][cron-build-shield]][cron-build]
[![GitHub PUSH Workflow Status][push-build-shield]][push-build]

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]


_Component targets:_ [Argon ONE V2 for Raspberry Pi 4][argon_one_pi4] and [Argon Fan HAT][argon_fan_hat].

![example][exampleimg]

## Requirements and installation

Requires Home Assistant 2026.7.0 or newer and direct access to the Raspberry Pi's
GPIO and I2C hardware. Enable I2C before installing the integration; see the
[community guide for the HassOS I2C Configurator add-on](https://community.home-assistant.io/t/add-on-hassos-i2c-configurator/264167).

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

Restart Home Assistant, then open **Settings > Devices & services > Add integration >
Argon40**. Select ONE V2 or Fan HAT. Setup checks I2C bus 1, writes to the controller
at address `0x1a`, and briefly runs the fan at 100% before setting it to 10%.
Confirm that you saw or heard the fan spin: an I2C acknowledgement alone cannot
verify physical rotation. ONE V2 setup also checks access to its GPIO4 button line.

The integration creates one device with a fan entity. ONE V2 also has a button
event entity; Fan HAT does not use a button GPIO. There are no configurable options.
The fan reports the last commanded speed, not measured RPM.

If setup fails, follow the error shown in the form. Home Assistant needs access to
`/dev/i2c-1` and, for ONE V2, the Raspberry Pi GPIO controller under `/dev/gpiochip*`.
Other software must not claim GPIO4 or independently change the fan speed.

YAML configuration is no longer used or imported. Add the integration through the
UI, then remove the old `argon40:` entry from `configuration.yaml` and restart.
Home Assistant raises a Repairs issue while that obsolete YAML entry remains.

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
they do not report measured fan speed.

## ONE V2 button

The event entity exposes `double` and `hold`, decoded from GPIO4 pulse
widths using the [manufacturer's Python driver](https://github.com/Argon40Tech/Argon40case/blob/master/src/scripts/argonpowerbutton-libgpiod.py)
and its [ONE daemon description](https://github.com/Argon40Tech/Argon40case/blob/master/src/scripts/argononed.py):

| Gesture | MCU pulse width | Event type |
| --- | --- | --- |
| Double tap | 20–30 ms | `double` |
| Hold for 3 seconds and release | 40–50 ms | `hold` |

The event entity currently exposes only `double` and `hold`. Separate physical
press, release and single-click signals still need verification on real hardware.

The integration publishes events for automations; it does not reboot or shut down
Home Assistant when these pulses arrive. It also preserves the legacy
`argon40_event` payload `{"action": "double-tap"}` for double clicks and uses
`{"action": "long_press"}` for long presses.

The [ONE V2 manual, page 11](https://www.mouser.com/datasheet/3/1361/1/AR1_PI4_V2_INSTRUCTION_MANUAL_20200922.pdf#page=11)
lists a short press while powered on as having no action. GPIO4 carries a pulse
encoding an MCU request, rather than separate edges for each physical button
press. Counting two pulses would therefore count two MCU requests, not two clicks.
Physical button behavior still needs verification on a real case.

### Capture button diagnostics

To enable debug logging immediately, open **Developer Tools > Actions**, switch
to YAML mode and run:

```yaml
action: logger.set_level
data:
  custom_components.argon40: debug
```

This takes effect without restarting Home Assistant. After collecting the logs,
run the same action with the previous log level (for example, `info`):

```yaml
action: logger.set_level
data:
  custom_components.argon40: info
```

These changes apply only to the current session. To keep debug logging enabled
after a restart, add it to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.argon40: debug
```

Merge this into any existing `logger` configuration and restart Home Assistant.
Remove this setting after testing if it should not persist across restarts.

The log records the GPIO chip selected at setup, every rising and falling edge,
its kernel monotonic timestamp in nanoseconds, and the interval since the previous
edge in milliseconds. Completed pulses include their duration and the decoded
event, or `unrecognized`. Falling edges without an earlier rising edge are also
logged. Raw edges are recorded before classification, including signals that do
not produce an event entity update.

Test single clicks, double clicks and holds separately, leaving a few seconds
between attempts. Note the case revision and gesture next to each log excerpt so
the raw signals can be compared. Kernel timestamps measure the edges; log message
timestamps can be later because events are read in batches. Disable debug logging
after collecting the results.

The `argon40.set_mode` action remains available for cases configured through
software. Set `always_on: true` to send `0xfe` (Always On), or `false` to send
`0xfd` (default mode), to I2C address `0x1a`. Successful I2C writes are included in
the debug log. This action controls power-on behavior, not button event detection.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[argon_one_pi4]: https://www.argon40.com/argon-one-raspberry-pi-4-case.html
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
