"""
Module pour le scouting d'equipes adverses en Clash
"""
import asyncio
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict

import config


@dataclass
class ChampionData:
    """Donnees d'un champion pour un joueur"""
    champion_id: int
    champion_name: str
    mastery_points: int
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0

    @property
    def winrate(self) -> float:
        if self.games_played == 0:
            return 0.0
        return (self.wins / self.games_played) * 100

    @property
    def kda(self) -> float:
        if self.total_deaths == 0:
            return (self.total_kills + self.total_assists) / 1.0
        return (self.total_kills + self.total_assists) / self.total_deaths


@dataclass
class DangerScore:
    """Score de danger pour un champion"""
    champion_id: int
    champion_name: str
    total_score: int
    reasons: List[str] = field(default_factory=list)
    player_name: str = ""
    mastery_points: int = 0
    games_played: int = 0
    winrate: float = 0.0


@dataclass
class RankInfo:
    """Informations de rang d'un joueur"""
    tier: str = ""
    rank: str = ""
    lp: int = 0
    wins: int = 0
    losses: int = 0

    @property
    def winrate(self) -> float:
        total = self.wins + self.losses
        if total == 0:
            return 0.0
        return (self.wins / total) * 100

    def to_lp_value(self) -> int:
        """Convertit le rang en valeur LP pour comparaison"""
        tier_value = config.RANK_VALUES.get(self.tier.upper(), 0)
        rank_values = {'IV': 0, 'III': 100, 'II': 200, 'I': 300}
        rank_value = rank_values.get(self.rank, 0)
        return tier_value + rank_value + self.lp


@dataclass
class PlayerData:
    """Donnees completes d'un joueur scout"""
    puuid: str
    game_name: str
    tag_line: str
    rank: RankInfo = field(default_factory=RankInfo)
    recent_winrate: float = 0.0
    recent_kda: float = 0.0
    main_role: str = "UNKNOWN"
    role_distribution: Dict[str, float] = field(default_factory=dict)
    top_champions: List[ChampionData] = field(default_factory=list)
    threat_score: float = 0.0
    is_private: bool = False
    error: Optional[str] = None


@dataclass
class ScoutResult:
    """Resultat complet du scouting"""
    players: List[PlayerData] = field(default_factory=list)
    optimal_bans: List[DangerScore] = field(default_factory=list)
    alternative_bans: List[DangerScore] = field(default_factory=list)
    team_composition: str = "unknown"  # "5-stack" / "3+2" / "scattered"
    average_elo: int = 0
    threat_comparison: float = 0.0  # vs our team


class ClashScoutModule:
    """Module de scouting pour les Clash"""

    def __init__(self, riot_api, data_dragon, db_manager):
        self.api = riot_api
        self.data_dragon = data_dragon
        self.db = db_manager

    async def scout_enemy_team(self, riot_id: str, tag: str) -> ScoutResult:
        """
        Scout une equipe adverse a partir du RiotID d'un joueur.
        Utilise l'API Clash pour trouver l'equipe.
        """
        result = ScoutResult()

        # 1. Recuperer le PUUID et summoner ID du joueur
        account = await self.api.get_account_by_riot_id(riot_id, tag)
        if not account:
            result.team_composition = "error"
            return result

        puuid = account['puuid']
        summoner = await self.api.get_summoner_by_puuid(puuid)
        if not summoner:
            result.team_composition = "error"
            return result

        summoner_id = summoner.get('id')

        # 2. Trouver l'equipe Clash
        clash_data = await self.api.get_clash_player(summoner_id)
        if not clash_data or len(clash_data) == 0:
            result.team_composition = "no_clash"
            return result

        # Prendre la premiere equipe active
        team_id = clash_data[0].get('teamId')
        if not team_id:
            result.team_composition = "no_team"
            return result

        # 3. Recuperer les membres de l'equipe
        team_data = await self.api.get_clash_team(team_id)
        if not team_data or 'players' not in team_data:
            result.team_composition = "error"
            return result

        players = team_data['players']

        # 4. Scout chaque joueur en parallele
        tasks = []
        for player in players:
            player_summoner_id = player.get('summonerId')
            tasks.append(self._fetch_player_data_by_summoner_id(player_summoner_id))

        player_results = await asyncio.gather(*tasks, return_exceptions=True)

        for player_data in player_results:
            if isinstance(player_data, Exception):
                print(f"[ClashScout] Erreur fetch player: {player_data}")
                continue
            if player_data:
                result.players.append(player_data)

        # 5. Analyser les donnees
        if result.players:
            result.team_composition = self._detect_team_composition(result.players)
            result.average_elo = self._calculate_average_elo(result.players)

            # Calculer les bans
            all_dangers = self._aggregate_danger_scores(result.players)
            result.optimal_bans = all_dangers[:5]
            result.alternative_bans = all_dangers[5:10]

        return result

    async def scout_team_by_players(self, player_puuids: List[str]) -> ScoutResult:
        """
        Scout une liste de joueurs (pas forcement en Clash).
        Utile pour analyser une equipe avant un match.
        """
        result = ScoutResult()

        # Scout chaque joueur en parallele
        tasks = [self.fetch_player_data(puuid) for puuid in player_puuids]
        player_results = await asyncio.gather(*tasks, return_exceptions=True)

        for player_data in player_results:
            if isinstance(player_data, Exception):
                print(f"[ClashScout] Erreur fetch player: {player_data}")
                continue
            if player_data:
                result.players.append(player_data)

        # Analyser
        if result.players:
            result.team_composition = self._detect_team_composition(result.players)
            result.average_elo = self._calculate_average_elo(result.players)

            all_dangers = self._aggregate_danger_scores(result.players)
            result.optimal_bans = all_dangers[:5]
            result.alternative_bans = all_dangers[5:10]

        return result

    async def _fetch_player_data_by_summoner_id(self, summoner_id: str) -> Optional[PlayerData]:
        """Fetch player data a partir du summoner ID (pour Clash API)"""
        # On doit d'abord recuperer le PUUID via summoner
        # L'API Summoner ne permet pas de query par summoner_id directement avec PUUID
        # On va utiliser l'endpoint by-summoner-id si disponible
        # Note: L'API moderne utilise PUUID, on fait une requete directe
        try:
            # Utiliser l'endpoint LEAGUE pour avoir le summoner_id -> on peut pas
            # On va devoir faire une requete speciale
            url = f"{self.api.platform_base}/lol/summoner/v4/summoners/{summoner_id}"
            summoner = await self.api.client.request(url, use_rate_limit=True)

            if not summoner:
                return None

            puuid = summoner.get('puuid')
            if not puuid:
                return None

            return await self.fetch_player_data(puuid)

        except Exception as e:
            print(f"[ClashScout] Erreur fetch by summoner_id {summoner_id}: {e}")
            return None

    async def fetch_player_data(self, puuid: str) -> Optional[PlayerData]:
        """Recupere toutes les donnees d'un joueur"""
        try:
            # Recuperer les infos de base
            summoner = await self.api.get_summoner_by_puuid(puuid)
            if not summoner:
                return None

            # Creer l'objet PlayerData
            # On doit recuperer le game_name via account API
            # Note: summoner n'a plus le 'name' field
            player = PlayerData(
                puuid=puuid,
                game_name=summoner.get('name', 'Unknown'),
                tag_line='EUW'
            )

            # Essayer de recuperer le vrai nom via account API
            # (on a besoin du game_name#tag_line)
            # Pour l'instant on garde le name du summoner

            # Fetch en parallele: rank, mastery, match history
            rank_task = self.api.get_league_entries_by_puuid(puuid)
            mastery_task = self.api.get_champion_masteries(puuid, count=10)
            history_task = self.api.get_match_history(puuid, count=20)

            ranks, masteries, match_ids = await asyncio.gather(
                rank_task, mastery_task, history_task,
                return_exceptions=True
            )

            # Traiter les rangs
            if isinstance(ranks, list) and ranks:
                for rank_data in ranks:
                    if rank_data.get('queueType') == 'RANKED_SOLO_5x5':
                        player.rank = RankInfo(
                            tier=rank_data.get('tier', ''),
                            rank=rank_data.get('rank', ''),
                            lp=rank_data.get('leaguePoints', 0),
                            wins=rank_data.get('wins', 0),
                            losses=rank_data.get('losses', 0)
                        )
                        break

            # Traiter les masteries
            champion_names = self.data_dragon.get_champion_names()
            if isinstance(masteries, list):
                for m in masteries:
                    champ_id = m.get('championId')
                    player.top_champions.append(ChampionData(
                        champion_id=champ_id,
                        champion_name=champion_names.get(champ_id, f"Champion {champ_id}"),
                        mastery_points=m.get('championPoints', 0)
                    ))

            # Traiter l'historique des matchs
            if isinstance(match_ids, list) and match_ids:
                await self._analyze_match_history(player, match_ids[:20])

            # Calculer le threat score
            player.threat_score = self.calculate_player_threat(player)

            return player

        except Exception as e:
            print(f"[ClashScout] Erreur fetch player {puuid}: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _analyze_match_history(self, player: PlayerData, match_ids: List[str]):
        """Analyse l'historique de matchs d'un joueur"""
        if not match_ids:
            return

        # Fetch les details des matchs (en parallele par batch pour eviter rate limit)
        batch_size = 5
        matches = []

        for i in range(0, len(match_ids), batch_size):
            batch = match_ids[i:i + batch_size]
            tasks = [self.api.get_match(match_id) for match_id in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, dict):
                    matches.append(r)

        if not matches:
            return

        # Analyser les matchs
        role_counts = defaultdict(int)
        champion_stats = {}  # champion_id -> stats
        total_kills = 0
        total_deaths = 0
        total_assists = 0
        wins = 0

        for match in matches:
            info = match.get('info', {})
            participants = info.get('participants', [])

            # Trouver le joueur dans le match
            player_data = None
            for p in participants:
                if p.get('puuid') == player.puuid:
                    player_data = p
                    break

            if not player_data:
                continue

            # Role
            role = player_data.get('teamPosition', 'UNKNOWN')
            if role:
                role_counts[role] += 1

            # Champion stats
            champ_id = player_data.get('championId')
            if champ_id:
                if champ_id not in champion_stats:
                    champion_stats[champ_id] = {
                        'games': 0, 'wins': 0,
                        'kills': 0, 'deaths': 0, 'assists': 0
                    }
                stats = champion_stats[champ_id]
                stats['games'] += 1
                if player_data.get('win'):
                    stats['wins'] += 1
                    wins += 1
                stats['kills'] += player_data.get('kills', 0)
                stats['deaths'] += player_data.get('deaths', 0)
                stats['assists'] += player_data.get('assists', 0)

            total_kills += player_data.get('kills', 0)
            total_deaths += player_data.get('deaths', 0)
            total_assists += player_data.get('assists', 0)

        # Calculer les stats finales
        total_games = len(matches)
        if total_games > 0:
            player.recent_winrate = (wins / total_games) * 100
            if total_deaths > 0:
                player.recent_kda = (total_kills + total_assists) / total_deaths
            else:
                player.recent_kda = total_kills + total_assists

        # Role principal
        if role_counts:
            total_roles = sum(role_counts.values())
            player.role_distribution = {
                role: (count / total_roles) * 100
                for role, count in role_counts.items()
            }
            player.main_role = max(role_counts, key=role_counts.get)

        # Mettre a jour les stats des champions
        champion_names = self.data_dragon.get_champion_names()
        for champ in player.top_champions:
            if champ.champion_id in champion_stats:
                stats = champion_stats[champ.champion_id]
                champ.games_played = stats['games']
                champ.wins = stats['wins']
                champ.losses = stats['games'] - stats['wins']
                champ.total_kills = stats['kills']
                champ.total_deaths = stats['deaths']
                champ.total_assists = stats['assists']

        # Ajouter les champions joues mais pas dans top mastery
        for champ_id, stats in champion_stats.items():
            if not any(c.champion_id == champ_id for c in player.top_champions):
                player.top_champions.append(ChampionData(
                    champion_id=champ_id,
                    champion_name=champion_names.get(champ_id, f"Champion {champ_id}"),
                    mastery_points=0,
                    games_played=stats['games'],
                    wins=stats['wins'],
                    losses=stats['games'] - stats['wins'],
                    total_kills=stats['kills'],
                    total_deaths=stats['deaths'],
                    total_assists=stats['assists']
                ))

    def detect_role(self, matches: List[Dict[str, Any]], puuid: str) -> Dict[str, float]:
        """Detecte la distribution des roles d'un joueur"""
        role_counts = defaultdict(int)

        for match in matches:
            info = match.get('info', {})
            for p in info.get('participants', []):
                if p.get('puuid') == puuid:
                    role = p.get('teamPosition', 'UNKNOWN')
                    if role:
                        role_counts[role] += 1
                    break

        total = sum(role_counts.values())
        if total == 0:
            return {}

        return {role: (count / total) * 100 for role, count in role_counts.items()}

    def calculate_danger_score(
        self,
        champion: ChampionData,
        player: PlayerData
    ) -> DangerScore:
        """Calcule le score de danger pour un champion"""
        cfg = config.DANGER_SCORE
        score = 0
        reasons = []

        # OTP check
        is_otp = False
        if champion.mastery_points >= cfg['OTP_MASTERY_THRESHOLD']:
            is_otp = True
            score += cfg['OTP_SCORE']
            reasons.append(f"OTP ({champion.mastery_points:,} pts)")

        # Recent spam check
        if champion.games_played >= cfg['RECENT_SPAM_THRESHOLD']:
            score += cfg['RECENT_SPAM_SCORE']
            reasons.append(f"Spam recent ({champion.games_played} games)")

        # Winrate bonus
        if champion.games_played >= 3:  # Minimum games for meaningful winrate
            wr_diff = champion.winrate - cfg['WINRATE_NEUTRAL']
            if wr_diff > 0:
                wr_score = int(wr_diff * cfg['WINRATE_SCORE_PER_PERCENT'])
                score += wr_score
                if wr_score > 0:
                    reasons.append(f"{champion.winrate:.0f}% WR")

        # Smurf detection
        if (champion.mastery_points < cfg['SMURF_MASTERY_MAX'] and
            champion.games_played >= 3 and
            champion.winrate >= cfg['SMURF_WR_THRESHOLD'] and
            champion.kda >= cfg['SMURF_KDA_THRESHOLD']):
            score += cfg['SMURF_SCORE']
            reasons.append("Smurf suspecte")

        return DangerScore(
            champion_id=champion.champion_id,
            champion_name=champion.champion_name,
            total_score=score,
            reasons=reasons,
            player_name=f"{player.game_name}",
            mastery_points=champion.mastery_points,
            games_played=champion.games_played,
            winrate=champion.winrate
        )

    def calculate_player_threat(self, player: PlayerData) -> float:
        """Calcule le score de menace global d'un joueur"""
        cfg = config.PLAYER_THREAT

        threat = 0.0

        # Winrate recent
        if player.recent_winrate > 50:
            threat += (player.recent_winrate - 50) * cfg['RECENT_WINRATE_WEIGHT']

        # KDA
        if player.recent_kda > 2.0:
            threat += (player.recent_kda - 2.0) * cfg['KDA_WEIGHT'] * 10

        # Rang
        rank_value = player.rank.to_lp_value()
        threat += (rank_value / 100) * cfg['RANK_WEIGHT']

        return threat

    def _aggregate_danger_scores(self, players: List[PlayerData]) -> List[DangerScore]:
        """Agrege et trie tous les danger scores"""
        all_dangers = []

        for player in players:
            for champion in player.top_champions:
                # Ne considerer que les champions joues recemment ou avec haute mastery
                if champion.games_played > 0 or champion.mastery_points > 50000:
                    danger = self.calculate_danger_score(champion, player)
                    if danger.total_score > 0:
                        all_dangers.append(danger)

        # Trier par score decroissant
        all_dangers.sort(key=lambda d: d.total_score, reverse=True)

        # Deduplicate par champion (garder le plus haut score)
        seen_champions = set()
        unique_dangers = []
        for danger in all_dangers:
            if danger.champion_id not in seen_champions:
                seen_champions.add(danger.champion_id)
                unique_dangers.append(danger)

        return unique_dangers

    def _detect_team_composition(self, players: List[PlayerData]) -> str:
        """Detecte le type de composition d'equipe (5-stack, duo, etc.)"""
        # Simplifie pour l'instant - on ne peut pas vraiment detecter les premades
        # sans analyser les historiques de matchs ensemble
        return f"{len(players)}-stack"

    def _calculate_average_elo(self, players: List[PlayerData]) -> int:
        """Calcule l'elo moyen de l'equipe"""
        if not players:
            return 0

        total_lp = sum(p.rank.to_lp_value() for p in players)
        return total_lp // len(players)

    def calculate_team_comparison(
        self,
        our_team: List[PlayerData],
        enemy_team: List[PlayerData]
    ) -> float:
        """Compare deux equipes et retourne un ratio de menace"""
        if not our_team or not enemy_team:
            return 0.0

        our_threat = sum(p.threat_score for p in our_team)
        enemy_threat = sum(p.threat_score for p in enemy_team)

        if our_threat == 0:
            return float('inf') if enemy_threat > 0 else 1.0

        return enemy_threat / our_threat
