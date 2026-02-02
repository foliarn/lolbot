"""
Module pour le Clash Scout - Analyse prédictive d'équipe
"""
import asyncio
from typing import Dict, Any, List, Optional
from collections import defaultdict

from config import DANGER_SCORE, ROLE_DETECTION
from utils.embeds import create_clash_embed
from utils.helpers import calculate_kda


class ClashScout:
    """Analyse une équipe Clash adverse et recommande des bans"""

    def __init__(self, riot_api, data_dragon, db_manager):
        self.api = riot_api
        self.data_dragon = data_dragon
        self.db = db_manager

    async def scout_team(
        self,
        discord_id: Optional[str] = None,
        riot_id: Optional[str] = None,
        tag: Optional[str] = None,
        alias: Optional[str] = None
    ):
        """
        Scout une équipe Clash et retourne les recommandations de bans

        Returns:
            Embed Discord avec l'analyse
        """
        # Résoudre le summoner ID
        if discord_id and not riot_id:
            user = await self.db.get_user(discord_id, alias)
            if not user:
                return None, "Aucun compte lié. Utilisez `/link` d'abord."
            summoner_id = user['summoner_id']
            puuid = user['riot_puuid']
        elif riot_id and tag:
            account = await self.api.get_account_by_riot_id(riot_id, tag)
            if not account:
                return None, "Compte Riot introuvable."
            puuid = account['puuid']
            summoner = await self.api.get_summoner_by_puuid(puuid)
            summoner_id = summoner['id']
        else:
            return None, "Fournissez un RiotID ou liez votre compte."

        # Récupérer l'équipe Clash
        clash_data = await self.api.get_clash_player(summoner_id)
        if not clash_data or len(clash_data) == 0:
            return None, "Aucune équipe Clash active trouvée."

        team_id = clash_data[0].get('teamId')
        if not team_id:
            return None, "Impossible de récupérer l'ID de l'équipe."

        # Récupérer les détails de l'équipe
        team_data = await self.api.get_clash_team(team_id)
        if not team_data:
            return None, "Impossible de récupérer les détails de l'équipe."

        team_name = team_data.get('name', 'Équipe Inconnue')
        players = team_data.get('players', [])

        if len(players) == 0:
            return None, "L'équipe ne contient aucun joueur."

        # Analyser chaque joueur en parallèle
        print(f"[ClashScout] Analyse de {len(players)} joueurs...")
        player_analyses = await asyncio.gather(
            *[self._analyze_player(player) for player in players]
        )

        # Filtrer les joueurs invalides
        player_analyses = [p for p in player_analyses if p is not None]

        if not player_analyses:
            return None, "Impossible d'analyser les joueurs de l'équipe."

        # Calculer les bans recommandés
        bans = self._calculate_bans(player_analyses)

        # Créer l'embed
        embed = create_clash_embed(team_name, bans, player_analyses)
        return embed, None

    async def _analyze_player(self, player: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyse un joueur et retourne ses champions dangereux

        Returns:
            {
                'name': str,
                'role': str,
                'champions': [{'name': str, 'score': int, 'reason': str, 'games': int}],
                'profile': str
            }
        """
        summoner_id = player.get('summonerId')
        puuid = player.get('puuid')  # Peut ne pas être disponible
        position = player.get('position', 'UNKNOWN')

        if not summoner_id:
            return None

        # Récupérer le PUUID si nécessaire
        if not puuid:
            summoner = await self.api.get_summoner_by_puuid(summoner_id)
            if summoner:
                puuid = summoner.get('puuid')

        if not puuid:
            return None

        # Récupérer les masteries
        masteries = await self.api.get_champion_masteries(puuid, 10)

        # Récupérer l'historique de matchs (SoloQ + Flex + Clash)
        match_ids_solo = await self.api.get_match_history(puuid, count=10, queue=420) or []
        match_ids_flex = await self.api.get_match_history(puuid, count=10, queue=440) or []
        match_ids_clash = await self.api.get_match_history(puuid, count=5, queue=700) or []

        all_match_ids = list(set(match_ids_solo + match_ids_flex + match_ids_clash))[:DANGER_SCORE['RECENT_GAMES_COUNT']]

        # Récupérer les détails des matchs
        match_details = await asyncio.gather(
            *[self.api.get_match(mid) for mid in all_match_ids]
        )
        match_details = [m for m in match_details if m is not None]

        # Analyser les données
        champion_stats = self._analyze_matches(match_details, puuid)
        role_distribution = self._detect_roles(match_details, puuid)

        # Calculer les scores de danger
        champion_scores = []
        for champ_id, stats in champion_stats.items():
            score, reason = await self._calculate_danger_score(
                champ_id,
                stats,
                masteries
            )

            champ_name = await self.data_dragon.get_champion_name_by_id(champ_id)

            champion_scores.append({
                'name': champ_name or f"Champion {champ_id}",
                'score': score,
                'reason': reason,
                'games': stats['games']
            })

        # Trier par score
        champion_scores.sort(key=lambda x: x['score'], reverse=True)

        # Déterminer le rôle principal
        main_role = max(role_distribution, key=role_distribution.get) if role_distribution else position

        # Déterminer le profil du joueur
        profile = self._determine_profile(champion_scores, role_distribution)

        return {
            'name': f"Player {summoner_id[:4]}",
            'role': main_role,
            'role_distribution': role_distribution,
            'champions': champion_scores[:5],
            'profile': profile
        }

    def _analyze_matches(self, matches: List[Dict[str, Any]], puuid: str) -> Dict[int, Dict[str, Any]]:
        """
        Analyse l'historique de matchs et retourne les stats par champion

        Returns:
            {champion_id: {'games': int, 'wins': int, 'kills': int, 'deaths': int, 'assists': int}}
        """
        champion_stats = defaultdict(lambda: {'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0})

        for match in matches:
            if not match:
                continue

            participants = match['info']['participants']
            for p in participants:
                if p['puuid'] == puuid:
                    champ_id = p['championId']
                    champion_stats[champ_id]['games'] += 1
                    champion_stats[champ_id]['wins'] += 1 if p['win'] else 0
                    champion_stats[champ_id]['kills'] += p['kills']
                    champion_stats[champ_id]['deaths'] += p['deaths']
                    champion_stats[champ_id]['assists'] += p['assists']
                    break

        return dict(champion_stats)

    def _detect_roles(self, matches: List[Dict[str, Any]], puuid: str) -> Dict[str, int]:
        """Détecte les rôles joués par le joueur"""
        role_count = defaultdict(int)

        for match in matches:
            if not match:
                continue

            participants = match['info']['participants']
            for p in participants:
                if p['puuid'] == puuid:
                    role = p.get('teamPosition', 'UNKNOWN')
                    if role:
                        role_count[role] += 1
                    break

        return dict(role_count)

    async def _calculate_danger_score(
        self,
        champ_id: int,
        stats: Dict[str, Any],
        masteries: List[Dict[str, Any]]
    ) -> tuple[int, str]:
        """
        Calcule le danger score d'un champion

        Returns:
            (score, reason)
        """
        score = 0
        reasons = []

        games = stats['games']
        wins = stats['wins']
        winrate = (wins / games * 100) if games > 0 else 0

        # Récupérer la maîtrise
        mastery_points = 0
        for m in masteries or []:
            if m['championId'] == champ_id:
                mastery_points = m['championPoints']
                break

        # Critère OTP
        if mastery_points >= DANGER_SCORE['OTP_MASTERY_THRESHOLD']:
            score += DANGER_SCORE['OTP_SCORE']
            reasons.append(f"OTP ({mastery_points:,} pts)")

        # Critère Récence
        if games >= DANGER_SCORE['RECENT_SPAM_THRESHOLD']:
            score += DANGER_SCORE['RECENT_SPAM_SCORE']
            reasons.append(f"Spam récent ({games} games)")

        # Critère Winrate
        if games > 0 and winrate > DANGER_SCORE['WINRATE_NEUTRAL']:
            wr_bonus = int((winrate - DANGER_SCORE['WINRATE_NEUTRAL']) * DANGER_SCORE['WINRATE_SCORE_PER_PERCENT'])
            score += wr_bonus
            reasons.append(f"{int(winrate)}% WR")

        # Critère Smurf
        if (mastery_points < DANGER_SCORE['SMURF_MASTERY_MAX'] and
            winrate >= DANGER_SCORE['SMURF_WR_THRESHOLD'] and
            games >= 3):

            # Calculer le KDA
            kills = stats['kills']
            deaths = stats['deaths']
            assists = stats['assists']
            kda_ratio, _ = calculate_kda(kills, deaths, assists)

            if kda_ratio >= DANGER_SCORE['SMURF_KDA_THRESHOLD']:
                score += DANGER_SCORE['SMURF_SCORE']
                reasons.append("⚠️ Smurf détecté")

        reason = " + ".join(reasons) if reasons else "Standard"
        return score, reason

    def _determine_profile(
        self,
        champion_scores: List[Dict[str, Any]],
        role_distribution: Dict[str, int]
    ) -> str:
        """Détermine le profil du joueur"""
        if not champion_scores:
            return "Pas de données"

        # Vérifier si OTP
        if champion_scores[0]['score'] >= DANGER_SCORE['OTP_SCORE'] * 1.5:
            return f"OTP {champion_scores[0]['name']}"

        # Vérifier si flex picker
        total_games = sum(role_distribution.values())
        if total_games > 0:
            main_role_percentage = max(role_distribution.values()) / total_games * 100
            if main_role_percentage < ROLE_DETECTION['ROLE_THRESHOLD']:
                return "Flex Picker"

        # Profil standard
        return "Pool standard"

    def _calculate_bans(self, player_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calcule les meilleurs bans basés sur l'analyse de l'équipe

        Returns:
            [{'champion': str, 'score': int, 'reason': str}]
        """
        all_threats = []

        for player in player_analyses:
            role = player.get('role', 'UNKNOWN')
            role_dist = player.get('role_distribution', {})

            for champ in player['champions']:
                # Ajouter le contexte du rôle si le joueur est flex
                if len(role_dist) > 1:
                    total = sum(role_dist.values())
                    role_percentages = {r: (c / total * 100) for r, c in role_dist.items()}
                    role_info = " / ".join([f"{r} ({int(p)}%)" for r, p in sorted(role_percentages.items(), key=lambda x: x[1], reverse=True)])
                    reason = f"{champ['reason']} - {role_info}"
                else:
                    reason = f"{champ['reason']} - {role}"

                all_threats.append({
                    'champion': champ['name'],
                    'score': champ['score'],
                    'reason': reason
                })

        # Éliminer les doublons (même champion)
        unique_threats = {}
        for threat in all_threats:
            champ = threat['champion']
            if champ not in unique_threats or threat['score'] > unique_threats[champ]['score']:
                unique_threats[champ] = threat

        # Trier par score et retourner le top 3
        sorted_threats = sorted(unique_threats.values(), key=lambda x: x['score'], reverse=True)
        return sorted_threats[:3]
