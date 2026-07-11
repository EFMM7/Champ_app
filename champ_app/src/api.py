"""
API FastAPI exposant les fonctions déjà testées (auth.py, fields.py, main.py).

Lancer en local :
    uvicorn api:app --reload --port 8000

Documentation interactive générée automatiquement : http://localhost:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator

from src.db import init_db
from src.auth import register_user, authenticate_user, AuthError
from src.fields import register_field, list_fields, get_field, FieldError, CROPS_DISPONIBLES
from src.demo_data import generate_synthetic_bands
from src.main import run_pipeline
from src.tokens import create_access_token, decode_access_token, TokenError

DB_PATH = Path(__file__).resolve().parent.parent / "output" / "app.db"

app = FastAPI(title="Suivi de champs — API")


def get_current_user_id(authorization: str = Header(None)) -> int:
    """
    Dépendance FastAPI : extrait et vérifie le token JWT de l'en-tête
    'Authorization: Bearer <token>'. Lève 401 si absent ou invalide.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token d'authentification manquant.")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return decode_access_token(token)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

# En dev uniquement : à restreindre à l'origine réelle de l'app en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    DB_PATH.parent.mkdir(exist_ok=True)
    init_db(DB_PATH)


# ---------- schémas de requête/réponse ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: int
    access_token: str
    token_type: str = "bearer"


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


# ---------- routes ----------

@app.post("/auth/register", response_model=AuthResponse)
def api_register(payload: RegisterRequest):
    try:
        user_id = register_user(DB_PATH, payload.email, payload.password)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"user_id": user_id, "access_token": create_access_token(user_id)}


@app.post("/auth/login", response_model=AuthResponse)
def api_login(payload: RegisterRequest):
    try:
        user_id = authenticate_user(DB_PATH, payload.email, payload.password)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return {"user_id": user_id, "access_token": create_access_token(user_id)}


@app.post("/fields", response_model=FieldResponse)
def api_create_field(payload: FieldCreateRequest, user_id: int = Depends(get_current_user_id)):
    if payload.bbox is None and payload.polygon is None:
        raise HTTPException(status_code=400, detail="Il faut fournir soit une bbox, soit un polygone.")
    try:
        field_id = register_field(
            DB_PATH, user_id, payload.name, payload.crop,
            bbox=payload.bbox, sowing_date=payload.sowing_date, polygon=payload.polygon,
        )
    except FieldError as e:
        raise HTTPException(status_code=400, detail=str(e))

    field = get_field(DB_PATH, field_id)
    return field


@app.get("/fields", response_model=list[FieldResponse])
def api_list_fields(user_id: int = Depends(get_current_user_id)):
    return list_fields(DB_PATH, user_id)


@app.get("/fields/{field_id}/zones")
def api_field_zones(field_id: int, method: str = "grid", user_id: int = Depends(get_current_user_id)):
    field = get_field(DB_PATH, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Champ introuvable.")
    if field["user_id"] != user_id:
        # on renvoie 404 plutôt que 403 pour ne pas révéler l'existence du
        # champ d'un autre utilisateur
        raise HTTPException(status_code=404, detail="Champ introuvable.")
    if method not in ("grid", "kmeans"):
        raise HTTPException(status_code=422, detail="method doit être 'grid' ou 'kmeans'.")

    # Mode démo : pas d'accès réseau à Sentinel Hub dans cet environnement.
    # En production, remplacer par : fetch_sentinel.fetch_field_bands(bbox_du_champ)
    bands = generate_synthetic_bands(seed=field_id)
    result, _ = run_pipeline(bands, n_rows=8, n_cols=12, method=method)
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
