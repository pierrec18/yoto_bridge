# Yoto Bridge

Passerelle entre une bibliothèque **Navidrome/Subsonic** et les cartes **Yoto
Make Your Own (MYO)**. L'interface permet de synchroniser la bibliothèque,
configurer les cartes, choisir un morceau ou une stratégie de lecture, puis
publier la carte sur Yoto (streaming ou hors ligne).

Le projet est prévu pour être déployé avec Docker Compose ou depuis Arcane.
L'interface est une PWA installable sur mobile.

## Fonctionnement

```text
Yoto ── GET /stream/{carte}/{piste}?t=... ──> Yoto Bridge ──> Navidrome
                                               (API Subsonic)
```

Le serveur ne transmet jamais l'URL ni le mot de passe Navidrome à Yoto. Pour
une piste en streaming, il choisit le morceau selon sa stratégie puis relaie
le MP3 transcodé par Navidrome. Pour une piste hors ligne, il envoie le fichier
à l'API officielle Yoto et mémorise le média déjà téléversé.

Modes disponibles : `fixed`, `playlist`, `album`, `random`, `smart` et
`search`. Le cache SQLite contient la bibliothèque et les cartes ; il est
persisté dans le dossier monté sur `/app/data`.

## Déploiement recommandé (Ubuntu + Arcane)

### 1. Préparer le dépôt et les secrets

Le fichier `.env` doit rester sur le serveur et ne doit jamais être commité.
Depuis le dossier du projet :

```bash
cp .env.example .env
mkdir -p /mnt/docker/yoto-bridge/data
sudo chown -R 10001:10001 /mnt/docker/yoto-bridge/data
openssl rand -hex 32       # renseigner le résultat dans YOTO_SESSION_SECRET
openssl rand -hex 32       # renseigner le résultat dans YOTO_SECRETS_KEY
chmod 600 .env
```

`YOTO_SECRETS_KEY` est la clé stable qui chiffre dans SQLite le mot de passe
Navidrome, les jetons Yoto et le token de streaming. La sauvegarder dans le
gestionnaire de secrets d'Arcane : sans elle, une base chiffrée ne peut pas
être relue. Ne jamais la régénérer lors d'une mise à jour.

Renseigner ensuite au minimum :

```dotenv
YOTO_DATA_DIR=/mnt/docker/yoto-bridge/data
YOTO_PUBLIC_BASE_URL=https://yotobridge.example.com
YOTO_AUTH_ENABLED=true
YOTO_OIDC_ISSUER_URL=https://id.example.com
YOTO_OIDC_CLIENT_ID=...
YOTO_OIDC_CLIENT_SECRET=...
YOTO_SESSION_SECRET=...
YOTO_SECRETS_KEY=...
```

Pour un premier démarrage local sans Pocket ID, laisser
`YOTO_AUTH_ENABLED=false` et utiliser l'URL locale ; réactiver OIDC avant
d'exposer le service sur Internet.

### 2. Configurer le client OIDC

Dans Pocket ID (ou un autre fournisseur OIDC), déclarer exactement :

```text
https://yotobridge.example.com/api/auth/callback
```

Le domaine de `YOTO_PUBLIC_BASE_URL`, le domaine utilisé par le navigateur et
celui du callback doivent être identiques. En production, l'URL publique doit
être en HTTPS.

### 3. Démarrer avec Docker Compose

```bash
docker compose pull
docker compose up -d
docker compose logs -f backend frontend
```

L'interface écoute par défaut sur `127.0.0.1:8081`. Le reverse proxy (Caddy,
Traefik, Nginx Proxy Manager, etc.) doit terminer TLS et rediriger le domaine
vers `http://127.0.0.1:8081`. Si le reverse proxy est lui-même un conteneur,
placez-le sur le même réseau Docker ou exposez explicitement le port avec un
pare-feu : le bind localhost est volontaire pour éviter une exposition LAN.

Le backend n'est pas publié sur un port de l'hôte. Les routes `/api`,
`/stream`, `/docs` et `/health` sont proxifiées par Nginx dans le conteneur
frontend.

Dans Arcane, créer un projet depuis ce dépôt, ajouter les variables du `.env`
dans l'environnement du projet, puis utiliser le même `docker-compose.yml`.
Le dossier `/mnt/docker/yoto-bridge/data` doit être un volume persistant du
projet, pas un dossier temporaire de synchronisation Git.

### 4. Initialiser l'application

1. Ouvrir le domaine et se connecter via OIDC.
2. Dans **Réglages**, renseigner l'URL HTTPS de Navidrome, l'utilisateur et le
   mot de passe dédié à Bridge, puis tester la connexion.
3. Dans **Dashboard**, lancer une synchronisation.
4. Créer une carte, configurer ses pistes et choisir **Publier sur Yoto**.
5. Associer la carte publiée dans l'application Yoto. Une piste streaming
   utilise le token partagé ; **Réglages → Réinitialiser le token** invalide
   immédiatement les anciennes URLs.

## Variables importantes

| Variable | Rôle |
| --- | --- |
| `YOTO_DATA_DIR` | Dossier persistant monté sur `/app/data` |
| `YOTO_PUBLIC_BASE_URL` | URL externe utilisée par Yoto et les callbacks OAuth |
| `YOTO_AUTH_ENABLED` | Active la protection OIDC (recommandé en production) |
| `YOTO_OIDC_*` | Paramètres du fournisseur OIDC/Pocket ID |
| `YOTO_SESSION_SECRET` | Signature des sessions web, 32 caractères minimum |
| `YOTO_SECRETS_KEY` | Chiffrement des secrets en base, à conserver à vie |
| `YOTO_CORS_ORIGINS` | Origines autorisées, séparées par des virgules ; vide = même origine |
| `YOTO_IMAGE_TAG` | Tag ou SHA d'image GHCR à déployer |
| `YOTO_WEB_PORT` | Port local du frontend (8081 par défaut) |
| `YOTO_SYNC_INTERVAL_SECONDS` | Intervalle de synchronisation (60–86400 s) |

Les images GHCR utilisent `latest` par défaut pour une installation simple.
Pour un déploiement reproductible, définir `YOTO_IMAGE_TAG` sur un tag semver
ou un tag SHA publié par la CI, puis mettre à jour volontairement.

Le backend refuse volontairement de démarrer avec une URL publique externe si
`YOTO_AUTH_ENABLED` ou `YOTO_SECRETS_KEY` manque : cela évite de publier par
accident une interface non protégée ou des identifiants en clair.

## Sécurité intégrée

- OIDC optionnel, validation stricte des secrets et cookie de session `Secure`
  lorsque l'URL publique est HTTPS.
- Protection CSRF des requêtes API mutantes lorsque OIDC est actif.
- Chiffrement Fernet des secrets SQLite avec `YOTO_SECRETS_KEY` ; les anciennes
  valeurs en clair restent lisibles et sont chiffrées à leur prochaine écriture.
- Token aléatoire obligatoire sur chaque URL `/stream`, comparable en temps
  constant et révocable.
- Backend non exposé sur l'hôte, conteneur backend non-root, filesystem en
  lecture seule, `no-new-privileges`, capabilities supprimées et healthchecks.
- Headers Nginx CSP, anti-clickjacking, `nosniff`, politique de référent et
  permissions navigateur ; logs d'accès désactivés sur `/stream` et logs
  `httpx` silencés pour éviter les jetons dans les journaux.
- Limites de validation sur URLs, tailles, bitrate, durée de session et nombre
  de pistes (1 à 100).

Mesures d'exploitation à conserver : HTTPS obligatoire via le reverse proxy,
pare-feu limitant le port du proxy, mises à jour régulières des images,
rotation du mot de passe Navidrome et sauvegardes chiffrées de `data/` **avec**
`YOTO_SECRETS_KEY`.

## Sauvegarde et mise à jour

Arrêter brièvement le backend avant une sauvegarde cohérente :

```bash
docker compose stop backend
sqlite3 /mnt/docker/yoto-bridge/data/yoto_bridge.sqlite \
  ".backup '/mnt/docker/yoto-bridge/data/yoto_bridge.backup.sqlite'"
docker compose start backend
```

Conserver aussi `.env` dans un coffre séparé. Pour mettre à jour :

```bash
docker compose pull
docker compose up -d
docker compose ps
```

Les petites migrations SQLite sont appliquées au démarrage. En cas de retour
arrière, redéfinir `YOTO_IMAGE_TAG` sur l'ancien tag ; ne supprimer ni le
volume de données ni la clé de chiffrement.

## Développement local

Backend :

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload --port 8000
```

Frontend :

```bash
cd frontend
npm ci
npm run dev
```

Pour construire les images localement :

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
```

## API et structure

La documentation OpenAPI est disponible sur `/docs` lorsque l'utilisateur est
authentifié. Les principales routes sont :

| Route | Fonction |
| --- | --- |
| `/api/auth/*` | Statut et flux OIDC |
| `/api/settings` | Source Navidrome et token de streaming |
| `/api/sync` | Synchronisation manuelle |
| `/api/library/*` | Recherche, artistes, albums, pochettes |
| `/api/cards/*` | CRUD cartes, pistes, génération, historique |
| `/api/yoto/*` | Connexion Yoto et publication |
| `/api/stats/*` | Tableau de bord et statistiques |
| `/stream/{card}/{track}` | Flux audio Yoto, token `t` obligatoire |

```text
backend/app/
  main.py, config.py, auth.py, csrf.py, secrets.py
  database.py, models.py, schemas.py
  providers/       # abstraction MusicProvider + Navidrome/Subsonic
  services/        # synchronisation, lecture, publication Yoto
  routers/         # API REST
frontend/src/      # React + Vite + Mantine + PWA
```

## Licence et contribution

Avant une contribution, lancer les tests backend et vérifier que `.env`, la
base SQLite et les journaux ne sont jamais ajoutés à Git. Les images sont
construites par GitHub Actions et publiées sur GHCR pour les branches/tags
configurés dans `.github/workflows/build-images.yml`.
