# 📋 Project Summary - LoL Discord Bot

## ✅ Statut du Projet

**Version :** 1.0.0
**Statut :** Prêt pour le développement et les tests
**Date :** 2026-02-02

## 📦 Fichiers Créés

### Configuration (4 fichiers)
- ✅ `.env.example` - Template de configuration
- ✅ `.gitignore` - Fichiers à ignorer
- ✅ `requirements.txt` - Dépendances Python
- ✅ `config.py` - Configuration centralisée

### Documentation (5 fichiers)
- ✅ `CLAUDE.md` - Spécifications complètes du projet
- ✅ `README.md` - Guide d'utilisation général
- ✅ `QUICKSTART.md` - Démarrage rapide
- ✅ `TECHNICAL.md` - Documentation technique
- ✅ `TODO.md` - Fonctionnalités futures

### Core (1 fichier)
- ✅ `main.py` - Point d'entrée du bot

### Database (3 fichiers)
- ✅ `database/__init__.py`
- ✅ `database/models.py` - Schéma SQLite
- ✅ `database/manager.py` - Gestionnaire DB asynchrone

### Riot API (4 fichiers)
- ✅ `riot_api/__init__.py`
- ✅ `riot_api/client.py` - Client HTTP + Rate Limiting
- ✅ `riot_api/endpoints.py` - Wrappers API Riot
- ✅ `riot_api/data_dragon.py` - Données statiques

### Modules (6 fichiers)
- ✅ `modules/__init__.py`
- ✅ `modules/patch_watcher.py` - Surveillance des patchs
- ✅ `modules/clash_scout.py` - Analyse Clash
- ✅ `modules/stats.py` - Statistiques joueur
- ✅ `modules/livegame.py` - Parties en cours
- ✅ `modules/review.py` - Analyse de match

### Cogs (4 fichiers)
- ✅ `cogs/__init__.py`
- ✅ `cogs/account_cog.py` - Commandes /link, /unlink, /accounts
- ✅ `cogs/subscription_cog.py` - Commandes /subscribe, /unsubscribe
- ✅ `cogs/utility_cog.py` - Commandes /stats, /livegame, /review, /clash

### Utils (4 fichiers)
- ✅ `utils/__init__.py`
- ✅ `utils/embeds.py` - Générateur d'embeds Discord
- ✅ `utils/scraper.py` - Web scraping patch notes
- ✅ `utils/helpers.py` - Fonctions utilitaires

### Scripts (1 fichier)
- ✅ `run.sh` - Script de lancement automatique

## 🎯 Fonctionnalités Implémentées

### ✅ Patch Watcher
- [x] Vérification automatique les mercredis (8h, 12h, 16h, 20h)
- [x] Comparaison des versions via Data Dragon
- [x] Diffing algorithm pour détecter les changements
- [x] Notifications DM par champion
- [x] Récapitulatif complet (buffs/nerfs)
- [x] Web scraping pour URL du patch note

### ✅ Gestion de Comptes
- [x] Liaison compte Riot → Discord
- [x] Support multi-comptes (smurfs)
- [x] Système d'alias
- [x] Compte principal automatique
- [x] Commandes /link, /unlink, /accounts

### ✅ Abonnements
- [x] Subscribe par champion
- [x] Subscribe all (récap complet)
- [x] Unsubscribe
- [x] Liste des abonnements
- [x] Validation des noms de champions

### ✅ Stats
- [x] Affichage du rang Solo/Duo et Flex
- [x] Top 3 maîtrises
- [x] Niveau du summoner
- [x] Support compte lié ou RiotID direct

### ✅ Live Game
- [x] Récupération partie en cours
- [x] Affichage par équipe (Bleue/Rouge)
- [x] Champions et joueurs
- [x] Mode de jeu et durée

### ✅ Review
- [x] Analyse de la dernière partie
- [x] KDA, CS, Vision Score
- [x] Dégâts et Or
- [x] Durée de partie
- [x] Résultat (Victory/Defeat)

### ✅ Clash Scout
- [x] Récupération de l'équipe Clash
- [x] Analyse de 5 joueurs en parallèle
- [x] Calcul du Danger Score avec 4 critères :
  - [x] OTP (mastery + % games saison)
  - [x] Récence (spam récent)
  - [x] Winrate
  - [x] Smurf detection
- [x] Détection de rôle (principal + flex pickers)
- [x] Top 3 bans recommandés
- [x] Analyse par joueur/rôle

### ✅ Infrastructure
- [x] Rate Limiting Token Bucket (20/s, 100/2min)
- [x] Cache SQLite avec expiration
- [x] Requêtes asynchrones (aiohttp)
- [x] Gestion d'erreurs API
- [x] Retry automatique sur 429

## 🔧 Configuration

### Variables Éditables (config.py)

```python
# Danger Score
DANGER_SCORE = {
    'OTP_MASTERY_THRESHOLD': 250000,
    'OTP_SEASON_PERCENTAGE': 50,
    'OTP_SCORE': 50,
    'RECENT_GAMES_COUNT': 10,
    'RECENT_SPAM_THRESHOLD': 5,
    'RECENT_SPAM_SCORE': 30,
    'WINRATE_NEUTRAL': 50,
    'WINRATE_SCORE_PER_PERCENT': 5,
    'SMURF_MASTERY_MAX': 50000,
    'SMURF_WR_THRESHOLD': 65,
    'SMURF_KDA_THRESHOLD': 3.5,
    'SMURF_SCORE': 80,
}

# Rôles
ROLE_DETECTION = {
    'HISTORY_GAMES': 10,
    'ROLE_THRESHOLD': 60,
}

# Cache TTL
CACHE_TTL = {
    'MATCH_HISTORY': 300,
    'LIVE_GAME': 60,
    'MASTERY': 3600,
    'RANK': 1800,
    'REGISTERED_USER': None,
}
```

## 📊 Schéma de Base de Données

### Table: users
```sql
id, discord_id, riot_puuid, summoner_id, game_name, tag_line,
region, is_primary, account_alias, created_at
```

### Table: subscriptions
```sql
id, discord_id, champion_name, subscribed_at
```

### Table: api_cache
```sql
id, cache_key, response_data, cached_at, expires_at
```

### Table: patch_version
```sql
id, version, checked_at
```

## 🚀 Démarrage

### Option 1 : Script automatique
```bash
./run.sh
```

### Option 2 : Manuel
```bash
cp .env.example .env
# Éditer .env avec vos tokens
pip install -r requirements.txt
python main.py
```

## 📝 Commandes Disponibles

| Commande | Description |
|----------|-------------|
| `/link` | Lier un compte Riot |
| `/unlink` | Délier un compte |
| `/accounts` | Voir ses comptes liés |
| `/subscribe` | S'abonner à un champion |
| `/unsubscribe` | Se désabonner |
| `/subscriptions` | Voir ses abonnements |
| `/stats` | Stats d'un joueur |
| `/livegame` | Partie en cours |
| `/review` | Analyser dernière partie |
| `/clash` | Scout équipe Clash |

## 🔍 Prochaines Étapes

### Avant de lancer en production
1. ✅ Créer un fichier `.env` avec les tokens
2. ✅ Tester toutes les commandes
3. ⬜ Vérifier les logs pour les erreurs
4. ⬜ Tester le Patch Watcher (mercredi)
5. ⬜ Obtenir une clé API Riot production (non-dev)

### Tests recommandés
- `/link` avec un compte valide
- `/stats` pour vérifier l'API
- `/subscribe` à un champion
- `/clash` si équipe active
- Attendre mercredi pour tester Patch Watcher

### Optimisations futures
- Voir `TODO.md` pour la liste complète
- Multi-régions (NA, KR, etc.)
- Tests unitaires
- Déploiement Docker

## 📖 Documentation

| Fichier | Contenu |
|---------|---------|
| `README.md` | Guide général d'utilisation |
| `QUICKSTART.md` | Installation en 5 minutes |
| `TECHNICAL.md` | Documentation développeur |
| `TODO.md` | Fonctionnalités futures |
| `CLAUDE.md` | Spécifications complètes |

## 💡 Notes Importantes

1. **Clé API Dev** : Limitée à 24h, renouveler quotidiennement
2. **Rate Limit** : 20/s et 100/2min, géré automatiquement
3. **Région** : EUW uniquement pour le moment
4. **Cache** : SQLite local, performances suffisantes pour < 1000 users
5. **Patch Watcher** : Ne vérifie que les mercredis

## 🐛 Troubleshooting

### Bot ne démarre pas
- Vérifier `.env` avec tokens valides
- Vérifier Python 3.10+
- Installer dépendances : `pip install -r requirements.txt`

### Commandes invisibles
- Attendre 1 minute pour sync
- Redémarrer Discord
- Vérifier logs : `Bot prêt!`

### Erreur API Riot
- Vérifier clé API sur developer.riotgames.com
- Renouveler si > 24h
- Vérifier rate limiting dans logs

## ✨ Crédits

**Développement :** Claude Sonnet 4.5
**Stack :** Python 3.10+, discord.py, aiohttp, SQLite
**APIs :** Riot Games API, Data Dragon

---

**🎮 Prêt à lancer le bot ? Consulte QUICKSTART.md !**
