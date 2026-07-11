"""
Création de compte et authentification.

Hachage de mot de passe en PBKDF2-HMAC-SHA256 (bibliothèque standard Python,
pas de dépendance externe). Pour une vraie mise en production, bcrypt ou
argon2 restent préférables, mais PBKDF2 via hashlib est un choix raisonnable
et suffisamment robuste pour un MVP.
"""

import hashlib
import os
import re
import sqlite3
from pathlib import Path

from src.db import get_connection

PBKDF2_ITERATIONS = 260_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    """Erreur de validation ou d'authentification (email invalide, déjà pris,
    mot de passe trop court, identifiants incorrects...)."""


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return digest.hex(), salt.hex()


def register_user(db_path: str | Path, email: str, password: str) -> int:
    """Crée un compte. Retourne l'id utilisateur. Lève AuthError si invalide."""
    email = email.strip().lower()

    if not EMAIL_RE.match(email):
        raise AuthError("Adresse email invalide.")
    if len(password) < 8:
        raise AuthError("Le mot de passe doit contenir au moins 8 caractères.")

    password_hash, salt = _hash_password(password)

    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, salt) VALUES (?, ?, ?)",
            (email, password_hash, salt),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise AuthError("Un compte existe déjà avec cet email.")
    finally:
        conn.close()


def authenticate_user(db_path: str | Path, email: str, password: str) -> int:
    """Vérifie les identifiants. Retourne l'id utilisateur si valide, lève AuthError sinon."""
    email = email.strip().lower()
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, password_hash, salt FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row is None:
            raise AuthError("Email ou mot de passe incorrect.")

        computed_hash, _ = _hash_password(password, bytes.fromhex(row["salt"]))
        if computed_hash != row["password_hash"]:
            raise AuthError("Email ou mot de passe incorrect.")

        return row["id"]
    finally:
        conn.close()
