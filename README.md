Support This Project If you find this project helpful, please consider supporting it. Your contributions help maintain and improve the project. Any support is greatly appreciated! ❤️ https://buymeacoffee.com/vansmak Thank you for your support!

This is a media card inspired by the upcoming media card. You can use or not use the following. Plex (jellyfin will get added), Sonarr, Radarr, Trakt, TMDB. Plex section shows recently added, sonarr and radarr shows upcoming (wanted). Trakt for now is just showing popular and tmdb is weekly trending but can be set to tv, movies or all. I wanted to be able to select a Plex title and launch it to a Plex client but it's not working yet. I may also have it hide popular and trending if it's already in Plex library. Or mark them with a plex symbol. Shows that aren't already tracked with a link to add to sonarr. Same for movies and radarr. For those not into the Arr's this is still good without.![Screenshot_20250122-214951](https://github.com/user-attachments/assets/fcd18754-d6b8-4e74-b489-8d5ffb94d945)
![VIEW](https://github.com/user-attachments/assets/e5eda74d-e50b-4dde-9985-45282dc99a51)


![Screenshot 2025-01-21 at 14-51-50 mediarr – Home Assistant](https://github.com/user-attachments/assets/4c73b44a-680a-42ea-8d2b-0d96806fb1c6)


copy the custom_components folder to your config
```
  /custom_components/mediarr/*
  
```
copy the www folder contents to your www folder
```
  www/community/mediarr-card/mediarr-card.js
```
Restart HA

requires sensors in config 1 or all 5
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

    trakt:
      client_id: "clientid"
      client_secret: "clientsecret"
      tmdb_api_key: "apikey" #needrd for posters
      trending_type: both
      max_items: 10

    tmdb:
      api_key: "apikey"
      trending_type: all
      max_items: 10
```

Restart HA 

add card to dashboard 
```
type: custom:mediarr-card
plex_entity: sensor.plex_mediarr
sonarr_entity: sensor.sonarr_mediarr
radarr_entity: sensor.radarr_mediarr
trakt_entity: sensor.trakt_mediarr
tmdb_entity: sensor.tmdb_mediarr
media_player_entity: media_player.your plex_media_player

```
