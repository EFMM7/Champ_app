"""
Démontre le flux complet : création de compte, connexion, enregistrement
d'un champ, puis déclenchement du pipeline de suivi sur ce champ.
"""

import json
from pathlib import Path

from src.db import init_db
from src.auth import register_user, authenticate_user, AuthError
from src.fields import register_field, list_fields, FieldError
from src.demo_data import generate_synthetic_bands
from src.main import run_pipeline

DB_PATH = Path(__file__).resolve().parent.parent / "output" / "demo.db"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def section(title):
    print(f"\n{'─' * 50}\n{title}\n{'─' * 50}")


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()  # repart d'une base propre à chaque exécution de la démo
    init_db(DB_PATH)

    section("1. Création de compte")
    user_id = register_user(DB_PATH, "jean.dupont@example.fr", "motdepasse123")
    print(f"Compte créé, user_id = {user_id}")

    print("Tentative avec un email déjà pris :")
    try:
        register_user(DB_PATH, "jean.dupont@example.fr", "autremotdepasse")
    except AuthError as e:
        print(f"  → Rejeté comme attendu : {e}")

    print("Tentative avec un mot de passe trop court :")
    try:
        register_user(DB_PATH, "autre@example.fr", "court")
    except AuthError as e:
        print(f"  → Rejeté comme attendu : {e}")

    section("2. Connexion")
    print("Mauvais mot de passe :")
    try:
        authenticate_user(DB_PATH, "jean.dupont@example.fr", "mauvais_mdp")
    except AuthError as e:
        print(f"  → Rejeté comme attendu : {e}")

    logged_in_id = authenticate_user(DB_PATH, "jean.dupont@example.fr", "motdepasse123")
    print(f"Connexion réussie, user_id = {logged_in_id}")

    section("3. Enregistrement d'un champ")
    # bbox approximative d'une parcelle en Beauce (~12 ha)
    bbox = (1.500, 48.300, 1.512, 48.308)
    field_id = register_field(
        DB_PATH, user_id,
        name="Parcelle Nord",
        crop="Blé tendre",
        bbox=bbox,
        sowing_date="2025-10-15",
    )
    print(f"Champ créé, field_id = {field_id}")

    print("Tentative avec une culture inconnue :")
    try:
        register_field(DB_PATH, user_id, "Test", "Kiwi", bbox)
    except FieldError as e:
        print(f"  → Rejeté comme attendu : {e}")

    print("Tentative avec une bbox incohérente (min > max) :")
    try:
        register_field(DB_PATH, user_id, "Test", "Blé tendre", (1.512, 48.308, 1.500, 48.300))
    except FieldError as e:
        print(f"  → Rejeté comme attendu : {e}")

    section("4. Liste des champs de l'utilisateur")
    fields = list_fields(DB_PATH, user_id)
    for f in fields:
        print(f"  {f['name']} — {f['crop']} — {f['area_ha']} ha (semé le {f['sowing_date']})")

    section("5. Déclenchement du pipeline de suivi sur ce champ")
    # en mode réel : fetch_sentinel.fetch_field_bands(bbox du champ)
    # ici : mode démo, données synthétiques, pour valider le branchement complet
    bands = generate_synthetic_bands()
    result, _ = run_pipeline(bands, n_rows=8, n_cols=12)
    result["field_id"] = field_id
    result["field_name"] = fields[0]["name"]

    out_path = OUTPUT_DIR / f"zones_field_{field_id}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"NDVI moyen : {result['field_mean_ndvi']}")
    print(f"Zones en alerte : {result['alert_count']}")
    print(f"Résultat exporté : {out_path}")


if __name__ == "__main__":
    main()
