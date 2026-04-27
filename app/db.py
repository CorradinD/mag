from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS items (
    sku TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    quantity REAL NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL REFERENCES items(sku),
    movement_type TEXT NOT NULL CHECK (movement_type IN ('carico', 'scarico')),
    quantity REAL NOT NULL CHECK (quantity > 0),
    unit_price REAL,
    operator TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS excel_update_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    files_total INTEGER NOT NULL DEFAULT 0,
    files_updated INTEGER NOT NULL DEFAULT 0,
    rows_updated INTEGER NOT NULL DEFAULT 0,
    rows_missing_sku INTEGER NOT NULL DEFAULT 0,
    rows_unknown_sku INTEGER NOT NULL DEFAULT 0,
    errors_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS excel_update_run_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES excel_update_runs(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    row_number INTEGER,
    sku TEXT,
    status TEXT NOT NULL,
    message TEXT,
    old_price REAL,
    new_price REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(database_path: Path) -> None:
    with connect(database_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def db_session(database_path: Path) -> Iterator[sqlite3.Connection]:
    conn = connect(database_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

