# mediarr/manager/sonarr.py
"""Sonarr integration for Mediarr."""

import os
import logging
from datetime import datetime, timedelta
import async_timeout
from zoneinfo import ZoneInfo
from ..common.sensor import MediarrSensor

_LOGGER = logging.getLogger(__name__)
DEFAULT_IMAGE_PATH = 'mediarr-images/sonarr/'

class SonarrMediarrSensor(MediarrSensor):
    def __init__(self, session, api_key, url, max_items, days_to_check):
        """Initialize the sensor."""
        super().__init__()
        self._session = session
        self._api_key = api_key
        self._url = url.rstrip('/')
        self._max_items = max_items
        self._days_to_check = days_to_check
        self._name = "Sonarr Mediarr"
        
        # We'll set up the image directory in async_added_to_hass
        self._www_dir = None

    async def async_added_to_hass(self):
        """Handle adding to Home Assistant."""
        self._www_dir = os.path.join(self.hass.config.path(), 'www', DEFAULT_IMAGE_PATH)
        if not os.path.exists(self._www_dir):
            os.makedirs(self._www_dir, mode=0o777)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"sonarr_mediarr_{self._url}"

    def parse_date(self, date_str: str) -> datetime:
        """Parse date string to timezone-aware datetime."""
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
        return dt

    async def _download_image(self, url, local_path):
        """Download image from URL and save to local path."""
        try:
            if os.path.exists(local_path):
                return True
                
            async with async_timeout.timeout(10):
                async with self._session.get(url) as response:
                    if response.status == 200:
                        with open(local_path, 'wb') as f:
                            f.write(await response.read())
                        return True
        except Exception as error:
            _LOGGER.error("Error downloading image: %s", error)
        return False

    async def _get_image_paths(self, series_id):
        """Get local image paths for poster and fanart."""
        poster_path = f'p{series_id}.jpg'
        fanart_path = f'f{series_id}.jpg'
        
        local_poster = os.path.join(self._www_dir, poster_path)
        local_fanart = os.path.join(self._www_dir, fanart_path)
        
        return {
            'poster': f'/local/{DEFAULT_IMAGE_PATH}{poster_path}',
            'fanart': f'/local/{DEFAULT_IMAGE_PATH}{fanart_path}',
            'local_poster': local_poster,
            'local_fanart': local_fanart
        }

    async def async_update(self):
        """Update the sensor."""
        try:
            if not self._www_dir:
                return

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
                        card_json = []

                        shows_dict = {}

                        for episode in upcoming_episodes:
                            if not episode.get('monitored', False):
                                continue

                            series = episode.get('series', {})
                            if not series.get('monitored', False):
                                continue

                            try:
                                air_date = self.parse_date(episode['airDate'])
                                if air_date < now:
                                    continue
                            except ValueError as e:
                                _LOGGER.warning("Error parsing date: %s", e)
                                continue

                            series_id = series['id']

                            # Get and download images
                            paths = await self._get_image_paths(series_id)
                            await self._download_image(
                                f"{self._url}/api/v3/mediacover/{series_id}/poster.jpg?apikey={self._api_key}",
                                paths['local_poster']
                            )
                            await self._download_image(
                                f"{self._url}/api/v3/mediacover/{series_id}/fanart.jpg?apikey={self._api_key}",
                                paths['local_fanart']
                            )

                            show_data = {
                                'title': series['title'],
                                'episode': episode.get('title', 'Unknown'),
                                'release': air_date.strftime('%Y-%m-%d'),
                                'aired': air_date.strftime('%Y-%m-%d'),
                                'number': f"S{episode.get('seasonNumber', 0):02d}E{episode.get('episodeNumber', 0):02d}",
                                'runtime': series.get('runtime', 0),
                                'network': series.get('network', 'N/A'),
                                'poster': paths['poster'],
                                'fanart': paths['fanart'],
                                'flag': True
                            }

                            if series_id not in shows_dict or air_date < self.parse_date(shows_dict[series_id]['aired']):
                                shows_dict[series_id] = show_data

                        upcoming_shows = list(shows_dict.values())
                        upcoming_shows.sort(key=lambda x: x['aired'])
                        card_json.extend(upcoming_shows[:self._max_items])

                        # Add default row only if no data is available
                        if not card_json:
                            card_json.append({
                                'title_default': '$title',
                                'line1_default': '$episode',
                                'line2_default': '$release',
                                'line3_default': '$number',
                                'line4_default': '$runtime - $network',
                                'icon': 'mdi:arrow-down-circle'
                            })

                        self._state = len(upcoming_shows)
                        self._attributes = {'data': card_json}
                        self._available = True
                    else:
                        raise Exception(f"Failed to connect to Sonarr. Status: {response.status}")

        except Exception as err:
            _LOGGER.error("Error updating Sonarr sensor: %s", err)
            self._state = 0
            self._attributes = {'data': []}
            self._available = False
