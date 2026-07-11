import importlib

import pytest
from fastapi.testclient import TestClient

from src import api
from src.tokens import TokenError, create_access_token, decode_access_token


def test_create_and_decode_access_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    import src.tokens as tokens

    importlib.reload(tokens)

    token = tokens.create_access_token(42)
    assert tokens.decode_access_token(token) == 42


def test_invalid_token_is_rejected_by_api(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "app.db")
    import src.tokens as tokens

    importlib.reload(tokens)

    with TestClient(api.app) as client:
        response = client.get("/fields", headers={"Authorization": "Bearer not-a-valid-token"})

    assert response.status_code == 401
    payload = response.json()["detail"]
    assert payload["error"] == "authentication_error"
    assert payload["detail"] == "Token invalide ou expiré."
    assert payload["message"] == "Token invalide ou expiré."
