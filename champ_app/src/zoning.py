"""Découpage d'un raster d'indice en zones et détection des zones à alerter."""

import numpy as np

# Seuils par défaut — À VALIDER PAR UN AGRONOME avant tout usage réel.
# Ce sont des hypothèses de travail, pas des références agronomiques établies.
DEFAULT_THRESHOLDS = {
    "critical": 0.35,
    "warning": 0.55,
}


def get_thresholds(overrides: dict | None = None) -> dict:
    """Retourne les seuils de zonage, avec possibilité de surcharge explicite."""
    thresholds = dict(DEFAULT_THRESHOLDS)
    if overrides:
        thresholds.update({k: float(v) for k, v in overrides.items() if v is not None})
    return thresholds


def zone_id(row: int, col: int) -> str:
    """Convertit (ligne, colonne) en identifiant type 'A1', 'B4'..."""
    return f"{chr(65 + row)}{col + 1}"


def split_into_zones(raster: np.ndarray, n_rows: int, n_cols: int) -> list[dict]:
    """
    Découpe un raster (H, W) en grille de n_rows x n_cols zones et calcule
    la moyenne de l'indice par zone (en ignorant les NaN = pixels masqués).

    Retourne une liste de dicts : {id, row, col, mean_value, valid_pixel_ratio}
    """
    h, w = raster.shape
    row_edges = np.linspace(0, h, n_rows + 1).astype(int)
    col_edges = np.linspace(0, w, n_cols + 1).astype(int)

    zones = []
    for r in range(n_rows):
        for c in range(n_cols):
            tile = raster[row_edges[r]:row_edges[r + 1], col_edges[c]:col_edges[c + 1]]
            valid = ~np.isnan(tile)
            valid_ratio = float(valid.mean()) if tile.size else 0.0
            mean_value = float(np.nanmean(tile)) if valid.any() else float("nan")
            zones.append({
                "id": zone_id(r, c),
                "row": r,
                "col": c,
                "mean_value": mean_value,
                "valid_pixel_ratio": round(valid_ratio, 3),
            })
    return zones


def classify_zone(mean_value: float, thresholds: dict | None = None) -> str:
    """Retourne 'critical', 'warning' ou 'ok' selon la valeur moyenne de la zone."""
    resolved_thresholds = get_thresholds(thresholds)
    if np.isnan(mean_value):
        return "no_data"
    if mean_value < resolved_thresholds["critical"]:
        return "critical"
    if mean_value < resolved_thresholds["warning"]:
        return "warning"
    return "ok"


def annotate_zones(zones: list[dict], thresholds: dict | None = None) -> list[dict]:
    """Ajoute le statut (critical/warning/ok/no_data) à chaque zone."""
    resolved_thresholds = get_thresholds(thresholds)
    for z in zones:
        z["status"] = classify_zone(z["mean_value"], resolved_thresholds)
    return zones
