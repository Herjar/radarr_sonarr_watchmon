# radarr-sonarr-watchmon

This script checks for recently watched movies/episodes on Trakt and stops monitoring in Radarr/Sonarr/Medusa.

Copy config.example.yml to config.yml and change settings.

If you do not want to use either Sonarr, Radarr or Medusa set enabled to False in config.yml.

First run should be done interactively to get authorized to Trakt.
The authorization is then saved to a file and the script can be run periodically in e.g. crontab.
