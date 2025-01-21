"""The Radarr Mediarr sensor."""
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_MAX_ITEMS = "max_items"
DEFAULT_MAX_ITEMS = 10
SCAN_INTERVAL = timedelta(minutes=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Radarr sensor."""
    session = async_get_clientsession(hass)
    
    sensor = RadarrMediarrSensor(
        session,
        config[CONF_API_KEY],
        config[CONF_URL],
        config[CONF_MAX_ITEMS]
    )
    
    async_add_entities([sensor], True)

class RadarrMediarrSensor(SensorEntity):
    """Radarr Mediarr Sensor class."""
    
    def __init__(self, session, api_key, url, max_items):
        """Initialize the sensor."""
        self._session = session
        self._api_key = api_key
        self._url = url.rstrip('/')
        self._max_items = max_items
        self._name = "Radarr Mediarr"
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"radarr_mediarr_{self._url}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def async_update(self):
        """Update the sensor."""
        try:
            headers = {'X-Api-Key': self._api_key}
            now = datetime.now().astimezone()  # Make timezone-aware

            async with async_timeout.timeout(10):
                async with self._session.get(
                    f"{self._url}/api/v3/movie",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        movies = await response.json()
                        upcoming_movies = []

                        for movie in movies:
                            if not movie.get('monitored', False):
                                continue

                            if movie.get('hasFile', False):
                                continue

                            release_dates = []
                            
                            # Parse and check each release date type
                            for date_field, date_type in [
                                ('digitalRelease', 'Digital'),
                                ('physicalRelease', 'Physical'),
                                ('inCinemas', 'Theaters')
                            ]:
                                if movie.get(date_field):
                                    try:
                                        # Ensure date is timezone-aware
                                        release_date = datetime.fromisoformat(
                                            movie[date_field].replace('Z', '+00:00')
                                        )
                                        if not release_date.tzinfo:
                                            release_date = release_date.replace(tzinfo=now.tzinfo)
                                        if release_date > now:
                                            release_dates.append((date_type, release_date))
                                    except ValueError as e:
                                        _LOGGER.warning("Error parsing date for %s: %s", 
                                                      movie.get('title', ''), e)
                                        continue

                            if release_dates:
                                release_dates.sort(key=lambda x: x[1])
                                release_type, release_date = release_dates[0]

                                movie_data = {
                                    "title": movie["title"],
                                    "year": movie["year"],
                                    "poster": f"{self._url}/api/v3/mediacover/{movie['id']}/poster.jpg?apikey={self._api_key}",
                                    "fanart": f"{self._url}/api/v3/mediacover/{movie['id']}/fanart.jpg?apikey={self._api_key}",
                                    "overview": movie["overview"],
                                    "runtime": movie.get("runtime", 0),
                                    "monitored": True,
                                    "releaseDate": release_date.isoformat(),
                                    "releaseType": release_type,
                                    "studio": movie.get("studio", ""),
                                    "genres": movie.get("genres", []),
                                    "ratings": movie.get("ratings", {})
                                }
                                upcoming_movies.append(movie_data)

                        upcoming_movies.sort(key=lambda x: x['releaseDate'])
                        self._state = len(upcoming_movies)
                        self._attributes = {'data': upcoming_movies[:self._max_items]}
                    else:
                        _LOGGER.error("Failed to connect to Radarr. Status code: %s", response.status)
                        self._state = 0
                        self._attributes = {'data': []}

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout connecting to Radarr")
            self._state = 0
            self._attributes = {'data': []}
        except Exception as err:
            _LOGGER.error("Error updating Radarr sensor: %s", err)
            self._state = 0
            self._attributes = {'data': []}