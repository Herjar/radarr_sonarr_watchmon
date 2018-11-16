# radarr-trakt-watched

A script to stop monitoring a movie in Radarr when you have watched the movie.
Watched status is picked up from trakt.

Copy config.example.yml to config.yml

Edit the config and set it up to run periodically in e.g. crontab.

To get the OAUTH_TOKEN you can start an interactive python session and type:
```
import trakt
trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH
trakt.init('traktuser')
```
And follow the instructions. Find CLIENT_ID and CLIENT_SECRET in the example config.
