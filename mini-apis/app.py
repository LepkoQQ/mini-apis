import os

from flask import Flask, Response

from api.response import json_ok
from api.valstore.blueprint import bp as valstore_bp
from api.valstore.db import init_db as init_valstore_db

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config["VALSTORE_DB_PATH"] = os.environ.get("VALSTORE_DB_PATH", "valstore.db")

init_valstore_db(app)
app.register_blueprint(valstore_bp, url_prefix="/valstore")


@app.get("/")
def hello() -> tuple[Response, int]:
    return json_ok("Hello, World!")


if __name__ == "__main__":
    app.run(host="0.0.0.0")
