"""
Module Weekly Challenges - Gestion des defis hebdomadaires
"""
import random
import traceback
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import discord

import config

PARIS_TZ = ZoneInfo("Europe/Paris")

class WeeklyChallenges:
    """Gestion des challenges hebdomadaires"""

    def __init__(self, riot_api, db_manager, bot):
        self.api = riot_api
        self.db = db_manager
        self.bot = bot

    def get_current_week_start(self) -> str:
        """Retourne la date du lundi de la semaine courante (format YYYY-MM-DD)"""
        now = datetime.now(PARIS_TZ)
        monday = now - timedelta(days=now.weekday())
        return monday.strftime('%Y-%m-%d')

    async def initialize_weekly_challenges(self) -> tuple[List[Dict[str, Any]], bool]:
        """
        Initialise les challenges pour une nouvelle semaine.
        Retourne (liste des challenges, is_new).
        """
        week_start = self.get_current_week_start()

        # Check if challenges already exist for this week
        existing = await self.db.get_weekly_challenges(week_start)
        if existing:
            print(f"[Challenges] Challenges already exist for week {week_start}")
            return existing, False

        created_challenges = []

        # Create global challenges
        global_ids = list(config.GLOBAL_CHALLENGES.keys())
        selected_global = random.sample(
            global_ids,
            min(config.GLOBAL_CHALLENGES_PER_WEEK, len(global_ids))
        )

        for challenge_id in selected_global:
            await self.db.create_weekly_challenge(
                challenge_id=challenge_id,
                challenge_type='global',
                week_start=week_start,
                assigned_to=None
            )
            created_challenges.append({
                'id': challenge_id,
                'type': 'global',
                **config.GLOBAL_CHALLENGES[challenge_id]
            })

        # Create personal challenges for each registered user
        users = await self.db.get_all_primary_users()
        personal_ids = list(config.PERSONAL_CHALLENGES.keys())

        for user in users:
            discord_id = user['discord_id']

            # Randomly assign personal challenges
            selected_personal = random.sample(
                personal_ids,
                min(config.PERSONAL_CHALLENGES_PER_PLAYER, len(personal_ids))
            )

            for challenge_id in selected_personal:
                await self.db.create_weekly_challenge(
                    challenge_id=challenge_id,
                    challenge_type='personal',
                    week_start=week_start,
                    assigned_to=discord_id
                )

        print(f"[Challenges] Created {len(created_challenges)} global challenges for week {week_start}")
        return created_challenges, True

    async def check_all_players(self) -> List[Dict[str, Any]]:
        """
        Verifie la progression de tous les joueurs enregistres.
        Retourne la liste des completions a annoncer.
        """
        completions = []
        week_start = self.get_current_week_start()

        users = await self.db.get_all_primary_users()

        for user in users:
            discord_id = user['discord_id']
            riot_puuid = user['riot_puuid']
            game_name = user['game_name']

            # Update weekly stats from new matches
            latest_match = await self._update_player_stats(riot_puuid, week_start)

            # Check challenge completions
            player_completions = await self._check_player_challenges(
                discord_id=discord_id,
                riot_puuid=riot_puuid,
                game_name=game_name,
                tag_line=user['tag_line'],
                week_start=week_start,
                latest_match_id=latest_match
            )

            completions.extend(player_completions)

        return completions

    async def _update_player_stats(self, riot_puuid: str, week_start: str) -> Optional[str]:
        """Met a jour les stats hebdomadaires ET split d'un joueur depuis ses matchs recents.
        Retourne le dernier match_id traite, ou None."""
        try:
            season_split = config.CURRENT_SEASON_SPLIT

            # Get cached weekly stats to find last processed match
            cached_weekly = await self.db.get_all_weekly_stats(riot_puuid, week_start)
            cached_split = await self.db.get_all_split_stats(riot_puuid, season_split)

            last_match_id = None
            if cached_weekly:
                for stat_data in cached_weekly.values():
                    if stat_data.get('last_match_id'):
                        last_match_id = stat_data['last_match_id']
                        break

            # Compute season start timestamp for API filtering
            season_start_ts = int(
                datetime.strptime(config.SEASON_START_DATE, '%Y-%m-%d')
                .replace(tzinfo=PARIS_TZ)
                .timestamp()
            )

            # Fetch all ranked matches since season start (paginated, 100 per page)
            all_match_ids = []
            page_start = 0
            while True:
                batch = await self.api.get_match_history(
                    puuid=riot_puuid,
                    start=page_start,
                    count=100,
                    queue=420,  # Ranked Solo/Duo
                    start_time=season_start_ts
                )
                if not batch:
                    break
                all_match_ids.extend(batch)
                if len(batch) < 100:
                    break
                page_start += 100

            if not all_match_ids:
                return None

            # Find new matches (stop at last processed match)
            new_match_ids = []
            for match_id in all_match_ids:
                if match_id == last_match_id:
                    break
                new_match_ids.append(match_id)

            if not new_match_ids:
                return None

            # Process new matches (oldest first)
            new_match_ids.reverse()

            # Initialize all stats from cache or defaults
            def get_weekly(key, default=0):
                return cached_weekly.get(key, {}).get('stat_value', default)

            def get_split(key, default=0):
                return cached_split.get(key, {}).get('stat_value', default)

            stats = {
                # Cumulative stats (sum across all games)
                'gold_earned': get_weekly('gold_earned'),
                'gold_spent': get_weekly('gold_spent'),
                'kills': get_weekly('kills'),
                'deaths': get_weekly('deaths'),
                'assists': get_weekly('assists'),
                'wins': get_weekly('wins'),
                'losses': get_weekly('losses'),
                'games_played': get_weekly('games_played'),

                # Damage
                'damage_dealt': get_weekly('damage_dealt'),
                'damage_dealt_physical': get_weekly('damage_dealt_physical'),
                'damage_dealt_magic': get_weekly('damage_dealt_magic'),
                'damage_dealt_true': get_weekly('damage_dealt_true'),
                'damage_taken': get_weekly('damage_taken'),

                # Objectives
                'turret_kills': get_weekly('turret_kills'),
                'turret_takedowns': get_weekly('turret_takedowns'),
                'inhibitor_kills': get_weekly('inhibitor_kills'),
                'dragon_kills': get_weekly('dragon_kills'),
                'baron_kills': get_weekly('baron_kills'),
                'rift_herald_kills': get_weekly('rift_herald_kills'),

                # Vision
                'vision_score_total': get_weekly('vision_score_total'),
                'wards_placed': get_weekly('wards_placed'),
                'wards_killed': get_weekly('wards_killed'),
                'control_wards_placed': get_weekly('control_wards_placed'),

                # Farm
                'cs_total': get_weekly('cs_total'),
                'jungle_cs': get_weekly('jungle_cs'),

                # Multi-kills
                'double_kills': get_weekly('double_kills'),
                'triple_kills': get_weekly('triple_kills'),
                'quadra_kills': get_weekly('quadra_kills'),
                'penta_kills': get_weekly('penta_kills'),

                # First objectives
                'first_blood_kills': get_weekly('first_blood_kills'),
                'first_blood_assists': get_weekly('first_blood_assists'),
                'first_tower_kills': get_weekly('first_tower_kills'),

                # CC
                'cc_time': get_weekly('cc_time'),

                # Time
                'time_played': get_weekly('time_played'),
                'longest_life': get_weekly('longest_life'),
                'time_dead': get_weekly('time_dead'),

                # Per-game records (max/min)
                'max_kills_game': get_weekly('max_kills_game'),
                'max_deaths_game': get_weekly('max_deaths_game'),
                'max_cs_game': get_weekly('max_cs_game'),
                'max_damage_game': get_weekly('max_damage_game'),
                'max_gold_game': get_weekly('max_gold_game'),
                'max_vision_game': get_weekly('max_vision_game'),
                'min_vision_game': get_weekly('min_vision_game', 999),
                'min_damage_game': get_weekly('min_damage_game', 999999),
                'max_cs_per_min': get_weekly('max_cs_per_min'),
                'max_damage_taken_game': get_weekly('max_damage_taken_game'),

                # Special achievements (count of games where condition met)
                'games_with_penta': get_weekly('games_with_penta'),
                'games_with_quadra': get_weekly('games_with_quadra'),
                'games_with_triple': get_weekly('games_with_triple'),
                'games_with_double': get_weekly('games_with_double'),
                'games_11cs_min': get_weekly('games_11cs_min'),
                'games_zero_deaths': get_weekly('games_zero_deaths'),
                'games_20_kills': get_weekly('games_20_kills'),
                'win_no_defensive': get_weekly('win_no_defensive'),
                'games_baron_and_dragon': get_weekly('games_baron_and_dragon'),

                # Unique tracking
                'unique_champ_wins': get_weekly('unique_champ_wins'),
            }
            games_counted = int(cached_weekly.get('games_played', {}).get('games_counted', 0))

            # Initialize split stats (same structure, different source)
            split_stats = {
                'gold_earned': get_split('gold_earned'),
                'gold_spent': get_split('gold_spent'),
                'kills': get_split('kills'),
                'deaths': get_split('deaths'),
                'assists': get_split('assists'),
                'wins': get_split('wins'),
                'losses': get_split('losses'),
                'games_played': get_split('games_played'),
                'damage_dealt': get_split('damage_dealt'),
                'damage_taken': get_split('damage_taken'),
                'turret_kills': get_split('turret_kills'),
                'turret_takedowns': get_split('turret_takedowns'),
                'dragon_kills': get_split('dragon_kills'),
                'baron_kills': get_split('baron_kills'),
                'vision_score_total': get_split('vision_score_total'),
                'wards_placed': get_split('wards_placed'),
                'wards_killed': get_split('wards_killed'),
                'control_wards_placed': get_split('control_wards_placed'),
                'cs_total': get_split('cs_total'),
                'jungle_cs': get_split('jungle_cs'),
                'double_kills': get_split('double_kills'),
                'triple_kills': get_split('triple_kills'),
                'quadra_kills': get_split('quadra_kills'),
                'penta_kills': get_split('penta_kills'),
                'first_blood_kills': get_split('first_blood_kills'),
                'first_tower_kills': get_split('first_tower_kills'),
                'cc_time': get_split('cc_time'),
                'time_played': get_split('time_played'),
                'games_with_penta': get_split('games_with_penta'),
                'games_with_quadra': get_split('games_with_quadra'),
                'games_zero_deaths': get_split('games_zero_deaths'),
                'games_20_kills': get_split('games_20_kills'),
                'games_11cs_min': get_split('games_11cs_min'),
                'unique_champ_wins': get_split('unique_champ_wins'),
                'games_baron_and_dragon': get_split('games_baron_and_dragon'),
                # Max records (for split)
                'max_kills_game': get_split('max_kills_game'),
                'max_cs_per_min': get_split('max_cs_per_min'),
                'max_damage_game': get_split('max_damage_game'),
            }
            split_games_counted = int(cached_split.get('games_played', {}).get('games_counted', 0))

            # Track champions won on (for split)
            # Stored as comma-separated string in last_match_id (TEXT column)
            split_champs_won = set()
            split_champs_str = cached_split.get('champs_won_list', {}).get('last_match_id', '')
            if split_champs_str and isinstance(split_champs_str, str):
                split_champs_won = set(split_champs_str.split(','))
                split_champs_won.discard('')

            # Track champions won on (for week)
            champs_won = set()
            champs_won_str = cached_weekly.get('champs_won_list', {}).get('last_match_id', '')
            if champs_won_str and isinstance(champs_won_str, str):
                champs_won = set(champs_won_str.split(','))
                champs_won.discard('')

            # Process each new match
            for match_id in new_match_ids:
                match_data = await self.api.get_match(match_id)
                if not match_data:
                    continue

                # Check if match is from this week
                match_timestamp = match_data.get('info', {}).get('gameCreation', 0) / 1000
                match_date = datetime.fromtimestamp(match_timestamp, PARIS_TZ)
                week_start_date = datetime.strptime(week_start, '%Y-%m-%d').replace(tzinfo=PARIS_TZ)

                if match_date < week_start_date:
                    continue

                # Find player data
                participants = match_data.get('info', {}).get('participants', [])
                player_data = None
                for p in participants:
                    if p.get('puuid') == riot_puuid:
                        player_data = p
                        break

                if not player_data:
                    continue

                # Get game duration in minutes
                game_duration_sec = match_data.get('info', {}).get('gameDuration', 0)
                game_duration_min = game_duration_sec / 60 if game_duration_sec > 0 else 1

                # Extract all stats from match
                won = player_data.get('win', False)
                kills = player_data.get('kills', 0)
                deaths = player_data.get('deaths', 0)
                assists = player_data.get('assists', 0)
                gold_earned = player_data.get('goldEarned', 0)
                gold_spent = player_data.get('goldSpent', 0)

                damage_dealt = player_data.get('totalDamageDealtToChampions', 0)
                damage_physical = player_data.get('physicalDamageDealtToChampions', 0)
                damage_magic = player_data.get('magicDamageDealtToChampions', 0)
                damage_true = player_data.get('trueDamageDealtToChampions', 0)
                damage_taken = player_data.get('totalDamageTaken', 0)

                turret_kills = player_data.get('turretKills', 0)
                turret_takedowns = player_data.get('turretTakedowns', 0)
                inhibitor_kills = player_data.get('inhibitorKills', 0)
                dragon_kills = player_data.get('dragonKills', 0)
                baron_kills = player_data.get('baronKills', 0)
                rift_herald_kills = player_data.get('challenges', {}).get('riftHeraldTakedowns', 0)

                vision_score = player_data.get('visionScore', 0)
                wards_placed = player_data.get('wardsPlaced', 0)
                wards_killed = player_data.get('wardsKilled', 0)
                control_wards = player_data.get('detectorWardsPlaced', 0)

                cs = player_data.get('totalMinionsKilled', 0)
                jungle_cs = player_data.get('neutralMinionsKilled', 0)
                total_cs = cs + jungle_cs
                cs_per_min = total_cs / game_duration_min if game_duration_min > 0 else 0

                double_kills = player_data.get('doubleKills', 0)
                triple_kills = player_data.get('tripleKills', 0)
                quadra_kills = player_data.get('quadraKills', 0)
                penta_kills = player_data.get('pentaKills', 0)

                first_blood_kill = player_data.get('firstBloodKill', False)
                first_blood_assist = player_data.get('firstBloodAssist', False)
                first_tower_kill = player_data.get('firstTowerKill', False)

                cc_time = player_data.get('timeCCingOthers', 0)
                longest_life = player_data.get('longestTimeSpentLiving', 0)
                time_dead = player_data.get('totalTimeSpentDead', 0)

                champion_id = player_data.get('championId', 0)

                # Update cumulative stats (WEEKLY)
                stats['gold_earned'] += gold_earned
                stats['gold_spent'] += gold_spent
                stats['kills'] += kills
                stats['deaths'] += deaths
                stats['assists'] += assists
                stats['games_played'] += 1
                games_counted += 1

                if won:
                    stats['wins'] += 1
                    champs_won.add(str(champion_id))
                else:
                    stats['losses'] += 1

                stats['damage_dealt'] += damage_dealt
                stats['damage_dealt_physical'] += damage_physical
                stats['damage_dealt_magic'] += damage_magic
                stats['damage_dealt_true'] += damage_true
                stats['damage_taken'] += damage_taken

                stats['turret_kills'] += turret_kills
                stats['turret_takedowns'] += turret_takedowns
                stats['inhibitor_kills'] += inhibitor_kills
                stats['dragon_kills'] += dragon_kills
                stats['baron_kills'] += baron_kills
                stats['rift_herald_kills'] += rift_herald_kills

                stats['vision_score_total'] += vision_score
                stats['wards_placed'] += wards_placed
                stats['wards_killed'] += wards_killed
                stats['control_wards_placed'] += control_wards

                stats['cs_total'] += total_cs
                stats['jungle_cs'] += jungle_cs

                stats['double_kills'] += double_kills
                stats['triple_kills'] += triple_kills
                stats['quadra_kills'] += quadra_kills
                stats['penta_kills'] += penta_kills

                if first_blood_kill:
                    stats['first_blood_kills'] += 1
                if first_blood_assist:
                    stats['first_blood_assists'] += 1
                if first_tower_kill:
                    stats['first_tower_kills'] += 1

                stats['cc_time'] += cc_time
                stats['time_played'] += game_duration_sec
                stats['time_dead'] += time_dead
                if longest_life > stats['longest_life']:
                    stats['longest_life'] = longest_life

                # Update max/min records (WEEKLY)
                if kills > stats['max_kills_game']:
                    stats['max_kills_game'] = kills
                if deaths > stats['max_deaths_game']:
                    stats['max_deaths_game'] = deaths
                if total_cs > stats['max_cs_game']:
                    stats['max_cs_game'] = total_cs
                if damage_dealt > stats['max_damage_game']:
                    stats['max_damage_game'] = damage_dealt
                if gold_earned > stats['max_gold_game']:
                    stats['max_gold_game'] = gold_earned
                if vision_score > stats['max_vision_game']:
                    stats['max_vision_game'] = vision_score
                if vision_score < stats['min_vision_game']:
                    stats['min_vision_game'] = vision_score
                if damage_dealt < stats['min_damage_game']:
                    stats['min_damage_game'] = damage_dealt
                if cs_per_min > stats['max_cs_per_min']:
                    stats['max_cs_per_min'] = cs_per_min
                if damage_taken > stats['max_damage_taken_game']:
                    stats['max_damage_taken_game'] = damage_taken

                # Special achievements (WEEKLY)
                if penta_kills > 0:
                    stats['games_with_penta'] += 1
                if quadra_kills > 0:
                    stats['games_with_quadra'] += 1
                if triple_kills > 0:
                    stats['games_with_triple'] += 1
                if double_kills > 0:
                    stats['games_with_double'] += 1
                if cs_per_min >= 11:
                    stats['games_11cs_min'] += 1
                if deaths == 0:
                    stats['games_zero_deaths'] += 1
                if kills >= 20:
                    stats['games_20_kills'] += 1
                if baron_kills > 0 and dragon_kills > 0:
                    stats['games_baron_and_dragon'] += 1

                # ===================== SPLIT STATS =====================
                split_stats['gold_earned'] += gold_earned
                split_stats['gold_spent'] += gold_spent
                split_stats['kills'] += kills
                split_stats['deaths'] += deaths
                split_stats['assists'] += assists
                split_stats['games_played'] += 1
                split_games_counted += 1

                if won:
                    split_stats['wins'] += 1
                    split_champs_won.add(str(champion_id))
                else:
                    split_stats['losses'] += 1

                split_stats['damage_dealt'] += damage_dealt
                split_stats['damage_taken'] += damage_taken
                split_stats['turret_kills'] += turret_kills
                split_stats['turret_takedowns'] += turret_takedowns
                split_stats['dragon_kills'] += dragon_kills
                split_stats['baron_kills'] += baron_kills
                split_stats['vision_score_total'] += vision_score
                split_stats['wards_placed'] += wards_placed
                split_stats['wards_killed'] += wards_killed
                split_stats['control_wards_placed'] += control_wards
                split_stats['cs_total'] += total_cs
                split_stats['jungle_cs'] += jungle_cs
                split_stats['double_kills'] += double_kills
                split_stats['triple_kills'] += triple_kills
                split_stats['quadra_kills'] += quadra_kills
                split_stats['penta_kills'] += penta_kills
                split_stats['cc_time'] += cc_time
                split_stats['time_played'] += game_duration_sec

                if first_blood_kill:
                    split_stats['first_blood_kills'] += 1
                if first_tower_kill:
                    split_stats['first_tower_kills'] += 1

                # Max records (SPLIT)
                if kills > split_stats['max_kills_game']:
                    split_stats['max_kills_game'] = kills
                if cs_per_min > split_stats['max_cs_per_min']:
                    split_stats['max_cs_per_min'] = cs_per_min
                if damage_dealt > split_stats['max_damage_game']:
                    split_stats['max_damage_game'] = damage_dealt

                # Special achievements (SPLIT)
                if penta_kills > 0:
                    split_stats['games_with_penta'] += 1
                if quadra_kills > 0:
                    split_stats['games_with_quadra'] += 1
                if deaths == 0:
                    split_stats['games_zero_deaths'] += 1
                if kills >= 20:
                    split_stats['games_20_kills'] += 1
                if cs_per_min >= 11:
                    split_stats['games_11cs_min'] += 1
                if baron_kills > 0 and dragon_kills > 0:
                    split_stats['games_baron_and_dragon'] += 1

                # Win without defensive items
                if won:
                    has_defensive = self._check_defensive_items(player_data)
                    if not has_defensive:
                        stats['win_no_defensive'] += 1

            # Update unique champs won count
            stats['unique_champ_wins'] = len(champs_won)
            split_stats['unique_champ_wins'] = len(split_champs_won)

            # Save all stats
            latest_match = new_match_ids[-1] if new_match_ids else last_match_id

            # Save WEEKLY stats
            for stat_type, value in stats.items():
                await self.db.update_weekly_stat(
                    riot_puuid=riot_puuid,
                    week_start=week_start,
                    stat_type=stat_type,
                    stat_value=float(value),
                    games_counted=games_counted,
                    last_match_id=latest_match
                )

            # Save champs won list as comma-separated string in last_match_id
            await self.db.update_weekly_stat(
                riot_puuid=riot_puuid,
                week_start=week_start,
                stat_type='champs_won_list',
                stat_value=0,
                games_counted=games_counted,
                last_match_id=','.join(champs_won) if champs_won else ''
            )

            # Save SPLIT stats
            for stat_type, value in split_stats.items():
                await self.db.update_split_stat(
                    riot_puuid=riot_puuid,
                    season_split=season_split,
                    stat_type=stat_type,
                    stat_value=float(value),
                    games_counted=split_games_counted,
                    last_match_id=latest_match
                )

            # Save split champs won list
            await self.db.update_split_stat(
                riot_puuid=riot_puuid,
                season_split=season_split,
                stat_type='champs_won_list',
                stat_value=0,
                games_counted=split_games_counted,
                last_match_id=','.join(split_champs_won) if split_champs_won else ''
            )

            return latest_match

        except Exception as e:
            print(f"[Challenges] Error updating stats for {riot_puuid}: {e}")
            traceback.print_exc()
            return None

    def _check_defensive_items(self, player_data: Dict) -> bool:
        """Verifie si le joueur a des items defensifs"""
        # Check items (item0-item6)
        for i in range(7):
            item_id = player_data.get(f'item{i}', 0)
            if item_id == 0:
                continue

            # Common defensive items by ID
            # This is a simplified check - covers most tank/defensive items
            defensive_items = {
                # Boots
                3047, 3111,  # Plated Steelcaps, Mercury's Treads
                # Armor items
                3075, 3076, 3077, 3143, 3110, 3068, 3742,  # Thornmail, Randuin's, Frozen Heart, Sunfire, Dead Man's
                # MR items
                3065, 3102, 3156, 3155,  # Spirit Visage, Banshee's, Maw, Hexdrinker
                # Health items
                3083, 3084, 3748,  # Warmog's, Titanic Hydra
                # Shield/Utility
                3190, 3193, 3026,  # Locket, Gargoyle, Guardian Angel
                # Tank Mythics
                6662, 6664, 6665, 6667,  # Iceborn, Turbo Chemtank, Jak'Sho, Radiant Virtue
                # Support items with health
                3109, 3107, 2065,  # Knight's Vow, Redemption, Shurelya's
            }
            if item_id in defensive_items:
                return True

        return False

    async def _check_player_challenges(
        self,
        discord_id: str,
        riot_puuid: str,
        game_name: str,
        tag_line: str,
        week_start: str,
        latest_match_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Verifie si un joueur a complete des challenges"""
        completions = []

        # Get player's weekly AND split stats
        weekly_stats = await self.db.get_all_weekly_stats(riot_puuid, week_start)
        split_stats = await self.db.get_all_split_stats(riot_puuid, config.CURRENT_SEASON_SPLIT)

        # Get challenges for this player
        challenges = await self.db.get_weekly_challenges(week_start, discord_id)

        for challenge_row in challenges:
            challenge_id = challenge_row['challenge_id']
            challenge_type = challenge_row['challenge_type']

            # Check if already completed
            existing = await self.db.get_challenge_completion(
                challenge_id, week_start, discord_id
            )
            if existing:
                continue

            # Get challenge definition
            if challenge_type == 'global':
                challenge_def = config.GLOBAL_CHALLENGES.get(challenge_id)
            else:
                challenge_def = config.PERSONAL_CHALLENGES.get(challenge_id)

            if not challenge_def:
                continue

            # Use split stats if scope is 'split', otherwise use weekly
            scope = challenge_def.get('scope', 'weekly')
            stats = split_stats if scope == 'split' else weekly_stats

            # Check completion
            completed, multiplier = self._check_challenge_completion(
                challenge_def, stats
            )

            if completed:
                # Check if first to complete (for global)
                is_first = False
                if challenge_type == 'global':
                    existing_completions = await self.db.get_challenge_completions_for_week(
                        challenge_id, week_start
                    )
                    is_first = len(existing_completions) == 0

                # Calculate points
                base_points = config.CHALLENGE_POINTS.get(
                    challenge_def.get('difficulty', 'medium'),
                    20
                )
                points = int(base_points * multiplier)

                if is_first:
                    points = int(points * config.FIRST_COMPLETION_BONUS)

                # Record completion
                await self.db.record_challenge_completion(
                    challenge_id=challenge_id,
                    week_start=week_start,
                    discord_id=discord_id,
                    is_first=is_first,
                    points_awarded=points
                )

                # Add points to leaderboard
                await self.db.add_challenge_points(
                    discord_id=discord_id,
                    season_split=config.CURRENT_SEASON_SPLIT,
                    points=points
                )

                completions.append({
                    'discord_id': discord_id,
                    'game_name': game_name,
                    'tag_line': tag_line,
                    'challenge_id': challenge_id,
                    'challenge_name': challenge_def.get('name', challenge_id),
                    'challenge_type': challenge_type,
                    'is_first': is_first,
                    'points': points,
                    'description': challenge_def.get('description', ''),
                    'latest_match_id': latest_match_id,
                })

        return completions

    def _check_challenge_completion(
        self,
        challenge_def: Dict,
        stats: Dict[str, Dict]
    ) -> Tuple[bool, float]:
        """
        Verifie si un challenge est complete.
        Retourne (completed, multiplier).

        Supports:
        - Single condition: {'stat': 'kills', 'op': '>=', 'value': 100}
        - Multiple conditions (AND): {'conditions': [...], 'logic': 'and'}
        - Multiple conditions (OR): {'conditions': [...], 'logic': 'or'}
        - Legacy format: {'stat_type': 'gold', 'target': 500000}
        - Computed stats: 'avg_kda', 'weekly_winrate', 'cs_per_min_avg'
        """
        multiplier = 1.0

        # Check minimum games requirement
        min_games = challenge_def.get('min_games', 0)
        games_played = stats.get('games_played', {}).get('stat_value', 0)
        if min_games > 0 and games_played < min_games:
            return False, 1.0

        # New format with conditions array
        if 'conditions' in challenge_def:
            return self._check_multi_conditions(challenge_def, stats)

        # New format with single condition
        if 'stat' in challenge_def:
            return self._check_single_condition(challenge_def, stats)

        # Legacy format support
        stat_type = challenge_def.get('stat_type')
        target = challenge_def.get('target', 0)

        # Direct stat mapping (most stats)
        direct_stats = {
            'gold': 'gold_earned',
            'gold_earned': 'gold_earned',
            'gold_spent': 'gold_spent',
            'towers': 'turret_takedowns',
            'turret_kills': 'turret_kills',
            'turret_takedowns': 'turret_takedowns',
            'damage_dealt': 'damage_dealt',
            'damage_taken': 'damage_taken',
            'kills': 'kills',
            'deaths': 'deaths',
            'assists': 'assists',
            'penta_kills': 'penta_kills',
            'quadra_kills': 'quadra_kills',
            'triple_kills': 'triple_kills',
            'double_kills': 'double_kills',
            'first_blood_kills': 'first_blood_kills',
            'first_tower_kills': 'first_tower_kills',
            'baron_kills': 'baron_kills',
            'dragon_kills': 'dragon_kills',
            'cc_time': 'cc_time',
            'vision_score_total': 'vision_score_total',
            'wards_placed': 'wards_placed',
            'control_wards_placed': 'control_wards_placed',
            'cs_total': 'cs_total',
            'jungle_cs': 'jungle_cs',
            'games_played': 'games_played',
            'wins': 'wins',
            'losses': 'losses',
            'win_no_defensive': 'win_no_defensive',
            'unique_champ_wins': 'unique_champ_wins',
            'games_with_penta': 'games_with_penta',
            'games_with_quadra': 'games_with_quadra',
            'games_with_triple': 'games_with_triple',
            'games_11cs_min': 'games_11cs_min',
            'games_zero_deaths': 'games_zero_deaths',
            'games_baron_and_dragon': 'games_baron_and_dragon',
            'max_cs_per_min': 'max_cs_per_min',
            'max_damage_taken_game': 'max_damage_taken_game',
        }

        if stat_type in direct_stats:
            current = stats.get(direct_stats[stat_type], {}).get('stat_value', 0)
            return current >= target, 1.0

        # Computed stats
        if stat_type == 'avg_kda':
            kills = stats.get('kills', {}).get('stat_value', 0)
            deaths = stats.get('deaths', {}).get('stat_value', 0)
            assists = stats.get('assists', {}).get('stat_value', 0)
            kda = (kills + assists) / max(deaths, 1)
            return kda >= target, 1.0

        elif stat_type == 'weekly_winrate':
            wins = stats.get('wins', {}).get('stat_value', 0)
            losses = stats.get('losses', {}).get('stat_value', 0)
            total = wins + losses
            if total < min_games:
                return False, 1.0
            winrate = (wins / total) * 100 if total > 0 else 0
            return winrate >= target, 1.0

        elif stat_type == 'cs_per_min_avg':
            cs = stats.get('cs_total', {}).get('stat_value', 0)
            time_played = stats.get('time_played', {}).get('stat_value', 0)
            time_min = time_played / 60 if time_played > 0 else 1
            cs_per_min = cs / time_min
            return cs_per_min >= target, 1.0

        elif stat_type == 'avg_vision':
            vision = stats.get('vision_score_total', {}).get('stat_value', 0)
            games = stats.get('games_played', {}).get('stat_value', 1)
            avg = vision / max(games, 1)
            return avg >= target, 1.0

        elif stat_type == 'win_streak':
            # Checked via tilt detector separately
            return False, 1.0

        elif stat_type == 'assaf':
            vision_min = stats.get('min_vision_game', {}).get('stat_value', 999)
            damage_min = stats.get('min_damage_game', {}).get('stat_value', 999999)
            if damage_min == 0:
                return True, challenge_def.get('zero_damage_multiplier', 3.0)
            elif vision_min < 10:
                return True, 1.0
            return False, 1.0

        elif stat_type == 'lp_gain':
            # TODO: Implement via rank history comparison
            return False, 1.0

        elif stat_type == 'wins_on_main':
            # TODO: Track champion-specific wins
            return False, 1.0

        return False, 1.0

    def _check_single_condition(
        self,
        condition: Dict,
        stats: Dict[str, Dict]
    ) -> Tuple[bool, float]:
        """Check a single condition."""
        stat = condition.get('stat', '')
        op = condition.get('op', '>=')
        target = condition.get('value', 0)
        multiplier = condition.get('multiplier', 1.0)

        # Get stat value
        current = self._get_stat_value(stat, stats)

        # Compare
        if op == '>=':
            result = current >= target
        elif op == '>':
            result = current > target
        elif op == '<=':
            result = current <= target
        elif op == '<':
            result = current < target
        elif op == '==':
            result = current == target
        elif op == '!=':
            result = current != target
        else:
            result = False

        return result, multiplier if result else 1.0

    def _check_multi_conditions(
        self,
        challenge_def: Dict,
        stats: Dict[str, Dict]
    ) -> Tuple[bool, float]:
        """Check multiple conditions with AND/OR logic."""
        conditions = challenge_def.get('conditions', [])
        logic = challenge_def.get('logic', 'and').lower()
        max_multiplier = 1.0

        results = []
        for cond in conditions:
            passed, mult = self._check_single_condition(cond, stats)
            results.append(passed)
            if passed and mult > max_multiplier:
                max_multiplier = mult

        if logic == 'and':
            return all(results), max_multiplier
        elif logic == 'or':
            return any(results), max_multiplier
        else:
            return False, 1.0

    def _get_stat_value(self, stat: str, stats: Dict[str, Dict]) -> float:
        """Get a stat value, handling computed stats."""
        # Direct stat
        if stat in stats:
            return stats[stat].get('stat_value', 0)

        # Computed stats
        if stat == 'avg_kda':
            kills = stats.get('kills', {}).get('stat_value', 0)
            deaths = stats.get('deaths', {}).get('stat_value', 0)
            assists = stats.get('assists', {}).get('stat_value', 0)
            return (kills + assists) / max(deaths, 1)

        elif stat == 'weekly_winrate':
            wins = stats.get('wins', {}).get('stat_value', 0)
            losses = stats.get('losses', {}).get('stat_value', 0)
            total = wins + losses
            return (wins / total) * 100 if total > 0 else 0

        elif stat == 'cs_per_min_avg':
            cs = stats.get('cs_total', {}).get('stat_value', 0)
            time_played = stats.get('time_played', {}).get('stat_value', 0)
            time_min = time_played / 60 if time_played > 0 else 1
            return cs / time_min

        elif stat == 'avg_vision':
            vision = stats.get('vision_score_total', {}).get('stat_value', 0)
            games = stats.get('games_played', {}).get('stat_value', 1)
            return vision / max(games, 1)

        elif stat == 'avg_damage':
            damage = stats.get('damage_dealt', {}).get('stat_value', 0)
            games = stats.get('games_played', {}).get('stat_value', 1)
            return damage / max(games, 1)

        elif stat == 'avg_gold':
            gold = stats.get('gold_earned', {}).get('stat_value', 0)
            games = stats.get('games_played', {}).get('stat_value', 1)
            return gold / max(games, 1)

        return 0

    async def process_week_end(self) -> Dict[str, Any]:
        """
        Traite la fin de semaine:
        - Applique les penalites pour challenges non completes
        - Genere le leaderboard final
        """
        week_start = self.get_current_week_start()

        # Check for uncompleted global challenges
        global_challenges = await self.db.get_weekly_challenges(week_start)
        penalties_applied = []

        for challenge in global_challenges:
            if challenge['challenge_type'] != 'global':
                continue

            challenge_id = challenge['challenge_id']
            completions = await self.db.get_challenge_completions_for_week(
                challenge_id, week_start
            )

            if not completions:
                # No one completed - apply penalty
                challenge_def = config.GLOBAL_CHALLENGES.get(challenge_id, {})

                # Check if should be cancelled instead
                if challenge_def.get('cancel_if_no_qualifier'):
                    # Check if anyone qualified (e.g., played enough games)
                    # Skip penalty if challenge was cancelled
                    continue

                await self.db.apply_penalty_to_all(
                    season_split=config.CURRENT_SEASON_SPLIT,
                    penalty_points=config.CHALLENGE_FAILURE_PENALTY
                )

                penalties_applied.append({
                    'challenge_id': challenge_id,
                    'challenge_name': challenge_def.get('name', challenge_id),
                    'penalty': config.CHALLENGE_FAILURE_PENALTY,
                })

        # Deactivate this week's challenges
        await self.db.deactivate_week_challenges(week_start)

        return {
            'week_start': week_start,
            'penalties': penalties_applied,
        }

    async def generate_leaderboard_embed(self) -> discord.Embed:
        """Genere l'embed du leaderboard des challenges"""
        leaderboard = await self.db.get_challenge_leaderboard(
            season_split=config.CURRENT_SEASON_SPLIT,
            limit=20
        )

        embed = discord.Embed(
            title=f"Leaderboard Challenges - {config.CURRENT_SEASON_SPLIT}",
            color=discord.Color.gold(),
            timestamp=datetime.now(PARIS_TZ)
        )

        if not leaderboard:
            embed.description = "Aucun point enregistre pour le moment."
            return embed

        lines = []
        for i, entry in enumerate(leaderboard, 1):
            name = entry.get('game_name') or f"<@{entry['discord_id']}>"
            points = entry['total_points']

            if i == 1:
                medal = ""
            elif i == 2:
                medal = ""
            elif i == 3:
                medal = ""
            else:
                medal = f"{i}."

            lines.append(f"{medal} **{name}** - {points} pts")

        embed.description = "\n".join(lines)

        return embed

    async def generate_challenges_embed(self, discord_id: str) -> discord.Embed:
        """Genere l'embed des challenges actifs pour un joueur"""
        week_start = self.get_current_week_start()
        challenges = await self.db.get_weekly_challenges(week_start, discord_id)

        embed = discord.Embed(
            title=f"Challenges de la semaine",
            description=f"Semaine du {week_start}",
            color=discord.Color.blue(),
            timestamp=datetime.now(PARIS_TZ)
        )

        global_challenges = []
        personal_challenges = []

        for ch in challenges:
            challenge_id = ch['challenge_id']
            challenge_type = ch['challenge_type']

            if challenge_type == 'global':
                challenge_def = config.GLOBAL_CHALLENGES.get(challenge_id, {})
                global_challenges.append((challenge_id, challenge_def))
            else:
                challenge_def = config.PERSONAL_CHALLENGES.get(challenge_id, {})
                personal_challenges.append((challenge_id, challenge_def))

        # Global challenges
        if global_challenges:
            lines = []
            for challenge_id, challenge_def in global_challenges:
                name = challenge_def.get('name', challenge_id)
                desc = challenge_def.get('description', '')
                difficulty = challenge_def.get('difficulty', 'medium')
                points = config.CHALLENGE_POINTS.get(difficulty, 20)

                # Check if completed
                completion = await self.db.get_challenge_completion(
                    challenge_id, week_start, discord_id
                )
                status = " Termine!" if completion else ""

                lines.append(f"**{name}** ({points} pts){status}\n> {desc}")

            embed.add_field(
                name="Challenges Globaux (1.5x si premier)",
                value="\n\n".join(lines),
                inline=False
            )

        # Personal challenges
        if personal_challenges:
            lines = []
            for challenge_id, challenge_def in personal_challenges:
                name = challenge_def.get('name', challenge_id)
                desc = challenge_def.get('description', '')
                difficulty = challenge_def.get('difficulty', 'medium')
                points = config.CHALLENGE_POINTS.get(difficulty, 20)

                # Check if completed
                completion = await self.db.get_challenge_completion(
                    challenge_id, week_start, discord_id
                )
                status = " Termine!" if completion else ""

                lines.append(f"**{name}** ({points} pts){status}\n> {desc}")

            embed.add_field(
                name="Tes Challenges Personnels",
                value="\n\n".join(lines),
                inline=False
            )

        return embed

    def create_completion_embed(self, completion: Dict[str, Any]) -> discord.Embed:
        """Cree un embed pour une completion de challenge"""
        is_first = completion.get('is_first', False)
        points = completion.get('points', 0)
        challenge_name = completion.get('challenge_name', 'Challenge')
        game_name = completion.get('game_name', 'Joueur')
        tag_line = completion.get('tag_line', '')
        description = completion.get('description', '')
        latest_match_id = completion.get('latest_match_id')

        if is_first:
            title = f"PREMIER! {game_name} complete {challenge_name}"
            color = discord.Color.gold()
        else:
            title = f"{game_name} complete {challenge_name}"
            color = discord.Color.green()

        desc_parts = [description, f"\n**+{points} points!**"]

        # Add link to the game that triggered the completion
        if latest_match_id:
            # Match ID format: EUW1_7281956482 -> extract number
            match_number = latest_match_id.split('_')[-1] if '_' in latest_match_id else latest_match_id
            match_url = f"https://www.leagueofgraphs.com/match/euw/{match_number}"
            desc_parts.append(f"\n[Voir la game]({match_url})")

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_parts),
            color=color,
            timestamp=datetime.now(PARIS_TZ)
        )

        if is_first:
            embed.set_footer(text="Bonus 1.5x pour le premier!")

        return embed
