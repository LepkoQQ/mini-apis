import json
from typing import Any

from flask import Blueprint, Response, current_app, request

from api.response import json_error, json_ok
from api.valstore.db import get_db

bp = Blueprint("valstore", __name__)

_TIMESTAMP = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"


@bp.before_request
def require_api_key() -> tuple[Response, int] | None:
    api_key: str = current_app.config.get("VALSTORE_API_KEY", "")
    if not api_key:
        return json_error("VALSTORE_API_KEY is not configured", 500)
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {api_key}":
        return json_error("unauthorized", 401)
    return None


def _not_found(group: str, key: str) -> tuple[Response, int]:
    return json_error(f"key '{key}' not found in group '{group}'", 404)


@bp.get("/")
def list_groups() -> tuple[Response, int]:
    db = get_db()
    rows = db.execute(
        "SELECT group_name, COUNT(*) as key_count FROM valstore GROUP BY group_name ORDER BY group_name"
    ).fetchall()

    groups: list[dict[str, Any]] = [
        {"group": row["group_name"], "key_count": row["key_count"]} for row in rows
    ]
    return json_ok(data={"groups": groups})


@bp.get("/<group>")
def list_keys(group: str) -> tuple[Response, int]:
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError:
        return json_error("page and per_page must be integers", 400)

    if page < 1 or per_page < 1:
        return json_error("page and per_page must be positive integers", 400)

    offset = (page - 1) * per_page
    db = get_db()

    count_row = db.execute(
        "SELECT COUNT(*) FROM valstore WHERE group_name = ?", (group,)
    ).fetchone()
    total: int = int(count_row[0]) if count_row is not None else 0

    if total == 0:
        return json_error(f"group '{group}' not found", 404)

    rows = db.execute(
        "SELECT key, created_at, updated_at FROM valstore"
        " WHERE group_name = ? ORDER BY key LIMIT ? OFFSET ?",
        (group, per_page, offset),
    ).fetchall()

    items: list[dict[str, Any]] = [
        {
            "key": row["key"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]

    result: dict[str, Any] = {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": items,
    }
    return json_ok(data=result)


@bp.get("/<group>/<key>")
def get_value(group: str, key: str) -> tuple[Response, int]:
    db = get_db()
    row = db.execute(
        "SELECT group_name, key, value, created_at, updated_at"
        " FROM valstore WHERE group_name = ? AND key = ?",
        (group, key),
    ).fetchone()

    if row is None:
        return _not_found(group, key)

    data: dict[str, Any] = {
        "group": row["group_name"],
        "key": row["key"],
        "value": json.loads(row["value"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    return json_ok(data=data)


@bp.put("/<group>/<key>")
def put_value(group: str, key: str) -> tuple[Response, int]:
    body = request.get_json(silent=True)
    if body is None:
        return json_error("request body must be valid JSON", 400)

    db = get_db()
    existing = db.execute(
        "SELECT 1 FROM valstore WHERE group_name = ? AND key = ?",
        (group, key),
    ).fetchone()

    value_str = json.dumps(body)

    if existing is None:
        db.execute(
            "INSERT INTO valstore (group_name, key, value, created_at, updated_at)"
            f" VALUES (?, ?, ?, {_TIMESTAMP}, {_TIMESTAMP})",
            (group, key, value_str),
        )
        db.commit()
        return json_ok("created", status_code=201)
    else:
        db.execute(
            f"UPDATE valstore SET value = ?, updated_at = {_TIMESTAMP}"
            " WHERE group_name = ? AND key = ?",
            (value_str, group, key),
        )
        db.commit()
        return json_ok("updated")


@bp.delete("/<group>/<key>")
def delete_value(group: str, key: str) -> tuple[Response, int]:
    db = get_db()
    cursor = db.execute(
        "DELETE FROM valstore WHERE group_name = ? AND key = ?",
        (group, key),
    )

    if cursor.rowcount == 0:
        return _not_found(group, key)

    db.commit()
    return json_ok("deleted")
