import os

from flask import Flask, render_template


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/ping")
    def ping():
        return {"message": "pong", "status": 200, "ok": True}

    return app
