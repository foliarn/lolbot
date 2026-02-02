# PROJET SPEC: Discord Bot LoL - Patch Watcher & Clash Scout

## 1. Vue d'ensemble du projet
Développement d'un bot Discord Python pour League of Legends avec deux fonctions principales :
1.  **Patch Watcher :** Surveillance automatique des mises à jour du jeu et notification par DM aux utilisateurs abonnés aux changements de statistiques de champions spécifiques.
2.  **Clash Scout :** Analyse prédictive d'une équipe adverse pour recommander des bans stratégiques basés sur l'historique et la maîtrise des joueurs.
3.  **Commandes utilitaires :** Stats de profil, Livegame, Review de match.

## 2. Stack Technique
* **Langage :** Python 3.10+
* **Discord Lib :** `discord.py` pour la gestion des Slash Commands (`/`).
* **Requêtes HTTP :** `aiohttp` (Obligatoire pour les requêtes asynchrones afin de ne pas bloquer le bot lors du scouting).
* **Base de données :** SQLite pour le stockage des utilisateurs, abonnements aux champions, et cache API.
* **API :** Riot Games API (Official) + Data Dragon (Static Data) + Web Scraping (Patch Notes Text).
* **Scraping :** BeautifulSoup4 pour extraire les liens des patch notes.

---

## 3. Structure du Projet

```
lolbot/
├── .env                          # Tokens Discord & Riot API (gitignored)
├── .gitignore                    # Ignorer .env, __pycache__, *.db
├── requirements.txt              # Dependencies Python
├── main.py                       # Point d'entrée du bot
├── config.py                     # Config centralisée (danger score weights, etc.)
├── database/
│   ├── __init__.py
│   ├── models.py                 # Schéma SQLite (Users, Subscriptions, Cache, etc.)
│   └── manager.py                # Gestionnaire DB (queries)
├── riot_api/
│   ├── __init__.py
│   ├── client.py                 # Client HTTP avec rate limiting
│   ├── endpoints.py              # Wrappers pour chaque endpoint Riot
│   └── data_dragon.py            # Gestion Data Dragon (versions, champion.json)
├── modules/
│   ├── __init__.py
│   ├── patch_watcher.py          # Tâche de fond (checks 8h/12h/16h/20h)
│   ├── clash_scout.py            # Logique de scouting + danger score
│   ├── stats.py                  # Commande /stats
│   ├── livegame.py               # Commande /livegame
│   └── review.py                 # Commande /review
├── cogs/
│   ├── __init__.py
│   ├── account_cog.py            # /link, /unlink, /accounts
│   ├── subscription_cog.py       # /subscribe, /unsubscribe
│   └── utility_cog.py            # /stats, /livegame, /review, /clash
└── utils/
    ├── __init__.py
    ├── embeds.py                 # Générateur d'embeds Discord
    ├── scraper.py                # Web scraping pour patch notes
    └── helpers.py                # Fonctions utilitaires (parsing RiotID, etc.)
```

---

## 4. Base de Données SQLite - Schéma Détaillé

### Table : `patch_version`
Stocke la version actuelle du patch pour le Patch Watcher.
```sql
CREATE TABLE patch_version (
    id INTEGER PRIMARY KEY,
    version TEXT NOT NULL,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table : `users`
Gère les comptes Discord et leurs comptes Riot (support multi-comptes/smurfs).
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT NOT NULL,
    riot_puuid TEXT NOT NULL,
    summoner_id TEXT,
    game_name TEXT NOT NULL,      -- RiotID
    tag_line TEXT NOT NULL,        -- Tag
    region TEXT DEFAULT 'EUW1',
    is_primary BOOLEAN DEFAULT 0,  -- Compte principal (utilisé par défaut)
    account_alias TEXT,             -- Nom du smurf (ex: "main", "smurf1")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(discord_id, riot_puuid)
);
```

### Table : `subscriptions`
Abonnements aux champions pour les notifications de patch.
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT NOT NULL,
    champion_name TEXT NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(discord_id, champion_name)
);
```

### Table : `api_cache`
Cache des requêtes API Riot avec expiration.
```sql
CREATE TABLE api_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,  -- Hash de la requête
    response_data TEXT NOT NULL,      -- JSON stringifié
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
```

**Stratégie de cache :**
- **Joueurs enregistrés** : Cache permanent (pas d'expiration).
- **Clash Scout** : Cache valide durant la session, puis suppression.
- **Stats live** : TTL défini dans `config.py`.

---

## 5. Configuration Éditable (`config.py`)

Toutes les variables sensibles pour le Danger Score et la détection de rôle sont centralisées ici.

```python
# Danger Score Configuration
DANGER_SCORE = {
    'OTP_MASTERY_THRESHOLD': 250000,        # Points de maîtrise pour OTP
    'OTP_SEASON_PERCENTAGE': 50,            # % des games cette saison sur ce champion
    'OTP_SCORE': 50,                        # Points bonus OTP

    'RECENT_GAMES_COUNT': 10,               # Nombre de games récentes à analyser
    'RECENT_SPAM_THRESHOLD': 5,             # Games jouées récemment sur ce champion
    'RECENT_SPAM_SCORE': 30,                # Points bonus spam récent

    'WINRATE_NEUTRAL': 50,                  # Winrate neutre (0 points)
    'WINRATE_SCORE_PER_PERCENT': 5,         # Points par % au-dessus de 50

    'SMURF_MASTERY_MAX': 50000,             # Mastery faible = possible smurf
    'SMURF_WR_THRESHOLD': 65,               # Winrate élevé (smurf)
    'SMURF_KDA_THRESHOLD': 3.5,             # KDA élevé (smurf)
    'SMURF_SCORE': 80,                      # Points bonus smurf détecté
}

# Role Detection
ROLE_DETECTION = {
    'HISTORY_GAMES': 10,                    # Games à analyser pour détecter rôle
    'ROLE_THRESHOLD': 60,                   # % pour considérer un rôle principal
}

# Patch Watcher
PATCH_CHECK_HOURS = [8, 12, 16, 20]         # Heures de vérification (mercredi)
PATCH_NOTES_URL = "https://www.leagueoflegends.com/fr-fr/news/game-updates/"

# Cache TTL (secondes)
CACHE_TTL = {
    'MATCH_HISTORY': 300,      # 5 min
    'LIVE_GAME': 60,           # 1 min
    'MASTERY': 3600,           # 1h
    'RANK': 1800,              # 30 min
    'REGISTERED_USER': None,   # Permanent
}

# Région supportée
DEFAULT_REGION = 'EUW1'
ROUTING_REGION = 'europe'  # Pour ACCOUNT-V1 et MATCH-V5
```

---

## 6. Module : Patch Watcher (Tâche de fond)

### Logique de fonctionnement
Le bot vérifie les patchs **tous les mercredis à 8h, 12h, 16h et 20h**.

1.  **Check Version :** Comparer la version locale (stockée en DB) avec `https://ddragon.leagueoflegends.com/api/versions.json`.
2.  **Fetch Data :** Si nouvelle version détectée, télécharger `champion.json` de Data Dragon.
3.  **Diffing Algorithm :** Comparer l'ancienne vs nouvelle version pour détecter les changements de stats (tous les sorts + stats de base).
4.  **Distribution :**
    * Pour chaque champion modifié, récupérer les abonnés : `SELECT discord_id FROM subscriptions WHERE champion_name = 'Ahri'`.
    * Envoyer un DM avec un **Embed Discord** contenant :
        - Changements de stats brutes (ex: "Q - Orbe Magique : Dégâts 60 → 70").
        - Lien vers le patch note officiel.

### Sources de données
* **Stats :** Data Dragon `champion.json`.
* **Lien patch notes :** Web scraping de `https://www.leagueoflegends.com/fr-fr/news/game-updates/` (BeautifulSoup4).

---

## 7. Commandes : Gestion de Compte

### `/link [RiotID] [Tag] [alias]`
Lie un compte Riot au compte Discord.
- `alias` (optionnel) : Nom du compte (ex: "main", "smurf1"). Si premier compte, devient automatiquement `is_primary=True`.
- Appels API : `ACCOUNT-V1` (RiotID → PUUID) puis `SUMMONER-V4` (PUUID → SummonerID).

### `/unlink [alias]`
Supprime un compte lié.

### `/accounts`
Affiche tous les comptes liés (indique le compte principal).

**Multi-comptes :**
- Par défaut, les commandes (`/stats`, `/review`, etc.) utilisent le **compte principal**.
- Pour utiliser un smurf : `/stats @smurf1` (spécifier l'alias).

---

## 8. Commandes : Abonnements

### `/subscribe [champion_name]`
Abonne l'utilisateur aux notifications de patch pour un champion.

### `/subscribe all`
Abonne l'utilisateur à **tous les champions**.
- Lors d'un patch, envoie un **récap condensé** :
  - "Buffs : Ahri, Zed, Jinx"
  - "Nerfs : Yasuo, Darius"
  - Lien vers le patch note complet.

### `/unsubscribe [champion_name]`
Désabonne d'un champion.

---

## 9. Module : Clash Scout (Intelligence & Algorithme)

### Commande
`/clash scout [Riot_ID] [Tag]` *(optionnel si compte lié, utilise le compte principal par défaut)*.

### Workflow API
1.  **Identity :** `ACCOUNT-V1` (RiotID → PUUID) → `SUMMONER-V4` (PUUID → SummonerID).
2.  **Team Discovery :** `CLASH-V1` (`/players/by-summoner/{id}`) pour récupérer le `teamId` et la liste des 5 coéquipiers.
    - Si pas d'équipe active : Message d'erreur.
    - Si équipe < 5 joueurs : Ignorer (ne devrait pas arriver).
3.  **Data Mining (Async - Parallélisé pour les 5 joueurs) :**
    * `CHAMPION-MASTERY-V4` : Top champions par points.
    * `MATCH-V5` : Récupérer les derniers MatchIDs (Filter: `queue=420` SoloQ, `queue=440` Flex, `queue=700` Clash).
    * `MATCH-V5 (Details)` : Analyser les matchs pour extraire : champion joué, rôle, résultat, KDA.
    * Si profil privé ou pas d'historique : Ignorer ce joueur.

### Détection de Rôle
- Analyser les **10 dernières games en SoloQ/Flex** + **dernières games Clash**.
- Si joueur joue > 60% d'un rôle : Rôle principal.
- Si joueur "flex picker" (plusieurs rôles) : **Grouper par rôle détecté**.
  - Exemple : "Top (60%) : Aatrox, Jax / Mid (40%) : Zed".

### Algorithme de "Danger Score"
Pour chaque champion trouvé, calculer un score (valeurs éditables dans `config.py`) :

- **Critère OTP :**
  - Mastery > 250k points **OU** > 50% des games de cette saison sur ce champion.
  - Score : **+50 points**.

- **Critère Récence :**
  - Joué > 5 fois dans les 10 derniers matchs.
  - Score : **+30 points**.

- **Critère Winrate :**
  - Winrate 50% = 0 points.
  - Chaque % au-dessus de 50 = **+5 points** (ex: 52% WR = +10 points).

- **Critère Smurf :**
  - Mastery < 50k **ET** WR > 65% **ET** KDA > 3.5.
  - Score : **+80 points**.

### Output (Embed Discord)
Afficher pour l'équipe adverse :
1.  **Top 3 Bans recommandés** (par Danger Score) avec la raison :
    - Ex: "Zed (180 pts) - OTP + Smurf détecté"
    - Ex: "Maokai (120 pts) - Spam récent + 60% WR"
2.  **Avertissements par Lane** (si joueur flex picker) :
    - Ex: "Toplaner - Top (60%): Aatrox, Jax / Mid (40%): Zed"
3.  **Profils détectés** :
    - Ex: "ADC - Joue uniquement Jinx/Caitlyn (OTP Bot)"

---

## 10. Commandes Utilitaires

### `/stats [RiotID] [@alias]`
Affiche Rang Solo/Flex (`LEAGUE-V4`) + Top 3 Mastery (`CHAMPION-MASTERY-V4`).
- Si `RiotID` non fourni : Utilise le compte principal lié.
- Si `@alias` fourni : Utilise le smurf spécifié.

### `/livegame [RiotID] [@alias]`
Récupère la partie en cours (`SPECTATOR-V4`).
- Affiche les 10 joueurs : champions, rangs, winrates récents.

### `/review [@alias]`
Analyse la dernière partie du compte principal (ou alias spécifié) via `MATCH-V5`.
- Métriques : Vision score, CS/min, comparaison vs opposant direct.
- Nécessite un compte lié (`/link`).

---

## 11. Contraintes & Gestion API

### Rate Limiting (Crucial)
* Clé Dev : **20 req/1s** et **100 req/2min**.
* **Stratégie :**
  - Implémenter un gestionnaire de Rate Limit (Token Bucket ou queue avec délais) dans `riot_api/client.py`.
  - Pour le Clash Scout, prioriser les données critiques et réduire l'historique si limite approchée.

### Gestion d'erreurs
- **API Riot down :** Changer le statut du bot Discord en "Absent" (idle status).
- **Commande sans compte lié :** Message explicite demandant de faire `/link` d'abord.
- **Rate limit atteint :** Message temporaire à l'utilisateur + retry automatique avec backoff.

### Environnement (`.env`)
```env
DISCORD_BOT_TOKEN=your_discord_token
RIOT_API_KEY=your_riot_api_key
```

---

## 12. Ordre d'Implémentation

1.  **Setup initial** : `.env`, `requirements.txt`, structure de dossiers.
2.  **Database** : `models.py` + `manager.py` (schéma SQLite).
3.  **Riot API Client** : `client.py` (rate limiting) + `endpoints.py` (wrappers basiques).
4.  **Commandes Account** : `/link`, `/unlink`, `/accounts` (pour pouvoir tester l'API).
5.  **Commande `/stats`** : Simple et permet de valider le flow API + cache.
6.  **Patch Watcher** : Version check + diff algorithm + notifications.
7.  **Subscriptions** : `/subscribe`, `/subscribe all`, `/unsubscribe`.
8.  **Clash Scout** : Logique complexe (scouting + danger score + détection rôle).
9.  **Commandes restantes** : `/livegame`, `/review`.

---

## 13. Features Bonus

- **Multi-comptes (Smurfs) :** Support complet avec système d'alias et compte principal.
- **Subscribe All :** Récap condensé de l'entièreté du patch (Buffs/Nerfs + lien).
- **Détection de profils flex :** Affichage groupé par rôle pour les joueurs multi-rôles.
- **Cache intelligent :** Permanent pour les joueurs enregistrés, temporaire pour le scouting.
