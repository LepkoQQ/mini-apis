import sqlite3

from flask import Flask, g


def get_db() -> sqlite3.Connection:
    if "valstore_db" not in g:
        g.valstore_db = sqlite3.connect(
            str(g.valstore_db_path),
        )
        g.valstore_db.row_factory = sqlite3.Row
    db: sqlite3.Connection = g.valstore_db
    return db


def close_db(e: BaseException | None = None) -> None:
    db: sqlite3.Connection | None = g.pop("valstore_db", None)
    if db is not None:
        db.close()


def init_db(app: Flask) -> None:
    def open_db() -> None:
        g.valstore_db_path = app.config["VALSTORE_DB_PATH"]

    app.before_request(open_db)

    db_path = str(app.config["VALSTORE_DB_PATH"])
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS valstore (
            group_name TEXT NOT NULL,
            key        TEXT NOT NULL,
            value      TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            PRIMARY KEY (group_name, key)
        )
        """)
    conn.commit()
    conn.close()

    app.teardown_appcontext(close_db)
