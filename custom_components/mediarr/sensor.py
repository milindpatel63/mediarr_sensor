"""The Mediarr integration sensors."""
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp
import async_timeout
from plexapi.server import PlexServer
import voluptuous as vol
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_API_KEY,
    CONF_URL,
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

# Common constants
CONF_MAX_ITEMS = "max_items"
CONF_DAYS = "days_to_check"
DEFAULT_MAX_ITEMS = 10
DEFAULT_DAYS = 60
SCAN_INTERVAL = timedelta(minutes=10)

# Plex specific constants
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 32400

# Trakt specific constants
CONF_TRENDING_TYPE = "trending_type"

# Platform schemas
PLEX_SCHEMA = {
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
}

SONARR_SCHEMA = {
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
    vol.Optional(CONF_DAYS, default=DEFAULT_DAYS): cv.positive_int,
}

RADARR_SCHEMA = {
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
}

TRAKT_SCHEMA = {
    vol.Required(CONF_CLIENT_ID): cv.string,
    vol.Required(CONF_CLIENT_SECRET): cv.string,
    vol.Required('tmdb_api_key'): cv.string,  # Add this line
    vol.Optional(CONF_TRENDING_TYPE, default="both"): vol.In(["movies", "shows", "both"]),
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
}

TMDB_SCHEMA = {
    vol.Required('api_key'): cv.string,
    vol.Optional('trending_type', default='all'): vol.In(['movie', 'tv', 'all']),
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
}


# Combined platform schema
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional("plex"): vol.Schema(PLEX_SCHEMA),
        vol.Optional("sonarr"): vol.Schema(SONARR_SCHEMA),
        vol.Optional("radarr"): vol.Schema(RADARR_SCHEMA),
        vol.Optional("trakt"): vol.Schema(TRAKT_SCHEMA),
        vol.Optional("tmdb"): vol.Schema(TMDB_SCHEMA),
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Mediarr sensor platform."""
    session = async_get_clientsession(hass)
    sensors = []

    # Set up Plex sensor if configured
    if "plex" in config:
        plex_config = config["plex"]
        host = plex_config[CONF_HOST]
        port = plex_config[CONF_PORT]
        token = plex_config[CONF_TOKEN]
        max_items = plex_config[CONF_MAX_ITEMS]
        base_url = f"http://{host}:{port}"

        def _create_server():
            """Create Plex server instance."""
            return PlexServer(base_url, token)

        try:
            server = await hass.async_add_executor_job(_create_server)
            sensors.append(PlexMediarrSensor(server, max_items))
        except Exception as error:
            _LOGGER.error("Error connecting to Plex server: %s", error)

    # Set up Sonarr sensor if configured
    if "sonarr" in config:
        sonarr_config = config["sonarr"]
        sensors.append(
            SonarrMediarrSensor(
                session,
                sonarr_config[CONF_API_KEY],
                sonarr_config[CONF_URL],
                sonarr_config[CONF_MAX_ITEMS],
                sonarr_config[CONF_DAYS]
            )
        )

    # Set up Radarr sensor if configured
    if "radarr" in config:
        radarr_config = config["radarr"]
        sensors.append(
            RadarrMediarrSensor(
                session,
                radarr_config[CONF_API_KEY],
                radarr_config[CONF_URL],
                radarr_config[CONF_MAX_ITEMS]
            )
        )

    # Set up Trakt sensor if configured
    if "trakt" in config:
        trakt_config = config["trakt"]
        sensors.append(
            TraktMediarrSensor(
                session,
                trakt_config[CONF_CLIENT_ID],
                trakt_config[CONF_CLIENT_SECRET],
                trakt_config[CONF_TRENDING_TYPE],
                trakt_config[CONF_MAX_ITEMS],
                trakt_config['tmdb_api_key']
            )
        )
# Set up TMDB sensor if configured
    if "tmdb" in config:
        tmdb_config = config["tmdb"]
        sensors.append(
            TMDBMediarrSensor(
                session,
                tmdb_config['api_key'],
                tmdb_config[CONF_MAX_ITEMS]
            )
        )

    if sensors:
        async_add_entities(sensors, True)

class PlexMediarrSensor(SensorEntity):
    """Representation of a Plex recently added sensor."""

    def __init__(self, server, max_items):
        """Initialize the sensor."""
        self._server = server
        self._max_items = max_items
        self._name = "Plex Mediarr"
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"plex_mediarr_{self._server.machineIdentifier}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def process_tv_show(self, item):
        """Process a TV show episode."""
        try:
            # Handle both Episode and Show objects
            if hasattr(item, 'type') and item.type == 'episode':
                show_title = item.grandparentTitle
                episode_title = item.title
                season_num = item.seasonNumber
                episode_num = item.episodeNumber
            else:
                show_title = item.title
                episode_title = None
                season_num = None
                episode_num = None

            return {
                'title': show_title,
                'episode': episode_title,
                'number': f"S{season_num:02d}E{episode_num:02d}" if season_num and episode_num else None,
                'aired': item.originallyAvailableAt.strftime('%Y-%m-%d') if hasattr(item, 'originallyAvailableAt') and item.originallyAvailableAt else '',
                'added': item.addedAt.strftime('%Y-%m-%d') if hasattr(item, 'addedAt') else '',
                'runtime': int(item.duration / 60000) if hasattr(item, 'duration') and item.duration else 0,
                'type': 'show',
                'poster': item.thumbUrl if hasattr(item, 'thumbUrl') else None,
                'fanart': item.artUrl if hasattr(item, 'artUrl') else None,
                'key': item.key if hasattr(item, 'key') else None,
                'ratingKey': item.ratingKey if hasattr(item, 'ratingKey') else None,
                'summary': item.summary if hasattr(item, 'summary') else ''
            }
        except Exception as e:
            _LOGGER.error("Error processing TV show: %s", e)
            return None

    def update(self):
        """Update sensor data."""
        try:
            recently_added = []
            
            for section in self._server.library.sections():
                if section.type in ['show', 'movie']:
                    items = section.recentlyAdded()
                    
                    for item in items:
                        try:
                            if section.type == 'show':
                                media_data = self.process_tv_show(item)
                                if media_data:
                                    recently_added.append(media_data)
                            else:
                                # Handle movies
                                media_data = {
                                    'title': item.title if hasattr(item, 'title') else 'Unknown',
                                    'year': item.year if hasattr(item, 'year') else '',
                                    'added': item.addedAt.strftime('%Y-%m-%d') if hasattr(item, 'addedAt') else '',
                                    'runtime': int(item.duration / 60000) if hasattr(item, 'duration') and item.duration else 0,
                                    'type': 'movie',
                                    'poster': item.thumbUrl if hasattr(item, 'thumbUrl') else None,
                                    'fanart': item.artUrl if hasattr(item, 'artUrl') else None,
                                    'key': item.key if hasattr(item, 'key') else None,
                                    'ratingKey': item.ratingKey if hasattr(item, 'ratingKey') else None,
                                    'summary': item.summary if hasattr(item, 'summary') else ''
                                }
                                recently_added.append(media_data)
                        except Exception as item_error:
                            _LOGGER.error("Error processing item: %s", item_error)
                            continue

            # Sort by date added, newest first
            recently_added.sort(key=lambda x: x.get('added', ''), reverse=True)
            
            self._state = len(recently_added)
            self._attributes = {'data': recently_added[:self._max_items]}

        except Exception as err:
            _LOGGER.error("Error updating Plex sensor: %s", err)
            self._state = 0
            self._attributes = {'data': []}

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

class TraktMediarrSensor(SensorEntity):
    """Representation of a Trakt popular media sensor."""

    def __init__(self, session, client_id, client_secret, trending_type, max_items, tmdb_api_key):
        """Initialize the sensor."""
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._trending_type = trending_type
        self._max_items = max_items
        self._tmdb_api_key = tmdb_api_key
        self._name = "Trakt Mediarr"
        self._state = None
        self._attributes = {}
        self._access_token = None
        self._available = False
        self._headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': client_id
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"trakt_mediarr_{self._trending_type}"

    async def _get_access_token(self):
        """Get OAuth access token from Trakt."""
        try:
            data = {
                'client_id': self._client_id,
                'client_secret': self._client_secret,
                'grant_type': 'client_credentials'
            }

            async with self._session.post(
                'https://api.trakt.tv/oauth/token',
                json=data,
                headers=self._headers
            ) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self._access_token = token_data.get('access_token')
                    if self._access_token:
                        self._headers['Authorization'] = f'Bearer {self._access_token}'
                        self._available = True
                        return True
                    else:
                        _LOGGER.error("No access token in Trakt response")
                        self._available = False
                        return False
                else:
                    _LOGGER.error("Failed to get Trakt access token. Status: %s", response.status)
                    self._available = False
                    return False
        except Exception as err:
            _LOGGER.error("Error getting Trakt access token: %s", err)
            self._available = False
            return False

    async def _fetch_popular(self, media_type):
        """Fetch popular items from Trakt."""
        try:
            params = {
                'limit': self._max_items
            }
            
            async with self._session.get(
                f"https://api.trakt.tv/{media_type}/popular",
                headers=self._headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status in [401, 403]:
                    # Try to refresh token and retry
                    if await self._get_access_token():
                        return await self._fetch_popular(media_type)
                
                _LOGGER.error("Failed to fetch Trakt %s popular. Status: %s", 
                            media_type, response.status)
                return []
        except Exception as err:
            _LOGGER.error("Error fetching Trakt %s: %s", media_type, err)
            return []

    async def _fetch_tmdb_data(self, tmdb_id, media_type):
        """Fetch poster from TMDB."""
        try:
            endpoint = 'tv' if media_type == 'show' else 'movie'
            headers = {
                'Authorization': f'Bearer {self._tmdb_api_key}',
                'accept': 'application/json'
            }
            
            async with self._session.get(
                f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    poster_path = data.get('poster_path')
                    if poster_path:
                        return {
                            'poster': f"https://image.tmdb.org/t/p/w500{poster_path}",
                            'backdrop': f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else None,
                            'overview': data.get('overview'),
                            'genres': [g['name'] for g in data.get('genres', [])]
                        }
                return {}
        except Exception as err:
            _LOGGER.error("Error fetching TMDB data: %s", err)
            return {}

    async def _process_item(self, item, media_type):
        """Process a single Trakt item."""
        try:
            base_item = {
                'title': item['title'],
                'year': item.get('year'),
                'type': media_type,
                'ids': item.get('ids', {}),
                'slug': item.get('ids', {}).get('slug'),
                'tmdb_id': item.get('ids', {}).get('tmdb'),
                'imdb_id': item.get('ids', {}).get('imdb'),
                'trakt_id': item.get('ids', {}).get('trakt')
            }

            # Fetch TMDB data if we have an ID
            if base_item['tmdb_id'] and self._tmdb_api_key:
                tmdb_data = await self._fetch_tmdb_data(base_item['tmdb_id'], media_type)
                base_item.update(tmdb_data)

            return base_item
        except Exception as err:
            _LOGGER.error("Error processing Trakt item: %s", err)
            return None

    async def async_update(self):
        """Update the sensor."""
        try:
            if not self._access_token:
                if not await self._get_access_token():
                    self._state = None
                    self._attributes = {}
                    self._available = False
                    return

            all_items = []
            
            if self._trending_type in ['shows', 'both']:
                shows = await self._fetch_popular('shows')
                for item in shows:
                    processed = await self._process_item(item, 'show')
                    if processed:
                        all_items.append(processed)
            
            if self._trending_type in ['movies', 'both']:
                movies = await self._fetch_popular('movies')
                for item in movies:
                    processed = await self._process_item(item, 'movie')
                    if processed:
                        all_items.append(processed)
            
            if all_items:
                self._state = len(all_items)
                self._attributes = {'data': all_items}
                self._available = True
            else:
                self._state = 0
                self._attributes = {'data': []}
                self._available = False

        except Exception as err:
            _LOGGER.error("Error updating Trakt sensor: %s", err)
            self._state = None
            self._attributes = {'data': []}
            self._available = False

class TMDBMediarrSensor(SensorEntity):
    """TMDB trending media sensor."""

    def __init__(self, session, api_key, max_items):
        self._session = session
        self._api_key = api_key
        self._max_items = max_items
        self._name = "TMDB Mediarr"
        self._state = None
        self._attributes = {}
        self._available = False

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def available(self):
        return self._available

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def unique_id(self):
        return "tmdb_mediarr_trending"

    async def async_update(self):
        try:
            headers = {
                'Authorization': f'Bearer {self._api_key}',
                'accept': 'application/json'
            }
            
            async with self._session.get(
                "https://api.themoviedb.org/3/trending/all/week",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    for item in data.get('results', []):
                        media_type = item.get('media_type')
                        if media_type in ['movie', 'tv']:
                            results.append({
                                'title': item.get('title') if media_type == 'movie' else item.get('name'),
                                'type': 'movie' if media_type == 'movie' else 'show',
                                'year': item.get('release_date', '').split('-')[0] if media_type == 'movie' else item.get('first_air_date', '').split('-')[0],
                                'overview': item.get('overview'),
                                'poster': f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else None,
                                'backdrop': f"https://image.tmdb.org/t/p/original{item.get('backdrop_path')}" if item.get('backdrop_path') else None,
                                'tmdb_id': item.get('id'),
                                'popularity': item.get('popularity'),
                                'vote_average': item.get('vote_average')
                            })
                    
                    self._state = len(results)
                    self._attributes = {'data': results[:self._max_items]}
                    self._available = True
                else:
                    _LOGGER.error("Failed to fetch TMDB trending. Status: %s", response.status)
                    self._state = 0
                    self._attributes = {'data': []}
                    self._available = False

        except Exception as err:
            _LOGGER.error("Error updating TMDB sensor: %s", err)
            self._state = 0
            self._attributes = {'data': []}
            self._available = False