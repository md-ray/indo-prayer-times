from datetime import timedelta
from datetime import date
import logging
from socket import IP_DEFAULT_MULTICAST_TTL
import requests
import datetime

#from prayer_times_calculator import PrayerTimesCalculator, exceptions
from requests.exceptions import ConnectionError as ConnError
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_point_in_time
from homeassistant.helpers.typing import ConfigType
import homeassistant.util.dt as dt_util

from .const import (
    DATA_UPDATED,
    DOMAIN,
    SENSOR_TYPES,
    CONF_CALC_METHOD,
    DEFAULT_CALC_METHOD,
    CALC_METHODS
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN),
        {
            DOMAIN: {
                vol.Optional(CONF_CALC_METHOD, default=DEFAULT_CALC_METHOD): vol.In(
                    CALC_METHODS
                ),
            }
        },
    ),
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import the Islamic Prayer component from config."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up the Islamic Prayer Component."""
    client = IndoPrayerClient(hass, config_entry)

    if not await client.async_setup():
        return False

    hass.data.setdefault(DOMAIN, client)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload Islamic Prayer entry from config_entry."""
    if hass.data[DOMAIN].event_unsub:
        hass.data[DOMAIN].event_unsub()
    hass.data.pop(DOMAIN)
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


class IndoPrayerClient:
    """Islamic Prayer Client Object."""

    def __init__(self, hass, config_entry):
        """Initialize the Islamic Prayer client."""
        self.hass = hass
        self.config_entry = config_entry
        self.prayer_times_info = {
            "indoprayer_imsak" : "00:00",
            "indoprayer_subuh" : "00:00",
            "indoprayer_dzuhur" : "00:00",
            "indoprayer_ashar" : "00:00",
            "indoprayer_maghrib" : "00:00",
            "indoprayer_isya" : "00:00",

        }
        self.available = True
        self.event_unsub = None
        _LOGGER.info("debug00")

    """
    @property
    def calc_method(self):
        return self.config_entry.options[CONF_CALC_METHOD]
    """

    def get_new_prayer_times(self):
        """Fetch prayer times for today.
        calc = PrayerTimesCalculator(
            latitude=self.hass.config.latitude,
            longitude=self.hass.config.longitude,
            calculation_method=self.calc_method,
            date=str(dt_util.now().date()),
        )
        return calc.fetch_prayer_times()
        """
        #Get Current ID city from config
        id_city = self.config_entry.options.get("id_city", 1108)
        str_id_city = str(id_city).zfill(4)

        today = date.today()
        dt_today = today.strftime("%Y/%m/%d")
        _LOGGER.info("debug01")
        # Call MyQuran API
        myquran_url = "https://api.myquran.com/v1/sholat/jadwal/" + str_id_city + "/" + dt_today
        response = requests.get(myquran_url)
        if (response.status_code == 200):
            retval = response.json()
            _LOGGER.info("Successful call to myquran API")
            return retval["data"]["jadwal"]
        else:
            _LOGGER.info("Failed call to myquran API")
            return None

    async def async_schedule_future_update(self):
        """Schedule future update for sensors.

        Midnight is a calculated time.  The specifics of the calculation
        depends on the method of the prayer time calculation.  This calculated
        midnight is the time at which the time to pray the Isha prayers have
        expired.

        Calculated Midnight: The Islamic midnight.
        Traditional Midnight: 12:00AM

        Update logic for prayer times:

        If the Calculated Midnight is before the traditional midnight then wait
        until the traditional midnight to run the update.  This way the day
        will have changed over and we don't need to do any fancy calculations.

        If the Calculated Midnight is after the traditional midnight, then wait
        until after the calculated Midnight.  We don't want to update the prayer
        times too early or else the timings might be incorrect.

        Example:
        calculated midnight = 11:23PM (before traditional midnight)
        Update time: 12:00AM

        calculated midnight = 1:35AM (after traditional midnight)
        update time: 1:36AM.

        """
        _LOGGER.info("Scheduling next update for Islamic prayer times")

        now = dt_util.utcnow()
        next_update_at = dt_util.start_of_local_day(now + timedelta(days=1))

        """
        midnight_dt = self.prayer_times_info["Midnight"]

        if now > dt_util.as_utc(midnight_dt):
            next_update_at = midnight_dt + timedelta(days=1, minutes=1)
            _LOGGER.debug(
                "Midnight is after day the changes so schedule update for after Midnight the next day"
            )
        else:
            _LOGGER.debug(
                "Midnight is before the day changes so schedule update for the next start of day"
            )
            next_update_at = dt_util.start_of_local_day(now + timedelta(days=1))
        """
        _LOGGER.info("Next update scheduled for: %s", next_update_at)

        self.event_unsub = async_track_point_in_time(
            self.hass, self.async_update, next_update_at
        )

    async def async_update(self, *_):
        """Update sensors with new prayer times."""
        try:
            prayer_times = await self.hass.async_add_executor_job(
                self.get_new_prayer_times
            )
            self.available = True
        except (exceptions.InvalidResponseError, ConnError):
            self.available = False
            _LOGGER.debug("Error retrieving prayer times")
            async_call_later(self.hass, 60, self.async_update)
            return
        _LOGGER.info("debug03")
        if (prayer_times != None):
            self.prayer_times_info["indoprayer_imsak"] = prayer_times["imsak"]
            self.prayer_times_info["indoprayer_subuh"] = prayer_times["subuh"]
            self.prayer_times_info["indoprayer_terbit"] = prayer_times["terbit"]
            self.prayer_times_info["indoprayer_dzuhur"] = prayer_times["dzuhur"]
            self.prayer_times_info["indoprayer_ashar"] = prayer_times["ashar"]
            self.prayer_times_info["indoprayer_maghrib"] = prayer_times["maghrib"]
            self.prayer_times_info["indoprayer_isya"] = prayer_times["isya"]
        else:
            self.prayer_times_info["indoprayer_imsak"] = "00:00"
            self.prayer_times_info["indoprayer_subuh"] = "00:00"
            self.prayer_times_info["indoprayer_terbit"] = "00:00"
            self.prayer_times_info["indoprayer_dzuhur"] = "00:00"
            self.prayer_times_info["indoprayer_ashar"] = "00:00"
            self.prayer_times_info["indoprayer_maghrib"] = "00:00"
            self.prayer_times_info["indoprayer_isya"] = "00:00"
            #for sensor_type in SENSOR_TYPES:
            #    self.prayer_times_info[sensor_type] = prayer_times[sensor_type]

        """
        for prayer, time in prayer_times.items():
            self.prayer_times_info[prayer] = dt_util.parse_datetime(
                f"{dt_util.now().date()} {time}"
            )
        
        """
        await self.async_schedule_future_update()

        _LOGGER.debug("New prayer times retrieved. Updating sensors")
        async_dispatcher_send(self.hass, DATA_UPDATED)

    async def async_setup(self):
        """Set up the Islamic prayer client."""
        #await self.async_add_options()

        try:
            await self.hass.async_add_executor_job(self.get_new_prayer_times)
        except (exceptions.InvalidResponseError, ConnError) as err:
            raise ConfigEntryNotReady from err

        await self.async_update()
        self.config_entry.add_update_listener(self.async_options_updated)

        self.hass.config_entries.async_setup_platforms(self.config_entry, PLATFORMS)

        return True

    """
    async def async_add_options(self):
        if not self.config_entry.options:
            data = dict(self.config_entry.data)
            calc_method = data.pop(CONF_CALC_METHOD, DEFAULT_CALC_METHOD)

            self.hass.config_entries.async_update_entry(
                self.config_entry, data=data, options={CONF_CALC_METHOD: calc_method}
            )
    """

    @staticmethod
    async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Triggered by config entry options updates."""
        if hass.data[DOMAIN].event_unsub:
            hass.data[DOMAIN].event_unsub()
        await hass.data[DOMAIN].async_update()