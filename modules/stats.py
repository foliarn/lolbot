"""
Module pour la commande /stats
"""
from typing import Optional
from utils.embeds import create_stats_embed


class StatsModule:
    """Gère l'affichage des statistiques d'un joueur"""

    def __init__(self, riot_api, data_dragon, db_manager):
        self.api = riot_api
        self.data_dragon = data_dragon
        self.db = db_manager

    async def get_stats(
        self,
        discord_id: Optional[str] = None,
        riot_id: Optional[str] = None,
        tag: Optional[str] = None,
        alias: Optional[str] = None
    ):
        """
        Récupère les stats d'un joueur

        Args:
            discord_id: ID Discord (pour compte lié)
            riot_id: RiotID (si non lié)
            tag: Tag du RiotID
            alias: Alias du smurf (optionnel)

        Returns:
            Embed Discord avec les stats
        """
        # Cas 1: Utilisateur avec compte lié
        if discord_id and not riot_id:
            print(f"[Stats] Looking up user: discord_id={repr(discord_id)}, alias={repr(alias)}")
            user = await self.db.get_user(discord_id, alias)
            print(f"[Stats] User found: {user}")
            if not user:
                return None, "Aucun compte lié. Utilisez `/link` d'abord."

            puuid = user['riot_puuid']
            summoner_id = user['summoner_id']
            game_name = user['game_name']
            tag_line = user['tag_line']

        # Cas 2: RiotID fourni directement
        elif riot_id and tag:
            # Récupérer le PUUID
            account = await self.api.get_account_by_riot_id(riot_id, tag)
            if not account:
                return None, "Compte Riot introuvable."

            puuid = account['puuid']
            game_name = account['gameName']
            tag_line = account['tagLine']

            # Récupérer le summoner
            summoner = await self.api.get_summoner_by_puuid(puuid)
            if not summoner:
                return None, "Impossible de récupérer les informations du summoner."

            summoner_id = summoner['id']

        else:
            return None, "Fournissez un RiotID ou liez votre compte avec `/link`."

        # Récupérer les données du summoner (niveau, etc.)
        summoner = await self.api.get_summoner_by_puuid(puuid)
        if not summoner:
            return None, "Impossible de récupérer les données du summoner."

        # Récupérer les rangs via PUUID (nouvel endpoint Riot API)
        print(f"[Stats] Récupération des rangs pour puuid: {puuid}")
        ranks = await self.api.get_league_entries_by_puuid(puuid)
        print(f"[Stats] Rangs reçus: {ranks}")

        masteries = await self.api.get_champion_masteries(puuid, 3)

        # Convertir les IDs de champions en noms
        champion_names = {}
        if masteries:
            for mastery in masteries:
                champ_id = mastery['championId']
                champ_name = await self.data_dragon.get_champion_name_by_id(champ_id)
                champion_names[champ_id] = champ_name or f"Champion {champ_id}"

        # Créer l'embed
        embed = create_stats_embed(
            game_name=game_name,
            tag_line=tag_line,
            level=summoner.get('summonerLevel', 0),
            ranks=ranks or [],
            masteries=masteries or [],
            champion_names=champion_names
        )

        return embed, None
