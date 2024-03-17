from flask import Blueprint, current_app

from ..spotify_auth import auth_to_spotify
from .utils import get_blueprint_routes

bp = Blueprint("spotify", __name__, url_prefix="/spotify")


@bp.route("/")
def index():
    routes = get_blueprint_routes(current_app, bp)
    return {"message": f"{bp.name} api index", "routes": routes}


@bp.route("/now-playing")
def now_playing():
    sp = auth_to_spotify(current_app)

    try:
        current_track = sp.currently_playing(additional_types="episode")
    except Exception as e:
        return {
            "message": f"Error: {e}",
            "ok": False,
        }, 500

    if not current_track or not current_track.get("is_playing"):
        return {
            "message": "Nothing currently playing",
            "ok": True,
            "is_playing": False,
        }

    playing_type = current_track.get("currently_playing_type") or "unknown"
    item = current_track.get("item") or {}
    album = item.get("album") or {}
    show = item.get("show") or {}
    artists = item.get("artists") or []
    images = album.get("images") or show.get("images") or []

    progress_ms = current_track.get("progress_ms") or 0
    duration_ms = item.get("duration_ms") or 0
    progress_obj = {
        "current": progress_ms,
        "total": duration_ms,
        "percentage": progress_ms / duration_ms if duration_ms else -1,
    }

    title = item.get("name") or ""
    album_name = album.get("name") or show.get("name") or ""
    artist_name = ", ".join(
        [artist.get("name") for artist in artists if artist.get("name")]
    )
    item_obj = {
        "title": title,
        "album": album_name,
        "artist": artist_name,
    }

    image = images[0]["url"] if images else None
    image_obj = {
        "original_url": image,
    }

    return {
        "message": f"Now playing {playing_type}",
        "ok": True,
        "is_playing": True,
        "progress": progress_obj,
        "item": item_obj,
        "image": image_obj,
    }
