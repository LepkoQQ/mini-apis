from typing import Any, Literal

from flask import Response, jsonify
from werkzeug.http import HTTP_STATUS_CODES

StatusOk = Literal[200, 201, 202, 204]


def json_ok(
    message: str | None = None,
    data: dict[str, Any] | None = None,
    status_code: StatusOk = 200,
) -> tuple[Response, int]:
    json_data = jsonify(
        {
            "ok": True,
            "status_code": status_code,
            "status": HTTP_STATUS_CODES[status_code],
            "message": message or "OK",
            "data": data or {},
            "error": None,
        }
    )
    return json_data, status_code
