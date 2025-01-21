class MediarrCard extends HTMLElement {
  constructor() {
    super();
    this.selectedType = 'plex';
    this.selectedIndex = 0;
  }

  set hass(hass) {
    if (!this.content) {
      this.innerHTML = `
        <ha-card>
          <div class="now-playing hidden">
            <div class="now-playing-background"></div>
            <div class="now-playing-content">
              <div class="now-playing-info">
                <div class="now-playing-title"></div>
                <div class="now-playing-subtitle"></div>
              </div>
              <div class="media-controls">
                <ha-icon class="control-button play-pause" icon="mdi:play"></ha-icon>
              </div>
            </div>
            <div class="progress-bar">
              <div class="progress-bar-fill"></div>
            </div>
          </div>
          <div class="media-content">
            <div class="media-background"></div>
            <div class="media-info"></div>
            <div class="play-button hidden">
              <ha-icon class="play-icon" icon="mdi:play-circle-outline">
                <ha-svg-icon></ha-svg-icon>
              </ha-icon>
            </div>
          </div>
          <div class="section-header">
            <div class="section-label">Recently Added</div>
          </div>
          <div class="plex-list"></div>
          <div class="section-header">
            <div class="section-label">Upcoming Shows</div>
          </div>
          <div class="show-list"></div>
          <div class="section-header">
            <div class="section-label">Upcoming Movies</div>
          </div>
          <div class="movie-list"></div>
        </ha-card>
      `;

      this.card = this.querySelector('ha-card');
      this.content = this.querySelector('.media-content');
      this.background = this.querySelector('.media-background');
      this.info = this.querySelector('.media-info');
      this.plexList = this.querySelector('.plex-list');
      this.showList = this.querySelector('.show-list');
      this.movieList = this.querySelector('.movie-list');
      this.playButton = this.querySelector('.play-button');
      this.nowPlaying = this.querySelector('.now-playing');
      this.nowPlayingTitle = this.querySelector('.now-playing-title');
      this.nowPlayingSubtitle = this.querySelector('.now-playing-subtitle');
      this.progressBar = this.querySelector('.progress-bar-fill');
      this.playPauseButton = this.querySelector('.play-pause');
      // Set up progress bar update interval
      this.progressInterval = setInterval(() => {
        if (this.config.media_player_entity && hass) {
          const entity = hass.states[this.config.media_player_entity];
          if (entity && entity.attributes.media_position && entity.attributes.media_duration) {
            const progress = (entity.attributes.media_position / entity.attributes.media_duration) * 100;
            this.progressBar.style.width = `${progress}%`;
          }
        }
      }, 1000);
      
      // Add click handler for play/pause button
      if (this.playPauseButton) {
        this.playPauseButton.onclick = (e) => {
          e.stopPropagation();
          if (this.config.media_player_entity && hass) {
            const entity = hass.states[this.config.media_player_entity];
            if (entity) {
              const service = entity.state === 'playing' ? 'media_pause' : 'media_play';
              hass.callService('media_player', service, {
                entity_id: this.config.media_player_entity
              });
            }
          }
        };
      }
      if (this.playButton) {
        this.playButton.onclick = (e) => {
          e.stopPropagation(); // Prevent triggering the media-content click
          console.log('Play button clicked');
          
          if (this.selectedType === 'plex' && this.config.media_player_entity && hass) {
            console.log('Plex playback conditions met');
            const entity = hass.states[this.config.media_player_entity];
            const plexEntity = hass.states[this.config.plex_entity];
            
            console.log('Media player entity:', this.config.media_player_entity);
            console.log('Media player state:', entity);
            console.log('Plex entity:', plexEntity);
            
            if (entity && plexEntity?.attributes?.data) {
              const mediaItem = plexEntity.attributes.data[this.selectedIndex];
              console.log('Selected media item:', mediaItem);
              
              if (mediaItem?.key) {
                console.log('Attempting to play media with key:', mediaItem.key);
                hass.callService('media_player', 'play_media', {
                  entity_id: this.config.media_player_entity,
                  media_content_id: mediaItem.key,
                  media_content_type: 'plex'
                }).then(() => {
                  console.log('Play media service called successfully');
                }).catch(error => {
                  console.error('Error calling play media service:', error);
                });
              } else {
                console.warn('No media key found for item');
              }
            } else {
              console.warn('Media player or Plex entity not found');
            }
          } else {
            console.warn('Basic conditions not met:', {
              selectedType: this.selectedType,
              hasMediaPlayer: Boolean(this.config.media_player_entity),
              hasHass: Boolean(hass)
            });
          }
        };
      }

      const style = document.createElement('style');
      style.textContent = `
        ha-card {
          overflow: hidden;
          padding-bottom: 8px;
        }
        .media-content {
          position: relative;
          width: 100%;
          height: 160px;
          overflow: hidden;
          border-radius: var(--ha-card-border-radius, 4px);
          margin-bottom: 8px;
          cursor: pointer;
        }
        .media-background {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-size: cover;
          background-position: center;
          background-repeat: no-repeat;
          transition: all 0.3s ease-in-out;
          filter: blur(var(--blur-radius, 0px));
          transform: scale(1.1);
        }
        .media-content:hover .media-background {
          transform: scale(1.15);
        }
        .media-info {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          padding: 12px;
          background: linear-gradient(transparent, rgba(0,0,0,0.8));
          color: white;
          opacity: 1;
          z-index: 1;
        }
        .play-button {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          z-index: 2;
          color: white;
          opacity: 0;
          transition: opacity 0.3s ease-in-out;
          background: rgba(0, 0, 0, 0.5);
          border-radius: 50%;
          padding: 8px;
          cursor: pointer;
        }
        .play-button ha-icon {
          --mdc-icon-size: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .play-button ha-svg-icon {
          width: 40px;
          height: 40px;
          fill: currentColor;
        }
        .media-content:hover .play-button:not(.hidden) {
          opacity: 1;
        }
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 4px 8px;
        }
        .section-label {
          font-weight: 500;
          font-size: 13px;
          color: var(--primary-text-color);
          text-transform: uppercase;
        }
        .show-list, .movie-list, .plex-list {
          padding: 0 8px;
          display: flex;
          gap: 6px;
          overflow-x: auto;
          scrollbar-width: thin;
          margin-bottom: 8px;
        }
        .media-item {
          flex: 0 0 auto;
          width: 90px;
          height: 135px;
          position: relative;
          cursor: pointer;
          transition: all 0.2s;
          border-radius: 4px;
          overflow: hidden;
        }
        .media-item:hover {
          transform: translateY(-2px);
        }
        .media-item.selected {
          box-shadow: 0 0 0 2px var(--primary-color);
        }
        .media-item img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .media-item::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          height: 50%;
          background: linear-gradient(transparent, rgba(0,0,0,0.9));
          pointer-events: none;
        }
        .media-item-title {
          position: absolute;
          bottom: 4px;
          left: 4px;
          right: 4px;
          font-size: 0.75em;
          color: white;
          z-index: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          line-height: 1.2;
          text-shadow: 1px 1px 1px rgba(0,0,0,0.5);
        }
        .title {
          font-size: 1.2em;
          font-weight: 500;
          margin-bottom: 2px;
        }
        .details {
          font-size: 1em;
          margin-bottom: 2px;
        }
        .metadata {
          font-size: 0.85em;
          opacity: 0.8;
        }
        .hidden {
          display: none;
        }

        /* Custom scrollbar styles */
        .show-list::-webkit-scrollbar,
        .movie-list::-webkit-scrollbar,
        .plex-list::-webkit-scrollbar {
          height: 4px;
        }
        .show-list::-webkit-scrollbar-track,
        .movie-list::-webkit-scrollbar-track,
        .plex-list::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.1);
          border-radius: 2px;
        }
        .show-list::-webkit-scrollbar-thumb,
        .movie-list::-webkit-scrollbar-thumb,
        .plex-list::-webkit-scrollbar-thumb {
          background: var(--primary-color);
          border-radius: 2px;
        }
        .now-playing {
          position: relative;
          width: 100%;
          height: 60px;
          background: var(--primary-background-color);
          overflow: hidden;
        }
        .now-playing.hidden {
          display: none;
        }
        .now-playing-background {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-size: cover;
          background-position: center;
          filter: blur(10px) brightness(0.3);
          transform: scale(1.2);
        }
        .now-playing-content {
          position: relative;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 16px;
          height: 44px;
          color: white;
        }
        .now-playing-info {
          flex: 1;
          overflow: hidden;
          margin-right: 16px;
        }
        .now-playing-title {
          font-weight: 500;
          font-size: 1em;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .now-playing-subtitle {
          font-size: 0.8em;
          opacity: 0.8;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .media-controls {
          display: flex;
          gap: 16px;
          align-items: center;
        }
        .control-button {
          --mdc-icon-size: 24px;
          cursor: pointer;
          opacity: 0.8;
          transition: opacity 0.2s;
        }
        .control-button:hover {
          opacity: 1;
        }
        .progress-bar {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: rgba(255,255,255,0.2);
        }
        .progress-bar-fill {
          height: 100%;
          background: var(--primary-color);
          width: 0%;
          transition: width 1s linear;
        }
      `;
      this.appendChild(style);
    }

    const config = this.config;
    // Update Now Playing section if media player is active
    if (this.config.media_player_entity) {
      const entity = hass.states[this.config.media_player_entity];
      if (entity && entity.state !== 'unavailable' && entity.state !== 'idle' && entity.state !== 'off') {
        this.nowPlaying.classList.remove('hidden');
        this.nowPlayingTitle.textContent = entity.attributes.media_title || '';
        this.nowPlayingSubtitle.textContent = entity.attributes.media_series_title || '';
        
        // Update play/pause button
        this.playPauseButton.setAttribute('icon', entity.state === 'playing' ? 'mdi:pause' : 'mdi:play');
        
        // Update progress bar if available
        if (entity.attributes.media_position && entity.attributes.media_duration) {
          const progress = (entity.attributes.media_position / entity.attributes.media_duration) * 100;
          this.progressBar.style.width = `${progress}%`;
        }
        
        // Update background if available
        if (entity.attributes.entity_picture) {
          const backgroundUrl = entity.attributes.entity_picture;
          this.querySelector('.now-playing-background').style.backgroundImage = `url('${backgroundUrl}')`;
        }
      } else {
        this.nowPlaying.classList.add('hidden');
      }
    }
    // Update Plex content
    const plexEntity = hass.states[config.plex_entity];
    if (plexEntity) {
      const plexItems = plexEntity.attributes.data || [];
      this.plexList.innerHTML = plexItems.map((item, index) => {
        return `
          <div class="media-item ${this.selectedType === 'plex' && index === this.selectedIndex ? 'selected' : ''}"
               data-type="plex"
               data-index="${index}">
            <img src="${item.poster}" alt="${item.title}">
            <div class="media-item-title">${item.title}</div>
          </div>
        `;
      }).join('');
    }

    // Update Sonarr content
    const sonarrEntity = hass.states[config.sonarr_entity];
    if (sonarrEntity) {
      const shows = sonarrEntity.attributes.data || [];
      this.showList.innerHTML = shows.map((show, index) => {
        return `
          <div class="media-item ${this.selectedType === 'sonarr' && index === this.selectedIndex ? 'selected' : ''}"
               data-type="sonarr"
               data-index="${index}">
            <img src="${show.poster}" alt="${show.title}">
            <div class="media-item-title">${show.title}</div>
          </div>
        `;
      }).join('');
    }

    // Update Radarr content
    const radarrEntity = hass.states[config.radarr_entity];
    if (radarrEntity) {
      const movies = radarrEntity.attributes.data || [];
      this.movieList.innerHTML = movies.map((movie, index) => {
        return `
          <div class="media-item ${this.selectedType === 'radarr' && index === this.selectedIndex ? 'selected' : ''}"
               data-type="radarr"
               data-index="${index}">
            <img src="${movie.poster}" alt="${movie.title}">
            <div class="media-item-title">${movie.title}</div>
          </div>
        `;
      }).join('');
    }

    // Add click handlers for media items
    this.querySelectorAll('.media-item').forEach(item => {
      item.onclick = () => {
        const type = item.dataset.type;
        const index = parseInt(item.dataset.index);
        this.selectedType = type;
        this.selectedIndex = index;

        let entity, mediaItem;
        switch(type) {
          case 'plex':
            entity = plexEntity;
            mediaItem = entity.attributes.data[index];
            break;
          case 'sonarr':
            entity = sonarrEntity;
            mediaItem = entity.attributes.data[index];
            break;
          case 'radarr':
            entity = radarrEntity;
            mediaItem = entity.attributes.data[index];
            break;
        }

        // Update background and info
        this.background.style.backgroundImage = `url('${mediaItem.fanart}')`;
        this.background.style.opacity = config.opacity || 0.7;

        // Show play button only for Plex content
        if (type === 'plex' && config.media_player_entity) {
          this.playButton.classList.remove('hidden');
        } else {
          this.playButton.classList.add('hidden');
        }

        // Update info based on type
        if (type === 'plex') {
          const addedDate = new Date(mediaItem.added).toLocaleDateString();
          const runtime = mediaItem.runtime ? `${mediaItem.runtime} min` : '';
          const subtitle = mediaItem.type === 'show' ? `${mediaItem.number || ''} - ${mediaItem.episode || ''}` : '';
          this.info.innerHTML = `
            <div class="title">${mediaItem.title}${mediaItem.year ? ` (${mediaItem.year})` : ''}</div>
            <div class="details">${subtitle}</div>
            <div class="metadata">Added: ${addedDate}${runtime ? ` | ${runtime}` : ''}</div>
          `;
        } else if (type === 'sonarr') {
          const airDate = new Date(mediaItem.airdate).toLocaleDateString();
          this.info.innerHTML = `
            <div class="title">${mediaItem.title}</div>
            <div class="details">${mediaItem.next_episode?.number || ''} - ${mediaItem.next_episode?.title || ''}</div>
            <div class="metadata">Airs: ${airDate}${mediaItem.network ? ` on ${mediaItem.network}` : ''}</div>
          `;
        } else if (type === 'radarr') {
          const releaseDate = new Date(mediaItem.releaseDate).toLocaleDateString();
          const runtime = mediaItem.runtime ? `${mediaItem.runtime} min` : '';
          this.info.innerHTML = `
            <div class="title">${mediaItem.title} (${mediaItem.year || ''})</div>
            <div class="details">${mediaItem.releaseType} Release</div>
            <div class="metadata">${releaseDate}${runtime ? ` | ${runtime}` : ''}</div>
          `;
        }

        // Update selected states
        this.querySelectorAll('.media-item').forEach(i => {
          i.classList.toggle('selected', 
            i.dataset.type === type && parseInt(i.dataset.index) === index);
        });
      };
    });

    // Initialize with first item if nothing is selected
    if (!this.background.style.backgroundImage) {
      const firstItem = this.querySelector('.media-item');
      if (firstItem) {
        firstItem.click();
      }
    }
  }

  setConfig(config) {
    if (!config.sonarr_entity && !config.radarr_entity && !config.plex_entity) {
      throw new Error('Please define at least one of sonarr_entity, radarr_entity, or plex_entity');
    }
    this.config = config;
  }

  static getStubConfig() {
    return {
      plex_entity: 'sensor.plex_mediarr',
      sonarr_entity: 'sensor.sonarr_mediarr',
      radarr_entity: 'sensor.radarr_mediarr',
      media_player_entity: '',
      opacity: 0.7,
      blur_radius: 0
    };
  }
    disconnectedCallback() {
      if (this.progressInterval) {
        clearInterval(this.progressInterval);
      }
    }
  }
  
customElements.define('mediarr-card', MediarrCard);

// Export the class for HACS
window.customCards = window.customCards || [];
window.customCards.push({
  type: "mediarr-card",
  name: "Mediarr Card",
  description: "A card for displaying Plex, Sonarr, and Radarr media",
  preview: true
});