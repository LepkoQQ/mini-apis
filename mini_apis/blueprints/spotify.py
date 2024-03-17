from flask import Blueprint, current_app, url_for

from .utils import get_blueprint_routes

bp = Blueprint("spotify", __name__, url_prefix="/spotify")


@bp.route("/")
def index():
    routes = get_blueprint_routes(current_app, bp)
    return {"message": f"{bp.name} api index", "routes": routes}


@bp.route("/now-playing")
def now_playing():
    return {"message": "Spotify now playing", "status": 200, "ok": True}
