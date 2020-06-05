#!/usr/bin/env python3
from __future__ import absolute_import, division, print_function

import sys
import os
from trakt import Trakt
from datetime import datetime, timedelta
from threading import Condition
import logging
import pickle
import requests
from pprint import pprint

# logging.basicConfig(level=logging.DEBUG)


class watchedMonitor(object):
    def __init__(self):
        self.is_authenticating = Condition()

        self.authorization = None

        # Bind trakt events
        Trakt.on('oauth.token_refreshed', self.on_token_refreshed)

    def auth_load(self):
        try:
            with open(os.path.join(sys.path[0], '.auth.pkl'), 'rb') as f:
                auth_file = pickle.load(f)
            self.authorization = auth_file
        except:
            pass

    def authenticate(self):
        if not self.is_authenticating.acquire(blocking=False):
            print('Authentication has already been started')
            return False

        # Request new device code
        code = Trakt['oauth/device'].code()

        print('Enter the code "%s" at %s to authenticate your account' % (
            code.get('user_code'),
            code.get('verification_url')
        ))

        # Construct device authentication poller
        poller = Trakt['oauth/device'].poll(**code)\
            .on('aborted', self.on_aborted)\
            .on('authenticated', self.on_authenticated)\
            .on('expired', self.on_expired)\
            .on('poll', self.on_poll)

        # Start polling for authentication token
        poller.start(daemon=False)

        # Wait for authentication to complete
        return self.is_authenticating.wait()

    def initialize(self):

        # Try to read auth from file
        self.auth_load()

        # If not read from file, get new auth and save to file
        if not self.authorization:
            self.authenticate()

        if not self.authorization:
            print('ERROR: Authentication required')
            exit(1)

        # Simulate expired token
        # self.authorization['expires_in'] = 0

        # print(self.authorization)
        # sys.exit()

    def trakt_get_movies(self, recent_days):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            # Expired token will be refreshed automatically (as `refresh=True`)
            today = datetime.now()
            recent_date = today - timedelta(days=recent_days)
            movies_watched_recently_imdbids = []

            print(" Trakt: movies watches in last "+str(recent_days)+" days:")
            for movie in Trakt['sync/history'].movies(start_at=recent_date, pagination=True):
                movie_dict = movie.to_dict()
                try:
                    movies_watched_recently_imdbids.append(movie_dict['ids']['imdb'])
                    print("  "+movie_dict['title'])
                except KeyError:
                    pass

        return movies_watched_recently_imdbids

    def radarr(self, recent_days, radarr_address, radarr_apikey):
        print("Radarr:")
        movies_watched_recently_imdbids = self.trakt_get_movies(recent_days)
        print("")

        # Get all movies from radarr
        response = requests.get("http://"+radarr_address+"/api/movie?apikey="+radarr_apikey)

        # Look for recently watched movies in Radarr and change monitored to False
        print(" Radarr: Movies found and changed monitored to False:")
        movies = response.json()
        for id in movies_watched_recently_imdbids:
            for movie in movies:
                try:
                    radarr_imdb = movie["imdbId"]
                except:
                    pass

                if id == radarr_imdb:
                    print("  "+movie["title"])
                    radarr_id = movie["id"]
                    movie_json = movie
                    movie_json["monitored"] = "False"
                    request_uri ='http://'+radarr_address+'/api/movie?apikey='+radarr_apikey
                    r = requests.put(request_uri, json=movie_json)


    def trakt_get_episodes(self, recent_days):
        with Trakt.configuration.oauth.from_response(self.authorization, refresh=True):
            # Expired token will be refreshed automatically (as `refresh=True`)
            today = datetime.now()    
            recent_date = today - timedelta(days=recent_days)
            show_episodes = dict()

            print(" Trakt: Episodes watched in last "+str(recent_days)+" days:")
            for episode in Trakt['sync/history'].shows(start_at=recent_date, pagination=True, extended='full'):
                episode_dict = episode.to_dict()
                ep_no = episode_dict['number']
                show = episode.show
                season = episode.season
                season_no = season.pk
                show_tvdb = show.pk[1]

                if show_tvdb in show_episodes:
                    # show_episodes_tvdbids[show_tvdb].append(episode_dict['ids']['tvdb'])
                    show_episodes[show_tvdb].append([season_no, ep_no])
                else:
                    show_episodes[show_tvdb] = []
                    show_episodes[show_tvdb].append([season_no, ep_no])

                print("  " + show.title + " - S"+str(season_no).zfill(2)+'E'+ str(episode_dict['number']).zfill(2) + ": " + episode_dict['title'])

        return show_episodes

    def sonarr(self, recent_days, sonarr_address, sonarr_apikey):

        print("Sonarr:")
        show_episodes = self.trakt_get_episodes(recent_days)

        print("")
        print(" Sonarr:")

        # Get all series from sonarr
        response = requests.get("http://"+sonarr_address+"/api/series?apikey="+sonarr_apikey)

        # Look for recently watched episodes in Sonarr and change monitored to False
        print(" Sonarr: Episodes found and changed monitored to False:")
        series = response.json()
        for showid_string in show_episodes:
            showid = int(showid_string)

            for show in series:
                try:
                    sonarr_tvdb = show["tvdbId"]
                    sonarr_id = show["id"]
                except:
                    sonarr_tvdb = 0
                    pass

                if showid == sonarr_tvdb:
                    print("  "+show["title"])

                    # Get all episodes in show from Sonarr
                    response_eps = requests.get("http://"+sonarr_address+"/api/episode/?seriesID="+str(sonarr_id)+"&apikey="+sonarr_apikey)
                    sonarr_show_eps = response_eps.json()

                    for trakt_season_ep in show_episodes[showid_string]:
                        trakt_season = trakt_season_ep[0]
                        trakt_ep = trakt_season_ep[1]

                        for sonarr_show_ep in sonarr_show_eps:
                            try:
                                # sonarr_ep_id = sonarr_show_ep["tvdbId"]
                                # sonarr_ep_id = sonarr_show_ep["tvDbEpisodeId"]
                                sonarr_ep = sonarr_show_ep["episodeNumber"]
                                sonarr_season = sonarr_show_ep["seasonNumber"]
                                sonarr_epid = sonarr_show_ep["id"]
                            except:
                                sonarr_ep = 0
                                sonarr_season = 0
                            
                            if trakt_season == sonarr_season and trakt_ep == sonarr_ep:
                                print("  " + " -S"+str(sonarr_season).zfill(2)+'E'+ str(sonarr_ep).zfill(2))

                                # Get sonarr episode
                                request_uri ='http://'+sonarr_address+'/api/episode/'+str(sonarr_epid)+'?apikey='+sonarr_apikey
                                sonarr_episode_json = requests.get(request_uri).json()

                                # Update sonarr episode
                                sonarr_episode_json["monitored"] = "False"
                                r = requests.put(request_uri, json=sonarr_episode_json)

    def medusa(self, recent_days, medusa_address, medusa_username, medusa_password):

        print("Medusa:")
        show_episodes = self.trakt_get_episodes(recent_days)

        print("")
        print(" Medusa: Episodes found and changed to Archived:")

        # Authenticate with the Medusa API & store the token
        data = '{"username": "'+medusa_username+'","password": "'+medusa_password+'"}'
        headers = {'Content-Type': 'application/json'}
        token = requests.post("http://"+medusa_address+"/api/v2/authenticate", data=data, headers=headers).json()['token']
        headers = {'authorization': 'Bearer ' + token}
		
        # Get all series from Medusa
        series = requests.get("http://"+medusa_address+"/api/v2/series?limit=1000", headers=headers).json()
		
	# Configure episode status to be Archived (6)
        medusa_status = '{"status": 6}'
		
        # Look for recently watched episodes in Medusa and change status to archived
        for showid_string in show_episodes:
            showid = int(showid_string)

            for show in series:
                try:
                    medusa_tvdb = show["id"]["tvdb"]
                    medusa_id = show["id"]["slug"]
                except:
                    medusa_tvdb = 0
                    pass

                if showid == medusa_tvdb:
                    # Get all episodes in show from Medusa
                    medusa_show_eps = requests.get("http://"+medusa_address+"/api/v2/series/"+medusa_id+"/episodes?limit=1000", headers=headers).json()

                    for trakt_season_ep in show_episodes[showid_string]:
                        trakt_season = trakt_season_ep[0]
                        trakt_ep = trakt_season_ep[1]

                        for medusa_show_ep in medusa_show_eps:
                            try:
                                medusa_ep = medusa_show_ep["episode"]
                                medusa_season = medusa_show_ep["season"]
                                medusa_epid = medusa_show_ep["slug"]
                                medusa_current_status = medusa_show_ep["status"]
                            except:
                                medusa_ep = 0
                                medusa_season = 0
                            
                            if trakt_season == medusa_season and trakt_ep == medusa_ep and medusa_current_status != "Archived" and medusa_current_status != "Ignored":
                                # Update Medusa episode status
                                medusa_patch = requests.patch("http://"+medusa_address+"/api/v2/series/"+medusa_id+"/episodes/"+medusa_epid, data=medusa_status, headers=headers).json()
								
                                # Confirm episode was updated and print details
                                if str(medusa_patch) == "{'status': 6}":
                                    print("  "+show["title"]+" - S"+str(medusa_season).zfill(2)+'E'+ str(medusa_ep).zfill(2))
                                else:
                                    print("  Error updating "+show["title"]+" - S"+str(medusa_season).zfill(2)+'E'+ str(medusa_ep).zfill(2))
				    
    
    def on_aborted(self):
        """Device authentication aborted.

        Triggered when device authentication was aborted (either with `DeviceOAuthPoller.stop()`
        or via the "poll" event)
        """

        print('Authentication aborted')

        # Authentication aborted
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_authenticated(self, authorization):
        """Device authenticated.

        :param authorization: Authentication token details
        :type authorization: dict
        """

        # Acquire condition
        self.is_authenticating.acquire()

        # Store authorization for future calls
        self.authorization = authorization
        print(authorization)
        print(type(authorization))

        # Save authorization to file
        with open('.auth.pkl', 'wb') as f:
            pickle.dump(authorization, f, pickle.HIGHEST_PROTOCOL)

        print('Authentication successful - authorization: %r' % self.authorization)

        # Authentication complete
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_expired(self):
        """Device authentication expired."""

        print('Authentication expired')

        # Authentication expired
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_poll(self, callback):
        """Device authentication poll.

        :param callback: Call with `True` to continue polling, or `False` to abort polling
        :type callback: func
        """

        # Continue polling
        callback(True)

    def on_token_refreshed(self, authorization):
        # OAuth token refreshed, store authorization for future calls
        self.authorization = authorization

        print('Token refreshed - authorization: %r' % self.authorization)


import yaml

if __name__ == '__main__':

    ########################## CONFIG #########################################
    with open(os.path.join(sys.path[0], "config.yml"), 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

    Trakt.configuration.defaults.client(
        id=cfg['trakt']['client_id'],
        secret=cfg['trakt']['client_secret']
    )
    Trakt.configuration.defaults.http(
        retry=True
    )
    Trakt.configuration.defaults.oauth(
        refresh=True
    )

    # trakt_user =  cfg['trakt']['trakt_user']
    recent_days = cfg['trakt']['recent_days']

    try: 
        radarr_use = cfg['radarr']['enabled'] 
        radarr_address = cfg['radarr']['address'] 
        # radarr_port = cfg['radarr']['port']
        radarr_apikey = cfg['radarr']['apikey']
    except:
        radarr_use = False 

    try: 
        sonarr_use = cfg['sonarr']['enabled']
        sonarr_address = cfg['sonarr']['address']
        # sonarr_port = cfg['sonarr']['port']
        sonarr_apikey = cfg['sonarr']['apikey']
    except:
        sonarr_use = False 

    try: 
        medusa_use = cfg['medusa']['enabled']
        medusa_address = cfg['medusa']['address']
        # medusa_port = cfg['medusa']['port']
        medusa_username = cfg['medusa']['username']
        medusa_password = cfg['medusa']['password']
    except:
        medusa_use = False
        
    ###########################################################################

    # Configure
    Trakt.base_url = 'http://api.trakt.tv'

    Trakt.configuration.defaults.client(
        id=cfg['trakt']['client_id'],
        secret=cfg['trakt']['client_secret']
    )

    Trakt.configuration.defaults.http(
        retry=True
    )
    Trakt.configuration.defaults.oauth(
        refresh=True
    )

    app = watchedMonitor()
    app.initialize()

    if radarr_use:
        app.radarr(recent_days, radarr_address, radarr_apikey)

    if sonarr_use:
        print("")
        print("")
        app.sonarr(recent_days, sonarr_address, sonarr_apikey)

    if medusa_use:
        print("")
        print("")
        app.medusa(recent_days, medusa_address, medusa_username, medusa_password)
