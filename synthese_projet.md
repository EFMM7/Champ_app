# Synthèse — App de suivi de la richesse des champs pour agriculteurs

## Le concept

Une application permettant aux agriculteurs de suivre l'état de leurs champs (vigueur de la végétation, stress hydrique, carences probables) à partir d'imagerie satellite, avec des alertes et recommandations localisées par zone.

## Approche technique retenue

**Données** : imagerie satellite Sentinel-2 (Copernicus), gratuite, résolution 10m/pixel, revisite tous les 5 jours (moins en pratique à cause des nuages).

**Indices calculés** :
- NDVI — vigueur générale de la végétation
- NDRE — plus sensible, détecte le stress azoté sur végétation déjà dense
- Indice d'humidité — stress hydrique

**Limite à assumer clairement auprès des utilisateurs** : le satellite ne mesure pas le sol directement, mais la végétation. Ce n'est pas du "temps réel" au sens strict (plutôt un suivi hebdomadaire), et 10m/pixel reste grossier pour de petites parcelles ou des zones très fines.

**Coût infrastructure** : la donnée est gratuite ; le coût réel est le traitement (calcul des indices, stockage, hébergement) — de l'ordre de quelques dizaines à centaines d'euros/mois pour un volume raisonnable de parcelles.

## Prototypes réalisés

- **Version desktop** : carte de champ en grille avec zones colorées par indice, panneau de détail par zone, liste de zones à surveiller, sélecteur d'indice (NDVI/NDRE/Humidité)
- **Version mobile** : pensée pour l'usage au champ — onglet "Ma position" par défaut (simule la géolocalisation), bouton "marquer comme traité", mode hors-ligne avec horodatage du cache local, navigation en 3 onglets accessibles au pouce

Point de vigilance technique : le GPS d'un téléphone standard peut dériver de plusieurs mètres — pour un vrai découpage en zones fines, il faudra soit un GPS RTK, soit accepter des zones plus grandes.

## Paysage concurrentiel

Le marché n'est pas vide, mais mal desservi à l'échelle du petit/moyen exploitant :

| Segment | Acteurs identifiés | Cible |
|---|---|---|
| Plateforme satellite généraliste | Farmonaut | Grandes exploitations, international |
| Solutions françaises télédétection + météo | Airinov, Sencrop, Dilepix | Exploitations françaises |
| Précision par drone | Sentera, Pix4Dfields, Agremo | Agronomes, coopératives, budgets plus élevés |

*Note : ces informations proviennent de sources à dominante marketing/SEO — fiables sur l'existence des acteurs, à vérifier pour des chiffres précis.*

**Angle différenciant potentiel** : peu d'acteurs semblent viser une simplicité radicale et une expérience mobile-first pensée pour l'exploitant seul au champ plutôt que pour l'agronome ou la coopérative.

## Modèles économiques envisageables

| Modèle | Avantage | Risque |
|---|---|---|
| Abonnement par hectare | Standard du secteur | Rebutant pour petites exploitations |
| Freemium + alertes premium | Adoption facile | Conversion incertaine |
| B2B2C via coopératives | Distribution rapide, confiance déjà établie | Marge plus faible, dépendance à l'intermédiaire |
| Marketplace de recommandations | Modèle gratuit pour l'agriculteur | Risque de biais si commission sur intrants vendus |

Le modèle B2B2C via coopératives semble le plus réaliste pour percer rapidement en France.

## Stratégie d'acquisition des premiers pilotes

Concentrer le lancement sur **une culture et une région** pour garder une cohérence agronomique dans les seuils et recommandations.

**Canaux réalistes** :
- Coopératives agricoles locales — déjà la confiance des agriculteurs, rôle de conseil établi
- Chambres d'agriculture — programmes d'expérimentation/innovation
- Groupes DEPHY ou GIEE — agriculteurs déjà engagés dans une démarche de réduction d'intrants
- Un agronome/technicien conseil comme premier partenaire, pour valider les seuils avant tout déploiement

**Structure de pilote suggérée** : 5 à 10 exploitations via une coopérative, sur une saison culturale complète, avec restitution en fin de saison pour vérifier la pertinence agronomique des recommandations — pas seulement l'usage de l'app.

Le critère de succès du pilote : est-ce que l'agriculteur change réellement une décision (apport, irrigation) grâce à l'app — pas juste s'il trouve la carte lisible.

## Cadre juridique et RGPD

Le RGPD s'applique pleinement dès qu'un compte utilisateur relie des données de champ (localisation précise, rendement, pratiques) à un agriculteur identifié — ce qui est le cas dès la création de compte.

**Points d'attention** :
- **Propriété de la donnée** : l'agriculteur en reste propriétaire par défaut ; tout partage avec un tiers (coopérative, assureur, fournisseur d'intrants) doit être un opt-in explicite, jamais implicite — c'est un sujet de méfiance historique dans l'agri-tech
- **Base légale** : le consentement explicite est la base la plus sûre pour ce type d'app, plutôt que l'intérêt légitime
- **Conservation et droit à l'effacement** : prévoir une politique de rétention claire et un moyen simple de récupérer/supprimer ses données
- **Hébergement** : si cloud américain (AWS/GCP/Azure), prévoir un cadre de transfert conforme, ou envisager un hébergement européen
- **Machine learning futur** : un consentement spécifique sera nécessaire pour utiliser les données à des fins d'entraînement de modèle, distinct du consentement de suivi initial

⚠️ Ceci n'est pas un avis juridique — avant tout lancement public, faire relire les CGU et la politique de confidentialité par un avocat spécialisé en droit du numérique/agricole (subtilités possibles autour du croisement avec les aides PAC).

## Pistes non explorées à ce stade

- Validation terrain des seuils de recommandation avec un agronome
- Modèle de machine learning pour affiner les recommandations à partir de données de rendement historiques

## Fichiers produits

- Prototype desktop : `apercu_champ.html`
- Prototype mobile : `apercu_champ_mobile.html`
