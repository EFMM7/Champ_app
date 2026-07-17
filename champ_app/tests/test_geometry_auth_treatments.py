"""Tests métier ciblés — point 3 de la roadmap du README :
'Ajouter des tests métier de plus en plus ciblés sur la géométrie,
l'authentification et les sorties de traitement.'
"""

import pytest

from src.analyses import save_analysis
from src.auth import AuthError, register_user, authenticate_user
from src.db import init_db
from src.fields import FieldError, register_field
from src.treatments import TreatmentError, save_treatment


def _make_user(db_path, email="owner@example.fr"):
    """Crée un utilisateur réel (nécessaire : fields.user_id a une contrainte FK)."""
    return register_user(db_path, email, "motdepasse123")


# ---------- Géométrie ----------

def test_register_field_rejects_polygon_with_less_than_three_points(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    with pytest.raises(FieldError, match="3 points"):
        register_field(db_path, user_id, "Champ", "Blé tendre", polygon=[(0.0, 0.0), (1.0, 1.0)])


def test_register_field_rejects_polygon_point_out_of_geographic_bounds(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 200.0)]  # latitude invalide
    with pytest.raises(FieldError, match="limites géographiques"):
        register_field(db_path, user_id, "Champ", "Blé tendre", polygon=polygon)


def test_register_field_rejects_degenerate_polygon(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    # 4 points quasi alignés -> bbox quasi nulle sur un axe
    polygon = [(0.0, 0.0), (0.0, 0.0000001), (0.0, 0.0000002), (0.0, 0.0000003)]
    with pytest.raises(FieldError):
        register_field(db_path, user_id, "Champ", "Blé tendre", polygon=polygon)


def test_register_field_rejects_inverted_bbox(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    with pytest.raises(FieldError, match="bbox incohérente"):
        register_field(db_path, user_id, "Champ", "Blé tendre", bbox=(1.505, 48.304, 1.500, 48.300))


def test_register_field_rejects_bbox_out_of_geographic_bounds(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    with pytest.raises(FieldError, match="limites géographiques"):
        register_field(db_path, user_id, "Champ", "Blé tendre", bbox=(1.500, 48.300, 1.505, 200.0))


def test_register_field_rejects_area_below_minimum(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    # bbox volontairement microscopique (quelques cm²)
    with pytest.raises(FieldError, match="trop petite"):
        register_field(db_path, user_id, "Champ", "Blé tendre", bbox=(1.5000000, 48.3000000, 1.5000001, 48.3000001))


def test_register_field_rejects_empty_name(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    with pytest.raises(FieldError, match="nom"):
        register_field(db_path, user_id, "   ", "Blé tendre", bbox=(1.500, 48.300, 1.505, 48.304))


def test_register_field_rejects_unknown_crop(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    with pytest.raises(FieldError, match="Culture inconnue"):
        register_field(db_path, user_id, "Champ", "Kiwi", bbox=(1.500, 48.300, 1.505, 48.304))


# ---------- Authentification ----------

def test_register_user_rejects_password_over_max_length(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)

    with pytest.raises(AuthError, match="128 caractères"):
        register_user(db_path, "long.password@example.fr", "x" * 200)


def test_login_is_case_insensitive_and_trims_whitespace_on_email(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)

    register_user(db_path, "Mixed.Case@Example.FR", "motdepasse123")
    # l'email doit être reconnu peu importe la casse et les espaces superflus
    user_id = authenticate_user(db_path, "  mixed.case@example.fr  ", "motdepasse123")
    assert isinstance(user_id, int)


def test_login_rejects_wrong_password_without_leaking_which_field_is_wrong(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)

    register_user(db_path, "user@example.fr", "motdepasse123")
    with pytest.raises(AuthError, match="Email ou mot de passe incorrect"):
        authenticate_user(db_path, "user@example.fr", "mauvais-mot-de-passe")

    with pytest.raises(AuthError, match="Email ou mot de passe incorrect"):
        authenticate_user(db_path, "inconnu@example.fr", "motdepasse123")


def test_register_user_rejects_duplicate_email(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)

    register_user(db_path, "duplicate@example.fr", "motdepasse123")
    with pytest.raises(AuthError, match="existe déjà"):
        register_user(db_path, "duplicate@example.fr", "autremotdepasse")


# ---------- Sorties de traitement ----------

def test_save_treatment_rejects_zone_id_not_in_analysis_result(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    field_id = register_field(db_path, user_id, "Champ", "Blé tendre", bbox=(1.500, 48.300, 1.505, 48.304))
    analysis = save_analysis(
        db_path, field_id, source="synthetic", method="grid", parameters={},
        result={"zones": [{"id": "A1"}, {"id": "A2"}], "field_mean_ndvi": 0.5},
    )

    with pytest.raises(TreatmentError, match="n'existe pas"):
        save_treatment(db_path, field_id, analysis["id"], zone_id="Z99")


def test_save_treatment_accepts_zone_id_present_in_analysis_result(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    field_id = register_field(db_path, user_id, "Champ", "Blé tendre", bbox=(1.500, 48.300, 1.505, 48.304))
    analysis = save_analysis(
        db_path, field_id, source="synthetic", method="grid", parameters={},
        result={"zones": [{"id": "A1"}, {"id": "A2"}], "field_mean_ndvi": 0.5},
    )

    treatment = save_treatment(db_path, field_id, analysis["id"], zone_id="A1", note="ok")
    assert treatment["zone_id"] == "A1"


def test_save_treatment_rejects_analysis_from_another_field(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(db_path)
    user_id = _make_user(db_path)

    field_a = register_field(db_path, user_id, "Champ A", "Blé tendre", bbox=(1.500, 48.300, 1.505, 48.304))
    field_b = register_field(db_path, user_id, "Champ B", "Orge", bbox=(2.500, 49.300, 2.505, 49.304))
    analysis_a = save_analysis(
        db_path, field_a, source="synthetic", method="grid", parameters={},
        result={"zones": [{"id": "A1"}], "field_mean_ndvi": 0.5},
    )

    with pytest.raises(TreatmentError, match="introuvable"):
        save_treatment(db_path, field_b, analysis_a["id"], zone_id="A1")