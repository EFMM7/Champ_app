"""
Récupération d'images Sentinel-2 via Sentinel Hub.

Nécessite un compte gratuit sur https://www.sentinel-hub.com/ (le tier gratuit
suffit pour du développement / un petit nombre de parcelles) et deux variables
d'environnement :

    SH_CLIENT_ID
    SH_CLIENT_SECRET

Ce module ne peut pas être exécuté dans un environnement sans accès réseau
vers services.sentinel-hub.com — voir demo_data.py pour tester la logique de
traitement des indices sans connexion réelle.
"""

import os
import datetime as dt
import numpy as np

from sentinelhub import (
    SHConfig,
    BBox,
    CRS,
    SentinelHubRequest,
    DataCollection,
    MimeType,
    bbox_to_dimensions,
)

# Evalscript : demande les bandes brutes nécessaires au calcul NDVI/NDRE.
# B04 = rouge, B05 = red edge, B08 = proche infrarouge
EVALSCRIPT_BANDS = """
//VERSION=3
function setup() {
  return {
    input: ["B04", "B05", "B08", "dataMask"],
    output: { bands: 4, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) {
  return [sample.B04, sample.B05, sample.B08, sample.dataMask];
}
"""


class SentinelHubConfigError(RuntimeError):
    """Levée quand la configuration Sentinel Hub n'est pas complète."""


def build_config() -> SHConfig:
    """Construit la config Sentinel Hub à partir des variables d'environnement."""
    config = SHConfig()
    config.sh_client_id = os.environ.get("SH_CLIENT_ID", "").strip()
    config.sh_client_secret = os.environ.get("SH_CLIENT_SECRET", "").strip()
    if not config.sh_client_id or not config.sh_client_secret:
        raise SentinelHubConfigError(
            "SH_CLIENT_ID et SH_CLIENT_SECRET doivent être définis. "
            "Créez un compte gratuit sur sentinel-hub.com pour les obtenir."
        )
    return config


def fetch_field_bands(
    bbox_coords: tuple[float, float, float, float],
    date: dt.date | None = None,
    resolution: int = 10,
) -> np.ndarray:
    """
    Récupère les bandes B04/B05/B08 + dataMask pour une parcelle.

    bbox_coords: (min_lon, min_lat, max_lon, max_lat) en WGS84
    date: jour visé ; si None, prend les 10 derniers jours (image la plus
          récente sans nuage sera choisie par Sentinel Hub)

    Retourne un array numpy de forme (H, W, 4).
    """
    if not isinstance(bbox_coords, tuple) or len(bbox_coords) != 4:
        raise ValueError("bbox_coords doit être un tuple de 4 coordonnées (min_lon, min_lat, max_lon, max_lat).")
    min_lon, min_lat, max_lon, max_lat = bbox_coords
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("bbox_coords doit décrire une bbox valide avec min<max sur chaque axe.")
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("bbox_coords contient des coordonnées hors limites géographiques.")
    if not isinstance(resolution, int) or resolution <= 0:
        raise ValueError("resolution doit être un entier positif.")

    try:
        config = build_config()
    except SentinelHubConfigError:
        raise

    bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
    size = bbox_to_dimensions(bbox, resolution=resolution)

    if date is None:
        time_interval = (
            (dt.date.today() - dt.timedelta(days=10)).isoformat(),
            dt.date.today().isoformat(),
        )
    else:
        time_interval = (date.isoformat(), date.isoformat())

    request = SentinelHubRequest(
        evalscript=EVALSCRIPT_BANDS,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=time_interval,
                mosaicking_order="leastCC",  # privilégie l'image la moins nuageuse
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=config,
    )

    data = request.get_data()
    return data[0]  # (H, W, 4) : B04, B05, B08, dataMask
