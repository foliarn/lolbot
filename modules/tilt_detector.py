"""
Module Tilt Detector - Detecte les series de defaites/victoires et envoie des messages generés par LLM
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import discord

import config


class TiltDetector:
    """Detecte les streaks de victoires/defaites et notifie avec messages LLM"""

    def __init__(self, riot_api, db_manager, bot, reputation_manager=None, commentary=None):
        self.api = riot_api
        self.db = db_manager
        self.bot = bot
        self.reputation = reputation_manager
        self.commentary = commentary

    async def check_all_players(self) -> List[Dict[str, Any]]:
        """
        Verifie tous les joueurs enregistres.
        Retourne la liste des notifications a envoyer.
        """
        notifications = []
        users = await self.db.get_all_primary_users()

        for user in users:
            notification = await self.check_player_streak(
                riot_puuid=user['riot_puuid'],
                discord_id=user['discord_id'],
                game_name=user['game_name']
            )
            if notification:
                notifications.append(notification)

        return notifications

    async def check_player_streak(
        self,
        riot_puuid: str,
        discord_id: str,
        game_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verifie le streak d'un joueur et retourne une notification si necessaire.
        """
        try:
            solo_ids = await self.api.get_match_history(
                puuid=riot_puuid, count=10, queue=420
            ) or []
            flex_ids = await self.api.get_match_history(
                puuid=riot_puuid, count=10, queue=440
            ) or []

            # Merge, deduplicate, sort newest-first, keep 10 most recent overall
            match_ids = list(dict.fromkeys(solo_ids + flex_ids))
            match_ids.sort(key=lambda m: int(m.split('_')[-1]), reverse=True)
            match_ids = match_ids[:10]

            if not match_ids:
                return None

            tilt_state = await self.db.get_tilt_state(riot_puuid)
            last_match_id = tilt_state['last_match_id'] if tilt_state else None

            # Check if there are new matches since last check
            new_match_ids = []
            for match_id in match_ids:
                if match_id == last_match_id:
                    break
                new_match_ids.append(match_id)

            if not new_match_ids:
                return None

            # Update reputation based on KDA of each new game
            if self.reputation:
                await self._update_reputation_from_matches(discord_id, riot_puuid, new_match_ids)

            streak_type, streak_count = await self._compute_streak(
                riot_puuid=riot_puuid,
                match_ids=match_ids
            )

            if streak_count < config.TILT_MIN_STREAK:
                if tilt_state:
                    await self.db.reset_tilt_state(riot_puuid)
                return None

            last_notified = tilt_state['last_notified_count'] if tilt_state else 0

            if streak_count <= last_notified:
                await self.db.update_tilt_state(
                    riot_puuid=riot_puuid,
                    streak_type=streak_type,
                    streak_count=streak_count,
                    last_notified_count=last_notified,
                    last_match_id=match_ids[0]
                )
                return None

            await self.db.update_tilt_state(
                riot_puuid=riot_puuid,
                streak_type=streak_type,
                streak_count=streak_count,
                last_notified_count=streak_count,
                last_match_id=match_ids[0]
            )

            reputation_data = None
            if self.reputation:
                try:
                    reputation_data = await self.reputation.get_reputation(discord_id)
                except Exception:
                    pass

            message = await self._generate_streak_message(
                streak_type=streak_type,
                streak_count=streak_count,
                player_name=game_name,
                reputation=reputation_data,
            )

            return {
                'discord_id': discord_id,
                'game_name': game_name,
                'streak_type': streak_type,
                'streak_count': streak_count,
                'message': message,
            }

        except Exception as e:
            print(f"[TiltDetector] Error checking {game_name}: {e}")
            return None

    async def _update_reputation_from_matches(self, discord_id: str, riot_puuid: str, match_ids: List[str]):
        """Met à jour la réputation en fonction du KDA de chaque nouvelle game."""
        for match_id in match_ids:
            try:
                match_data = await self.api.get_match(match_id)
                if not match_data:
                    continue
                participants = match_data.get('info', {}).get('participants', [])
                player = next((p for p in participants if p.get('puuid') == riot_puuid), None)
                if not player:
                    continue
                await self.reputation.update_game_kda(
                    discord_id=discord_id,
                    kills=player.get('kills', 0),
                    deaths=player.get('deaths', 0),
                    assists=player.get('assists', 0),
                    champion=player.get('championName'),
                    match_id=match_id,
                )
            except Exception as e:
                print(f"[Reputation] Error processing match {match_id}: {e}")

    async def _compute_streak(
        self,
        riot_puuid: str,
        match_ids: List[str]
    ) -> Tuple[str, int]:
        """Calcule le streak actuel a partir des matchs."""
        streak_type = None
        streak_count = 0

        for match_id in match_ids:
            try:
                match_data = await self.api.get_match(match_id)
                if not match_data:
                    continue

                participants = match_data.get('info', {}).get('participants', [])
                player_data = next((p for p in participants if p.get('puuid') == riot_puuid), None)
                if not player_data:
                    continue

                current_type = 'win' if player_data.get('win', False) else 'loss'

                if streak_type is None:
                    streak_type = current_type
                    streak_count = 1
                elif current_type == streak_type:
                    streak_count += 1
                else:
                    break

            except Exception as e:
                print(f"[TiltDetector] Error processing match {match_id}: {e}")
                continue

        return streak_type or 'none', streak_count

    async def _generate_streak_message(
        self,
        streak_type: str,
        streak_count: int,
        player_name: str,
        reputation=None,
    ) -> str:
        """Génère un message via LLM (fallback statique si LLM indisponible)."""
        if self.commentary:
            try:
                return await self.commentary.tilt_message(
                    player_name=player_name,
                    streak_type=streak_type,
                    streak_count=streak_count,
                    reputation=reputation,
                )
            except Exception as e:
                print(f"[TiltDetector] LLM error: {e}")

        if streak_type == 'loss':
            return f"{player_name} est en lose streak de {streak_count}... Quelqu'un appelle une ambulance."
        return f"{player_name} est en win streak de {streak_count} ! Incroyable !"

    def create_tilt_embed(self, notification: Dict[str, Any]) -> discord.Embed:
        """Cree un embed pour une notification de streak."""
        streak_type = notification['streak_type']
        streak_count = notification['streak_count']
        message = notification['message']

        if streak_type == 'loss':
            color = discord.Color.red()
            title = f"WALL OF SHAME — {streak_count} Défaites"
        else:
            color = discord.Color.green()
            title = f"GG — {streak_count} Victoires"

        embed = discord.Embed(
            title=title,
            description=message,
            color=color,
            timestamp=datetime.now()
        )
        embed.set_footer(text=notification['game_name'])
        return embed
