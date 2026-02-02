# Documentation Technique

Documentation complète pour développeurs.

## Architecture

### Vue d'ensemble

```
User (Discord) -> Bot (main.py) -> Cogs -> Modules -> API Riot
                                        -> Database (SQLite)
                                        -> Data Dragon
```

### Flux de données

1. **Commande Discord** : L'utilisateur tape `/stats`
2. **Cog** : `utility_cog.py` intercepte la commande
3. **Module** : `stats.py` traite la logique métier
4. **API Client** : `riot_api/client.py` gère le rate limiting
5. **Endpoints** : `riot_api/endpoints.py` appelle l'API Riot
6. **Cache** : Vérifie `database/manager.py` avant la requête
7. **Response** : Retourne un embed généré par `utils/embeds.py`

## Composants

### 1. Database Manager (`database/manager.py`)

Gère toutes les opérations SQLite de manière asynchrone.

**Méthodes principales :**
- `add_user()` : Ajoute un compte Riot lié
- `get_user()` : Récupère un compte (par alias ou principal)
- `add_subscription()` : Ajoute un abonnement
- `get_cache()` / `set_cache()` : Gestion du cache API

**Schéma DB :**
```sql
users: discord_id, riot_puuid, summoner_id, is_primary, account_alias
subscriptions: discord_id, champion_name
api_cache: cache_key, response_data, expires_at
patch_version: version, checked_at
```

### 2. Riot API Client (`riot_api/client.py`)

Client HTTP asynchrone avec rate limiting Token Bucket.

**Rate Limiter :**
- 2 buckets : 1 seconde (20 tokens) et 2 minutes (100 tokens)
- Recharge automatique
- Attente automatique si limite atteinte

**Utilisation :**
```python
data = await client.request(
    url="https://...",
    cache_key="unique_key",
    cache_ttl=300  # 5 minutes
)
```

### 3. Data Dragon (`riot_api/data_dragon.py`)

Gère les données statiques (champions, versions).

**Fonctions clés :**
- `get_latest_version()` : Dernière version du jeu
- `fetch_champion_data()` : Télécharge champion.json
- `compare_versions()` : Diff entre deux versions
- `get_champion_name_by_id()` : Convertit ID -> Nom

### 4. Patch Watcher (`modules/patch_watcher.py`)

Tâche de fond qui vérifie les patchs.

**Workflow :**
1. Loop toutes les heures avec `@tasks.loop`
2. Vérifie si c'est mercredi et heure de check
3. Compare version DB vs version Data Dragon
4. Si nouvelle version : `compare_versions()`
5. Notifie les abonnés par DM

**Personnalisation :**
```python
# Dans config.py
PATCH_CHECK_HOURS = [8, 12, 16, 20]  # Modifier ici
```

### 5. Clash Scout (`modules/clash_scout.py`)

Analyse complexe d'équipe Clash.

**Algorithme :**

1. **Récupération des données (parallélisée) :**
   ```python
   player_analyses = await asyncio.gather(
       *[self._analyze_player(p) for p in players]
   )
   ```

2. **Pour chaque joueur :**
   - Masteries (top 10)
   - Historique de matchs (SoloQ + Flex + Clash)
   - Détails de chaque match (KDA, champion, rôle)

3. **Calcul du Danger Score :**
   ```python
   score = 0
   if mastery > OTP_THRESHOLD: score += OTP_SCORE
   if recent_games > SPAM_THRESHOLD: score += SPAM_SCORE
   if winrate > NEUTRAL: score += (wr - 50) * WR_MULTIPLIER
   if smurf_detected: score += SMURF_SCORE
   ```

4. **Détection de rôle :**
   - Compte les rôles dans les 10 dernières games
   - Si > 60% sur un rôle : rôle principal
   - Sinon : flex picker avec distribution

5. **Recommandations de bans :**
   - Agrège tous les champions dangereux
   - Supprime les doublons (garde le score max)
   - Retourne le top 3

**Optimisations possibles :**
- Réduire `RECENT_GAMES_COUNT` si rate limit
- Augmenter les seuils de score pour moins de faux positifs

## Cogs (Commandes Discord)

### Structure d'un Cog

```python
class MyCog(commands.Cog):
    def __init__(self, bot, dependencies):
        self.bot = bot
        self.dep = dependencies

    @app_commands.command(name="mycommand")
    async def mycommand(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Logique
        await interaction.followup.send("Résultat")

async def setup(bot):
    await bot.add_cog(MyCog(bot, bot.dep))
```

### Bonnes pratiques

1. **Toujours defer** pour les commandes longues :
   ```python
   await interaction.response.defer(ephemeral=True)
   ```

2. **Gestion d'erreurs** :
   ```python
   embed, error = await module.do_something()
   if error:
       await interaction.followup.send(error, ephemeral=True)
   else:
       await interaction.followup.send(embed=embed)
   ```

3. **Descriptions claires** :
   ```python
   @app_commands.describe(
       riot_id="Ton RiotID (ex: Faker)",
       tag="Ton tag (ex: KR1)"
   )
   ```

## Cache Strategy

### TTL par type de données

```python
CACHE_TTL = {
    'MATCH_HISTORY': 300,      # 5 min (peut changer rapidement)
    'LIVE_GAME': 60,           # 1 min (très volatile)
    'MASTERY': 3600,           # 1h (stable)
    'RANK': 1800,              # 30 min (change après games)
    'REGISTERED_USER': None,   # Permanent (ne change jamais)
}
```

### Invalidation du cache

**Automatique :**
- `clear_expired_cache()` : Supprime les entrées expirées

**Manuelle :**
```python
await db.clear_cache_by_pattern("match_history:puuid:xyz")
```

## Gestion des erreurs API Riot

### Codes de retour

- `200` : Succès
- `404` : Ressource introuvable (compte, match, etc.)
- `429` : Rate limit atteint → Retry après X secondes
- `403` : Clé API invalide
- `503` : Service indisponible

### Stratégie de retry

```python
if response.status == 429:
    retry_after = int(response.headers.get('Retry-After', 1))
    await asyncio.sleep(retry_after)
    return await self.request(url, use_rate_limit=False)
```

## Performance

### Requêtes parallèles

**Bon exemple (Clash Scout) :**
```python
# Analyser 5 joueurs en parallèle
analyses = await asyncio.gather(
    *[analyze_player(p) for p in players]
)
```

**Mauvais exemple :**
```python
# Séquentiel, très lent
for player in players:
    analysis = await analyze_player(player)
```

### Optimisations

1. **Batch requests** quand possible
2. **Cache agressif** pour données stables
3. **Limiter les appels** dans les loops

## Tests

### Tester une commande

```python
# Terminal 1 : Lancer le bot
python main.py

# Discord : Tester
/link riot_id:TestUser tag:EUW
/stats
```

### Debug mode

```python
# Dans main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Mock API (pour tests sans rate limit)

```python
# Créer riot_api/mock_client.py
class MockAPIClient:
    async def get_account_by_riot_id(self, name, tag):
        return {'puuid': 'mock_puuid', 'gameName': name}
```

## Ajout de fonctionnalités

### Ajouter une nouvelle commande

1. **Créer le module** (`modules/new_feature.py`) :
   ```python
   class NewFeature:
       def __init__(self, api, db):
           self.api = api
           self.db = db

       async def do_something(self):
           # Logique
           return result
   ```

2. **Ajouter au bot** (`main.py`) :
   ```python
   self.new_feature = NewFeature(self.riot_api, self.db_manager)
   ```

3. **Créer la commande** (dans un cog) :
   ```python
   @app_commands.command(name="newcmd")
   async def newcmd(self, interaction):
       result = await self.bot.new_feature.do_something()
       await interaction.response.send_message(result)
   ```

4. **Redémarrer le bot**

### Ajouter un nouveau endpoint Riot

Dans `riot_api/endpoints.py` :
```python
async def get_new_endpoint(self, param: str) -> Optional[Dict]:
    url = f"{self.platform_base}/lol/endpoint/v1/{param}"
    cache_key = f"new_endpoint:{param}"
    return await self.client.request(url, cache_key, CACHE_TTL['CUSTOM'])
```

## Déploiement

### Production

1. **Utiliser une clé API production** (non-dev)
2. **Configurer un service systemd** :
   ```ini
   [Unit]
   Description=LoL Discord Bot
   After=network.target

   [Service]
   Type=simple
   User=lolbot
   WorkingDirectory=/home/lolbot/lolbot
   ExecStart=/home/lolbot/lolbot/venv/bin/python main.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Logs avec rotation** :
   ```python
   import logging
   from logging.handlers import RotatingFileHandler

   handler = RotatingFileHandler('bot.log', maxBytes=10000000, backupCount=5)
   logging.basicConfig(handlers=[handler], level=logging.INFO)
   ```

### Monitoring

- **Uptime** : https://uptimerobot.com/
- **Logs** : Vérifier `bot.log`
- **Base de données** : Sauvegarder `lolbot.db` régulièrement

## Contribution

1. Fork le repo
2. Créer une branche : `git checkout -b feature/ma-feature`
3. Commit : `git commit -m "Add: nouvelle feature"`
4. Push : `git push origin feature/ma-feature`
5. Ouvrir une Pull Request

## Support

- Issues GitHub : Pour les bugs
- Discussions : Pour les questions
