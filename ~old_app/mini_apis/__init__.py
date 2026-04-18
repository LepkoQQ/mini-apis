import os

from flask import Flask, render_template


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    config_object = os.getenv("FLASK_APP_CONFIG", "mini_apis.config.development")
    print(f" * Using config: {config_object}")
    app.config.from_object(config_object)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/ping")
    def ping():
        return {
            "message": "pong",
            "status": "OK",
            "status_code": 200,
            "ok": True,
        }

    from .blueprints import spotify

    app.register_blueprint(spotify.bp)

    return app
