"""Plex integration for Mediarr using direct API calls."""
import os
import logging
import xml.etree.ElementTree as ET
import aiohttp
import aiofiles
import async_timeout
import voluptuous as vol
from homeassistant.const import CONF_TOKEN, CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv
from ..common.const import CONF_MAX_ITEMS, DEFAULT_MAX_ITEMS
from ..common.sensor import MediarrSensor

_LOGGER = logging.getLogger(__name__)

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 32400
DEFAULT_IMAGE_PATH = 'mediarr-images/plex/'

PLEX_SCHEMA = {
    vol.Required(CONF_TOKEN): cv.string,
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_MAX_ITEMS, default=DEFAULT_MAX_ITEMS): cv.positive_int,
}

class PlexMediarrSensor(MediarrSensor):
    """Representation of a Plex recently added sensor."""

    def __init__(self, hass, config, sections):
        """Initialize the sensor."""
        super().__init__()
        self._base_url = f"http://{config[CONF_HOST]}:{config[CONF_PORT]}"
        self._token = config[CONF_TOKEN]
        self._max_items = config[CONF_MAX_ITEMS]
        self._name = "Plex Mediarr"
        self._sections = sections
        self._www_dir = os.path.join(hass.config.path(), 'www', DEFAULT_IMAGE_PATH)
        self.hass = hass

    async def async_added_to_hass(self):
        """Handle adding to Home Assistant."""
        await self.hass.async_add_executor_job(os.makedirs, self._www_dir, 0o777, True)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return "plex_mediarr"

    async def _fetch_recently_added(self, section_id):
        """Fetch recently added items from a Plex section."""
        url = f"{self._base_url}/library/sections/{section_id}/recentlyAdded"
        headers = {"X-Plex-Token": self._token}
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        return ET.fromstring(xml_content)  # Parse XML
                    else:
                        raise Exception(f"Failed to fetch recently added: {response.status}")

    async def _save_image(self, url, local_path):
        """Download and save an image locally."""
        headers = {"X-Plex-Token": self._token}
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        async with aiofiles.open(local_path, 'wb') as file:
                            await file.write(content)

    async def async_update(self):
        """Update sensor data."""
        try:
            await self.hass.async_add_executor_job(os.makedirs, self._www_dir, 0o777, True)

            recently_added = []
            card_json = []  # Start without default lines

            for section_id in self._sections:
                try:
                    data = await self._fetch_recently_added(section_id)
                    for item in data.findall(".//Video"):
                        rating_key = item.get('ratingKey')
                        poster_path = os.path.join(self._www_dir, f"poster_{rating_key}.jpg")
                        fanart_path = os.path.join(self._www_dir, f"fanart_{rating_key}.jpg")

                        # Download and save images locally
                        if 'thumb' in item.attrib:
                            await self._save_image(f"{self._base_url}{item.attrib['thumb']}?X-Plex-Token={self._token}", poster_path)
                        if 'art' in item.attrib:
                            await self._save_image(f"{self._base_url}{item.attrib['art']}?X-Plex-Token={self._token}", fanart_path)

                        media_data = {
                            'title': item.attrib.get('title', 'Unknown'),
                            'episode': item.attrib.get('originalTitle', 'N/A'),
                            'release': item.attrib.get('originallyAvailableAt', 'Unknown'),
                            'number': item.attrib.get('index', 'N/A'),
                            'runtime': int(item.attrib.get('duration', 0)) // 60000,  # Convert to minutes
                            'genres': ', '.join([genre.attrib.get('tag', '') for genre in item.findall(".//Genre")]),
                            'poster': f"/local/{DEFAULT_IMAGE_PATH}poster_{rating_key}.jpg",
                            'fanart': f"/local/{DEFAULT_IMAGE_PATH}fanart_{rating_key}.jpg",
                        }
                        recently_added.append(media_data)

                except Exception as section_err:
                    _LOGGER.error("Error updating section %s: %s", section_id, section_err)

            recently_added.sort(key=lambda x: x.get('added', ''), reverse=True)
            card_json.extend(recently_added[:self._max_items])

            if not card_json:
                # Add default if no data
                card_json.append({
                    'title_default': '$title',
                    'line1_default': '$episode',
                    'line2_default': '$release',
                    'line3_default': '$number - $rating - $runtime',
                    'line4_default': '$genres',
                    'icon': 'mdi:eye-off'
                })

            self._state = len(recently_added)
            self._attributes = {'data': card_json}
            self._available = True

        except Exception as err:
            _LOGGER.error("Error updating Plex sensor: %s", err)
            self._state = 0
            self._attributes = {'data': []}
            self._available = False

    @classmethod
    async def create_sensors(cls, hass, config):
        """Create a single Plex sensor for all sections."""
        try:
            base_url = f"http://{config[CONF_HOST]}:{config[CONF_PORT]}"
            token = config[CONF_TOKEN]

            # Fetch sections
            url = f"{base_url}/library/sections"
            headers = {"X-Plex-Token": token, "Accept": "application/xml"}
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            raise Exception(f"Error fetching library sections: {response.status}")
                        xml_content = await response.text()

            # Parse XML
            root = ET.fromstring(xml_content)
            sections = [directory.get("key") for directory in root.findall(".//Directory") if directory.get("key")]

            return [cls(hass, config, sections)]

        except Exception as error:
            _LOGGER.error("Error initializing Plex sensors: %s", error)
            return []
