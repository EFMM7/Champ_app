"""Calcul des indices de végétation à partir des bandes Sentinel-2."""

import numpy as np


def _safe_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Division évitant les NaN/divisions par zéro (pixels masqués, bords)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(denominator != 0, numerator / denominator, 0.0)
    return np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)


def compute_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """NDVI = (NIR - Rouge) / (NIR + Rouge). Plage : [-1, 1]."""
    return _safe_ratio(nir - red, nir + red)


def compute_ndre(red_edge: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """NDRE = (NIR - RedEdge) / (NIR + RedEdge). Plus sensible à l'azote foliaire."""
    return _safe_ratio(nir - red_edge, nir + red_edge)


def compute_all_indices(bands: np.ndarray) -> dict[str, np.ndarray]:
    """
    bands: array (H, W, 4) = [B04 (rouge), B05 (red edge), B08 (NIR), dataMask]

    Retourne un dict avec les rasters ndvi, ndre, et le masque de validité.
    """
    red = bands[:, :, 0]
    red_edge = bands[:, :, 1]
    nir = bands[:, :, 2]
    data_mask = bands[:, :, 3].astype(bool)

    ndvi = compute_ndvi(red, nir)
    ndre = compute_ndre(red_edge, nir)

    # les pixels hors parcelle / nuageux sont mis à NaN pour être exclus des moyennes
    ndvi = np.where(data_mask, ndvi, np.nan)
    ndre = np.where(data_mask, ndre, np.nan)

    return {"ndvi": ndvi, "ndre": ndre, "valid_mask": data_mask}
