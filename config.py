"""
Configuration centralisée pour le bot LoL
Toutes les valeurs sont éditables pour ajuster le comportement du bot
"""

# Cache TTL (secondes)
CACHE_TTL = {
    'MATCH_HISTORY': 300,      # 5 min (liste des match IDs)
    'MATCH_DETAIL': None,      # Permanent (résultat d'un match, immuable)
    'MATCH_TIMELINE': 604800,  # 7 jours (timeline volumineuse ~640KB/match)
    'LIVE_GAME': 60,           # 1 min
    'MASTERY': 3600,           # 1h
    'RANK': 1800,              # 30 min
    'REGISTERED_USER': None,   # Permanent
}

# Région supportée
DEFAULT_REGION = 'EUW1'
ROUTING_REGION = 'europe'  # Pour ACCOUNT-V1 et MATCH-V5

# Rate Limiting
RATE_LIMIT = {
    'REQUESTS_PER_SECOND': 20,
    'REQUESTS_PER_TWO_MINUTES': 100,
}

# Data Dragon
DATA_DRAGON_BASE_URL = "https://ddragon.leagueoflegends.com"
DATA_DRAGON_CDN = "https://ddragon.leagueoflegends.com/cdn"

# Riot API
RIOT_API_BASE = {
    'platform': 'https://euw1.api.riotgames.com',
    'regional': 'https://europe.api.riotgames.com',
}

# Leaderboard
LEADERBOARD_DAILY_CHANNEL_ID = 1470463042767552584  # Set to Discord channel ID (int)
LEADERBOARD_WEEKLY_CHANNEL_ID = 1470463064821207196
LEADERBOARD_HOUR = 10  # Heure d'envoi (Paris time)
LEADERBOARD_MINUTE = 0

# Danger Score Configuration (Clash Scout)
DANGER_SCORE = {
    'OTP_MASTERY_THRESHOLD': 250000,        # Points de maitrise pour OTP
    'OTP_SEASON_PERCENTAGE': 50,            # % des games cette saison sur ce champion
    'OTP_SCORE': 25,                        # Points bonus OTP

    'RECENT_GAMES_COUNT': 10,               # Nombre de games recentes a analyser
    'RECENT_SPAM_THRESHOLD': 5,             # Games jouees recemment sur ce champion
    'RECENT_SPAM_SCORE': 30,                # Points bonus spam recent

    'WINRATE_NEUTRAL': 50,                  # Winrate neutre (0 points)
    'WINRATE_SCORE_PER_PERCENT': 2,         # Points par % au-dessus de 50

    'SMURF_MASTERY_MAX': 50000,             # Mastery faible = possible smurf
    'SMURF_WR_THRESHOLD': 60,               # Winrate eleve (smurf)
    'SMURF_KDA_THRESHOLD': 3,               # KDA eleve (smurf)
    'SMURF_SCORE': 80,                      # Points bonus smurf detecte
}

# Role detection (Clash Scout)
ROLE_DETECTION = {
    'HISTORY_GAMES': 20,                    # Games a analyser pour detecter role
    'ROLE_THRESHOLD': 60,                   # % pour considerer un role principal
}

# Player threat score weights
PLAYER_THREAT = {
    'RECENT_WINRATE_WEIGHT': 1.0,
    'KDA_WEIGHT': 0.5,
    'RANK_WEIGHT': 1.0,
}

# Rank values for threat calculation
RANK_VALUES = {
    'IRON': 0, 'BRONZE': 400, 'SILVER': 800, 'GOLD': 1200,
    'PLATINUM': 1600, 'EMERALD': 2000, 'DIAMOND': 2400,
    'MASTER': 2800, 'GRANDMASTER': 3200, 'CHALLENGER': 3600
}

# ==================== TILT DETECTOR ====================

# Channel for tilt/win streak announcements
TILT_CHANNEL_ID = 1470464009877717022  # Set to Discord channel ID (int)

# Check interval in minutes (30 = check every 30 min)
TILT_CHECK_INTERVAL_MINUTES = 30

# Loss streak messages - 5 messages per threshold (3, 4, 5, 6+)
# {player} will be replaced with the player's name
# {count} will be replaced with the streak count
TILT_MESSAGES = {
    3: [
        "TODO: Message 1 pour 3 defaites - {player}",
        "TODO: Message 2 pour 3 defaites - {player}",
        "TODO: Message 3 pour 3 defaites - {player}",
        "TODO: Message 4 pour 3 defaites - {player}",
        "TODO: Message 5 pour 3 defaites - {player}",
    ],
    4: [
        "TODO: Message 1 pour 4 defaites - {player}",
        "TODO: Message 2 pour 4 defaites - {player}",
        "TODO: Message 3 pour 4 defaites - {player}",
        "TODO: Message 4 pour 4 defaites - {player}",
        "TODO: Message 5 pour 4 defaites - {player}",
    ],
    5: [
        "TODO: Message 1 pour 5 defaites - {player}",
        "TODO: Message 2 pour 5 defaites - {player}",
        "TODO: Message 3 pour 5 defaites - {player}",
        "TODO: Message 4 pour 5 defaites - {player}",
        "TODO: Message 5 pour 5 defaites - {player}",
    ],
    6: [  # 6+ losses
        "TODO: Message 1 pour 6+ defaites - {player} ({count} loose streak)",
        "TODO: Message 2 pour 6+ defaites - {player} ({count} loose streak)",
        "TODO: Message 3 pour 6+ defaites - {player} ({count} loose streak)",
        "TODO: Message 4 pour 6+ defaites - {player} ({count} loose streak)",
        "TODO: Message 5 pour 6+ defaites - {player} ({count} loose streak)",
    ],
}

# Win streak messages - 5 messages per threshold (3, 4, 5, 6+)
WIN_MESSAGES = {
    3: [
        "TODO: Message 1 pour 3 victoires - {player}",
        "TODO: Message 2 pour 3 victoires - {player}",
        "TODO: Message 3 pour 3 victoires - {player}",
        "TODO: Message 4 pour 3 victoires - {player}",
        "TODO: Message 5 pour 3 victoires - {player}",
    ],
    4: [
        "TODO: Message 1 pour 4 victoires - {player}",
        "TODO: Message 2 pour 4 victoires - {player}",
        "TODO: Message 3 pour 4 victoires - {player}",
        "TODO: Message 4 pour 4 victoires - {player}",
        "TODO: Message 5 pour 4 victoires - {player}",
    ],
    5: [
        "TODO: Message 1 pour 5 victoires - {player}",
        "TODO: Message 2 pour 5 victoires - {player}",
        "TODO: Message 3 pour 5 victoires - {player}",
        "TODO: Message 4 pour 5 victoires - {player}",
        "TODO: Message 5 pour 5 victoires - {player}",
    ],
    6: [  # 6+ wins
        "TODO: Message 1 pour 6+ victoires - {player} ({count} win streak)",
        "TODO: Message 2 pour 6+ victoires - {player} ({count} win streak)",
        "TODO: Message 3 pour 6+ victoires - {player} ({count} win streak)",
        "TODO: Message 4 pour 6+ victoires - {player} ({count} win streak)",
        "TODO: Message 5 pour 6+ victoires - {player} ({count} win streak)",
    ],
}

# ==================== WEEKLY CHALLENGES ====================

# Channel for challenge announcements and leaderboard
CHALLENGE_ANNOUNCEMENTS_CHANNEL_ID = 1470464204073861295  # Set to Discord channel ID (int)
CHALLENGE_LEADERBOARD_CHANNEL_ID = 1470464204073861295

# Current season split (for points tracking)
CURRENT_SEASON_SPLIT = "2025_split1"  # Update each split
SEASON_START_DATE = "2025-01-08"  # Start date of current split (for fetching all ranked games)

# Challenge leaderboard time (Monday 10:00 Paris)
CHALLENGE_LEADERBOARD_HOUR = 10
CHALLENGE_LEADERBOARD_MINUTE = 0

# Point values by difficulty
CHALLENGE_POINTS = {
    'easy': 10,
    'medium': 20,
    'hard': 35,
    'very_hard': 50,
}

# First completion bonus multiplier (1.5x)
FIRST_COMPLETION_BONUS = 1.5

# Penalty points when global challenge not completed by anyone
CHALLENGE_FAILURE_PENALTY = -10

# =============================================================================
# GLOBAL CHALLENGES - Available to everyone, first to complete gets 1.5x bonus
# =============================================================================
# Format options:
#   Legacy:  {'stat_type': 'kills', 'target': 100}
#   Single:  {'stat': 'kills', 'op': '>=', 'value': 100}
#   Multi:   {'conditions': [...], 'logic': 'and'/'or'}
#
# WEEKLY stats (reset every Monday):
#   gold_earned, gold_spent, kills, deaths, assists, wins, losses, games_played,
#   damage_dealt, damage_taken, turret_kills, turret_takedowns, inhibitor_kills,
#   dragon_kills, baron_kills, rift_herald_kills, vision_score_total, wards_placed,
#   wards_killed, control_wards_placed, cs_total, jungle_cs, double_kills,
#   triple_kills, quadra_kills, penta_kills, first_blood_kills, first_tower_kills,
#   cc_time, time_played, time_dead, longest_life
#
# SPLIT stats (persist all split - same names, stored in split_stats_cache):
#   gold_earned, gold_spent, kills, deaths, assists, wins, losses, games_played,
#   damage_dealt, damage_taken, turret_kills, turret_takedowns, dragon_kills,
#   baron_kills, vision_score_total, wards_placed, wards_killed, control_wards_placed,
#   cs_total, jungle_cs, double_kills, triple_kills, quadra_kills, penta_kills,
#   first_blood_kills, first_tower_kills, cc_time, time_played, unique_champ_wins,
#   games_with_penta, games_with_quadra, games_zero_deaths, games_20_kills,
#   games_11cs_min, max_kills_game, max_cs_per_min, max_damage_game
#
# Per-game records (max/min) - WEEKLY only:
#   max_kills_game, max_deaths_game, max_cs_game, max_damage_game, max_gold_game,
#   max_vision_game, min_vision_game, min_damage_game, max_cs_per_min,
#   max_damage_taken_game
#
# Achievement counts:
#   games_with_penta, games_with_quadra, games_with_triple, games_with_double,
#   games_11cs_min, games_zero_deaths, games_20_kills, win_no_defensive,
#   games_baron_and_dragon, unique_champ_wins
#
# Computed stats:
#   avg_kda, weekly_winrate, cs_per_min_avg, avg_vision, avg_damage, avg_gold
#
# To use SPLIT stats instead of weekly, use 'scope': 'split' in challenge def
# =============================================================================

GLOBAL_CHALLENGES = {
    'juif': {
        'name': 'Juif',
        'description': 'Gagner 500k gold sur la semaine',
        'difficulty': 'medium',
        'stat_type': 'gold_earned',
        'target': 500000,
    },
    'rekkles': {
        'name': 'Rekkles',
        'description': 'Avoir un KDA moyen de 3.0+',
        'difficulty': 'medium',
        'stat_type': 'avg_kda',
        'target': 3.0,
        'min_games': 5,
    },
    'pilote': {
        'name': 'Pilote du 11 septembre',
        'description': 'Detruire 50+ tours',
        'difficulty': 'hard',
        'stat_type': 'turret_takedowns',
        'target': 50,
    },
    'winner': {
        'name': 'Winner',
        'description': 'Etre en winstreak de 5+',
        'difficulty': 'hard',
        'stat_type': 'win_streak',
        'target': 5,
    },
    'wr_maxer': {
        'name': 'WR Maxer',
        'description': 'Avoir 65%+ de winrate sur la semaine (20 games minimum)',
        'difficulty': 'very_hard',
        'stat_type': 'weekly_winrate',
        'target': 65,
        'min_games': 20,
        'cancel_if_no_qualifier': True,
    },
    'ambulance': {
        'name': 'Call an ambulance !! But not for me',
        'description': 'Gagner une partie avec 0 item defensif',
        'difficulty': 'hard',
        'stat_type': 'win_no_defensive',
        'target': 1,
    },
    'assaf': {
        'name': 'ASSAF MAXING',
        'description': 'Avoir moins de 10 de score de vision OU 0 degats sur une game (x3 pts)',
        'difficulty': 'medium',
        'stat_type': 'assaf',
        'target': 1,
        'zero_damage_multiplier': 3,
    },
    # New challenges
    'pentakill': {
        'name': 'PENTAKILL',
        'description': 'Faire un pentakill cette semaine',
        'difficulty': 'very_hard',
        'stat_type': 'games_with_penta',
        'target': 1,
    },
    'quadra_collector': {
        'name': 'Quadriceps',
        'description': 'Faire 3 quadrakills cette semaine',
        'difficulty': 'very_hard',
        'stat_type': 'quadra_kills',
        'target': 3,
    },
    'triple_threat': {
        'name': 'Triple Threat',
        'description': 'Faire 10 triple kills cette semaine',
        'difficulty': 'medium',
        'stat_type': 'triple_kills',
        'target': 10,
    },
    'double_trouble': {
        'name': 'Double Trouble',
        'description': 'Faire 30 double kills cette semaine',
        'difficulty': 'easy',
        'stat_type': 'double_kills',
        'target': 30,
    },
    'cs_god': {
        'name': 'CS God',
        'description': 'Atteindre 11 CS/min dans une game',
        'difficulty': 'very_hard',
        'stat_type': 'max_cs_per_min',
        'target': 11,
    },
    'tank': {
        'name': 'Tank',
        'description': 'Prendre 2M de dégâts sur la semaine',
        'difficulty': 'hard',
        'stat_type': 'damage_taken',
        'target': 2000000,
    },
    'first_blood_hunter': {
        'name': 'RP Epstein',
        'description': 'Faire 10 first blood cette semaine',
        'difficulty': 'hard',
        'stat_type': 'first_blood_kills',
        'target': 10,
    },
    'cc_machine': {
        'name': 'Machine à stun',
        'description': 'Infliger 500 secondes de CC cette semaine',
        'difficulty': 'medium',
        'stat_type': 'cc_time',
        'target': 500,
    },
    'big_spender': {
        'name': 'RP Natha',
        'description': 'Depenser 400k gold cette semaine',
        'difficulty': 'medium',
        'stat_type': 'gold_spent',
        'target': 400000,
    },
    'powerfarmer': {
        'name': 'Powerfarmer (gank + stp)',
        'description': 'Farmer 500 camps jungle cette semaine',
        'difficulty': 'hard',
        'stat_type': 'jungle_cs',
        'target': 500,
    },
    'tower_destroyer': {
        'name': 'Saroumane',
        'description': 'First tower dans 5 games',
        'difficulty': 'hard',
        'stat_type': 'first_tower_kills',
        'target': 5,
    },
    'dragon_slayer': {
        'name': 'Dragonnet',
        'description': 'Tuer 20 dragons cette semaine',
        'difficulty': 'hard',
        'stat_type': 'dragon_kills',
        'target': 20,
    },
    'baron_nashor': {
        'name': 'Baron Nashor',
        'description': 'Tuer 10 barons cette semaine',
        'difficulty': 'hard',
        'stat_type': 'baron_kills',
        'target': 10,
    },
    'vision_control': {
        'name': 'Défi impossible',
        'description': 'Placer 100 control wards cette semaine',
        'difficulty': 'medium',
        'stat_type': 'control_wards_placed',
        'target': 100,
    },
    'ward_clearer': {
        'name': 'Éboueur',
        'description': 'Detruire 50 wards cette semaine',
        'difficulty': 'medium',
        'stat_type': 'wards_killed',
        'target': 50,
    },
    'damage_dealer': {
        'name': 'Calma calma',
        'description': 'Infliger 1M de degats aux champions cette semaine',
        'difficulty': 'hard',
        'stat_type': 'damage_dealt',
        'target': 1000000,
    },
    'serial_killer': {
        'name': 'Killer Queen',
        'description': 'Faire 200 kills cette semaine',
        'difficulty': 'hard',
        'stat_type': 'kills',
        'target': 200,
    },
    'perfect_game': {
        'name': 'Unkillable Demon King',
        'description': 'Gagner une game sans mourir',
        'difficulty': 'hard',
        'stat_type': 'games_zero_deaths',
        'target': 1,
    },
    'carry': {
        'name': 'Carry Potter',
        'description': 'Faire 20+ kills dans une game',
        'difficulty': 'hard',
        'stat_type': 'games_20_kills',
        'target': 3,
    },
    # Example of multi-condition challenge (AND)
    # 'rich_and_tanky': {
    #     'name': 'Rich and Tanky',
    #     'description': 'Gagner 300k gold ET prendre 150k degats',
    #     'difficulty': 'hard',
    #     'conditions': [
    #         {'stat': 'gold_earned', 'op': '>=', 'value': 300000},
    #         {'stat': 'damage_taken', 'op': '>=', 'value': 150000},
    #     ],
    #     'logic': 'and',
    # },
}

# =============================================================================
# PERSONAL CHALLENGES - Assigned randomly to each player each week
# =============================================================================

PERSONAL_CHALLENGES = {
    'climb': {
        'name': 'Climb',
        'description': 'Gagner +50 LP cette semaine',
        'difficulty': 'medium',
        'stat_type': 'lp_gain',
        'target': 50,
    },
    'consistent': {
        'name': 'Consistent',
        'description': 'Jouer 15+ ranked games',
        'difficulty': 'easy',
        'stat_type': 'games_played',
        'target': 15,
    },
    'clean': {
        'name': 'Clean',
        'description': 'KDA moyen de 2.5+ sur la semaine',
        'difficulty': 'easy',
        'stat_type': 'avg_kda',
        'target': 2.5,
        'min_games': 5,
    },
    'main_character': {
        'name': 'Main character',
        'description': '5 victoires sur ton champion le plus joue',
        'difficulty': 'medium',
        'stat_type': 'wins_on_main',
        'target': 5,
    },
    'diversify': {
        'name': 'Diversify',
        'description': 'Gagner sur 5 champions differents',
        'difficulty': 'medium',
        'stat_type': 'unique_champ_wins',
        'target': 5,
    },
    'grinder': {
        'name': 'Grinder',
        'description': 'Jouer 25+ ranked games',
        'difficulty': 'medium',
        'stat_type': 'games_played',
        'target': 25,
    },
    'vision_king': {
        'name': 'Vision King',
        'description': 'Score de vision moyen de 30+',
        'difficulty': 'medium',
        'stat_type': 'avg_vision',
        'target': 30,
        'min_games': 5,
    },
    'farmer': {
        'name': 'Farmer',
        'description': 'CS moyen de 7/min sur la semaine',
        'difficulty': 'easy',
        'stat_type': 'cs_per_min_avg',
        'target': 7,
        'min_games': 5,
    },
    'elite_farmer': {
        'name': 'Elite Farmer',
        'description': 'CS moyen de 9/min sur la semaine',
        'difficulty': 'hard',
        'stat_type': 'cs_per_min_avg',
        'target': 9,
        'min_games': 5,
    },
    'team_player': {
        'name': 'Team Player',
        'description': 'Faire 150 assists cette semaine',
        'difficulty': 'medium',
        'stat_type': 'assists',
        'target': 150,
    },
    'survivor': {
        'name': 'Survivor',
        'description': 'Moins de 50 morts cette semaine (10 games min)',
        'difficulty': 'hard',
        'conditions': [
            {'stat': 'deaths', 'op': '<', 'value': 50},
            {'stat': 'games_played', 'op': '>=', 'value': 10},
        ],
        'logic': 'and',
    },
    'winstreak_3': {
        'name': 'Hot Streak',
        'description': 'Atteindre une winstreak de 3+',
        'difficulty': 'easy',
        'stat_type': 'win_streak',
        'target': 3,
    },
}

# How many global challenges per week (randomly selected)
GLOBAL_CHALLENGES_PER_WEEK = 6

# How many personal challenges per player per week
PERSONAL_CHALLENGES_PER_PLAYER = 2

# ==================== TRAINING EXERCISES ====================
# Per-game exercises evaluated against match timeline data
# Conditions use timeline stat extractors from TrainingExercises module
# Available stats:
#   deaths_before_time, kills_before_time, total_cs_at_time,
#   damage_to_champions_at_time, gold_at_time, gold_advantage_at_time,
#   level_at_time, wards_placed_before_time
# Operators: '==', '!=', '>=', '<=', '>', '<'
# time_ms: timestamp in milliseconds (e.g., 840000 = 14 min)

TRAINING_EXERCISES = {
    'survive_lane': {
        'name': 'Survive Laning Phase',
        'description': 'Ne pas mourir avant 14 minutes',
        'conditions': [
            {'stat': 'deaths_before_time', 'op': '==', 'value': 0, 'time_ms': 840000}
        ],
    },
    'cs_at_20': {
        'name': 'CS Goal',
        'description': 'Atteindre 200 CS a 20 minutes',
        'conditions': [
            {'stat': 'total_cs_at_time', 'op': '>=', 'value': 200, 'time_ms': 1200000}
        ],
    },
    'early_damage': {
        'name': 'Early Aggression',
        'description': 'Infliger 3000 degats aux champions avant 10 minutes',
        'conditions': [
            {'stat': 'damage_to_champions_at_time', 'op': '>=', 'value': 3000, 'time_ms': 600000}
        ],
    },
    'early_gold': {
        'name': 'Gold Lead',
        'description': 'Avoir 1000 gold d\'avance a 15 minutes',
        'conditions': [
            {'stat': 'gold_advantage_at_time', 'op': '>=', 'value': 1000, 'time_ms': 900000}
        ],
    },
    'vision_early': {
        'name': 'Vision Control',
        'description': 'Placer 5 wards avant 10 minutes',
        'conditions': [
            {'stat': 'wards_placed_before_time', 'op': '>=', 'value': 5, 'time_ms': 600000}
        ],
    },
    'first_blood_king': {
        'name': 'First Blood King',
        'description': 'Obtenir un kill avant 3 minutes',
        'conditions': [
            {'stat': 'kills_before_time', 'op': '>=', 'value': 1, 'time_ms': 180000}
        ],
    },
}
