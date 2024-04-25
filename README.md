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


