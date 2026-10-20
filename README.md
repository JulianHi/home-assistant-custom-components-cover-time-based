# Cover Time Based Component
Cover Time Based Component for your Home-Assistant (http://www.home-assistant.io)

With this component you can add a time-based cover. You can set a switch to open and another to close the cover. 
For example, you can use an Aqara Wall Switch Double Key and standard 4 wire motor roller shutters to do this.

<a href='https://ko-fi.com/A0A12HZT1' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://cdn.ko-fi.com/cdn/kofi4.png?v=2' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

Features:
* Position tracking is calculated locally (bundled `travelcalculator.py`, adapted from XKNX 0.9.4) - no external `xknx` requirement anymore.
* Optional `sticky_travel_end_position`: when the cover stops at a fully closed (0) or fully open (100) position, the corresponding switch stays on, so the motor keeps pushing against the end stop. Useful for shutters that need to be pressed into the end position.
* Optional `unique_id`, so the entity can be managed in the Home Assistant UI. Defaults to the device id.

## Installation
* Copy all files in custom_components/cover_time_based to your <config directory>/custom_components/cover_time_based/ directory.
* Restart Home-Assistant.
* Add the configuration to your configuration.yaml file.

### Usage
To use this component in your installation, add the following to your configuration.yaml file:

### Example configuration.yaml entry

```
cover:
  - platform: cover_time_based
	devices:
	  room_rolling_shutter:
	   name: Room Rolling Shutter
	   travelling_time_down: 23
	   travelling_time_up: 25
	   open_switch_entity_id: switch.wall_switch_right
	   close_switch_entity_id: switch.wall_switch_left
	   sticky_travel_end_position: false
	   unique_id: room_rolling_shutter
	   aliases:
	    - room_rolling_shutter
```


### Options
| Option | Required | Default | Description |
|---|---|---|---|
| `name` | no | device id | Friendly name |
| `travelling_time_down` | no | 25 | Seconds to fully close |
| `travelling_time_up` | no | 25 | Seconds to fully open |
| `open_switch_entity_id` | yes | | Switch that opens the cover |
| `close_switch_entity_id` | yes | | Switch that closes the cover |
| `sticky_travel_end_position` | no | `false` | Keep the switch on when stopped at position 0 or 100 |
| `unique_id` | no | device id | Unique id of the entity |
| `aliases` | no | | List of aliases |
