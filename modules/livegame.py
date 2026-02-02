"""
Module pour la commande /livegame
"""
from typing import Optional, Dict, Any
from utils.embeds import create_livegame_embed
from utils.helpers import get_queue_name


class LiveGameModule:
    """Gère l'affichage des parties en cours"""

    def __init__(self, riot_api, data_dragon, db_manager):
        self.api = riot_api
        self.data_dragon = data_dragon
        self.db = db_manager

    async def get_live_game(
        self,
        discord_id: Optional[str] = None,
        riot_id: Optional[str] = None,
        tag: Optional[str] = None,
        alias: Optional[str] = None
    ):
        """
        Récupère la partie en cours d'un joueur

        Returns:
            Embed Discord avec les infos de la partie
        """
        # Résoudre le PUUID
        if discord_id and not riot_id:
            user = await self.db.get_user(discord_id, alias)
            if not user:
                return None, "Aucun compte lié. Utilisez `/link` d'abord."
            puuid = user['riot_puuid']
            game_name = user['game_name']
        elif riot_id and tag:
            account = await self.api.get_account_by_riot_id(riot_id, tag)
            if not account:
                return None, "Compte Riot introuvable."
            puuid = account['puuid']
            game_name = account['gameName']
        else:
            return None, "Fournissez un RiotID ou liez votre compte."

        # Récupérer la partie en cours
        game = await self.api.get_active_game(puuid)
        if not game:
            return None, f"{game_name} n'est pas en partie actuellement."

        # Parser les données
        game_mode = get_queue_name(game.get('gameQueueConfigId', 0))
        game_length = game.get('gameLength', 0)

        # Organiser par équipe
        teams = {'Équipe Bleue': [], 'Équipe Rouge': []}

        for participant in game.get('participants', []):
            team = 'Équipe Bleue' if participant['teamId'] == 100 else 'Équipe Rouge'

            # Récupérer le nom du champion
            champ_id = participant.get('championId')
            champ_name = await self.data_dragon.get_champion_name_by_id(champ_id)

            # Récupérer le rang (simplifié, on ne fait pas toutes les API calls)
            player_data = {
                'name': participant.get('summonerName', 'Unknown'),
                'champion': champ_name or f"Champ {champ_id}",
                'rank': 'N/A',  # Pourrait être récupéré avec une call supplémentaire
                'winrate': 'N/A'
            }

            teams[team].append(player_data)

        # Créer l'embed
        embed = create_livegame_embed(game_mode, game_length, teams)
        return embed, None
