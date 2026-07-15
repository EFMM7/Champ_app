"""
API FastAPI exposant les fonctions déjà testées (auth.py, fields.py, main.py).

Lancer en local :
    uvicorn api:app --reload --port 8000

Documentation interactive générée automatiquement : http://localhost:8000/docs
"""

import os
from datetime import date
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator

from src import tokens as tokens_module
from src.db import init_db
from src.auth import register_user, authenticate_user, AuthError
from src.analyses import save_analysis, list_analyses
from src.treatments import save_treatment, list_treatments, TreatmentError
from src.fields import register_field, list_fields, get_field, FieldError, CROPS_DISPONIBLES
from src.config import load_environment
from src.demo_data import generate_synthetic_bands
from src.fetch_sentinel import SentinelHubConfigError, fetch_field_bands
from src.main import run_pipeline
from src.tokens import is_production_environment

load_environment()

DB_PATH = Path(__file__).resolve().parent.parent / "output" / "app.db"


def get_db_path() -> Path:
    env_path = os.environ.get("CHAMP_DB_PATH")
    if env_path:
        return Path(env_path)
    return DB_PATH


def get_allowed_origins() -> list[str]:
    raw_value = os.environ.get("CORS_ALLOWED_ORIGINS")
    if raw_value:
        return [item.strip() for item in raw_value.split(",") if item.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = get_db_path()
    db_path.parent.mkdir(exist_ok=True)
    if is_production_environment():
        tokens_module.get_secret_key()
    init_db(db_path)
    yield


app = FastAPI(title="Suivi de champs — API", lifespan=lifespan)


def _raise_api_error(status_code: int, error: str, detail: str) -> None:
    raise HTTPException(status_code=status_code, detail={"error": error, "detail": detail, "message": detail})


def get_current_user_id(authorization: str = Header(None)) -> int:
    """
    Dépendance FastAPI : extrait et vérifie le token JWT de l'en-tête
    'Authorization: Bearer <token>'. Lève 401 si absent ou invalide.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        _raise_api_error(401, "authentication_error", "Token d'authentification manquant.")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return tokens_module.decode_access_token(token)
    except tokens_module.TokenError as e:
        _raise_api_error(401, "authentication_error", str(e))

# Config CORS configurable via variable d'environnement pour éviter l'ouverture totale en production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def api_health():
    return {
        "status": "ok",
        "database": "ready",
        "environment": "production" if is_production_environment() else "development",
        "database_path": str(get_db_path()),
    }


# ---------- schémas de requête/réponse ----------

class RegisterRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: int
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 7 * 24 * 60 * 60


class FieldCreateRequest(BaseModel):
    name: str
    crop: str
    bbox: tuple[float, float, float, float] | None = None  # min_lon, min_lat, max_lon, max_lat
    polygon: list[tuple[float, float]] | None = None  # [(lon, lat), ...], prime sur bbox si fourni
    sowing_date: str | None = None

    @field_validator("crop")
    @classmethod
    def crop_must_be_known(cls, v):
        if v not in CROPS_DISPONIBLES:
            raise ValueError(f"Culture inconnue. Choix possibles : {', '.join(CROPS_DISPONIBLES)}")
        return v


class FieldResponse(BaseModel):
    id: int
    name: str
    crop: str
    sowing_date: str | None
    area_ha: float
    polygon: list[tuple[float, float]] | None = None


class ErrorResponse(BaseModel):
    error: str
    detail: str


class AnalysisRequest(BaseModel):
    source: str = "synthetic"
    acquisition_date: date | None = None
    resolution: int = 10
    method: str = "grid"
    n_rows: int = 8
    n_cols: int = 12
    n_zones: int = 6
    critical_threshold: float | None = None
    warning_threshold: float | None = None


class ZoneTreatmentRequest(BaseModel):
    analysis_id: int
    zone_id: str
    note: str | None = None


# ---------- routes ----------

@app.post("/auth/register", response_model=AuthResponse)
def api_register(payload: RegisterRequest):
    email = payload.email.strip().lower()
    if not email or "@" not in email or "." not in email.split("@", 1)[1]:
        _raise_api_error(422, "validation_error", "Adresse email invalide.")

    try:
        user_id = register_user(get_db_path(), email, payload.password)
    except AuthError as e:
        _raise_api_error(400, "auth_error", str(e))
    return {
        "user_id": user_id,
        "access_token": tokens_module.create_access_token(user_id),
        "expires_in_seconds": tokens_module.TOKEN_EXPIRY_HOURS * 60 * 60,
    }


@app.post("/auth/login", response_model=AuthResponse)
def api_login(payload: RegisterRequest):
    try:
        user_id = authenticate_user(get_db_path(), payload.email, payload.password)
    except AuthError as e:
        _raise_api_error(401, "auth_error", str(e))
    return {
        "user_id": user_id,
        "access_token": tokens_module.create_access_token(user_id),
        "expires_in_seconds": tokens_module.TOKEN_EXPIRY_HOURS * 60 * 60,
    }


@app.post("/fields", response_model=FieldResponse)
def api_create_field(payload: FieldCreateRequest, user_id: int = Depends(get_current_user_id)):
    if payload.bbox is None and payload.polygon is None:
        _raise_api_error(400, "validation_error", "Il faut fournir soit une bbox, soit un polygone.")
    try:
        field_id = register_field(
            get_db_path(), user_id, payload.name, payload.crop,
            bbox=payload.bbox, sowing_date=payload.sowing_date, polygon=payload.polygon,
        )
    except FieldError as e:
        _raise_api_error(400, "validation_error", str(e))

    field = get_field(get_db_path(), field_id)
    return field


@app.get("/fields", response_model=list[FieldResponse])
def api_list_fields(user_id: int = Depends(get_current_user_id)):
    return list_fields(get_db_path(), user_id)


@app.get("/fields/{field_id}", response_model=FieldResponse)
def api_get_field(field_id: int, user_id: int = Depends(get_current_user_id)):
    field = get_field(get_db_path(), field_id)
    if field is None:
        _raise_api_error(404, "not_found", "Champ introuvable.")
    if field["user_id"] != user_id:
        _raise_api_error(404, "not_found", "Champ introuvable.")
    return field


def _get_owned_field(field_id: int, user_id: int) -> dict:
    field = get_field(get_db_path(), field_id)
    if field is None or field["user_id"] != user_id:
        _raise_api_error(404, "not_found", "Champ introuvable.")
    return field


@app.post("/fields/{field_id}/analyses")
def api_create_analysis(
    field_id: int,
    payload: AnalysisRequest,
    user_id: int = Depends(get_current_user_id),
):
    field = _get_owned_field(field_id, user_id)
    if payload.source not in ("synthetic", "sentinel"):
        _raise_api_error(422, "validation_error", "source doit être 'synthetic' ou 'sentinel'.")
    if payload.method not in ("grid", "kmeans"):
        _raise_api_error(422, "validation_error", "method doit être 'grid' ou 'kmeans'.")
    if payload.n_rows < 1 or payload.n_cols < 1 or payload.n_zones < 1 or payload.resolution < 1:
        _raise_api_error(422, "validation_error", "Les dimensions de zonage doivent être des entiers positifs.")

    thresholds = {
        "critical": payload.critical_threshold,
        "warning": payload.warning_threshold,
    }
    if payload.source == "synthetic":
        bands = generate_synthetic_bands(seed=field_id)
    else:
        bbox = (
            field["bbox_min_lon"],
            field["bbox_min_lat"],
            field["bbox_max_lon"],
            field["bbox_max_lat"],
        )
        try:
            bands = fetch_field_bands(bbox, date=payload.acquisition_date, resolution=payload.resolution)
        except SentinelHubConfigError as exc:
            _raise_api_error(503, "sentinel_configuration_error", str(exc))
        except Exception as exc:
            _raise_api_error(502, "sentinel_request_error", f"Impossible de récupérer les données Sentinel : {exc}")
    result, _ = run_pipeline(
        bands,
        n_rows=payload.n_rows,
        n_cols=payload.n_cols,
        method=payload.method,
        n_zones=payload.n_zones,
        thresholds=thresholds,
    )
    result["field_id"] = field_id
    return save_analysis(
        get_db_path(),
        field_id,
        source=payload.source,
        method=payload.method,
        parameters=payload.model_dump(mode="json"),
        result=result,
    )


@app.get("/fields/{field_id}/analyses")
def api_list_analyses(field_id: int, user_id: int = Depends(get_current_user_id)):
    _get_owned_field(field_id, user_id)
    return list_analyses(get_db_path(), field_id)


@app.post("/fields/{field_id}/treatments")
def api_create_treatment(
    field_id: int,
    payload: ZoneTreatmentRequest,
    user_id: int = Depends(get_current_user_id),
):
    _get_owned_field(field_id, user_id)
    try:
        return save_treatment(
            get_db_path(), field_id, payload.analysis_id, payload.zone_id, payload.note,
        )
    except TreatmentError as exc:
        _raise_api_error(400, "validation_error", str(exc))


@app.get("/fields/{field_id}/treatments")
def api_list_treatments(field_id: int, user_id: int = Depends(get_current_user_id)):
    _get_owned_field(field_id, user_id)
    return list_treatments(get_db_path(), field_id)


@app.get("/fields/{field_id}/zones")
def api_field_zones(
    field_id: int,
    method: str = "grid",
    n_rows: int = 8,
    n_cols: int = 12,
    n_zones: int = 6,
    critical_threshold: float | None = None,
    warning_threshold: float | None = None,
    user_id: int = Depends(get_current_user_id),
):
    field = get_field(get_db_path(), field_id)
    if field is None:
        _raise_api_error(404, "not_found", "Champ introuvable.")
    if field["user_id"] != user_id:
        # on renvoie 404 plutôt que 403 pour ne pas révéler l'existence du
        # champ d'un autre utilisateur
        _raise_api_error(404, "not_found", "Champ introuvable.")
    if method not in ("grid", "kmeans"):
        _raise_api_error(422, "validation_error", "method doit être 'grid' ou 'kmeans'.")
    if n_rows < 1 or n_cols < 1:
        _raise_api_error(422, "validation_error", "n_rows et n_cols doivent être des entiers positifs.")
    if n_zones < 1:
        _raise_api_error(422, "validation_error", "n_zones doit être un entier positif.")

    thresholds = None
    if critical_threshold is not None or warning_threshold is not None:
        thresholds = {
            "critical": critical_threshold,
            "warning": warning_threshold,
        }

    # Mode démo : pas d'accès réseau à Sentinel Hub dans cet environnement.
    # En production, remplacer par : fetch_sentinel.fetch_field_bands(bbox_du_champ)
    bands = generate_synthetic_bands(seed=field_id)
    result, _ = run_pipeline(
        bands,
        n_rows=n_rows,
        n_cols=n_cols,
        method=method,
        n_zones=n_zones,
        thresholds=thresholds,
    )
    result["field_id"] = field_id
    result["field_name"] = field["name"]
    return result


@app.get("/crops")
def api_crops():
    return CROPS_DISPONIBLES


# Sert l'app mobile (HTML/JS/manifest/icônes) depuis le même serveur que
# l'API : un seul déploiement, même domaine (donc plus besoin de CORS entre
# front et back en production), et l'app devient installable (PWA) puisque
# manifest.json et le service worker doivent être servis en HTTPS réel.
# Monté APRÈS toutes les routes /api pour ne jamais les masquer.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
