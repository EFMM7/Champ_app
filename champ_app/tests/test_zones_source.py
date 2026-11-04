from fastapi.testclient import TestClient

from src import api


def test_zones_endpoint_labels_demo_data_as_synthetic(monkeypatch, tmp_path):
    """/zones n'utilise que des bandes simulées : la réponse doit le dire."""
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "app.db")

    with TestClient(api.app) as client:
        token = client.post(
            "/auth/register",
            json={"email": "zones.owner@example.fr", "password": "motdepasse123"},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        field_id = client.post(
            "/fields",
            json={"name": "Parcelle Nord", "crop": "Blé tendre", "bbox": [1.500, 48.300, 1.505, 48.304]},
            headers=headers,
        ).json()["id"]

        response = client.get(f"/fields/{field_id}/zones", headers=headers)

    assert response.status_code == 200
    assert response.json()["source"] == "synthetic"
