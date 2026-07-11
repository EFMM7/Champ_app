from pathlib import Path

import pytest

from src.fields import FieldError, register_field


def test_register_field_rejects_self_intersecting_polygon(tmp_path):
    db_path = tmp_path / "app.db"
    from src.db import init_db

    init_db(db_path)

    polygon = [
        (0.0, 0.0),
        (2.0, 0.0),
        (0.0, 2.0),
        (2.0, 2.0),
    ]

    with pytest.raises(FieldError, match="polygone"):
        register_field(db_path, 1, "Champ", "Blé tendre", polygon=polygon)


def test_register_field_rejects_duplicate_vertices(tmp_path):
    db_path = tmp_path / "app.db"
    from src.db import init_db

    init_db(db_path)

    polygon = [
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 0.0),
        (0.0, 1.0),
    ]

    with pytest.raises(FieldError, match="dupli"):
        register_field(db_path, 1, "Champ", "Blé tendre", polygon=polygon)
