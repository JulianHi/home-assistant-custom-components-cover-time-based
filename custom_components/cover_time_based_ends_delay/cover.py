"""Cover Time based."""
import logging

import voluptuous as vol

from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers.event import async_track_utc_time_change, async_track_time_interval
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    PLATFORM_SCHEMA,
    CoverEntity,
)
from homeassistant.const import (
    CONF_NAME,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
)

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity

from .travelcalculator import TravelCalculator
from .travelcalculator import TravelStatus

_LOGGER = logging.getLogger(__name__)

CONF_DEVICES = 'devices'
CONF_NAME = 'name'
CONF_ALIASES = 'aliases'
CONF_TRAVELLING_TIME_DOWN = 'travelling_time_down'
CONF_TRAVELLING_TIME_UP = 'travelling_time_up'
CONF_STICKY_TRAVEL_END_POSITIONS = 'sticky_travel_end_position'
CONF_UNIQUE_ID = 'unique_id'

DEFAULT_TRAVEL_TIME = 25
DEFAULT_STICKY_TRAVEL_END_POSITIONS = False

CONF_OPEN_SWITCH_ENTITY_ID = 'open_switch_entity_id'
CONF_CLOSE_SWITCH_ENTITY_ID = 'close_switch_entity_id'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_DEVICES, default={}): vol.Schema(
            {
                cv.string: {
                    vol.Optional(CONF_NAME): cv.string,
                    vol.Optional(CONF_OPEN_SWITCH_ENTITY_ID): cv.string,
                    vol.Optional(CONF_CLOSE_SWITCH_ENTITY_ID): cv.string,
                    vol.Optional(CONF_ALIASES, default=[]):
                        vol.All(cv.ensure_list, [cv.string]),

                    vol.Optional(CONF_TRAVELLING_TIME_DOWN, default=DEFAULT_TRAVEL_TIME):
                        cv.positive_int,
                    vol.Optional(CONF_TRAVELLING_TIME_UP, default=DEFAULT_TRAVEL_TIME):
                        cv.positive_int,

                    vol.Optional(CONF_STICKY_TRAVEL_END_POSITIONS, default=DEFAULT_STICKY_TRAVEL_END_POSITIONS):
                        cv.boolean,

                    vol.Optional(CONF_UNIQUE_ID): cv.string,
                }
            }
        ),
    }
)

def devices_from_config(domain_config):
    """Parse configuration and add cover devices."""
    devices = []
    for device_id, config in domain_config[CONF_DEVICES].items():
        name = config.pop(CONF_NAME)
        travel_time_down = config.pop(CONF_TRAVELLING_TIME_DOWN)
        travel_time_up = config.pop(CONF_TRAVELLING_TIME_UP)
        sticky_travel_end_position = config.pop(CONF_STICKY_TRAVEL_END_POSITIONS)
        open_switch_entity_id = config.pop(CONF_OPEN_SWITCH_ENTITY_ID)
        close_switch_entity_id = config.pop(CONF_CLOSE_SWITCH_ENTITY_ID)
        unique_id = config.pop(CONF_UNIQUE_ID)
        device = CoverTimeBased(device_id, unique_id, name, travel_time_down, travel_time_up, sticky_travel_end_position, open_switch_entity_id, close_switch_entity_id)
        devices.append(device)
    return devices

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the cover platform."""
    async_add_entities(devices_from_config(config))

class CoverTimeBased(CoverEntity, RestoreEntity):
	
    def __init__(self, device_id, unique_id, name, travel_time_down, travel_time_up, sticky_travel_end_position,  open_switch_entity_id, close_switch_entity_id):
        """Initialize the cover."""
        self._travel_time_down = travel_time_down
        self._travel_time_up = travel_time_up
        self._sticky_travel_end_position = sticky_travel_end_position
        self._open_switch_entity_id = open_switch_entity_id
        self._close_switch_entity_id = close_switch_entity_id        
        
        if name:
            self._name = name
        else:
            self._name = device_id

        if unique_id:
            self._unique_id = unique_id
        else:
            self._unique_id = device_id
		
        self._unsubscribe_auto_updater = None

        self.tc = TravelCalculator(self._travel_time_down, self._travel_time_up)

    async def async_added_to_hass(self):
        """ Only cover's position matters.             """
        """ The rest is calculated from this attribute."""
        old_state = await self.async_get_last_state()
        _LOGGER.debug('async_added_to_hass :: oldState %s', old_state)
        if (
                old_state is not None and
                self.tc is not None and
                old_state.attributes.get(ATTR_CURRENT_POSITION) is not None):
            self.tc.set_position(int(
                old_state.attributes.get(ATTR_CURRENT_POSITION)))

    def _handle_my_button(self):
        """Handle the MY button press"""
        if self.tc.is_traveling():
            _LOGGER.debug('_handle_my_button :: button stops cover')
            self.tc.stop()
            self.stop_auto_updater()

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return self._unique_id


    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attr = {}
        if self._travel_time_down is not None:
            attr[CONF_TRAVELLING_TIME_DOWN] = self._travel_time_down
        if self._travel_time_up is not None:
            attr[CONF_TRAVELLING_TIME_UP] = self._travel_time_up
        if self._sticky_travel_end_position is not None:
            attr[CONF_STICKY_TRAVEL_END_POSITIONS] = self._sticky_travel_end_position
        return attr

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self.tc.current_position()

    @property
    def is_opening(self):
        """Return if the cover is opening or not."""
        return self.tc.is_traveling() and \
               self.tc.travel_direction == TravelStatus.DIRECTION_UP

    @property
    def is_closing(self):
        """Return if the cover is closing or not."""
        return self.tc.is_traveling() and \
               self.tc.travel_direction == TravelStatus.DIRECTION_DOWN

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self.tc.is_closed()

    @property
    def assumed_state(self):
        """Return True because covers can be stopped midway."""
        return True

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            _LOGGER.debug('async_set_cover_position: %d', position)
            await self.set_position(position)

    async def async_close_cover(self, **kwargs):
        """Turn the device close."""
        _LOGGER.debug('async_close_cover')
        self.tc.start_travel_down()

        self.start_auto_updater()
        await self._async_handle_command(SERVICE_CLOSE_COVER)

    async def async_open_cover(self, **kwargs):
        """Turn the device open."""
        _LOGGER.debug('async_open_cover')
        self.tc.start_travel_up()

        self.start_auto_updater()
        await self._async_handle_command(SERVICE_OPEN_COVER)

    async def async_stop_cover(self, **kwargs):
        """Turn the device stop."""
        _LOGGER.debug('async_stop_cover')
        self._handle_my_button()
        await self._async_handle_command(SERVICE_STOP_COVER)

    async def set_position(self, position):
        _LOGGER.debug('set_position')
        """Move cover to a designated position."""
        current_position = self.tc.current_position()
        _LOGGER.debug('set_position :: current_position: %d, new_position: %d',
                      current_position, position)
        command = None
        if position < current_position:
            command = SERVICE_CLOSE_COVER
        elif position > current_position:
            command = SERVICE_OPEN_COVER
        if command is not None:
            self.start_auto_updater()
            self.tc.start_travel(position)
            _LOGGER.debug('set_position :: command %s', command)
            await self._async_handle_command(command)
        return

    def start_auto_updater(self):
        """Start the autoupdater to update HASS while cover is moving."""
        _LOGGER.debug('start_auto_updater')
        if self._unsubscribe_auto_updater is None:
            _LOGGER.debug('init _unsubscribe_auto_updater')
            interval = timedelta(seconds=0.1)
            self._unsubscribe_auto_updater = async_track_time_interval(
                self.hass, self.auto_updater_hook, interval)

    @callback
    def auto_updater_hook(self, now):
        """Call for the autoupdater."""
        _LOGGER.debug('auto_updater_hook')
        self.async_schedule_update_ha_state()
        if self.position_reached():
            _LOGGER.debug('auto_updater_hook :: position_reached')
            self.stop_auto_updater()
        self.hass.async_create_task(self.auto_stop_if_necessary())

    def stop_auto_updater(self):
        """Stop the autoupdater."""
        _LOGGER.debug('stop_auto_updater')
        if self._unsubscribe_auto_updater is not None:
            self._unsubscribe_auto_updater()
            self._unsubscribe_auto_updater = None

    def position_reached(self):
        """Return if cover has reached its final position."""
        return self.tc.position_reached()

    async def auto_stop_if_necessary(self):
        """Do auto stop if necessary."""
        if self.position_reached():
            _LOGGER.debug('auto_stop_if_necessary :: calling stop command')
            await self._async_handle_command(SERVICE_STOP_COVER)
            self.tc.stop()
    
    
    async def _async_handle_command(self, command, *args):
        if command == "close_cover":
            cmd = "DOWN"
            self._state = False
            await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": self._open_switch_entity_id}, False)
            await self.hass.services.async_call("homeassistant", "turn_on", {"entity_id": self._close_switch_entity_id}, False)
            
        elif command == "open_cover":
            cmd = "UP"
            self._state = True
            await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": self._close_switch_entity_id}, False)
            await self.hass.services.async_call("homeassistant", "turn_on", {"entity_id": self._open_switch_entity_id}, False)
 
        elif command == "stop_cover":
            cmd = "STOP"
            self._state = True

            if self._sticky_travel_end_position and self.tc.current_position() == 0:
                await self.hass.services.async_call("homeassistant", "turn_off",
                                                    {"entity_id": self._open_switch_entity_id}, False)
                await self.hass.services.async_call("homeassistant", "turn_on",
                                                    {"entity_id": self._close_switch_entity_id}, False)
            elif self._sticky_travel_end_position and self.tc.current_position() == 100:
                await self.hass.services.async_call("homeassistant", "turn_off",
                                                    {"entity_id": self._close_switch_entity_id}, False)
                await self.hass.services.async_call("homeassistant", "turn_on",
                                                    {"entity_id": self._open_switch_entity_id}, False)
            else:
                await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": self._close_switch_entity_id}, False)
                await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": self._open_switch_entity_id}, False)

        _LOGGER.debug('_async_handle_command :: %s', cmd)
        
        # Update state of entity
        self.async_write_ha_state()
