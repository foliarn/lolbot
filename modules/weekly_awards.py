"""
Weekly Awards - Calcule les gagnants des 6 prix hebdomadaires.
Données sources : weekly_stats_cache, tilt_tracker, rank_history.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

import config

PARIS_TZ = ZoneInfo("Europe/Paris")


class WeeklyAward:
    def __init__(self, award_id: str, name: str, winner_name: str, discord_id: str,
                 stat_label: str, stat_value: str, raw_value: float):
        self.award_id = award_id
        self.name = name
        self.winner_name = winner_name
        self.discord_id = discord_id
        self.stat_label = stat_label
        self.stat_value = stat_value
        self.raw_value = raw_value


class WeeklyAwardsModule:

    def __init__(self, db_manager):
        self.db = db_manager

    async def compute_awards(self, week_start: str) -> List[WeeklyAward]:
        """
        Calcule les 6 awards pour la semaine donnée (format 'YYYY-MM-DD').
        Retourne une liste d'Award (peut être vide si pas assez de données).
        """
        users = await self.db.get_all_primary_users()
        if not users:
            return []

        # Collect data for every player
        player_data = []
        for user in users:
            row = {
                'discord_id': user['discord_id'],
                'game_name': user['game_name'],
                'puuid': user['riot_puuid'],
            }

            # Weekly stats cache
            stats = await self.db.get_all_weekly_stats(user['riot_puuid'], week_start)
            row['deaths'] = float(stats.get('deaths', {}).get('stat_value', 0))
            row['games_played'] = float(stats.get('games_played', {}).get('stat_value', 0))
            row['avg_kda'] = float(stats.get('avg_kda', {}).get('stat_value', 0))
            row['avg_kda_games'] = float(stats.get('avg_kda', {}).get('games_counted', 0))

            # LP delta for the week (from rank_history)
            row['lp_gain'] = await self._get_lp_delta(user['riot_puuid'], week_start)

            # Tilt tracker — loss streak
            tilt = await self.db.get_tilt_state(user['riot_puuid'])
            if tilt and tilt.get('streak_type') == 'loss':
                row['loss_streak'] = int(tilt.get('streak_count', 0))
            else:
                row['loss_streak'] = 0

            player_data.append(row)

        awards = []

        # 1. Inter de la semaine — most deaths
        winner = _pick(player_data, 'deaths', 'desc', min_value=1)
        if winner:
            awards.append(WeeklyAward(
                'inter', config.WEEKLY_AWARDS['inter']['name'],
                winner['game_name'], winner['discord_id'],
                'Morts', str(int(winner['deaths'])),
                winner['deaths'],
            ))

        # 2. Prix Kaizen — most LP gained
        winner = _pick(player_data, 'lp_gain', 'desc')
        if winner and winner['lp_gain'] > 0:
            awards.append(WeeklyAward(
                'kaizen', config.WEEKLY_AWARDS['kaizen']['name'],
                winner['game_name'], winner['discord_id'],
                'LP gagnés', f"+{int(winner['lp_gain'])} LP",
                winner['lp_gain'],
            ))

        # 3. Tapis rouge — longest loss streak
        winner = _pick(player_data, 'loss_streak', 'desc', min_value=1)
        if winner:
            awards.append(WeeklyAward(
                'tapis', config.WEEKLY_AWARDS['tapis']['name'],
                winner['game_name'], winner['discord_id'],
                'Défaites consécutives', str(winner['loss_streak']),
                winner['loss_streak'],
            ))

        # 4. Prix Jeudi Noir — most LP lost
        winner = _pick(player_data, 'lp_gain', 'asc')
        if winner and winner['lp_gain'] < 0:
            awards.append(WeeklyAward(
                'jeudi', config.WEEKLY_AWARDS['jeudi']['name'],
                winner['game_name'], winner['discord_id'],
                'LP perdus', f"{int(winner['lp_gain'])} LP",
                winner['lp_gain'],
            ))

        # 5. Larbin de Riot — most games played
        winner = _pick(player_data, 'games_played', 'desc', min_value=1)
        if winner:
            awards.append(WeeklyAward(
                'larbin', config.WEEKLY_AWARDS['larbin']['name'],
                winner['game_name'], winner['discord_id'],
                'Games jouées', str(int(winner['games_played'])),
                winner['games_played'],
            ))

        # 6. KDA player — best avg KDA (min 5 games)
        eligible = [p for p in player_data if p['avg_kda_games'] >= 5]
        winner = _pick(eligible, 'avg_kda', 'desc') if eligible else None
        if winner:
            awards.append(WeeklyAward(
                'kda', config.WEEKLY_AWARDS['kda']['name'],
                winner['game_name'], winner['discord_id'],
                'KDA moyen', f"{winner['avg_kda']:.2f}",
                winner['avg_kda'],
            ))

        return awards

    async def _get_lp_delta(self, puuid: str, week_start: str) -> float:
        """
        Calcule le delta LP de la semaine (lundi → maintenant) via rank_history.
        """
        # Monday 00:00 Paris → UTC naive string
        try:
            monday = datetime.strptime(week_start, '%Y-%m-%d')
            monday = monday.replace(tzinfo=PARIS_TZ)
            monday_utc = monday.astimezone(timezone.utc).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return 0.0

        from modules.leaderboard import rank_to_lp, TIER_ORDER, RANK_ORDER

        # Current rank
        current_snap = await self.db.get_latest_rank(puuid, 'RANKED_SOLO_5x5')
        if not current_snap:
            return 0.0

        current_lp = rank_to_lp(
            current_snap.get('tier', ''),
            current_snap.get('rank', ''),
            current_snap.get('league_points', 0),
        )

        # Rank at Monday
        monday_snap = await self.db.get_rank_at_time(puuid, 'RANKED_SOLO_5x5', monday_utc)
        if not monday_snap:
            return 0.0

        monday_lp = rank_to_lp(
            monday_snap.get('tier', ''),
            monday_snap.get('rank', ''),
            monday_snap.get('league_points', 0),
        )

        return float(current_lp - monday_lp)


def _pick(
    players: List[Dict[str, Any]],
    stat: str,
    order: str,
    min_value: float = None,
) -> Optional[Dict[str, Any]]:
    """Retourne le joueur avec la valeur la plus haute (desc) ou basse (asc) pour `stat`."""
    eligible = [p for p in players if stat in p]
    if min_value is not None:
        eligible = [p for p in eligible if p[stat] >= min_value]
    if not eligible:
        return None
    return sorted(eligible, key=lambda p: p[stat], reverse=(order == 'desc'))[0]
