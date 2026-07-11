"""Teste l'API avec de vraies requêtes HTTP, y compris l'authentification par token JWT."""

from pathlib import Path
from fastapi.testclient import TestClient

DB_PATH = Path(__file__).resolve().parent.parent / "output" / "app.db"
if DB_PATH.exists():
    DB_PATH.unlink()

from src.api import app

client = TestClient(app)
client.__enter__()  # déclenche l'event "startup" (création des tables)


def show(title, response):
    print(f"\n{title}")
    print(f"  status: {response.status_code}")
    print(f"  body:   {response.json()}")


# 1. inscription -> reçoit un token
r = client.post("/auth/register", json={"email": "marie.leroy@example.fr", "password": "motdepasse123"})
show("POST /auth/register", r)
token = r.json()["access_token"]
auth_headers = {"Authorization": f"Bearer {token}"}

# 1bis. email déjà pris
r = client.post("/auth/register", json={"email": "marie.leroy@example.fr", "password": "autremdp123"})
show("POST /auth/register (email déjà pris, doit échouer)", r)

# 2. connexion -> reçoit aussi un token
r = client.post("/auth/login", json={"email": "marie.leroy@example.fr", "password": "motdepasse123"})
show("POST /auth/login", r)

r = client.post("/auth/login", json={"email": "marie.leroy@example.fr", "password": "mauvais"})
show("POST /auth/login (mauvais mot de passe, doit échouer)", r)

# 3. accès à une route protégée SANS token -> doit échouer
r = client.get("/fields")
show("GET /fields (sans token, doit échouer 401)", r)

# 3bis. avec un token invalide -> doit échouer
r = client.get("/fields", headers={"Authorization": "Bearer faux.token.ici"})
show("GET /fields (token invalide, doit échouer 401)", r)

# 4. création de champ AVEC token (user_id n'est plus dans le corps de la requête)
r = client.post("/fields", json={
    "name": "Parcelle Nord",
    "crop": "Blé tendre",
    "bbox": [1.500, 48.300, 1.505, 48.304],
    "sowing_date": "2025-10-15",
}, headers=auth_headers)
show("POST /fields (avec token)", r)
field_id = r.json()["id"]

# 4bis. création de champ avec un vrai POLYGONE (pas juste une bbox)
l_shape = [[1.500,48.300],[1.503,48.300],[1.503,48.3018],[1.505,48.3018],[1.505,48.304],[1.500,48.304]]
r = client.post("/fields", json={
    "name": "Parcelle en L",
    "crop": "Maïs",
    "polygon": l_shape,
}, headers=auth_headers)
show("POST /fields (avec polygone réel, forme en L)", r)

# 4ter. ni bbox ni polygone -> doit échouer
r = client.post("/fields", json={"name": "Test", "crop": "Blé tendre"}, headers=auth_headers)
show("POST /fields (ni bbox ni polygone, doit échouer 400)", r)

# 5. liste des champs avec token -> ne voit que ses propres champs
r = client.get("/fields", headers=auth_headers)
show("GET /fields (avec token)", r)

# 6. données de zones du champ, avec token
r = client.get(f"/fields/{field_id}/zones", headers=auth_headers)
zones_data = r.json()
print(f"\nGET /fields/{field_id}/zones (avec token, méthode grid par défaut)")
print(f"  status: {r.status_code}")
print(f"  NDVI moyen: {zones_data['field_mean_ndvi']}, alertes: {zones_data['alert_count']}, méthode: {zones_data['grid']['method']}")

# 6bis. avec segmentation k-means
r = client.get(f"/fields/{field_id}/zones?method=kmeans", headers=auth_headers)
zones_data_km = r.json()
print(f"\nGET /fields/{field_id}/zones?method=kmeans")
print(f"  status: {r.status_code}")
print(f"  NDVI moyen: {zones_data_km['field_mean_ndvi']}, alertes: {zones_data_km['alert_count']}, méthode: {zones_data_km['grid']['method']}")

# 7. un DEUXIÈME utilisateur ne doit pas pouvoir voir le champ du premier
r = client.post("/auth/register", json={"email": "autre.utilisateur@example.fr", "password": "motdepasse456"})
other_token = r.json()["access_token"]
r = client.get(f"/fields/{field_id}/zones", headers={"Authorization": f"Bearer {other_token}"})
show("GET /fields/{field_id}/zones (champ d'un AUTRE utilisateur, doit échouer 404)", r)

# 8. liste des cultures disponibles (route publique, pas de token nécessaire)
r = client.get("/crops")
show("GET /crops", r)
