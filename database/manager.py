"""
Gestionnaire de base de données SQLite avec support asynchrone
"""
import aiosqlite
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from .models import SCHEMA


class DatabaseManager:
    def __init__(self, db_path: str = "lolbot.db"):
        self.db_path = db_path

    async def initialize(self):
        """Initialise la base de données et crée les tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    # ==================== Users ====================

    async def add_user(
        self,
        discord_id: str,
        riot_puuid: str,
        summoner_id: str,
        game_name: str,
        tag_line: str,
        region: str = "EUW1",
        account_alias: Optional[str] = None
    ) -> bool:
        """Ajoute un compte Riot pour un utilisateur Discord"""
        async with aiosqlite.connect(self.db_path) as db:
            # Vérifier si c'est le premier compte
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE discord_id = ?",
                (discord_id,)
            )
            count = (await cursor.fetchone())[0]
            is_primary = 1 if count == 0 else 0

            try:
                await db.execute(
                    """INSERT INTO users
                    (discord_id, riot_puuid, summoner_id, game_name, tag_line, region, is_primary, account_alias)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (discord_id, riot_puuid, summoner_id, game_name, tag_line, region, is_primary, account_alias)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_user(self, discord_id: str, alias: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Récupère un compte utilisateur (principal par défaut)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if alias:
                cursor = await db.execute(
                    "SELECT * FROM users WHERE discord_id = ? AND account_alias = ?",
                    (discord_id, alias)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM users WHERE discord_id = ? AND is_primary = 1",
                    (discord_id,)
                )

            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_users(self, discord_id: str) -> List[Dict[str, Any]]:
        """Récupère tous les comptes d'un utilisateur Discord"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE discord_id = ? ORDER BY is_primary DESC, created_at ASC",
                (discord_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def remove_user(self, discord_id: str, alias: Optional[str] = None) -> bool:
        """Supprime un compte utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            if alias:
                await db.execute(
                    "DELETE FROM users WHERE discord_id = ? AND account_alias = ?",
                    (discord_id, alias)
                )
            else:
                # Supprime le compte principal
                await db.execute(
                    "DELETE FROM users WHERE discord_id = ? AND is_primary = 1",
                    (discord_id,)
                )

            await db.commit()

            # Si on a supprimé le compte principal, promouvoir le plus ancien
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE discord_id = ?",
                (discord_id,)
            )
            count = (await cursor.fetchone())[0]

            if count > 0:
                await db.execute(
                    """UPDATE users SET is_primary = 1
                    WHERE discord_id = ?
                    ORDER BY created_at ASC LIMIT 1""",
                    (discord_id,)
                )
                await db.commit()

            return True

    # ==================== Subscriptions ====================

    async def add_subscription(self, discord_id: str, champion_name: str) -> bool:
        """Ajoute un abonnement à un champion"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO subscriptions (discord_id, champion_name) VALUES (?, ?)",
                    (discord_id, champion_name)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_subscription(self, discord_id: str, champion_name: str) -> bool:
        """Supprime un abonnement à un champion"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM subscriptions WHERE discord_id = ? AND champion_name = ?",
                (discord_id, champion_name)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_subscriptions(self, discord_id: str) -> List[str]:
        """Récupère tous les abonnements d'un utilisateur"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT champion_name FROM subscriptions WHERE discord_id = ?",
                (discord_id,)
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_subscribers(self, champion_name: str) -> List[str]:
        """Récupère tous les utilisateurs abonnés à un champion"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT discord_id FROM subscriptions WHERE champion_name = ?",
                (champion_name,)
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_all_subscribers(self) -> List[str]:
        """Récupère tous les utilisateurs ayant au moins un abonnement"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT discord_id FROM subscriptions WHERE champion_name = 'ALL'"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    # ==================== Patch Version ====================

    async def get_patch_version(self) -> Optional[str]:
        """Récupère la version du patch actuel"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT version FROM patch_version ORDER BY id DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def update_patch_version(self, version: str):
        """Met à jour la version du patch"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO patch_version (version) VALUES (?)",
                (version,)
            )
            await db.commit()

    # ==================== Cache ====================

    async def get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Récupère une entrée du cache si elle n'est pas expirée"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT response_data, expires_at FROM api_cache
                WHERE cache_key = ?""",
                (cache_key,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            response_data, expires_at = row

            # Vérifier l'expiration
            if expires_at:
                expiry = datetime.fromisoformat(expires_at)
                if datetime.now() > expiry:
                    # Cache expiré, le supprimer
                    await db.execute(
                        "DELETE FROM api_cache WHERE cache_key = ?",
                        (cache_key,)
                    )
                    await db.commit()
                    return None

            return json.loads(response_data)

    async def set_cache(self, cache_key: str, response_data: Dict[str, Any], ttl: Optional[int] = None):
        """Stocke une entrée dans le cache"""
        async with aiosqlite.connect(self.db_path) as db:
            expires_at = None
            if ttl:
                expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

            await db.execute(
                """INSERT OR REPLACE INTO api_cache (cache_key, response_data, cached_at, expires_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)""",
                (cache_key, json.dumps(response_data), expires_at)
            )
            await db.commit()

    async def clear_expired_cache(self):
        """Nettoie les entrées de cache expirées"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM api_cache WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.now().isoformat(),)
            )
            await db.commit()

    async def clear_cache_by_pattern(self, pattern: str):
        """Supprime les entrées de cache correspondant à un motif"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM api_cache WHERE cache_key LIKE ?",
                (f"%{pattern}%",)
            )
            await db.commit()
