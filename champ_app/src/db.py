"""Base de données SQLite : comptes utilisateurs et champs enregistrés."""

import sqlite3
from pathlib import Path


def _normalize_db_path(db_path: str | Path) -> Path:
    path = Path(db_path)
    path.parent.mkdir(exist_ok=True, parents=True)
    return path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    crop TEXT NOT NULL,
    sowing_date TEXT,
    bbox_min_lon REAL NOT NULL,
    bbox_min_lat REAL NOT NULL,
    bbox_max_lon REAL NOT NULL,
    bbox_max_lat REAL NOT NULL,
    polygon_geojson TEXT,
    area_ha REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    path = _normalize_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path) -> None:
    path = _normalize_db_path(db_path)
    conn = get_connection(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
