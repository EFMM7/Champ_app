"""Persistence and retrieval of field analysis results."""

import json
from pathlib import Path

from src.db import get_connection


def save_analysis(
    db_path: str | Path,
    field_id: int,
    source: str,
    method: str,
    parameters: dict,
    result: dict,
) -> dict:
    """Store one completed analysis and return its public metadata."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO analyses (field_id, source, method, parameters_json, result_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                field_id,
                source,
                method,
                json.dumps(parameters, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
            ),
        )
        conn.commit()
        analysis_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return _decode_analysis(dict(row))
    finally:
        conn.close()


def list_analyses(db_path: str | Path, field_id: int) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM analyses WHERE field_id = ? ORDER BY created_at DESC, id DESC",
            (field_id,),
        ).fetchall()
        return [_decode_analysis(dict(row)) for row in rows]
    finally:
        conn.close()


def _decode_analysis(analysis: dict) -> dict:
    return {
        "id": analysis["id"],
        "field_id": analysis["field_id"],
        "source": analysis["source"],
        "method": analysis["method"],
        "parameters": json.loads(analysis["parameters_json"]),
        "result": json.loads(analysis["result_json"]),
        "created_at": analysis["created_at"],
    }
