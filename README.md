Support This Project If you find this project helpful, please consider supporting it. Your contributions help maintain and improve the project. Any support is greatly appreciated! ❤️ https://buymeacoffee.com/vansmak Thank you for your support!

custom card to show upcoming sonarr and radarr and recently added to plex

![Screenshot 2025-01-21 at 14-51-50 mediarr – Home Assistant](https://github.com/user-attachments/assets/4c73b44a-680a-42ea-8d2b-0d96806fb1c6)


copy the custom_components folder to your config
```
  /custom_components/plex-mediarr/*
  /custom_components/radarr-mediarr/*
  /custom_components/sonarr-mediarr/*
```
copy the www folder contents to your www folder
```
  www/community/mediarr-card/mediarr-card.js
```
Restart HA

requires sensors in config 1 or all 3
```
sensor:
  - platform: mediarr
    plex:
      host: localhost
      port: 32400
      token: your_plex_token
      max_items: 10
    
    sonarr:
      url: http://localhost:8989
      api_key: your_sonarr_api_key
      max_items: 10
      days_to_check: 60
    
    radarr:
      url: http://localhost:7878
      api_key: your_radarr_api_key
      max_items: 10
```

Restart HA 

add card to dashboard 
```
type: custom:mediarr-card
plex_entity: sensor.plex_mediarr
sonarr_entity: sensor.sonarr_mediarr
radarr_entity: sensor.radarr_mediarr
media_player_entity: media_player.your plex_media_player

```
future plans include Jellyfin and HACS

Clik to play, limited right now
