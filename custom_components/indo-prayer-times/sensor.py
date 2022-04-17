"""Platform to retrieve Islamic prayer times information for Home Assistant."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util
import logging
import datetime
from datetime import date

from .const import DATA_UPDATED, DOMAIN, PRAYER_TIMES_ICON, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Islamic prayer times sensor platform."""

    _LOGGER.info("xxx00")
    client = hass.data[DOMAIN]

    entities = []
    for sensor_type in SENSOR_TYPES:
        entities.append(IndoPrayerTimeSensor(sensor_type, client))

    async_add_entities(entities, True)


class IndoPrayerTimeSensor(SensorEntity):
    """Representation of an Islamic prayer time sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = PRAYER_TIMES_ICON
    _attr_should_poll = False

    def __init__(self, sensor_type, client):
        """Initialize the Islamic prayer time sensor."""
        self.sensor_type = sensor_type
        self.client = client
        _LOGGER.info("xxx01")

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{SENSOR_TYPES[self.sensor_type]}"

    @property
    def unique_id(self):
        """Return the unique id of the entity."""
        return self.sensor_type

    @property
    def native_value(self):
        """Return the state of the sensor."""
        #return self.client.prayer_times_info.get(self.sensor_type).astimezone(
        #    dt_util.UTC
        _LOGGER.info("xxx02")
        today = date.today()
        dt_today = today.strftime("%Y-%m-%d")
        #jadwal = self.client.prayer_times_info.get(self.sensor_type).split(":")
        isostr = dt_today + " " + self.client.prayer_times_info.get(self.sensor_type) + ":00+07:00"
        _LOGGER.info("asoy = " + isostr)
        date_time_obj = datetime.datetime.fromisoformat(isostr)
        #date_time_obj = datetime.datetime.strptime(dt_today + " " + self.client.prayer_times_info.get(self.sensor_type), '%Y-%m-%d %H:%M').astimezone(dt_util.UTC)
        return date_time_obj #.astimezone(dt_util.UTC)
        #return self.client.prayer_times_info.get(self.sensor_type).astimezone(dt_util.UTC)
        

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, DATA_UPDATED, self.async_write_ha_state)
        )