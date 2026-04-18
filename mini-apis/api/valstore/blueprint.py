import json
import re
from datetime import datetime
from typing import Any

from flask import Blueprint, Response, current_app, request

from api.response import json_error, json_ok
from api.valstore.db import get_db

bp = Blueprint("valstore", __name__)

_BULK_MAX = 50
_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-:]+$")
_TIMESTAMP = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"


def _invalid_name(label: str, name: str) -> tuple[Response, int] | None:
    if not _NAME_RE.match(name):
        return json_error(f"{label} name contains invalid characters", 400)
    return None


def _not_found(group: str, key: str) -> tuple[Response, int]:
    return json_error(f"key '{key}' not found in group '{group}'", 404)


@bp.before_request
def require_api_key() -> tuple[Response, int] | None:
    api_key: str = current_app.config.get("VALSTORE_API_KEY", "")
    if not api_key:
        return json_error("VALSTORE_API_KEY is not configured", 500)
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {api_key}":
        return json_error("unauthorized", 401)
    return None


@bp.get("/")
def list_groups() -> tuple[Response, int]:
    db = get_db()
    rows = db.execute(
        "SELECT group_name FROM valstore GROUP BY group_name ORDER BY group_name"
    ).fetchall()

    groups: list[str] = [row["group_name"] for row in rows]
    return json_ok(data={"groups": groups})


@bp.get("/<group>")
def list_keys(group: str) -> tuple[Response, int]:
    if err := _invalid_name("group", group):
        return err

    # bulk get when ?keys= is provided
    raw_keys = request.args.get("keys", None)
    if raw_keys is not None:
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        if not keys:
            return json_error("'keys' query param is empty", 400)
        if len(keys) > _BULK_MAX:
            return json_error(f"number of keys exceeds maximum of {_BULK_MAX}", 400)
        keys_set = set(keys)
        for k in keys_set:
            if err := _invalid_name("key", k):
                return err

        db = get_db()
        placeholders = ",".join("?" * len(keys_set))
        rows = db.execute(
            f"SELECT key, value, created_at, updated_at FROM valstore"
            f" WHERE group_name = ? AND key IN ({placeholders})",
            (group, *keys_set),
        ).fetchall()

        found = {
            row["key"]: {
                "value": json.loads(row["value"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        }
        missing = [k for k in keys_set if k not in found]
        return json_ok(data={"found": found, "missing": missing})

    # paginated key listing
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError:
        return json_error("page and per_page must be integers", 400)

    if page < 1 or per_page < 1:
        return json_error("page and per_page must be positive integers", 400)
    if per_page > _BULK_MAX:
        return json_error(f"per_page exceeds maximum of {_BULK_MAX}", 400)

    offset = (page - 1) * per_page
    db = get_db()

    count_row = db.execute(
        "SELECT COUNT(*) FROM valstore WHERE group_name = ?", (group,)
    ).fetchone()
    total: int = int(count_row[0]) if count_row is not None else 0

    if total == 0:
        return json_error(f"group '{group}' not found", 404)

    rows = db.execute(
        "SELECT key FROM valstore"
        " WHERE group_name = ? ORDER BY key LIMIT ? OFFSET ?",
        (group, per_page, offset),
    ).fetchall()

    key_list: list[str] = [row["key"] for row in rows]

    result: dict[str, Any] = {
        "total": total,
        "page": page,
        "per_page": per_page,
        "keys": key_list,
    }
    return json_ok(data=result)


@bp.get("/<group>/<key>")
def get_value(group: str, key: str) -> tuple[Response, int]:
    if err := _invalid_name("group", group):
        return err
    if err := _invalid_name("key", key):
        return err

    db = get_db()
    row = db.execute(
        "SELECT value, created_at, updated_at"
        " FROM valstore WHERE group_name = ? AND key = ?",
        (group, key),
    ).fetchone()

    if row is None:
        return _not_found(group, key)

    data: dict[str, Any] = {
        "value": json.loads(row["value"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    return json_ok(data=data)


@bp.put("/<group>/<key>")
def put_value(group: str, key: str) -> tuple[Response, int]:
    if err := _invalid_name("group", group):
        return err
    if err := _invalid_name("key", key):
        return err

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


@bp.delete("/<group>")
def delete_old_keys(group: str) -> tuple[Response, int]:
    if err := _invalid_name("group", group):
        return err

    before = request.args.get("before", "").strip()
    if not before:
        return json_error("'before' query param is required", 400)
    try:
        datetime.fromisoformat(before)
    except ValueError:
        return json_error("'before' must be a valid ISO-8601 timestamp", 400)

    db = get_db()
    cursor = db.execute(
        "DELETE FROM valstore WHERE group_name = ? AND created_at < ?",
        (group, before),
    )
    db.commit()
    return json_ok(data={"deleted": cursor.rowcount})


@bp.delete("/<group>/<key>")
def delete_value(group: str, key: str) -> tuple[Response, int]:
    if err := _invalid_name("group", group):
        return err
    if err := _invalid_name("key", key):
        return err

    db = get_db()
    cursor = db.execute(
        "DELETE FROM valstore WHERE group_name = ? AND key = ?",
        (group, key),
    )

    if cursor.rowcount == 0:
        return _not_found(group, key)

    db.commit()
    return json_ok("deleted")
