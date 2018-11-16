#!/usr/bin/env python

from datetime import datetime
import requests
import trakt
from trakt.users import User
import yaml

with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

########################## CONFIG #########################################
trakt.core.OAUTH_TOKEN = cfg['trakt']['oauth_token']
trakt.core.CLIENT_ID = cfg['trakt']['client_id']
trakt.core.CLIENT_SECRET = cfg['trakt']['client_secret']
trakt_user =  cfg['trakt']['trakt_user']
recent_days = cfg['trakt']['recent_days']

radarr_ip = cfg['radarr']['ip'] 
radarr_port = cfg['radarr']['port']
radarr_apikey = cfg['radarr']['apikey']
###########################################################################

trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH

# Get all watched movies
me = trakt.users.User(trakt_user)
movies_watched = me.watched_movies

# Get recently watched movies
print("Movies watches in last "+str(recent_days)+" days:")
movies_watched_recently = []
movies_watched_recently_imdbids = []
now = datetime.today()

for movie in movies_watched:
    last_watched_at = datetime.strptime(movie.last_watched_at[0:10], '%Y-%m-%d')
    watched_delta = days = now - last_watched_at
    watched_days = watched_delta.days
    if watched_days < recent_days:
        print(movie.title).encode('utf-8')
        movies_watched_recently.append(movie)
        movies_watched_recently_imdbids.append(movie.ids["ids"]["imdb"])
print()

# Get all movies from radarr
response = requests.get("http://"+radarr_ip+":"+str(radarr_port)+"/api/movie?apikey="+radarr_apikey)

# Look for recently watched movies in Radarr and change monitored to False
for movie in response.json():
    try:
        radarr_imdb = movie["imdbId"]
    except:
        # print("imdbID missing")
        pass

    for id in movies_watched_recently_imdbids:
        if id == radarr_imdb:
            print("Setting monitored to False for: "+movie["title"])
            radarr_id = movie["id"]
            movie_json = movie
            movie_json["monitored"] = "False"
            request_uri ='http://'+radarr_ip+':'+str(radarr_port)+'/api/movie?apikey='+radarr_apikey
            r = requests.put(request_uri, json=movie_json)
