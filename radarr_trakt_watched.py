#!/usr/bin/env python

from datetime import datetime
import os
import json
import requests
import trakt
from trakt.users import User


trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH
trakt.core.OAUTH_TOKEN = 'xxx'
trakt.core.CLIENT_ID = '131180931168c71c44673fb8b2896017bcf79b4791a504d2d91bec4120bff3d1'
trakt.core.CLIENT_SECRET = '1aed035ad7f62cfcd38c35f3ced19c8298e9d0f1dcb7dc553df32eb14808736b'
trakt_user = 'xxx'
recent_days = 30

radarr_ip = 'x.x.x.x' 
radarr_port = '7878'
radarr_apikey = 'xxx'

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
response = requests.get("http://"+radarr_ip+":"+radarr_port+"/api/movie?apikey="+radarr_apikey)

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
            request_uri ='http://'+radarr_ip+':'+radarr_port+'/api/movie?apikey='+radarr_apikey
            r = requests.put(request_uri, json=movie_json)
