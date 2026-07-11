"""
Émission et vérification de tokens JWT pour les sessions API.

⚠️ SECRET_KEY : ici lue depuis une variable d'environnement avec une valeur
par défaut UNIQUEMENT pour le développement local. En production, elle doit
être définie via une vraie variable d'environnement secrète, jamais commitée.
"""

import os
import datetime as dt

from jose import jwt, JWTError

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-secret-do-not-use-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24 * 7  # 7 jours


class TokenError(Exception):
    """Token manquant, invalide, ou expiré."""


def create_access_token(user_id: int) -> str:
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Retourne le user_id encodé dans le token. Lève TokenError si invalide/expiré."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise TokenError("Token invalide ou expiré.")

    user_id = payload.get("sub")
    if user_id is None:
        raise TokenError("Token mal formé.")
    return int(user_id)
