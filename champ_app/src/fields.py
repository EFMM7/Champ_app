"""Enregistrement et consultation des champs (parcelles) d'un utilisateur."""

import json
import math
from pathlib import Path

from src.db import get_connection

CROPS_DISPONIBLES = [
    "Blé tendre", "Blé dur", "Orge", "Maïs", "Colza",
    "Tournesol", "Betterave", "Pomme de terre", "Vigne",
]

METERS_PER_DEGREE_LAT = 111_320


class FieldError(Exception):
    """Erreur de validation lors de l'enregistrement d'un champ."""


def _bbox_area_ha(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> float:
    """
    Calcule une surface approximative en hectares pour une bbox WGS84.
    Approximation locale (suffisante pour une parcelle de quelques hectares) :
    1° de latitude ≈ 111 320 m ; 1° de longitude ≈ 111 320 * cos(latitude) m.
    """
    mean_lat_rad = math.radians((min_lat + max_lat) / 2)
    height_m = (max_lat - min_lat) * METERS_PER_DEGREE_LAT
    width_m = (max_lon - min_lon) * METERS_PER_DEGREE_LAT * math.cos(mean_lat_rad)
    area_m2 = abs(height_m * width_m)
    return round(area_m2 / 10_000, 3)  # 1 ha = 10 000 m²


def _polygon_area_ha(polygon: list[tuple[float, float]]) -> float:
    """
    Calcule l'aire d'un polygone WGS84 par la formule du lacet (shoelace),
    après projection équirectangulaire locale centrée sur le polygone —
    même niveau d'approximation que _bbox_area_ha, mais pour une forme
    quelconque plutôt qu'un simple rectangle. Suffisant pour une parcelle
    agricole (quelques hectares à quelques centaines d'hectares) ; une vraie
    projection cartographique serait nécessaire pour de très grandes surfaces.

    polygon : liste de (lon, lat), dans l'ordre, pas besoin de refermer
    (le premier point n'a pas besoin d'être répété à la fin).
    """
    lats = [p[1] for p in polygon]
    mean_lat_rad = math.radians(sum(lats) / len(lats))
    meters_per_deg_lon = METERS_PER_DEGREE_LAT * math.cos(mean_lat_rad)

    # projette chaque point (lon, lat) en mètres (x, y) autour de l'origine locale
    xs = [p[0] * meters_per_deg_lon for p in polygon]
    ys = [p[1] * METERS_PER_DEGREE_LAT for p in polygon]

    n = len(polygon)
    area_m2 = 0.0
    for i in range(n):
        j = (i + 1) % n
        area_m2 += xs[i] * ys[j] - xs[j] * ys[i]
    area_m2 = abs(area_m2) / 2

    return round(area_m2 / 10_000, 3)


def _bbox_from_polygon(polygon: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    return (min(lons), min(lats), max(lons), max(lats))


def register_field(
    db_path: str | Path,
    user_id: int,
    name: str,
    crop: str,
    bbox: tuple[float, float, float, float] | None = None,
    sowing_date: str | None = None,
    polygon: list[tuple[float, float]] | None = None,
) -> int:
    """
    bbox : (min_lon, min_lat, max_lon, max_lat) en WGS84 — utilisé tel quel
           si `polygon` n'est pas fourni.
    polygon : liste de (lon, lat) décrivant le contour réel de la parcelle.
              Si fourni, prime sur `bbox` : la bbox est dérivée automatique-
              ment du polygone (pour les besoins de récupération satellite),
              et la surface est calculée sur la forme réelle plutôt que sur
              le rectangle englobant.

    Retourne l'id du champ créé. Lève FieldError si les données sont invalides.
    """
    if not name.strip():
        raise FieldError("Le nom du champ est obligatoire.")
    if crop not in CROPS_DISPONIBLES:
        raise FieldError(f"Culture inconnue. Choix possibles : {', '.join(CROPS_DISPONIBLES)}")

    polygon_json = None

    if polygon is not None:
        if len(polygon) < 3:
            raise FieldError("Un polygone doit avoir au moins 3 points.")
        for lon, lat in polygon:
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise FieldError("Coordonnées hors des limites géographiques valides.")
        bbox = _bbox_from_polygon(polygon)
        area_ha = _polygon_area_ha(polygon)
        polygon_json = json.dumps(polygon)
    else:
        if bbox is None:
            raise FieldError("Il faut fournir soit une bbox, soit un polygone.")
        min_lon, min_lat, max_lon, max_lat = bbox
        if min_lon >= max_lon or min_lat >= max_lat:
            raise FieldError("Coordonnées de la parcelle invalides (bbox incohérente).")
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise FieldError("Coordonnées hors des limites géographiques valides.")
        area_ha = _bbox_area_ha(*bbox)

    if area_ha < 0.01:
        raise FieldError("La parcelle semble trop petite (< 0.01 ha) — vérifiez les coordonnées.")

    min_lon, min_lat, max_lon, max_lat = bbox

    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO fields
               (user_id, name, crop, sowing_date, bbox_min_lon, bbox_min_lat, bbox_max_lon, bbox_max_lat, polygon_geojson, area_ha)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name.strip(), crop, sowing_date, min_lon, min_lat, max_lon, max_lat, polygon_json, area_ha),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _decode_polygon(row_dict: dict) -> dict:
    if row_dict.get("polygon_geojson"):
        row_dict["polygon"] = json.loads(row_dict["polygon_geojson"])
    else:
        row_dict["polygon"] = None
    return row_dict


def list_fields(db_path: str | Path, user_id: int) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM fields WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [_decode_polygon(dict(row)) for row in rows]
    finally:
        conn.close()


def get_field(db_path: str | Path, field_id: int) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM fields WHERE id = ?", (field_id,)).fetchone()
        return _decode_polygon(dict(row)) if row else None
    finally:
        conn.close()
