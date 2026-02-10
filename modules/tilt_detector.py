"""
Module Tilt Detector - Detecte les series de defaites/victoires et envoie des messages
"""
import random
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import discord

import config


class TiltDetector:
    """Detecte les streaks de victoires/defaites et notifie"""

    def __init__(self, riot_api, db_manager, bot):
        self.api = riot_api
        self.db = db_manager
        self.bot = bot

    async def check_all_players(self, guild: discord.Guild) -> List[Dict[str, Any]]:
        """
        Verifie tous les joueurs enregistres qui sont en ligne.
        Retourne la liste des notifications a envoyer.
        """
        notifications = []

        # Get all primary users
        users = await self.db.get_all_primary_users()

        for user in users:
            discord_id = user['discord_id']
            riot_puuid = user['riot_puuid']
            game_name = user['game_name']

            # Check if user is online on Discord
            member = guild.get_member(int(discord_id))
            if not member:
                continue

            # Skip if offline or invisible
            if member.status in (discord.Status.offline, discord.Status.invisible):
                continue

            # Check for streaks
            notification = await self.check_player_streak(
                riot_puuid=riot_puuid,
                discord_id=discord_id,
                game_name=game_name
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
            # Get recent ranked matches (solo/duo and flex)
            match_ids = await self.api.get_match_history(
                puuid=riot_puuid,
                count=10,
                queue=420  # Ranked Solo/Duo
            )

            if not match_ids:
                return None

            # Get current tilt state
            tilt_state = await self.db.get_tilt_state(riot_puuid)
            last_match_id = tilt_state['last_match_id'] if tilt_state else None

            # Find new matches since last check
            new_match_ids = []
            for match_id in match_ids:
                if match_id == last_match_id:
                    break
                new_match_ids.append(match_id)

            if not new_match_ids:
                return None

            # Get match details and compute streak
            streak_type, streak_count = await self._compute_streak(
                riot_puuid=riot_puuid,
                match_ids=match_ids
            )

            if streak_count < 3:
                # Reset tilt state if streak broken
                if tilt_state:
                    await self.db.reset_tilt_state(riot_puuid)
                return None

            # Check if we need to notify
            last_notified = tilt_state['last_notified_count'] if tilt_state else 0

            # Only notify if streak increased
            if streak_count <= last_notified:
                # Update last match but don't notify
                await self.db.update_tilt_state(
                    riot_puuid=riot_puuid,
                    streak_type=streak_type,
                    streak_count=streak_count,
                    last_notified_count=last_notified,
                    last_match_id=match_ids[0]
                )
                return None

            # Update tilt state
            await self.db.update_tilt_state(
                riot_puuid=riot_puuid,
                streak_type=streak_type,
                streak_count=streak_count,
                last_notified_count=streak_count,
                last_match_id=match_ids[0]
            )

            # Generate notification
            message = self._get_streak_message(
                streak_type=streak_type,
                streak_count=streak_count,
                player_name=game_name
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

    async def _compute_streak(
        self,
        riot_puuid: str,
        match_ids: List[str]
    ) -> Tuple[str, int]:
        """
        Calcule le streak actuel a partir des matchs.
        Retourne (type, count) ou type est 'win' ou 'loss'.
        """
        streak_type = None
        streak_count = 0

        for match_id in match_ids:
            try:
                match_data = await self.api.get_match(match_id)
                if not match_data:
                    continue

                # Find player in participants
                participants = match_data.get('info', {}).get('participants', [])
                player_data = None
                for p in participants:
                    if p.get('puuid') == riot_puuid:
                        player_data = p
                        break

                if not player_data:
                    continue

                won = player_data.get('win', False)
                current_type = 'win' if won else 'loss'

                if streak_type is None:
                    streak_type = current_type
                    streak_count = 1
                elif current_type == streak_type:
                    streak_count += 1
                else:
                    # Streak broken
                    break

            except Exception as e:
                print(f"[TiltDetector] Error processing match {match_id}: {e}")
                continue

        return streak_type or 'none', streak_count

    def _get_streak_message(
        self,
        streak_type: str,
        streak_count: int,
        player_name: str
    ) -> str:
        """
        Retourne un message aleatoire pour le streak.
        """
        if streak_type == 'loss':
            messages = config.TILT_MESSAGES
        else:
            messages = config.WIN_MESSAGES

        # Determine threshold (3, 4, 5, or 6+)
        threshold = min(streak_count, 6)
        if threshold < 3:
            threshold = 3

        # Get messages for this threshold
        threshold_messages = messages.get(threshold, messages.get(6, []))

        if not threshold_messages:
            return f"{player_name} est en {'lose' if streak_type == 'loss' else 'win'} streak de {streak_count}!"

        # Pick random message
        message = random.choice(threshold_messages)

        # Replace placeholders
        message = message.replace('{player}', player_name)
        message = message.replace('{count}', str(streak_count))

        return message

    def create_tilt_embed(
        self,
        notification: Dict[str, Any]
    ) -> discord.Embed:
        """
        Cree un embed pour une notification de tilt.
        """
        streak_type = notification['streak_type']
        streak_count = notification['streak_count']
        message = notification['message']

        if streak_type == 'loss':
            color = discord.Color.red()
            title = f"WALL OF SHAME - {streak_count} Defaites"
            emoji = ""
        else:
            color = discord.Color.green()
            title = f"GG - {streak_count} Victoires"
            emoji = ""

        embed = discord.Embed(
            title=f"{emoji} {title} {emoji}",
            description=message,
            color=color,
            timestamp=datetime.now()
        )

        embed.set_footer(text=f"Streak detectee pour {notification['game_name']}")

        return embed
