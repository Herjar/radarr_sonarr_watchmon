#!/usr/bin/env python3

import sys
import os
import yaml
import pickle
import requests
from datetime import datetime, timedelta
from trakt import Trakt
from threading import Condition


class watchedMonitor(object):
    def __init__(self):
        self.is_authenticating = Condition()

        self.authorization = None

        self.recent_days = 30

        self.radarr_use = True
        self.radarr_address = ''
        self.radarr_apikey = ''
        self.radarr_tag_id = False
        self.radarr_unmonitor = True

        self.sonarr_use = True
        self.sonarr_address = ''
        self.sonarr_apikey = ''
        self.sonarr_tag_id = False
        self.sonarr_unmonitor = True

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

            print(" Trakt: Movies watched in last "+str(recent_days)+" days:")
            try:
                for movie in Trakt['sync/history'].movies(start_at=recent_date, pagination=True):
                    movie_dict = movie.to_dict()
                    try:
                        movies_watched_recently_imdbids.append(movie_dict['ids']['imdb'])
                        print("  - "+movie_dict['title'])
                    except KeyError:
                        pass
            except:
                print("ERROR: Could not get data from Trakt. Maybe authentication is out of date? Try to delete .auth.pkl file and run script again.")
                sys.exit()

        return movies_watched_recently_imdbids


    def radarr(self):
        print("Movies:")
        movies_watched_recently_imdbids = self.trakt_get_movies(self.recent_days)
        print("")

        # Get all movies from radarr
        response = requests.get("http://"+self.radarr_address+"/api/v3/movie?apikey="+self.radarr_apikey)

        if response.status_code == 401:
            sys.exit(" ERROR: Unauthorized request to Radarr API. Are you sure the API key is correct?")

        # Look for recently watched movies in Radarr and change monitored to False
        print(" Radarr:")

        if self.radarr_tag:
            self.radarr_tag_set_id()

        if self.radarr_tag_id:
            print("  * Movies will be tagged in Radarr")
        
        if self.radarr_unmonitor:
            print("  * Movies will be unmonitored in Radarr")

        print("\n  Movies found and changed in Radarr:")
        movies = response.json()
        for id in movies_watched_recently_imdbids:
            for movie in movies:
                try:
                    radarr_imdb = movie["imdbId"]
                except:
                    continue

                if id == radarr_imdb:
                    print("   - "+movie["title"])
                    radarr_id = movie["id"]
                    movie_json = movie

                    if self.radarr_tag_id:
                        if self.radarr_tag_id not in movie_json["tags"]:
                            movie_json["tags"].append(self.radarr_tag_id)

                    if self.radarr_unmonitor:
                        movie_json["monitored"] = False

                    request_uri = 'http://'+self.radarr_address+'/api/v3/movie?apikey='+self.radarr_apikey
                    r = requests.put(request_uri, json=movie_json)
                    if r.status_code != 200 and r.status_code != 202:
                        print("   Error "+str(r.status_code)+": "+str(r.json()["message"]))

        print("")
        print("")


    def radarr_tag_set_id(self):
        # Get all tags from radarr
        response = requests.get("http://"+self.radarr_address+"/api/v3/tag?apikey="+self.radarr_apikey)

        if response.status_code == 401:
            sys.exit(" ERROR: Unauthorized request to Radarr API. Are you sure the API key is correct?")

        for tag in response.json():
            if tag['label'] == self.radarr_tag:
                # Tag already exist in radarr
                print("  * Found tag in Radarr. Using existing tag id.")
                self.radarr_tag_id = tag['id']

        if not self.radarr_tag_id:
            print("  * Radarr tag does not exist. Creating new tag.")
            tag_new_json = {'id': 0, 'label': self.radarr_tag}
            request_uri ='http://'+self.radarr_address+'/api/v3/tag?apikey='+self.radarr_apikey
            r = requests.post(request_uri, json=tag_new_json)
            if r.status_code != 200 and r.status_code != 201 and r.status_code != 202:
                print("   Error "+str(r.status_code)+" adding tag: "+str(r.json()[0]["errorMessage"]))

            self.radarr_tag_id = r.json()['id']


    def sonarr_tag_set_id(self):
        # Get all tags from sonarr
        response = requests.get("http://"+self.sonarr_address+"/api/v3/tag?apikey="+self.sonarr_apikey)

        if response.status_code == 401:
            sys.exit(" ERROR: Unauthorized request to Sonarr API. Are you sure the API key is correct?")

        for tag in response.json():
            if tag['label'] == self.sonarr_tag:
                # Tag already exist in sonarr
                print("  * Found tag in Sonarr. Using existing tag id.")
                self.sonarr_tag_id = tag['id']

        if not self.sonarr_tag_id:
            print("  * Sonarr tag does not exist. Creating new tag.")
            tag_new_json = {'id': 0, 'label': self.sonarr_tag}
            request_uri ='http://'+self.sonarr_address+'/api/v3/tag?apikey='+self.sonarr_apikey
            r = requests.post(request_uri, json=tag_new_json)
            if r.status_code != 200 and r.status_code != 201 and r.status_code != 202:
                print("   Error "+str(r.status_code)+" adding tag: "+str(r.json()[0]["errorMessage"]))

            self.sonarr_tag_id = r.json()['id']


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


    def sonarr(self):

        print("TV:")
        show_episodes = self.trakt_get_episodes(self.recent_days)

        print("")
        print(" Sonarr:")

        if self.sonarr_tag:
            self.sonarr_tag_set_id()

        if self.sonarr_tag_id:
            print("  * Shows will be tagged in Sonarr")
        
        if self.sonarr_unmonitor:
            print("  * Episodes will be unmonitored in Sonarr")

        # Get all series from sonarr
        response = requests.get("http://"+self.sonarr_address+"/api/series?apikey="+self.sonarr_apikey)

        if response.status_code == 401:
            sys.exit("ERROR: Unauthorized request to Sonarr API. Are you sure the API key is correct?")

        # Look for recently watched episodes in Sonarr and change monitored to False
        print("\n  Episodes found and changed in Sonarr:")
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
                    print("   "+show["title"])

                    if self.sonarr_tag_id:
                        # Add tag to show
                        request_uri = "http://"+self.sonarr_address+"/api/series/"+str(sonarr_id)+"?apikey="+self.sonarr_apikey
                        response_show = requests.get(request_uri)
                        sonarr_show_json = response_show.json()

                        if self.sonarr_tag_id not in sonarr_show_json["tags"]:
                            sonarr_show_json["tags"].append(self.sonarr_tag_id)
                            r = requests.put(request_uri, json=sonarr_show_json)
                            if r.status_code != 200 and r.status_code != 202:
                                print("   Error "+str(r.status_code)+": "+str(r.json()["message"]))

                    # Get all episodes in show from Sonarr
                    response_eps = requests.get("http://"+self.sonarr_address+"/api/episode/?seriesID="+str(sonarr_id)+"&apikey="+self.sonarr_apikey)
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
                                print("    - S"+str(sonarr_season).zfill(2)+'E'+ str(sonarr_ep).zfill(2))

                                # Get sonarr episode
                                request_uri ='http://'+self.sonarr_address+'/api/episode/'+str(sonarr_epid)+'?apikey='+self.sonarr_apikey
                                sonarr_episode_json = requests.get(request_uri).json()

                                if self.sonarr_unmonitor:
                                    sonarr_episode_json["monitored"] = False

                                r = requests.put(request_uri, json=sonarr_episode_json)
                                if r.status_code != 200 and r.status_code != 202:
                                   print("   Error: "+str(r.json()["message"]))


    def medusa(self, recent_days, medusa_address, medusa_username, medusa_password):
        print("")
        print("")
        print("TV:")
        show_episodes = self.trakt_get_episodes(recent_days)

        print("")
        print(" Medusa: Episodes found and changed to Archived:")

        # Authenticate with the Medusa API & store the token
        data = '{"username": "'+medusa_username+'","password": "'+medusa_password+'"}'
        headers = {'Content-Type': 'application/json'}
        token = requests.post("http://"+medusa_address+"/api/v2/authenticate", data=data, headers=headers).json()['token']
        headers = {'authorization': 'Bearer ' + token}

        # Get all series from Medusa
        response = requests.get("http://"+medusa_address+"/api/v2/series?limit=1000", headers=headers)

        if response.status_code == 401:
            sys.exit("ERROR: Unauthorized request to Medusa API. Are you sure the API key is correct?")

        series = response.json()

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


if __name__ == '__main__':
    app = watchedMonitor()
    app.initialize()

    ########################## CONFIG #########################################
    with open(os.path.join(sys.path[0], "config.yml"), 'r') as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

    try:
        app.recent_days = cfg['trakt']['recent_days']
    except:
        app.recent_days = 30

    try:
        app.radarr_use = cfg['radarr']['enabled']
        app.radarr_address = cfg['radarr']['address']
        app.radarr_apikey = cfg['radarr']['apikey']
    except:
        app.radarr_use = False

    try:
        app.radarr_tag = cfg['radarr']['tag']
    except:
        app.radarr_tag = False

    try:
        app.radarr_unmonitor = cfg['radarr']['unmonitor']
    except:
        app.radarr_unmonitor = True

    try:
        app.sonarr_use = cfg['sonarr']['enabled']
        app.sonarr_address = cfg['sonarr']['address']
        app.sonarr_apikey = cfg['sonarr']['apikey']
    except:
        app.sonarr_use = False

    try:
        app.sonarr_tag = cfg['sonarr']['tag']
    except:
        app.sonarr_tag = False

    try:
        app.sonarr_unmonitor = cfg['sonarr']['unmonitor']
    except:
        app.sonarr_unmonitor = True

    try:
        medusa_use = cfg['medusa']['enabled']
        medusa_address = cfg['medusa']['address']
        medusa_username = cfg['medusa']['username']
        medusa_password = cfg['medusa']['password']
    except:
        medusa_use = False

    ###########################################################################

    Trakt.base_url = 'http://api.trakt.tv'
    Trakt.configuration.defaults.http(retry=True)
    Trakt.configuration.defaults.oauth(refresh=True)
    Trakt.configuration.defaults.client(
        id=cfg['trakt']['client_id'],
        secret=cfg['trakt']['client_secret']
    )

    if app.radarr_use:
        app.radarr()

    if app.sonarr_use:
        app.sonarr()

    if medusa_use:
        app.medusa(recent_days, medusa_address, medusa_username, medusa_password)
