"""Radarr integration for Mediarr with fixes."""
import os
import logging
from datetime import datetime
import async_timeout
from ..common.sensor import MediarrSensor

_LOGGER = logging.getLogger(__name__)
DEFAULT_IMAGE_PATH = 'mediarr-images/radarr/'

class RadarrMediarrSensor(MediarrSensor):
    def __init__(self, session, api_key, url, max_items):
        """Initialize the sensor."""
        super().__init__()
        self._session = session
        self._api_key = api_key
        self._url = url.rstrip('/')
        self._max_items = max_items
        self._name = "Radarr Mediarr"
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
        return f"radarr_mediarr_{self._url}"

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

    async def _get_image_paths(self, movie_id):
        """Get local image paths for poster and fanart."""
        poster_path = f'p{movie_id}.jpg'
        fanart_path = f'f{movie_id}.jpg'

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
        if not self._www_dir:
            return

        try:
            headers = {'X-Api-Key': self._api_key}
            now = datetime.now().astimezone()

            async with async_timeout.timeout(10):
                async with self._session.get(
                    f"{self._url}/api/v3/movie",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        movies = await response.json()
                        card_json = []

                        upcoming_movies = []

                        for movie in movies:
                            if not movie.get('monitored', False) or movie.get('hasFile', False):
                                continue

                            release_dates = []
                            for date_field, date_type in [
                                ('digitalRelease', 'Digital'),
                                ('physicalRelease', 'Physical'),
                                ('inCinemas', 'Theaters')
                            ]:
                                if movie.get(date_field):
                                    try:
                                        release_date = datetime.fromisoformat(
                                            movie[date_field].replace('Z', '+00:00')
                                        )
                                        if not release_date.tzinfo:
                                            release_date = release_date.replace(tzinfo=now.tzinfo)
                                        if release_date > now:
                                            release_dates.append((date_type, release_date))
                                    except ValueError as e:
                                        _LOGGER.warning("Error parsing date for movie %s: %s", 
                                                    movie.get('title', 'Unknown'), e)
                                        continue

                            if release_dates:
                                release_dates.sort(key=lambda x: x[1])
                                release_type, release_date = release_dates[0]

                                # Get and download images
                                paths = await self._get_image_paths(movie['id'])
                                poster_url = f"{self._url}/api/v3/mediacover/{movie['id']}/poster.jpg?apikey={self._api_key}"
                                fanart_url = f"{self._url}/api/v3/mediacover/{movie['id']}/fanart.jpg?apikey={self._api_key}"

                                await self._download_image(poster_url, paths['local_poster'])
                                await self._download_image(fanart_url, paths['local_fanart'])

                                movie_data = {
                                    "title": movie["title"],
                                    "release": f"{release_type} - {release_date.strftime('%Y-%m-%d')}",
                                    "aired": release_date.strftime("%Y-%m-%d"),
                                    "year": movie["year"],
                                    "poster": paths['poster'],
                                    "fanart": paths['fanart'],
                                    "genres": ", ".join(movie.get("genres", [])[:3]),
                                    "runtime": movie.get("runtime", 0),
                                    "rating": str(movie.get("ratings", {}).get("value", "")),
                                    "studio": movie.get("studio", "N/A"),
                                    "flag": True
                                }
                                upcoming_movies.append(movie_data)

                        upcoming_movies.sort(key=lambda x: x['aired'])
                        card_json.extend(upcoming_movies[:self._max_items])

                        # Add default row only if no data is available
                        if not card_json:
                            card_json.append({
                                'title_default': '$title',
                                'line1_default': '$release',
                                'line2_default': '$genres',
                                'line3_default': '$rating - $runtime',
                                'line4_default': '$studio',
                                'icon': 'mdi:arrow-down-circle'
                            })

                        self._state = len(upcoming_movies)
                        self._attributes = {'data': card_json}
                        self._available = True
                    else:
                        raise Exception(f"Failed to connect to Radarr. Status: {response.status}")

        except Exception as err:
            _LOGGER.error("Error updating Radarr sensor: %s", err)
            self._state = 0
            self._attributes = {'data': []}
            self._available = False
