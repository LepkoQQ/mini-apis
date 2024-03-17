import os

import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth


def auth_to_spotify(current_app):
    cache_path = os.path.join(current_app.instance_path, "spotify-auth-cache.json")
    auth_manager = SpotifyOAuth(
        scope="user-read-currently-playing",
        redirect_uri="http://localhost:5000/",
        open_browser=False,
        cache_handler=CacheFileHandler(cache_path=cache_path),
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    return sp
