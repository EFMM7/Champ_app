from fastapi.testclient import TestClient

from src import api


def test_get_field_details_requires_auth_and_owner(monkeypatch, tmp_path):
    db_path = tmp_path / "app.db"
    monkeypatch.setattr(api, "DB_PATH", db_path)

    with TestClient(api.app) as client:
        register_response = client.post(
            "/auth/register",
            json={"email": "field.owner@example.fr", "password": "motdepasse123"},
        )
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        field_response = client.post(
            "/fields",
            json={
                "name": "Parcelle Nord",
                "crop": "Blé tendre",
                "bbox": [1.500, 48.300, 1.505, 48.304],
            },
            headers=headers,
        )
        assert field_response.status_code == 200
        field_id = field_response.json()["id"]

        detail_response = client.get(f"/fields/{field_id}", headers=headers)
        assert detail_response.status_code == 200
        payload = detail_response.json()
        assert payload["id"] == field_id
        assert payload["name"] == "Parcelle Nord"
        assert payload["crop"] == "Blé tendre"
        assert payload["area_ha"] > 0

        other_register = client.post(
            "/auth/register",
            json={"email": "other.user@example.fr", "password": "motdepasse456"},
        )
        assert other_register.status_code == 200
        other_token = other_register.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        forbidden_response = client.get(f"/fields/{field_id}", headers=other_headers)
        assert forbidden_response.status_code == 404
