"""Persistence for treatment confirmations recorded against analysis zones."""

from pathlib import Path

from src.db import get_connection


class TreatmentError(Exception):
    """A treatment cannot be saved because its analysis is invalid."""


def save_treatment(
    db_path: str | Path,
    field_id: int,
    analysis_id: int,
    zone_id: str,
    note: str | None = None,
) -> dict:
    normalized_zone_id = zone_id.strip()
    if not normalized_zone_id:
        raise TreatmentError("L'identifiant de zone est obligatoire.")

    conn = get_connection(db_path)
    try:
        analysis = conn.execute(
            "SELECT id FROM analyses WHERE id = ? AND field_id = ?",
            (analysis_id, field_id),
        ).fetchone()
        if analysis is None:
            raise TreatmentError("Analyse introuvable pour cette parcelle.")

        cursor = conn.execute(
            """INSERT INTO zone_treatments (field_id, analysis_id, zone_id, note)
               VALUES (?, ?, ?, ?)""",
            (field_id, analysis_id, normalized_zone_id, note.strip() if note else None),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM zone_treatments WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_treatments(db_path: str | Path, field_id: int) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM zone_treatments WHERE field_id = ? ORDER BY treated_at DESC, id DESC",
            (field_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
