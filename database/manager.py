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
                print(f"[DB] Query: SELECT * FROM users WHERE discord_id = {repr(discord_id)} AND account_alias = {repr(alias)}")
                cursor = await db.execute(
                    "SELECT * FROM users WHERE discord_id = ? AND account_alias = ?",
                    (discord_id, alias)
                )
            else:
                print(f"[DB] Query: SELECT * FROM users WHERE discord_id = {repr(discord_id)} AND is_primary = 1")
                cursor = await db.execute(
                    "SELECT * FROM users WHERE discord_id = ? AND is_primary = 1",
                    (discord_id,)
                )

            row = await cursor.fetchone()
            print(f"[DB] Result: {dict(row) if row else None}")
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

    # ==================== Rank History ====================

    async def save_rank_snapshot(
        self,
        riot_puuid: str,
        queue_type: str,
        tier: str,
        rank: str,
        league_points: int,
        wins: int,
        losses: int
    ):
        """Sauvegarde un snapshot du rang d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO rank_history
                (riot_puuid, queue_type, tier, rank, league_points, wins, losses)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (riot_puuid, queue_type, tier, rank, league_points, wins, losses)
            )
            await db.commit()

    async def get_rank_at_time(
        self,
        riot_puuid: str,
        queue_type: str,
        target_time: str
    ) -> Optional[Dict[str, Any]]:
        """Recupere le rang d'un joueur a un moment donne (le plus proche avant target_time)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM rank_history
                WHERE riot_puuid = ? AND queue_type = ? AND recorded_at <= ?
                ORDER BY recorded_at DESC LIMIT 1""",
                (riot_puuid, queue_type, target_time)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_latest_rank(
        self,
        riot_puuid: str,
        queue_type: str
    ) -> Optional[Dict[str, Any]]:
        """Recupere le dernier rang enregistre d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM rank_history
                WHERE riot_puuid = ? AND queue_type = ?
                ORDER BY recorded_at DESC LIMIT 1""",
                (riot_puuid, queue_type)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_registered_puuids(self) -> List[str]:
        """Recupere tous les PUUIDs des utilisateurs enregistres"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT riot_puuid FROM users"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_user_by_puuid(self, riot_puuid: str) -> Optional[Dict[str, Any]]:
        """Recupere un utilisateur par son PUUID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE riot_puuid = ? LIMIT 1",
                (riot_puuid,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    # ==================== Clash Teams ====================

    async def create_clash_team(
        self,
        team_name: str,
        creator_discord_id: str,
        member_discord_ids: List[str]
    ) -> Optional[int]:
        """Cree une equipe Clash avec ses membres. Retourne l'ID de l'equipe."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Creer l'equipe
                cursor = await db.execute(
                    """INSERT INTO clash_teams (team_name, created_by_discord_id)
                    VALUES (?, ?)""",
                    (team_name, creator_discord_id)
                )
                team_id = cursor.lastrowid

                # Ajouter les membres
                for position, discord_id in enumerate(member_discord_ids):
                    await db.execute(
                        """INSERT INTO clash_team_members (team_id, discord_id, position)
                        VALUES (?, ?, ?)""",
                        (team_id, discord_id, position)
                    )

                await db.commit()
                return team_id
            except aiosqlite.IntegrityError:
                return None

    async def get_clash_team(
        self,
        team_name: str,
        creator_discord_id: str
    ) -> Optional[Dict[str, Any]]:
        """Recupere une equipe Clash par son nom et createur"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM clash_teams
                WHERE team_name = ? AND created_by_discord_id = ?""",
                (team_name, creator_discord_id)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            team = dict(row)

            # Recuperer les membres
            cursor = await db.execute(
                """SELECT ctm.discord_id, ctm.position, u.game_name, u.tag_line, u.riot_puuid
                FROM clash_team_members ctm
                LEFT JOIN users u ON ctm.discord_id = u.discord_id AND u.is_primary = 1
                WHERE ctm.team_id = ?
                ORDER BY ctm.position""",
                (team['id'],)
            )
            members = await cursor.fetchall()
            team['members'] = [dict(m) for m in members]

            return team

    async def get_clash_team_by_id(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Recupere une equipe Clash par son ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM clash_teams WHERE id = ?",
                (team_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            team = dict(row)

            # Recuperer les membres
            cursor = await db.execute(
                """SELECT ctm.discord_id, ctm.position, u.game_name, u.tag_line, u.riot_puuid
                FROM clash_team_members ctm
                LEFT JOIN users u ON ctm.discord_id = u.discord_id AND u.is_primary = 1
                WHERE ctm.team_id = ?
                ORDER BY ctm.position""",
                (team_id,)
            )
            members = await cursor.fetchall()
            team['members'] = [dict(m) for m in members]

            return team

    async def get_user_clash_teams(self, discord_id: str) -> List[Dict[str, Any]]:
        """Recupere toutes les equipes dont l'utilisateur fait partie"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Equipes creees par l'utilisateur
            cursor = await db.execute(
                """SELECT ct.*, 'creator' as role
                FROM clash_teams ct
                WHERE ct.created_by_discord_id = ?
                ORDER BY ct.created_at DESC""",
                (discord_id,)
            )
            created_teams = await cursor.fetchall()

            # Equipes ou l'utilisateur est membre
            cursor = await db.execute(
                """SELECT ct.*, 'member' as role
                FROM clash_teams ct
                JOIN clash_team_members ctm ON ct.id = ctm.team_id
                WHERE ctm.discord_id = ? AND ct.created_by_discord_id != ?
                ORDER BY ct.created_at DESC""",
                (discord_id, discord_id)
            )
            member_teams = await cursor.fetchall()

            all_teams = []
            for row in list(created_teams) + list(member_teams):
                team = dict(row)
                # Recuperer les membres
                cursor = await db.execute(
                    """SELECT ctm.discord_id, ctm.position, u.game_name, u.tag_line
                    FROM clash_team_members ctm
                    LEFT JOIN users u ON ctm.discord_id = u.discord_id AND u.is_primary = 1
                    WHERE ctm.team_id = ?
                    ORDER BY ctm.position""",
                    (team['id'],)
                )
                members = await cursor.fetchall()
                team['members'] = [dict(m) for m in members]
                all_teams.append(team)

            return all_teams

    async def delete_clash_team(self, team_id: int) -> bool:
        """Supprime une equipe Clash"""
        async with aiosqlite.connect(self.db_path) as db:
            # Supprimer d'abord les membres (meme si CASCADE devrait le faire)
            await db.execute(
                "DELETE FROM clash_team_members WHERE team_id = ?",
                (team_id,)
            )
            # Supprimer l'equipe
            cursor = await db.execute(
                "DELETE FROM clash_teams WHERE id = ?",
                (team_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_clash_team_members_data(self, team_id: int) -> List[Dict[str, Any]]:
        """Recupere les donnees des membres d'une equipe (puuid, game_name, etc.)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT u.riot_puuid, u.summoner_id, u.game_name, u.tag_line, u.region,
                          ctm.position
                FROM clash_team_members ctm
                JOIN users u ON ctm.discord_id = u.discord_id AND u.is_primary = 1
                WHERE ctm.team_id = ?
                ORDER BY ctm.position""",
                (team_id,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
