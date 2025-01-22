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

requires 3 sensors in config 
```
- platform: sonarr_mediarr
  url: http://192.168.254.205:8989 #use your own of course
  api_key: fromsonarrsettingsgeneral
  max_items: 10 #default is 10

- platform: radarr_mediarr
  url: http://192.168.254.205:7878 #use your own of course
  api_key: fromradarrsettingsgeneral
  max_items: 10 #default is 10

- platform: plex_mediarr
  host: 192.168.254.205 #use your own of course
  port: 32400
  token: your plex token
  max_items: 10 #default is 10
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
