#(THIS DISCORD BOT IS 100% VIBE CODED BY CLAUDE CODE (OPUS 4.5) -- IM TRYING OUT TO SEE THE EXTENT OF VIBE CODING ON A SIMPLE PROJECT))

# LoL Bot - Patch Watcher & Clash Scout

Bot Discord Python pour League of Legends avec surveillance de patchs et analyse d'équipes Clash.

## Fonctionnalités

### 🔔 Patch Watcher
- Surveillance automatique des mises à jour du jeu
- Notifications par DM pour les changements de champions spécifiques
- Récapitulatif complet de patch disponible
- Vérifications les mercredis à 8h, 12h, 16h et 20h

### ⚔️ Clash Scout
- Analyse prédictive d'une équipe adverse
- Recommandations de bans stratégiques basées sur :
  - Maîtrise des champions (OTP detection)
  - Historique récent de jeu
  - Winrate et KDA
  - Détection de smurfs
- Analyse par rôle avec support des flex pickers

### 📊 Commandes Utilitaires
- `/stats` : Affiche rang et maîtrises
- `/livegame` : Partie en cours avec détails des joueurs
- `/review` : Analyse de la dernière partie jouée

## Installation

### Prérequis
- Python 3.10+
- Un compte Discord Developer
- Une clé API Riot Games

### 1. Cloner le projet
```bash
git clone <url-du-repo>
cd lolbot
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Configuration
Créer un fichier `.env` à la racine du projet :
```env
DISCORD_BOT_TOKEN=ton_token_discord
RIOT_API_KEY=ta_cle_riot_api
```

#### Obtenir un token Discord
1. Aller sur https://discord.com/developers/applications
2. Créer une nouvelle application
3. Aller dans "Bot" et créer un bot
4. Copier le token

#### Obtenir une clé API Riot
1. Aller sur https://developer.riotgames.com/
2. Se connecter avec ton compte Riot
3. Copier la clé de développement (renouveler toutes les 24h)

### 4. Inviter le bot sur ton serveur
1. Dans le Developer Portal, aller dans "OAuth2" > "URL Generator"
2. Sélectionner les scopes : `bot` et `applications.commands`
3. Permissions du bot : `Send Messages`, `Embed Links`, `Read Message History`
4. Copier l'URL générée et l'ouvrir dans un navigateur

### 5. Lancer le bot
```bash
python main.py
```

## Utilisation

### Gestion de compte

#### Lier un compte Riot
```
/link riot_id:Faker tag:KR1
```

Pour ajouter un smurf :
```
/link riot_id:MonSmurf tag:EUW alias:smurf1
```

#### Voir ses comptes liés
```
/accounts
```

#### Délier un compte
```
/unlink alias:smurf1
```

### Abonnements aux patchs

#### S'abonner à un champion
```
/subscribe champion:Ahri
```

#### S'abonner au récapitulatif complet
```
/subscribe champion:all
```

#### Voir ses abonnements
```
/subscriptions
```

#### Se désabonner
```
/unsubscribe champion:Ahri
```

### Commandes de statistiques

#### Voir les stats d'un joueur
```
/stats
/stats riot_id:Faker tag:KR1
/stats alias:smurf1
```

#### Voir une partie en cours
```
/livegame
/livegame riot_id:Faker tag:KR1
```

#### Analyser sa dernière partie
```
/review
/review alias:smurf1
```

### Clash Scout

#### Analyser une équipe Clash
```
/clash riot_id:EnemyPlayer tag:EUW
```

Le bot retournera :
- Top 3 bans recommandés avec scores et raisons
- Analyse par joueur/rôle
- Détection des profils (OTP, Flex Picker, etc.)

## Configuration Avancée

Les paramètres du Danger Score et de la détection de rôle sont dans `config.py` :

```python
DANGER_SCORE = {
    'OTP_MASTERY_THRESHOLD': 250000,    # Points pour OTP
    'OTP_SEASON_PERCENTAGE': 50,        # % de games pour OTP
    'OTP_SCORE': 50,                    # Points bonus OTP
    'RECENT_GAMES_COUNT': 10,           # Games récentes analysées
    'RECENT_SPAM_THRESHOLD': 5,         # Games pour spam récent
    'RECENT_SPAM_SCORE': 30,            # Points bonus spam
    'WINRATE_NEUTRAL': 50,              # WR neutre
    'WINRATE_SCORE_PER_PERCENT': 5,     # Points par % WR
    'SMURF_MASTERY_MAX': 50000,         # Mastery max pour smurf
    'SMURF_WR_THRESHOLD': 65,           # WR smurf
    'SMURF_KDA_THRESHOLD': 3.5,         # KDA smurf
    'SMURF_SCORE': 80,                  # Points bonus smurf
}
```

## Structure du Projet

```
lolbot/
├── main.py                 # Point d'entrée
├── config.py               # Configuration
├── database/               # Gestion SQLite
├── riot_api/               # Client API Riot
├── modules/                # Logique métier
├── cogs/                   # Commandes Discord
└── utils/                  # Utilitaires
```

## Limitations

### Clé API de développement
- 20 requêtes/seconde
- 100 requêtes/2 minutes
- Renouvelée toutes les 24h

Le bot implémente un rate limiter automatique.

### Région
Actuellement configuré pour **EUW** uniquement.

## Troubleshooting

### Le bot ne répond pas
1. Vérifier que le bot est bien en ligne sur Discord
2. Vérifier les logs dans le terminal
3. Vérifier que les commandes slash sont synchronisées (`/tree sync`)

### Erreur API Riot
1. Vérifier que la clé API est valide (renouveler si > 24h)
2. Vérifier le rate limiting dans les logs
3. Vérifier que le compte Riot existe sur EUW

### Notifications de patch non reçues
1. Vérifier les abonnements avec `/subscriptions`
2. Vérifier que c'est bien mercredi et une heure de check (8h, 12h, 16h, 20h)
3. Vérifier les logs du Patch Watcher

## Contribution

Les contributions sont les bienvenues ! N'hésite pas à ouvrir une issue ou une pull request.

## Licence

Ce projet est sous licence MIT.
