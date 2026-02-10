"""
Wrappers pour les endpoints de l'API Riot Games
"""
from typing import Optional, Dict, Any, List
from config import RIOT_API_BASE, DEFAULT_REGION, ROUTING_REGION, CACHE_TTL


class RiotEndpoints:
    """Wrappers pour tous les endpoints Riot utilisés"""

    def __init__(self, client):
        self.client = client
        self.platform_base = RIOT_API_BASE['platform']
        self.regional_base = RIOT_API_BASE['regional']

    # ==================== ACCOUNT-V1 ====================

    async def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le PUUID à partir du RiotID

        Returns: {'puuid': str, 'gameName': str, 'tagLine': str}
        """
        url = f"{self.regional_base}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        cache_key = f"account:riotid:{game_name}#{tag_line}"
        return await self.client.request(url, cache_key, CACHE_TTL['REGISTERED_USER'])

    async def get_account_by_puuid(self, puuid: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le gameName et tagLine à partir du PUUID

        Returns: {'puuid': str, 'gameName': str, 'tagLine': str}
        """
        url = f"{self.regional_base}/riot/account/v1/accounts/by-puuid/{puuid}"
        cache_key = f"account:puuid:{puuid}"
        return await self.client.request(url, cache_key, CACHE_TTL['REGISTERED_USER'])

    # ==================== SUMMONER-V4 ====================

    async def get_summoner_by_puuid(self, puuid: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations du summoner à partir du PUUID

        Returns: {'id': str, 'accountId': str, 'puuid': str, 'name': str, 'summonerLevel': int}
        """
        url = f"{self.platform_base}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        cache_key = f"summoner:puuid:{puuid}"
        return await self.client.request(url, cache_key, CACHE_TTL['REGISTERED_USER'])

    # ==================== LEAGUE-V4 ====================

    async def get_league_entries_by_puuid(self, puuid: str) -> Optional[List[Dict[str, Any]]]:
        """
        Récupère les rangs du joueur (Solo/Duo et Flex) via PUUID

        Returns: List of {'queueType': str, 'tier': str, 'rank': str, 'leaguePoints': int, 'wins': int, 'losses': int}
        """
        url = f"{self.platform_base}/lol/league/v4/entries/by-puuid/{puuid}"
        cache_key = f"league:puuid:{puuid}"

        # Faire la requête
        result = await self.client.request(url, cache_key, CACHE_TTL['RANK'])

        # Si le résultat est vide, supprimer du cache pour permettre un refresh
        # (évite de cacher un résultat "non classé" pendant 30 min)
        if result is not None and len(result) == 0:
            print(f"[API] Rang vide pour {puuid}, pas de mise en cache")
            if self.client.db_manager:
                await self.client.db_manager.clear_cache_by_pattern(cache_key)

        return result

    # ==================== CHAMPION-MASTERY-V4 ====================

    async def get_champion_masteries(self, puuid: str, count: int = 5) -> Optional[List[Dict[str, Any]]]:
        """
        Récupère les champions avec le plus de maîtrise

        Returns: List of {'championId': int, 'championPoints': int, 'championLevel': int}
        """
        url = f"{self.platform_base}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count={count}"
        cache_key = f"mastery:puuid:{puuid}:top{count}"
        return await self.client.request(url, cache_key, CACHE_TTL['MASTERY'])

    async def get_champion_mastery(self, puuid: str, champion_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère la maîtrise d'un champion spécifique

        Returns: {'championId': int, 'championPoints': int, 'championLevel': int}
        """
        url = f"{self.platform_base}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champion_id}"
        cache_key = f"mastery:puuid:{puuid}:champion:{champion_id}"
        return await self.client.request(url, cache_key, CACHE_TTL['MASTERY'])

    # ==================== MATCH-V5 ====================

    async def get_match_history(
        self,
        puuid: str,
        start: int = 0,
        count: int = 20,
        queue: Optional[int] = None,
        start_time: Optional[int] = None
    ) -> Optional[List[str]]:
        """
        Récupère les IDs des derniers matchs

        Args:
            puuid: PUUID du joueur
            start: Index de départ
            count: Nombre de matchs (max 100)
            queue: Type de queue (420=SoloQ, 440=Flex, 700=Clash)
            start_time: Epoch timestamp en secondes (filtre les matchs apres cette date)

        Returns: List of match IDs
        """
        url = f"{self.regional_base}/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
        if queue:
            url += f"&queue={queue}"
        if start_time:
            url += f"&startTime={start_time}"

        cache_key = f"match_history:puuid:{puuid}:queue:{queue}:start:{start}:count:{count}:st:{start_time}"
        return await self.client.request(url, cache_key, CACHE_TTL['MATCH_HISTORY'])

    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les détails d'un match

        Returns: Match data avec 'info' et 'metadata'
        """
        url = f"{self.regional_base}/lol/match/v5/matches/{match_id}"
        cache_key = f"match:{match_id}"
        return await self.client.request(url, cache_key, CACHE_TTL['MATCH_DETAIL'])

    async def get_match_timeline(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère la timeline d'un match (frames par minute, événements)

        Returns: Timeline data avec 'info.frames' et 'info.frameInterval'
        """
        url = f"{self.regional_base}/lol/match/v5/matches/{match_id}/timeline"
        cache_key = f"timeline:{match_id}"
        return await self.client.request(url, cache_key, CACHE_TTL['MATCH_TIMELINE'])

    # ==================== SPECTATOR-V4 ====================

    async def get_active_game(self, puuid: str) -> Optional[Dict[str, Any]]:
        """
        Récupère la partie en cours d'un joueur

        Returns: Game data ou None si pas en partie
        """
        url = f"{self.platform_base}/lol/spectator/v4/active-games/by-summoner/{puuid}"
        return await self.client.request(url, use_rate_limit=True)

    # ==================== CLASH-V1 ====================

    async def get_clash_player_by_puuid(self, puuid: str) -> Optional[List[Dict[str, Any]]]:
        """
        Récupère les équipes Clash du joueur via PUUID

        Returns: List of {'teamId': str, 'position': str, 'role': str}
        """
        url = f"{self.platform_base}/lol/clash/v1/players/by-puuid/{puuid}"
        return await self.client.request(url, use_rate_limit=True)

    async def get_clash_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les détails d'une équipe Clash

        Returns: {'id': str, 'name': str, 'players': [...]}
        """
        url = f"{self.platform_base}/lol/clash/v1/teams/{team_id}"
        return await self.client.request(url, use_rate_limit=True)
