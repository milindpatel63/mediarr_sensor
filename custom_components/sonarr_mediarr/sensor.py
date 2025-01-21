"""The Sonarr Mediarr sensor."""
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp
import async_timeout
import voluptuous as vol
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_MAX_ITEMS = "max_items"
CONF_DAYS = "days_to_check"
DEFAULT_MAX_ITEMS = 10
DEFAULT_DAYS = 60
SCAN_INTERVAL = timedelta(minutes=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
    vol.Optional(CONF_DAYS, default=DEFAULT_DAYS): cv.positive_int,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Sonarr sensor."""
    session = async_get_clientsession(hass)
    
    sensor = SonarrMediarrSensor(
        session,
        config[CONF_API_KEY],
        config[CONF_URL],
        config[CONF_MAX_ITEMS],
        config[CONF_DAYS]
    )
    
    async_add_entities([sensor], True)

class SonarrMediarrSensor(SensorEntity):
    """Sonarr Mediarr Sensor class."""
    
    def __init__(self, session, api_key, url, max_items, days_to_check):
        """Initialize the sensor."""
        self._session = session
        self._api_key = api_key
        self._url = url.rstrip('/')
        self._max_items = max_items
        self._days_to_check = days_to_check
        self._name = "Sonarr Mediarr"
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"sonarr_mediarr_{self._url}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._attributes

    def parse_date(self, date_str: str) -> datetime:
        """Parse date string to timezone-aware datetime."""
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
        return dt

    async def async_update(self):
        """Update the sensor."""
        try:
            headers = {'X-Api-Key': self._api_key}
            now = datetime.now(ZoneInfo('UTC'))
            params = {
                'start': now.strftime('%Y-%m-%d'),
                'end': (now + timedelta(days=self._days_to_check)).strftime('%Y-%m-%d'),
                'includeSeries': 'true'
            }

            async with async_timeout.timeout(10):
                async with self._session.get(
                    f"{self._url}/api/v3/calendar",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        upcoming_episodes = await response.json()
                        shows_dict = {}

                        for episode in upcoming_episodes:
                            series = episode.get('series', {})
                            if not episode.get('monitored', False) or not series.get('monitored', False):
                                continue

                            try:
                                air_date = self.parse_date(episode['airDate'])
                                if air_date < now:
                                    continue
                            except ValueError as e:
                                _LOGGER.warning("Error parsing date for %s: %s", 
                                              episode.get('title', ''), e)
                                continue

                            series_id = series['id']
                            show_data = {
                                'title': series['title'],
                                'episodes': [{
                                    'title': episode.get('title', 'Unknown'),
                                    'number': f"S{episode.get('seasonNumber', 0):02d}E{episode.get('episodeNumber', 0):02d}",
                                    'airdate': episode['airDate'],
                                    'overview': episode.get('overview', '')
                                }],
                                'runtime': series.get('runtime', 0),
                                'network': series.get('network', ''),
                                'poster': f"{self._url}/api/v3/mediacover/{series['id']}/poster.jpg?apikey={self._api_key}",
                                'fanart': f"{self._url}/api/v3/mediacover/{series['id']}/fanart.jpg?apikey={self._api_key}",
                                'airdate': episode['airDate'],
                                'monitored': True,
                                'next_episode': {
                                    'title': episode.get('title', 'Unknown'),
                                    'number': f"S{episode.get('seasonNumber', 0):02d}E{episode.get('episodeNumber', 0):02d}"
                                }
                            }

                            if series_id in shows_dict:
                                current_date = self.parse_date(shows_dict[series_id]['airdate'])
                                new_date = self.parse_date(episode['airDate'])
                                if new_date < current_date:
                                    shows_dict[series_id]['airdate'] = episode['airDate']
                                    shows_dict[series_id]['next_episode'] = show_data['next_episode']
                                shows_dict[series_id]['episodes'].append(show_data['episodes'][0])
                            else:
                                shows_dict[series_id] = show_data

                        upcoming_shows = list(shows_dict.values())
                        upcoming_shows.sort(key=lambda x: self.parse_date(x['airdate']))

                        self._state = len(upcoming_shows)
                        self._attributes = {'data': upcoming_shows[:self._max_items]}

                    else:
                        _LOGGER.error("Failed to connect to Sonarr. Status code: %s", response.status)
                        self._state = 0
                        self._attributes = {'data': []}

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout connecting to Sonarr")
            self._state = 0
            self._attributes = {'data': []}
        except Exception as err:
            _LOGGER.error("Error updating Sonarr sensor: %s", err)
            self._state = 0
            self._attributes = {'data': []}