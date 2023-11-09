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

## Installation

1. Enable I2C. This is the most important step. Disabled I2C prevents the integraion from running and shows an error in logs.
   * [Official way](https://www.home-assistant.io/common-tasks/os#enable-i2c-via-home-assistant-operating-system-terminal)
   * [Using Add-on HassOS I2C Configurator](https://community.home-assistant.io/t/add-on-hassos-i2c-configurator/264167) (the easiest way)
3. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
4. If you do not have a `custom_components` directory (folder) there, you need to create it.
5. In the `custom_components` directory (folder) create a new folder called `argon40`.
6. Download _all_ the files from the `custom_components/argon40/` directory (folder) in this repository.
7. Place the files you downloaded in the new directory (folder) you created.
8. Add `argon40:` to your `configuration.yaml`
9. Restart Home Assistant

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/argon40/__init__.py
custom_components/argon40/const.py
custom_components/argon40/manifest.json
custom_components/argon40/services.yaml
```

## Configuration is done via configuration.yaml

<!---->

#### Config

1. Add CPU Temperature sensor:
```yaml
sensor:
  - platform: command_line
    name: CPU Temp
    command: "cat /sys/class/thermal/thermal_zone0/temp"
    unit_of_measurement: "°C"
    value_template: "{{ value | multiply(0.001) | round(1) }}"
```
2. Add automation:
```yaml
automation:
alias: Set CPU Fan Speed
description: Adjust fan speed based on CPU temperature
trigger:
  - platform: homeassistant
    event: start
  - platform: numeric_state
    entity_id: sensor.processor_temperature
    below: "35"
  - platform: numeric_state
    entity_id: sensor.processor_temperature
    above: "35"
  - platform: numeric_state
    entity_id: sensor.processor_temperature
    above: "45"
  - platform: numeric_state
    entity_id: sensor.processor_temperature
    above: "50"
  - platform: numeric_state
    entity_id: sensor.processor_temperature
    above: "55"
  - platform: numeric_state
    entity_id: sensor.processor_temperature
    above: "60"
  - platform: numeric_state
    entity_id: sensor.processor_temperature
    above: "65"
  - platform: numeric_state
    entity_id: sensor.processor_temperature
    above: "70"
action:
  - choose:
      - conditions:
          - condition: numeric_state
            entity_id: sensor.processor_temperature
            above: "70"
        sequence:
          - service: argon40.set_fan_speed
            data:
              speed: 100
          - service: input_number.set_value
            data:
              value: 100
            target:
              entity_id: input_number.current_fanspeed
      - conditions:
          - condition: numeric_state
            entity_id: sensor.processor_temperature
            above: "65"
        sequence:
          - service: argon40.set_fan_speed
            data:
              speed: 75
          - service: input_number.set_value
            data:
              value: 75
            target:
              entity_id: input_number.current_fanspeed
      - conditions:
          - condition: numeric_state
            entity_id: sensor.processor_temperature
            above: "60"
        sequence:
          - service: argon40.set_fan_speed
            data:
              speed: 50
          - service: input_number.set_value
            data:
              value: 50
            target:
              entity_id: input_number.current_fanspeed
      - conditions:
          - condition: numeric_state
            entity_id: sensor.processor_temperature
            above: "55"
        sequence:
          - service: argon40.set_fan_speed
            data:
              speed: 40
          - service: input_number.set_value
            data:
              value: 40
            target:
              entity_id: input_number.current_fanspeed
      - conditions:
          - condition: numeric_state
            entity_id: sensor.processor_temperature
            above: "50"
        sequence:
          - service: argon40.set_fan_speed
            data:
              speed: 30
          - service: input_number.set_value
            data:
              value: 30
            target:
              entity_id: input_number.current_fanspeed
      - conditions:
          - condition: numeric_state
            entity_id: sensor.processor_temperature
            above: "45"
        sequence:
          - service: argon40.set_fan_speed
            data:
              speed: 20
          - service: input_number.set_value
            data:
              value: 20
            target:
              entity_id: input_number.current_fanspeed
      - conditions:
          - condition: numeric_state
            entity_id: sensor.processor_temperature
            above: "35"
        sequence:
          - service: argon40.set_fan_speed
            data:
              speed: 10
          - service: input_number.set_value
            data:
              value: 10
            target:
              entity_id: input_number.current_fanspeed
      - conditions:
          - condition: numeric_state
            entity_id: sensor.processor_temperature
            below: "35"
        sequence:
          - service: argon40.set_fan_speed
            data:
              speed: 2
          - service: input_number.set_value
            data:
              value: 2
            target:
              entity_id: input_number.current_fanspeed
    default:
      - service: argon40.set_fan_speed
        data:
          speed: 0
      - service: input_number.set_value
        data:
          value: 0
        target:
          entity_id: input_number.current_fanspeed
```

#### Bonus - button double-tap detection

```yaml
automation:
  - alias: "Argon40 button double-tap"
    trigger:
      platform: event
      event_type: argon40_event
      event_data:
        action: double-tap
    action:
      - service: persistent_notification.create
        data:
          title: "Argon 40"
          message: "Button was double-tapped"
```

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[argon_one_pi4]: https://www.argon40.com/argon-one-raspberry-pi-4-case.html
[argon_one_pi3]: https://www.argon40.com/argon-one-raspberry-pi-3-case.html
[argon_fan_hat]: https://www.argon40.com/argon-fan-hat-for-raspberry-pi-4-raspberry-pi-3b-and-raspberry-pi-3-b.html

[buymecoffee]: https://www.buymeacoffee.com/Misiu
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge

[commits]: https://github.com/Misiu/argon40/commits/master
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
