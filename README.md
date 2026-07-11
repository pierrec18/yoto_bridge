# Yoto Radio Server (Yoto Bridge)

Serveur qui permet d'utiliser une bibliothèque **Navidrome** comme source audio
pour des cartes **Yoto Make Your Own (MYO)**. Le contenu n'est jamais stocké sur
la carte : chaque piste MYO pointe vers une URL de streaming servie par ce
serveur, qui choisit dynamiquement le morceau et le proxifie depuis Navidrome.

> État actuel : **backend fonctionnel + interface web React**. Validé de bout en
> bout contre un vrai Navidrome (config, synchro, cartes, sélection de contenu,
> streaming MP3 avec requêtes `Range`). L'intégration de l'API officielle Yoto
> (§18) reste à faire.

## Comment ça marche

```
Carte Yoto ──GET /stream/{card}/{track}──▶ Yoto Bridge ──stream.view (MP3)──▶ Navidrome
```

1. Une carte MYO déclare N pistes de type `stream`, chacune ciblant
   `GET /stream/{card_id}/{track_number}` sur ce serveur.
2. À la lecture, le serveur retrouve la **stratégie** associée à cette piste
   (morceau fixe, playlist, album, aléatoire, smart, recherche), choisit un
   morceau, puis demande à Navidrome un transcodage MP3 via l'API Subsonic
   `stream.view` et **proxifie** le flux.
3. Les identifiants et l'URL Navidrome ne sont **jamais** exposés à la Yoto (§14).

Les FLAC ne sont jamais décodés localement : le transcodage est délégué à
Navidrome.

### Point important sur les requêtes `Range`

La Yoto peut ré-interroger la même URL plusieurs fois pour une seule lecture
(requêtes `Range` de seek, reprises réseau). Pour éviter de tirer un nouveau
morceau à chaque requête HTTP, un petit cache TTL par `(carte, piste)` renvoie le
**même** morceau pendant une courte fenêtre (`YOTO_RESOLUTION_TTL_SECONDS`, 8 s
par défaut). La sémantique exacte piste-suivante / précédente devra être affinée
sur du matériel réel — c'est le premier point à valider en test physique.

### Token de streaming

Chaque URL `/stream` exige un jeton partagé (`?t=...`), généré automatiquement et
stocké côté serveur. Il est intégré aux URLs copiées depuis l'éditeur de carte
(donc déposées sur la Yoto). En cas de fuite, un bouton **Réglages →
Réinitialiser** régénère le jeton : les anciennes URLs renvoient alors `403` et
il suffit de recopier les nouvelles. Endpoint : `POST /api/settings/reset-token`.

## Modes de lecture (§5)

| Mode       | `config` attendu                                             |
|------------|-------------------------------------------------------------|
| `fixed`    | `{"song_id": "..."}`                                         |
| `playlist` | `{"playlist_id": "..."}` (lecture séquentielle, progression) |
| `album`    | `{"album_id": "..."}` (lecture séquentielle, progression)    |
| `random`   | `{}` (évite le morceau précédent)                            |
| `smart`    | `{}` (évite morceau, artiste et album précédents)            |
| `search`   | `{"query": "...", "genre": "...", "min_rating": 4, "min_year": 2010}` |

## Architecture du code

```
backend/
  app/
    main.py            # app FastAPI, CORS, lifespan + scheduler
    config.py          # configuration via variables d'env (YOTO_*)
    database.py        # moteur SQLAlchemy async + sessions
    models.py          # tables (settings, cards, card_tracks, history, cache…)
    schemas.py         # modèles Pydantic de l'API
    scheduler.py       # synchronisation périodique (démarrage + horaire)
    providers/
      base.py          # interface MusicProvider (abstraction source, §16)
      subsonic.py      # implémentation Navidrome (API Subsonic)
      factory.py       # construction du provider depuis les réglages
    services/
      library.py       # synchronisation bibliothèque -> cache SQLite
      playback.py      # résolution piste -> morceau (cœur du système)
    routers/           # settings, cards, library, sync, stats, stream
  tests/               # pytest (provider, playback, API)
```

L'abstraction `MusicProvider` (§16) garantit que le reste de l'application ne
dépend jamais directement de Navidrome. Futurs providers : Plex, Jellyfin, Emby,
Audiobookshelf.

## API REST (extrait)

| Méthode & route | Rôle |
|-----------------|------|
| `GET/PUT /api/settings`, `POST /api/settings/test` | Config Navidrome + test connexion |
| `POST /api/sync` | Synchronisation manuelle |
| `GET /api/library/search\|playlists\|albums\|artists\|genres` | Bibliothèque en cache |
| `GET/POST/PUT/DELETE /api/cards[...]` | CRUD cartes |
| `POST /api/cards/{id}/duplicate` | Dupliquer une carte |
| `PUT /api/cards/{id}/tracks/{n}` | Configurer une piste |
| `POST /api/cards/{id}/generate` | Génération automatique du mapping (§9) |
| `GET /api/cards/{id}/history` | Historique de la carte |
| `GET /api/stats/dashboard`, `/api/stats/top-tracks` | Dashboard & stats |
| `GET /stream/{card}/{track}` | **Streaming proxifié pour la Yoto** |

Documentation interactive OpenAPI : `http://localhost:8000/docs`.

## Lancer en local

Backend :

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload            # http://localhost:8000
```

Frontend (Vite proxifie `/api` et `/stream` vers le backend) :

```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

Ensuite, dans l'interface : **Réglages** → renseigner l'URL/identifiants
Navidrome et tester la connexion, puis **Dashboard → Synchroniser**, puis créer
une **Carte** et configurer ses pistes.

## Docker

```bash
docker compose up --build
# Interface web : http://localhost:8080
# API / OpenAPI  : http://localhost:8000/docs
# Données persistées dans ./data
```

### Authentification OIDC / Pocket ID

L'authentification est optionnelle et désactivée par défaut. Les pages, l'API et
la documentation sont protégées lorsqu'elle est active. Les URL `/stream/...`
restent publiques, mais exigent toujours leur jeton partagé afin que les lecteurs
Yoto puissent les lire.

1. Dans Pocket ID, créer un client OIDC avec cette URL de callback :
   `https://votre-domaine/api/auth/callback`.
2. Copier `.env.example` vers `.env`, renseigner le client ID, le secret et
   générer `YOTO_SESSION_SECRET` avec `openssl rand -hex 32`.
3. Passer `YOTO_AUTH_ENABLED=true`, puis reconstruire le backend.

Exemple :

```dotenv
YOTO_AUTH_ENABLED=true
YOTO_OIDC_ISSUER_URL=https://id.example.com
YOTO_OIDC_CLIENT_ID=...
YOTO_OIDC_CLIENT_SECRET=...
YOTO_OIDC_SCOPES=openid profile email
YOTO_SESSION_SECRET=...
```

Après une mise à jour ajoutant les pochettes, lancer une synchronisation de la
bibliothèque. Les pochettes sont alors affichées dans la recherche et l'éditeur.
Lors de la publication, Yoto les convertit automatiquement en icônes 16×16 ; le
résultat est mis en cache pour éviter de téléverser plusieurs fois la même image.

### Installation mobile (PWA)

L'interface est installable comme application dès qu'elle est servie en HTTPS.

- Android / Chrome : ouvrir le bridge puis choisir **Installer l'application**
  (le bouton **Installer** apparaît aussi dans l'en-tête lorsqu'il est disponible).
- iPhone / Safari : bouton **Partager**, puis **Sur l'écran d'accueil**.

Le shell et les ressources visuelles sont disponibles hors connexion. Les actions
sur la bibliothèque, les cartes et les flux audio nécessitent toujours le serveur.

## Tests

```bash
cd backend && source .venv/bin/activate
pytest
```

## Interface web

React + Vite + Mantine (`frontend/`). Pages : Dashboard (état + stats + synchro),
Bibliothèque (recherche instantanée), Cartes (CRUD + duplication), Édition de
carte (mapping des pistes, sélecteur de contenu multi-onglets, génération
automatique). Aucune logique métier côté front : tout passe par l'API REST.

## Prochaines étapes

- Intégration de l'API officielle Yoto (§18) : publication automatique des
  playlists MYO et des pistes `stream`.
- Chiffrement du mot de passe Navidrome au repos.
- Validation de la sémantique suivant/précédent sur matériel Yoto réel.
- Statistiques avancées (top morceaux/cartes, durée d'écoute) déjà amorcées côté
  API (`/api/stats/top-tracks`).
