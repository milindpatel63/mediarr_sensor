"""The Plex Mediarr sensor."""
from datetime import timedelta
import logging
from plexapi.server import PlexServer
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_MAX_ITEMS = "max_items"

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 32400
DEFAULT_MAX_ITEMS = 10

SCAN_INTERVAL = timedelta(minutes=5)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Plex sensor."""
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    token = config[CONF_TOKEN]
    max_items = config[CONF_MAX_ITEMS]

    base_url = f"http://{host}:{port}"

    def _create_server():
        """Create Plex server instance."""
        return PlexServer(base_url, token)

    try:
        server = await hass.async_add_executor_job(_create_server)
    except Exception as error:
        _LOGGER.error("Error connecting to Plex server: %s", error)
        return

    sensor = PlexMediarrSensor(server, max_items)
    async_add_entities([sensor], True)

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