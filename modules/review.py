"""
Module pour la commande /review
"""
from typing import Optional
from utils.embeds import create_review_embed
from utils.helpers import calculate_kda, format_duration


class ReviewModule:
    """Gère l'analyse de la dernière partie"""

    def __init__(self, riot_api, data_dragon, db_manager):
        self.api = riot_api
        self.data_dragon = data_dragon
        self.db = db_manager

    async def review_last_game(
        self,
        discord_id: str,
        alias: Optional[str] = None
    ):
        """
        Analyse la dernière partie d'un utilisateur

        Returns:
            Embed Discord avec l'analyse
        """
        # Récupérer le compte
        user = await self.db.get_user(discord_id, alias)
        if not user:
            return None, "Aucun compte lié. Utilisez `/link` d'abord."

        puuid = user['riot_puuid']
        game_name = user['game_name']

        # Récupérer l'historique de matchs
        match_ids = await self.api.get_match_history(puuid, start=0, count=1)
        if not match_ids:
            return None, "Aucune partie récente trouvée."

        # Récupérer les détails du match
        match_data = await self.api.get_match(match_ids[0])
        if not match_data:
            return None, "Impossible de récupérer les détails de la partie."

        # Trouver le participant
        participants = match_data['info']['participants']
        player_data = None

        for p in participants:
            if p['puuid'] == puuid:
                player_data = p
                break

        if not player_data:
            return None, "Impossible de trouver vos données dans cette partie."

        # Extraire les stats
        champion_name = player_data['championName']
        result = "Victory" if player_data['win'] else "Defeat"

        kills = player_data['kills']
        deaths = player_data['deaths']
        assists = player_data['assists']
        _, kda_string = calculate_kda(kills, deaths, assists)

        cs = player_data['totalMinionsKilled'] + player_data.get('neutralMinionsKilled', 0)
        game_duration = match_data['info']['gameDuration']
        cs_per_min = round(cs / (game_duration / 60), 1)

        stats = {
            'cs': cs,
            'cs_per_min': cs_per_min,
            'vision_score': player_data.get('visionScore', 0),
            'damage': player_data.get('totalDamageDealtToChampions', 0),
            'gold': player_data.get('goldEarned', 0),
            'duration': format_duration(game_duration)
        }

        # Créer l'embed
        embed = create_review_embed(
            game_name=game_name,
            champion=champion_name,
            result=result,
            kda=kda_string,
            stats=stats
        )

        return embed, None
