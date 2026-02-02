# PROJET SPEC: Discord Bot LoL - Patch Watcher & Clash Scout

## 1. Vue d'ensemble du projet
Développement d'un bot Discord Python pour League of Legends avec deux fonctions principales :
1.  **Patch Watcher :** Surveillance automatique des mises à jour du jeu et notification par DM aux utilisateurs abonnés aux changements de statistiques de champions spécifiques.
2.  **Clash Scout :** Analyse prédictive d'une équipe adverse pour recommander des bans stratégiques basés sur l'historique et la maîtrise des joueurs.
3.  **Commandes utilitaires :** Stats de profil, Livegame, Review de match.

## 2. Stack Technique
* **Langage :** Python 3.10+
* **Discord Lib :** `discord.py` (ou `pycord`) pour la gestion des Slash Commands (`/`).
* **Requêtes HTTP :** `aiohttp` (Obligatoire pour les requêtes asynchrones afin de ne pas bloquer le bot lors du scouting).
* **Base de données :** SQLite (MVP) ou MongoDB. Stockage des utilisateurs, abonnements aux champions, et cache API.
* **API :** Riot Games API (Official) + Data Dragon (Static Data) + Web Scraping (Patch Notes Text).

---

## 3. Module : Patch Watcher (Tâche de fond)

### Logique de fonctionnement
Le bot doit exécuter une boucle de polling (ex: toutes les 30 min).
1.  **Check Version :** Comparer la version actuelle locale avec `https://ddragon.leagueoflegends.com/api/versions.json`.
2.  **Fetch Data :** Si nouvelle version, télécharger `champion.json` (Data Dragon).
3.  **Diffing Algorithm :** Comparer les objets JSON (Ancienne vs Nouvelle version) pour détecter les changements de stats (Dégâts, CD, Mana, etc.).
4.  **Distribution :**
    * Vérifier dans la DB : `SELECT user_id FROM subscriptions WHERE champion = 'Ahri'`.
    * Envoyer un DM formaté avec les changements précis.

### Sources de données
* **Stats :** Data Dragon JSON.
* **Text/Context :** Scraper `https://www.leagueoflegends.com/fr-fr/news/game-updates/` pour récupérer le lien de l'article (car l'API ne donne pas le texte "humain").

---

## 4. Module : Clash Scout (Intelligence & Algorithme)

### Commande
`/clash scout [Riot_ID] [Tag]`

### Workflow API
1.  **Identity :** `ACCOUNT-V1` (RiotID -> PUUID) -> `SUMMONER-V4` (PUUID -> SummonerID).
2.  **Team Discovery :** `CLASH-V1` (`/players/by-summoner/{id}`) pour récupérer le `teamId` et la liste des 5 coéquipiers.
3.  **Data Mining (Async - Parallélisé pour les 5 joueurs) :**
    * `CHAMPION-MASTERY-V4` : Top 5 champions par points.
    * `MATCH-V5` : Récupérer les 20 derniers MatchIDs (Filter: `queue=420` pour SoloQ, `queue=440` pour Flex, `queue=700` pour Clash).
    * `MATCH-V5 (Details)` : Analyser les matchs pour extraire le champion joué, le résultat, et le KDA.

### Algorithme de "Danger Score" (Ban Recommendation)
Pour chaque champion trouvé, calculer un score :
* **Critère OTP :** Mastery > 500k points (+Score).
* **Critère Récence :** Joué > 5 fois dans les 20 derniers matchs (+Score).
* **Critère Performance :** Winrate > 60% sur ce champion (+Score).
* **Critère Smurf :** Basse mastery mais très haut WR/KDA récent (+Score critique).

### Output (Embed Discord)
Afficher pour l'équipe adverse :
1.  **Top 3 Bans recommandés** (avec la raison : ex "OTP Zed", "Spam Maokai récent").
2.  Avertissements par Lane (ex: "Toplaner joue uniquement Tanks").

---

## 5. Commandes Utilitaires

* `/stats [RiotID]` : Affiche Rang Solo/Flex (`LEAGUE-V4`) + Top 3 Mastery.
* `/livegame [RiotID]` : Récupère la partie en cours (`SPECTATOR-V4`). Affiche les champions, rangs et Winrates des 10 joueurs.
* `/review` : Analyse la dernière partie (`MATCH-V5`) et donne des métriques clés (Vision score, CS/min vs Opposant).

---

## 6. Contraintes & Gestion API

### Rate Limiting (Crucial)
* Clé Dev : 20 req/1s et 100 req/2min.
* **Stratégie :** Implémenter un gestionnaire de Rate Limit (Bucket Token ou décorateur d'attente).
* Pour le Clash Scout, prioriser les données (réduire l'historique analysé si on approche de la limite).

### Base de données (Schéma simplifié)
* `Users` : { discord_id, riot_puuid, region }
* `Subscriptions` : { user_id, champion_name }
* `Cache` : { request_hash, json_response, timestamp } (Pour éviter de spammer l'API Riot sur des requêtes identiques).

---

## 7. Instructions pour l'IA (Claude)
1.  Commence par créer la structure du projet et la connexion API avec gestion des erreurs (403, 429).
2.  Implémente la commande `/clash scout` en utilisant `asyncio.gather` pour paralléliser les appels API des 5 joueurs.
3.  Implémente ensuite le module de Patch Watcher avec une tâche `discord.ext.tasks.loop`.
