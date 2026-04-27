from __future__ import annotations

import sqlite3
from typing import Iterable


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def list_items(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT sku, description, price, quantity, created_at, updated_at FROM items ORDER BY sku"
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_item(conn: sqlite3.Connection, sku: str) -> dict | None:
    row = conn.execute(
        "SELECT sku, description, price, quantity, created_at, updated_at FROM items WHERE sku = ?",
        (sku,),
    ).fetchone()
    return row_to_dict(row) if row else None


def create_item(conn: sqlite3.Connection, sku: str, description: str, price: float, quantity: float) -> dict:
    conn.execute(
        """
        INSERT INTO items (sku, description, price, quantity, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (sku.strip(), description.strip(), price, quantity),
    )
    return get_item(conn, sku.strip()) or {}


def update_item(conn: sqlite3.Connection, sku: str, description: str, price: float) -> dict | None:
    conn.execute(
        """
        UPDATE items
        SET description = ?, price = ?, updated_at = CURRENT_TIMESTAMP
        WHERE sku = ?
        """,
        (description.strip(), price, sku),
    )
    return get_item(conn, sku)


def create_movement(
    conn: sqlite3.Connection,
    sku: str,
    movement_type: str,
    quantity: float,
    operator: str | None,
    note: str | None,
) -> dict:
    item = get_item(conn, sku)
    if item is None:
        raise ValueError("Articolo non trovato")

    signed_quantity = quantity if movement_type == "carico" else -quantity
    new_quantity = float(item["quantity"]) + signed_quantity
    if new_quantity < 0:
        raise ValueError("Giacenza insufficiente per lo scarico")

    conn.execute(
        """
        INSERT INTO inventory_movements (sku, movement_type, quantity, unit_price, operator, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (sku, movement_type, quantity, item["price"], operator or None, note or None),
    )
    conn.execute(
        "UPDATE items SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE sku = ?",
        (new_quantity, sku),
    )
    movement_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return get_movement(conn, movement_id) or {}


def get_movement(conn: sqlite3.Connection, movement_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT id, sku, movement_type, quantity, unit_price, operator, note, created_at
        FROM inventory_movements
        WHERE id = ?
        """,
        (movement_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def list_movements(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    rows = conn.execute(
        """
        SELECT m.id, m.sku, i.description, m.movement_type, m.quantity, m.unit_price,
               m.operator, m.note, m.created_at
        FROM inventory_movements m
        JOIN items i ON i.sku = m.sku
        ORDER BY m.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def price_map(conn: sqlite3.Connection) -> dict[str, float]:
    rows = conn.execute("SELECT sku, price FROM items").fetchall()
    return {str(row["sku"]).strip(): float(row["price"]) for row in rows}


def create_update_run(conn: sqlite3.Connection, files_total: int) -> int:
    conn.execute(
        "INSERT INTO excel_update_runs (status, files_total) VALUES (?, ?)",
        ("running", files_total),
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def add_update_row(
    conn: sqlite3.Connection,
    run_id: int,
    file_path: str,
    status: str,
    row_number: int | None = None,
    sku: str | None = None,
    message: str | None = None,
    old_price: float | None = None,
    new_price: float | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO excel_update_run_rows
        (run_id, file_path, row_number, sku, status, message, old_price, new_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, file_path, row_number, sku, status, message, old_price, new_price),
    )


def finish_update_run(conn: sqlite3.Connection, run_id: int) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM excel_update_run_rows WHERE run_id = ? GROUP BY status",
        (run_id,),
    ).fetchall()
    counts = {row["status"]: int(row["count"]) for row in rows}
    files_updated = conn.execute(
        "SELECT COUNT(DISTINCT file_path) FROM excel_update_run_rows WHERE run_id = ? AND status = 'updated'",
        (run_id,),
    ).fetchone()[0]
    errors_count = counts.get("error", 0)
    status = "completed_with_errors" if errors_count else "completed"
    conn.execute(
        """
        UPDATE excel_update_runs
        SET status = ?, files_updated = ?, rows_updated = ?, rows_missing_sku = ?,
            rows_unknown_sku = ?, errors_count = ?
        WHERE id = ?
        """,
        (
            status,
            int(files_updated),
            counts.get("updated", 0),
            counts.get("missing_sku", 0),
            counts.get("unknown_sku", 0),
            errors_count,
            run_id,
        ),
    )
    return get_update_run(conn, run_id) or {}


def get_update_run(conn: sqlite3.Connection, run_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM excel_update_runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        return None
    result = row_to_dict(row)
    details = conn.execute(
        "SELECT * FROM excel_update_run_rows WHERE run_id = ? ORDER BY id",
        (run_id,),
    ).fetchall()
    result["rows"] = [row_to_dict(detail) for detail in details]
    return result

