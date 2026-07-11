# Pipeline de suivi de champ — comptes, parcelles, NDVI/NDRE via Sentinel-2

Code réel du projet (pas des mockups) : gestion de compte, enregistrement de
parcelles, récupération (ou simulation) de bandes Sentinel-2, calcul NDVI et
NDRE, découpage en zones, détection d'alertes, export JSON + cartes PNG.

## Priorités réelles du projet

Pour éviter de disperser l'effort, les priorités du moment sont les suivantes :

1. **Stabiliser le cœur métier** : inscription/connexion, création de champ,
   validation de géométrie, stockage et lecture cohérents.
2. **Valider la qualité des résultats** : indices et zonage sur des données
   réelles ou au moins des données de démo réalistes, sans se disperser sur
   des sujets trop éloignés du cœur du produit.
3. **Rendre l'API plus sûre et plus robuste** : secrets via variables
   d'environnement, CORS maîtrisé, tests de régression autour des cas limites.
4. **Élargir la couverture de tests** sur la validation métier et les sorties
   de traitement, avant de penser à des améliorations plus "cosmétiques".

Les sujets suivants restent utiles, mais sont **secondaires** tant que le
cœur de l'application n'est pas stabilisé : PWA, déploiement multiplateforme,
app native, ou stockage de données plus avancé.

## Structure

```
src/
  db.py                → schéma SQLite (users, fields)
  auth.py              → création de compte, connexion (PBKDF2)
  fields.py            → enregistrement des parcelles, calcul de surface
  api.py               → API FastAPI (endpoints HTTP réels, protégés par JWT)
  tokens.py            → émission / vérification des tokens JWT de session
  test_api.py           → tests de l'API via de vraies requêtes HTTP
  fetch_sentinel.py    → appel réel à l'API Sentinel Hub (nécessite une clé)
  indices.py           → calcul NDVI / NDRE à partir des bandes brutes
  zoning.py            → découpage en grille + classification (ok/warning/critical)
  zoning_kmeans.py     → découpage en zones homogènes réelles (k-means)
  compare_zoning.py    → compare visuellement grille vs k-means sur les mêmes données
  demo_data.py         → génère des bandes synthétiques (pour tester sans réseau)
  main.py              → pipeline indices/zones, en ligne de commande
  demo_flow.py         → démo bout-en-bout : compte → champ → pipeline (sans API)
output/
  demo.db              → base SQLite générée par demo_flow.py
  zones.json           → données de zones (sortie de main.py)
  zones_field_1.json   → données de zones liées à un champ précis
  carte_ndvi.png / carte_ndre.png
static/                → servi directement par l'API (voir "Installer l'app")
  onboarding_mobile.html
  apercu_champ_mobile.html
  manifest.json         → manifest PWA (nom, icônes, couleurs)
  service-worker.js     → requis pour l'installabilité Android/Chrome
  icon-192.png / icon-512.png
generate_icons.py      → régénère les icônes de static/ si besoin
```

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

⚠️ **Toutes les commandes ci-dessous s'exécutent depuis la racine du projet
(`champ_app/`, le dossier qui contient `src/` et `requirements.txt`), pas
depuis l'intérieur de `src/`.** Les modules s'importent entre eux via
`from src.xxx import ...`, donc Python doit être lancé avec `-m` (mode
module) plutôt que directement sur le fichier — `python -m src.main` et non
`python src/main.py`, sans quoi Python ne retrouve pas les modules
(`ModuleNotFoundError: No module named 'src'`).

**Lancer l'API (serveur HTTP réel)** :
```bash
uvicorn src.api:app --reload --port 8000
```
Documentation interactive auto-générée : http://localhost:8000/docs

Endpoints disponibles :
| Méthode | Route | Auth requise | Rôle |
|---|---|---|---|
| POST | `/auth/register` | non | Créer un compte, renvoie un token JWT et sa durée de validité |
| POST | `/auth/login` | non | Se connecter, renvoie un token JWT et sa durée de validité |
| POST | `/fields` | oui | Enregistrer un champ (rattaché à l'utilisateur du token) |
| GET | `/fields` | oui | Lister les champs de l'utilisateur du token |
| GET | `/fields/{field_id}/zones` | oui | Zones NDVI/NDRE d'un champ (`?method=grid` ou `kmeans`, avec `n_rows`, `n_cols`, `n_zones` optionnels, 404 si pas le sien) |
| GET | `/crops` | non | Liste des cultures reconnues |

L'authentification se fait via l'en-tête `Authorization: Bearer <token>`, token obtenu à l'inscription ou la connexion.

**Tester l'API sans lancer de serveur (TestClient)** :
```bash
python -m src.test_api
```

**Démo bout-en-bout sans passer par l'API (compte + champ + pipeline)** :
```bash
python -m src.demo_flow
```

**Juste le pipeline en mode démo** :
```bash
python -m src.main --demo
```

**Mode réel Sentinel Hub (nécessite un compte gratuit sur sentinel-hub.com)** :
```bash
export SH_CLIENT_ID="votre_id"
export SH_CLIENT_SECRET="votre_secret"
python -m src.main --bbox 2.30,48.85,2.35,48.90
```

## Ce qui est réellement testé vs. ce qui ne l'est pas

- **Testé et fonctionnel** (exécuté dans cet environnement, résultats vérifiés) :
  - **l'API FastAPI en entier**, via de vraies requêtes HTTP (`test_api.py`) :
    inscription, doublon d'email rejeté (400), connexion, mauvais mot de
    passe rejeté (401), accès sans token rejeté (401), token invalide
    rejeté (401), création de champ, culture invalide rejetée (422), liste
    des champs, récupération des zones NDVI/NDRE, **et isolation entre
    utilisateurs vérifiée** (un utilisateur ne peut pas voir le champ d'un
    autre — 404)
  - **le module `tokens.py`** : création/décodage de token, rejet d'un
    token invalide, rejet d'un token expiré (testé avec un token expiré
    fabriqué manuellement)
  - création de compte avec validation (email, mot de passe ≥ 8 caractères,
    unicité) et rejet propre des cas invalides
  - connexion avec vérification du mot de passe haché (PBKDF2, pas de mot de
    passe stocké en clair)
  - enregistrement d'un champ avec validation (culture dans une liste
    connue, bbox géographiquement cohérente) et calcul automatique de la
    surface en hectares à partir des coordonnées
  - le calcul des indices, le découpage en zones, la classification, l'export
    JSON, et la génération des cartes — sur données synthétiques réalistes
- **Non testé ici** : l'appel réel à Sentinel Hub (`fetch_sentinel.py`).
  Le code suit l'API officielle `sentinelhub-py`, mais je n'ai pas pu
  l'exécuter dans cet environnement (pas d'accès réseau vers
  `services.sentinel-hub.com`). À tester avec vos propres identifiants.

## Contour réel de la parcelle (polygone) plutôt qu'un simple rectangle

`register_field()` accepte maintenant soit une `bbox` (comme avant, pour
compatibilité), soit un `polygon` réel — une liste de points `(lon, lat)`.
Quand un polygone est fourni :
- la bbox est dérivée automatiquement (utile pour la requête satellite, qui
  a besoin d'un rectangle englobant)
- la surface est calculée sur la vraie forme (formule du lacet sur une
  projection équirectangulaire locale), pas sur le rectangle englobant —
  testé sur une forme en L : 13.519 ha réels contre 20+ ha si on avait
  utilisé la bbox englobante
- le polygone est stocké tel quel (`polygon_geojson` en base) et renvoyé
  par l'API pour être réaffiché

**Écran mobile correspondant** : `onboarding_mobile.html` utilise
maintenant une vraie carte (Leaflet + OpenStreetMap) avec un outil de
dessin de polygone (Leaflet.draw) au lieu d'un rectangle simulé sur un
dégradé. La formule de calcul de surface côté client (JavaScript) est
volontairement identique à celle du serveur (Python) — **vérifié** : les
deux donnent 13.519 ha sur la même forme en L, testés indépendamment.

## Deux méthodes de segmentation, et pourquoi ça compte

- **`grid`** (défaut) : grille régulière fixe (8x12 = 96 zones). Rapide,
  simple, mais arbitraire — une zone de grille peut couper en deux une
  vraie zone de stress, ou au contraire regrouper des sous-parties très
  différentes.
- **`kmeans`** : `n_zones` zones homogènes réelles, calculées par clustering
  sur la valeur d'indice + la position spatiale. Sur les données de test
  (`compare_zoning.py`), ça change concrètement le résultat : la même
  parcelle synthétique donne **8 zones d'alerte éparpillées** en mode
  grille contre **1 seule zone bien délimitée** en mode k-means — beaucoup
  plus proche de ce qu'un agronome tracerait à la main pour une
  recommandation d'intervention ciblée.

Comparer les deux : `python -m src.compare_zoning` (génère une image
côte-à-côte dans `output/comparaison_grille_vs_kmeans.png`).

## Priorité secondaire — PWA et déploiement

Le projet contient déjà une base de **PWA** : les fichiers de l'interface
mobile sont servis par l'API, et l'app peut être installée sur un téléphone
via un navigateur moderne. Cela reste utile, mais ce n'est pas la priorité
majeure tant que le cœur métier n'est pas pleinement stabilisé.

À garder en vue, mais sans faire perdre de temps maintenant :
- `static/manifest.json` et `static/service-worker.js`
- un déploiement HTTPS propre pour pouvoir installer l'app sur mobile
- une évolution vers une vraie app native seulement si l'usage métier le
  justifie réellement

## Choix de sécurité à noter

- Mots de passe hachés en PBKDF2-HMAC-SHA256 avec sel aléatoire (pas de
  dépendance externe). Pour une vraie mise en production, bcrypt ou argon2
  restent préférables mais PBKDF2 est un choix raisonnable pour un MVP.
- Les erreurs de connexion renvoient volontairement le même message
  ("email ou mot de passe incorrect") que l'email existe ou non, pour éviter
  de révéler quels comptes existent (énumération d'utilisateurs).
- Sessions gérées par token JWT (`tokens.py`), valable 7 jours, transmis via
  l'en-tête `Authorization: Bearer`. Le `user_id` n'est plus jamais transmis
  en clair par le client — il est toujours dérivé du token côté serveur.
- Les réponses d'erreur sont désormais structurées et cohérentes : chaque
  erreur renvoie un objet avec `error`, `detail` et `message`, ce qui facilite
  une intégration côté client et un traitement homogène des validations.
- ⚠️ `JWT_SECRET_KEY` a une valeur par défaut **uniquement pour le
  développement local** — à définir via la variable d'environnement
  `JWT_SECRET_KEY` avant tout déploiement réel.
- Le CORS est désormais limité par défaut à des origines locales sûres
  (`localhost` / `127.0.0.1` sur les ports 3000 et 8000), avec possibilité
  de surcharger la liste via `CORS_ALLOWED_ORIGINS`.
- Un utilisateur qui demande les zones d'un champ qui ne lui appartient pas
  reçoit un 404 (pas un 403), pour ne pas révéler l'existence du champ d'un
  autre utilisateur — testé dans `test_api.py`.

## Prochaines étapes, par ordre de priorité

1. **Valider le cœur du flux** sur des parcelles réelles ou des données de
   démo plus proches du terrain, puis ajuster les seuils de zonage si besoin.
2. **Renforcer la sécurité d'exploitation** : `JWT_SECRET_KEY` obligatoire en
   environnement réel, CORS restreint, secrets gérés proprement.
3. **Ajouter des tests métier de plus en plus ciblés** sur la géométrie,
   l'authentification et les sorties de traitement.
4. **Préparer une évolution plus robuste si l'usage devient concret** : base de
   données plus solide, logs, monitoring, puis seulement après la stabilité du
   cœur fonctionnel.
