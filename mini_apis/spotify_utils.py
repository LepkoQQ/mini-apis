import glob
import os
from urllib.parse import urlsplit

import requests
import spotipy
from PIL import Image, ImageEnhance
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


spotify_image_cache_dir = "spotify-image-cache"


def cache_spotify_image(current_app, image_url):
    if not image_url:
        return None

    cache_dir_path = os.path.join(current_app.instance_path, spotify_image_cache_dir)

    image_name = f"{urlsplit(image_url).path.strip('/')}.jpg"
    image_save_path = os.path.join(cache_dir_path, image_name)

    if os.path.exists(image_save_path):
        # update modified time
        os.utime(image_save_path)
        return f"/{spotify_image_cache_dir}/{image_name}"

    max_cache_count = 100
    half_cache_count = max_cache_count // 2

    cached_images = glob.glob(f"{cache_dir_path}/**/*.jpg", recursive=True)
    cached_images_count = len(cached_images)
    if cached_images_count > max_cache_count:
        # sort by modified time
        sorted_images = list(sorted(cached_images, key=os.path.getmtime))
        # delete the oldest images and leave half of the max cache count
        oldest_images = sorted_images[:-half_cache_count]
        for image in oldest_images:
            os.remove(image)

    try:
        r = requests.get(image_url, stream=True)
        r.raw.decode_content = True
        with Image.open(r.raw) as im:
            im = im.resize((240, 240))
            im = im.convert("RGB")
            im = ImageEnhance.Color(im).enhance(1.5)
            os.makedirs(os.path.dirname(image_save_path), exist_ok=True)
            im.save(image_save_path, format="JPEG", quality=60)
        return f"/{spotify_image_cache_dir}/{image_name}"
    except Exception as e:
        print(f"Error: {e}")
        return None
