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
                # Find the oldest remaining account
                cursor = await db.execute(
                    "SELECT id FROM users WHERE discord_id = ? ORDER BY created_at ASC LIMIT 1",
                    (discord_id,)
                )
                oldest = await cursor.fetchone()
                if oldest:
                    await db.execute(
                        "UPDATE users SET is_primary = 1 WHERE id = ?",
                        (oldest[0],)
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

    # ==================== Tilt Tracker ====================

    async def get_tilt_state(self, riot_puuid: str) -> Optional[Dict[str, Any]]:
        """Recupere l'etat de streak d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tilt_tracker WHERE riot_puuid = ?",
                (riot_puuid,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_tilt_state(
        self,
        riot_puuid: str,
        streak_type: str,
        streak_count: int,
        last_notified_count: int,
        last_match_id: str
    ):
        """Met a jour l'etat de streak d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO tilt_tracker
                (riot_puuid, streak_type, streak_count, last_notified_count, last_match_id, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (riot_puuid, streak_type, streak_count, last_notified_count, last_match_id)
            )
            await db.commit()

    async def reset_tilt_state(self, riot_puuid: str):
        """Reset l'etat de streak d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM tilt_tracker WHERE riot_puuid = ?",
                (riot_puuid,)
            )
            await db.commit()

    # ==================== Weekly Challenges ====================

    async def get_weekly_challenges(self, week_start: str, discord_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupere les challenges de la semaine"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if discord_id:
                # Get global + personal challenges for this user
                cursor = await db.execute(
                    """SELECT * FROM weekly_challenges
                    WHERE week_start = ? AND is_active = 1
                    AND (challenge_type = 'global' OR assigned_to = ?)
                    ORDER BY challenge_type DESC, challenge_id""",
                    (week_start, discord_id)
                )
            else:
                # Get all challenges
                cursor = await db.execute(
                    """SELECT * FROM weekly_challenges
                    WHERE week_start = ? AND is_active = 1
                    ORDER BY challenge_type DESC, challenge_id""",
                    (week_start,)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_weekly_challenge(
        self,
        challenge_id: str,
        challenge_type: str,
        week_start: str,
        assigned_to: Optional[str] = None
    ) -> bool:
        """Cree un challenge pour la semaine"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """INSERT INTO weekly_challenges
                    (challenge_id, challenge_type, week_start, assigned_to)
                    VALUES (?, ?, ?, ?)""",
                    (challenge_id, challenge_type, week_start, assigned_to)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def deactivate_week_challenges(self, week_start: str):
        """Desactive tous les challenges d'une semaine"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE weekly_challenges SET is_active = 0 WHERE week_start = ?",
                (week_start,)
            )
            await db.commit()

    # ==================== Challenge Completions ====================

    async def get_challenge_completion(
        self,
        challenge_id: str,
        week_start: str,
        discord_id: str
    ) -> Optional[Dict[str, Any]]:
        """Verifie si un joueur a complete un challenge"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM challenge_completions
                WHERE challenge_id = ? AND week_start = ? AND discord_id = ?""",
                (challenge_id, week_start, discord_id)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_challenge_completions_for_week(
        self,
        challenge_id: str,
        week_start: str
    ) -> List[Dict[str, Any]]:
        """Recupere toutes les completions d'un challenge pour une semaine"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM challenge_completions
                WHERE challenge_id = ? AND week_start = ?
                ORDER BY completed_at ASC""",
                (challenge_id, week_start)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def record_challenge_completion(
        self,
        challenge_id: str,
        week_start: str,
        discord_id: str,
        is_first: bool,
        points_awarded: int
    ) -> bool:
        """Enregistre la completion d'un challenge"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """INSERT INTO challenge_completions
                    (challenge_id, week_start, discord_id, is_first, points_awarded)
                    VALUES (?, ?, ?, ?, ?)""",
                    (challenge_id, week_start, discord_id, is_first, points_awarded)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    # ==================== Challenge Points ====================

    async def get_challenge_points(
        self,
        discord_id: str,
        season_split: str
    ) -> int:
        """Recupere les points d'un joueur pour une saison"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT total_points FROM challenge_points
                WHERE discord_id = ? AND season_split = ?""",
                (discord_id, season_split)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def add_challenge_points(
        self,
        discord_id: str,
        season_split: str,
        points: int
    ):
        """Ajoute des points a un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO challenge_points (discord_id, season_split, total_points, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(discord_id, season_split)
                DO UPDATE SET total_points = total_points + ?, updated_at = CURRENT_TIMESTAMP""",
                (discord_id, season_split, points, points)
            )
            await db.commit()

    async def get_challenge_leaderboard(
        self,
        season_split: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Recupere le leaderboard des challenges"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT cp.discord_id, cp.total_points, u.game_name, u.tag_line
                FROM challenge_points cp
                LEFT JOIN users u ON cp.discord_id = u.discord_id AND u.is_primary = 1
                WHERE cp.season_split = ?
                ORDER BY cp.total_points DESC
                LIMIT ?""",
                (season_split, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def apply_penalty_to_all(self, season_split: str, penalty_points: int):
        """Applique une penalite a tous les joueurs enregistres"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get all registered discord_ids
            cursor = await db.execute(
                "SELECT DISTINCT discord_id FROM users WHERE is_primary = 1"
            )
            rows = await cursor.fetchall()

            for row in rows:
                discord_id = row[0]
                await db.execute(
                    """INSERT INTO challenge_points (discord_id, season_split, total_points, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(discord_id, season_split)
                    DO UPDATE SET total_points = total_points + ?, updated_at = CURRENT_TIMESTAMP""",
                    (discord_id, season_split, penalty_points, penalty_points)
                )

            await db.commit()

    # ==================== Weekly Stats Cache ====================

    async def get_weekly_stat(
        self,
        riot_puuid: str,
        week_start: str,
        stat_type: str
    ) -> Optional[Dict[str, Any]]:
        """Recupere une stat hebdomadaire cachee"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM weekly_stats_cache
                WHERE riot_puuid = ? AND week_start = ? AND stat_type = ?""",
                (riot_puuid, week_start, stat_type)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_weekly_stat(
        self,
        riot_puuid: str,
        week_start: str,
        stat_type: str,
        stat_value: float,
        games_counted: int,
        last_match_id: str
    ):
        """Met a jour une stat hebdomadaire"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO weekly_stats_cache
                (riot_puuid, week_start, stat_type, stat_value, games_counted, last_match_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(riot_puuid, week_start, stat_type)
                DO UPDATE SET stat_value = ?, games_counted = ?, last_match_id = ?, updated_at = CURRENT_TIMESTAMP""",
                (riot_puuid, week_start, stat_type, stat_value, games_counted, last_match_id,
                 stat_value, games_counted, last_match_id)
            )
            await db.commit()

    async def get_all_weekly_stats(
        self,
        riot_puuid: str,
        week_start: str
    ) -> Dict[str, Dict[str, Any]]:
        """Recupere toutes les stats hebdomadaires d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM weekly_stats_cache
                WHERE riot_puuid = ? AND week_start = ?""",
                (riot_puuid, week_start)
            )
            rows = await cursor.fetchall()
            return {row['stat_type']: dict(row) for row in rows}

    async def clear_old_weekly_stats(self, weeks_to_keep: int = 4):
        """Nettoie les stats hebdomadaires anciennes"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """DELETE FROM weekly_stats_cache
                WHERE week_start < date('now', ? || ' days')""",
                (f"-{weeks_to_keep * 7}",)
            )
            await db.commit()

    async def get_all_primary_users(self) -> List[Dict[str, Any]]:
        """Recupere tous les utilisateurs avec leur compte principal"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE is_primary = 1"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ==================== Split Stats Cache ====================

    async def get_split_stat(
        self,
        riot_puuid: str,
        season_split: str,
        stat_type: str
    ) -> Optional[Dict[str, Any]]:
        """Recupere une stat de split cachee"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM split_stats_cache
                WHERE riot_puuid = ? AND season_split = ? AND stat_type = ?""",
                (riot_puuid, season_split, stat_type)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_split_stat(
        self,
        riot_puuid: str,
        season_split: str,
        stat_type: str,
        stat_value: float,
        games_counted: int,
        last_match_id: str
    ):
        """Met a jour une stat de split"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO split_stats_cache
                (riot_puuid, season_split, stat_type, stat_value, games_counted, last_match_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(riot_puuid, season_split, stat_type)
                DO UPDATE SET stat_value = ?, games_counted = ?, last_match_id = ?, updated_at = CURRENT_TIMESTAMP""",
                (riot_puuid, season_split, stat_type, stat_value, games_counted, last_match_id,
                 stat_value, games_counted, last_match_id)
            )
            await db.commit()

    async def get_all_split_stats(
        self,
        riot_puuid: str,
        season_split: str
    ) -> Dict[str, Dict[str, Any]]:
        """Recupere toutes les stats de split d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM split_stats_cache
                WHERE riot_puuid = ? AND season_split = ?""",
                (riot_puuid, season_split)
            )
            rows = await cursor.fetchall()
            return {row['stat_type']: dict(row) for row in rows}

    async def reset_all_challenge_points(self, season_split: str):
        """Reset tous les scores de challenges a 0 pour un split"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE challenge_points SET total_points = 0, updated_at = CURRENT_TIMESTAMP WHERE season_split = ?",
                (season_split,)
            )
            await db.commit()

    async def reset_split_stats(self, season_split: str):
        """Reset toutes les stats d'un split (pour nouveau split)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM split_stats_cache WHERE season_split = ?",
                (season_split,)
            )
            await db.commit()

    # ==================== Training Exercises ====================

    async def enable_exercise(self, riot_puuid: str, exercise_id: str) -> bool:
        """Active le tracking d'un exercice pour un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """INSERT INTO exercise_tracking (riot_puuid, exercise_id)
                    VALUES (?, ?)""",
                    (riot_puuid, exercise_id)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def disable_exercise(self, riot_puuid: str, exercise_id: str) -> bool:
        """Desactive le tracking d'un exercice pour un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM exercise_tracking WHERE riot_puuid = ? AND exercise_id = ?",
                (riot_puuid, exercise_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_enabled_exercises(self, riot_puuid: str) -> List[Dict[str, Any]]:
        """Recupere les exercices actives d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM exercise_tracking WHERE riot_puuid = ?",
                (riot_puuid,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_exercise_users(self) -> List[str]:
        """Recupere tous les PUUIDs ayant au moins un exercice active"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT riot_puuid FROM exercise_tracking"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def update_exercise_last_match(self, riot_puuid: str, exercise_id: str, last_match_id: str):
        """Met a jour le curseur de dernier match traite pour un exercice"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE exercise_tracking SET last_match_id = ?
                WHERE riot_puuid = ? AND exercise_id = ?""",
                (last_match_id, riot_puuid, exercise_id)
            )
            await db.commit()

    async def record_exercise_attempt(
        self,
        riot_puuid: str,
        exercise_id: str,
        match_id: str,
        success: bool,
        match_timestamp: int
    ) -> bool:
        """Enregistre une tentative d'exercice"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """INSERT INTO exercise_attempts
                    (riot_puuid, exercise_id, match_id, success, match_timestamp)
                    VALUES (?, ?, ?, ?, ?)""",
                    (riot_puuid, exercise_id, match_id, success, match_timestamp)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_exercise_stats(self, riot_puuid: str, exercise_id: str) -> Dict[str, int]:
        """Recupere les stats d'un exercice (total et succes)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT COUNT(*) as total, SUM(CASE WHEN success THEN 1 ELSE 0 END) as success
                FROM exercise_attempts
                WHERE riot_puuid = ? AND exercise_id = ?""",
                (riot_puuid, exercise_id)
            )
            row = await cursor.fetchone()
            return {'total': row[0] or 0, 'success': row[1] or 0}

    async def get_all_exercise_stats(self, riot_puuid: str) -> Dict[str, Dict[str, int]]:
        """Recupere les stats de tous les exercices d'un joueur"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT exercise_id,
                       COUNT(*) as total,
                       SUM(CASE WHEN success THEN 1 ELSE 0 END) as success
                FROM exercise_attempts
                WHERE riot_puuid = ?
                GROUP BY exercise_id""",
                (riot_puuid,)
            )
            rows = await cursor.fetchall()
            return {row[0]: {'total': row[1] or 0, 'success': row[2] or 0} for row in rows}
