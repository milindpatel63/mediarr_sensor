# mediarr/sensor.py
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from custom_components.mediarr.common.const import (
    CONF_MAX_ITEMS, 
    CONF_DAYS, 
    DEFAULT_MAX_ITEMS, 
    DEFAULT_DAYS,
    TRAKT_ENDPOINTS,
    TMDB_ENDPOINTS
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Mediarr sensors from YAML configuration."""
    session = async_get_clientsession(hass)
    sensors = []

    # Server Sensors
    if "plex" in config:
        from .server.plex import PlexMediarrSensor
        plex_sensors = await PlexMediarrSensor.create_sensors(hass, config["plex"])
        sensors.extend(plex_sensors)

    # Manager Sensors
    if "sonarr" in config:
        from .manager.sonarr import SonarrMediarrSensor
        sensors.append(SonarrMediarrSensor(
            session,
            config["sonarr"]["api_key"],
            config["sonarr"]["url"],
            config["sonarr"].get("max_items", DEFAULT_MAX_ITEMS),
            config["sonarr"].get("days_to_check", DEFAULT_DAYS)
        ))

    if "radarr" in config:
        from .manager.radarr import RadarrMediarrSensor
        sensors.append(RadarrMediarrSensor(
            session,
            config["radarr"]["api_key"],
            config["radarr"]["url"],
            config["radarr"].get("max_items", DEFAULT_MAX_ITEMS)
        ))

    # Discovery Sensors - Trakt
    if "trakt" in config:
        from .discovery.trakt import TraktMediarrSensor
        for endpoint in TRAKT_ENDPOINTS:
            if config["trakt"].get(endpoint, endpoint == 'trending'):  # trending enabled by default
                sensors.append(TraktMediarrSensor(
                    session,
                    config["trakt"]["client_id"],
                    config["trakt"]["client_secret"],
                    endpoint,
                    config["trakt"].get("media_type", "both"),
                    config["trakt"].get("max_items", DEFAULT_MAX_ITEMS),
                    config["trakt"].get("tmdb_api_key")
                ))

    # Discovery Sensors - TMDB
    if "tmdb" in config:
        from .discovery.tmdb import TMDBMediarrSensor
        for endpoint in TMDB_ENDPOINTS:
            if config["tmdb"].get(endpoint, endpoint == 'trending'):  # trending enabled by default
                sensors.append(TMDBMediarrSensor(
                    session,
                    config["tmdb"]["api_key"],
                    endpoint=endpoint,
                    max_items=config["tmdb"].get("max_items", DEFAULT_MAX_ITEMS)
                ))

    if sensors:
        async_add_entities(sensors, True)