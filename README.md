# radarr-sonarr-watchmon

This script checks for recently watched movies/episodes on Trakt and stops monitoring and/or adds tags in Radarr/Sonarr/Medusa.

First run should be done interactively to get authorized to Trakt.
The authorization is then saved to a file and the script can be run periodically in e.g. crontab.


## Configuration

Copy config.example.yml to config.yml and change settings.

If you do not want to use either Sonarr, Radarr or Medusa set enabled to False in config.yml.

Radarr supports unmonitoring movies watched and/or adding a tag to the movie and/or deleting movie file.

Sonarr supports unmonitoring episodes watched and/or adding a tag to the show and/or deleting episode file.

Medusa supports unmonitoring episodes watched.



## Docker 🐳

Running `radarr_sonarr_watchmon.py` in a container means zero host-side Python dependencies and a portable, reproducible setup for cron jobs, NAS devices, Kubernetes **CronJobs**, GitHub Actions, or anywhere Docker is available.

### 1  Build the image

```bash
git clone https://github.com/Herjar/radarr_sonarr_watchmon.git
cd radarr_sonarr_watchmon

# multi-stage build → final image ≈ 80 MB
docker build -t arr-watchmon:latest .
```

### 2 Run the container
#### 2.1 Run with environment variables (no config.yml)

The supplied docker-entrypoint.sh converts env-vars into a temporary config.yml before launching the script.

```bash
touch $PWD/.auth.pkl
docker run --rm -it \
  -e TZ=Asia/Jerusalem \
  -e RADARR_ADDRESS=x.x.x.x:7878 \
  -e RADARR_APIKEY=<APIKEY> \
  -e SONARR_ADDRESS=x.x.x.x:8989 \
  -e SONARR_APIKEY=<APIKEY> \
  -v $PWD/.auth.pkl:/app/.auth.pkl          # Trakt token cache
  arr-watchmon:latest
```

#### Environment-variable reference
| Group  | Variables                                                                                                                                                                                                                                |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Trakt  | `TRAKT_RECENT_DAYS`                                                                                                                                                                                                                      |
| Radarr | `RADARR_ENABLED`, `RADARR_ADDRESS`, `RADARR_APIKEY`, `RADARR_TAG`, `RADARR_UNMONITOR`, `RADARR_DELETE_FILE`                                                                                                                              |
| Sonarr | `SONARR_ENABLED`, `SONARR_ADDRESS`, `SONARR_APIKEY`, `SONARR_TAG`, `SONARR_UNMONITOR`, `SONARR_DELETE_FILE`                                                                                                                              |
| Medusa | `MEDUSA_ENABLED`, `MEDUSA_ADDRESS`, `MEDUSA_USERNAME`, `MEDUSA_PASSWORD`                                                                                                                                                                 |

Booleans accept true / false (lower-case).

#### 2.2 Run with an external config.yml
```bash
touch $PWD/.auth.pkl
docker run --rm \
  -e TZ=Asia/Jerusalem \
  -v $PWD/config.yml:/config/config.yml:ro \
  -v $PWD/.auth.pkl:/config/.auth.pkl \
  arr-watchmon:latest
```

The default CMD inside the image is:
python radarr_sonarr_watchmon.py --config /config/config.yml

#### 2.3 Scheduled runs with docker-compose
```yaml
# docker-compose.yml
version: "3.9"

services:
  watchmon:
    image: arr-watchmon:latest      # or: build: .
    container_name: watchmon
    environment:
      TZ: Asia/Jerusalem
      RADARR_ADDRESS: "radarr:7878"
      RADARR_APIKEY:  "..."
      SONARR_ADDRESS: "sonarr:8989"
      SONARR_APIKEY:  "..."
    volumes:
      - ./auth.pkl:/app/.auth.pkl
    restart: unless-stopped
```
Schedule the compose service externally—cron, systemd timer, Kubernetes CronJob, etc.—because radarr_sonarr_watchmon.py executes once and exits cleanly.

### 3 Updating
```bash
git pull                       # fetch new commits
docker build -t arr-watchmon:latest .
docker compose up -d           # or rerun `docker run …`
```
Layer-caching makes rebuilds fast and incremental.


