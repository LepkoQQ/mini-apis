from flask import Flask, Response

from api.response import json_ok

app = Flask(__name__)


@app.get("/")
def hello() -> tuple[Response, int]:
    return json_ok("Hello, World!")


if __name__ == "__main__":
    app.run(host="0.0.0.0")
