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

# ==================== REPUTATION ====================

REPUTATION = {
    # --- LP change (daily) ---
    # Thresholds (LP)
    'LP_GAIN_BIG':   50,    # >= this → big_gain
    'LP_GAIN':       15,    # >= this → gain
    'LP_LOSS':      -20,    # <= this → loss
    'LP_LOSS_BIG':  -50,    # <= this → big_loss
    # Deltas applied to score
    'LP_DELTA_BIG_GAIN':  8.0,
    'LP_DELTA_GAIN':      3.0,
    'LP_DELTA_LOSS':     -5.0,
    'LP_DELTA_BIG_LOSS': -12.0,

    # --- KDA per game ---
    # Thresholds
    'KDA_GREAT':   6.0,    # >= this → great (12/10 territory)
    'KDA_GOOD':    3.0,    # >= this → good
    'KDA_BAD':     1.5,    # < this  → bad
    'KDA_TERRIBLE': 0.8,   # < this  → terrible (1/10 territory)
    # Deltas
    'KDA_DELTA_GREAT':    5.0,
    'KDA_DELTA_GOOD':     2.0,
    'KDA_DELTA_BAD':     -3.0,
    'KDA_DELTA_TERRIBLE': -7.0,

    # --- Weekly winrate ---
    'WINRATE_MIN_GAMES': 5,      # ignore if fewer games
    'WINRATE_GREAT':  60.0,      # >= this → great
    'WINRATE_GOOD':   52.0,      # >= this → good
    'WINRATE_BAD':    45.0,      # < this  → bad
    'WINRATE_TERRIBLE': 35.0,    # < this  → terrible
    # Deltas
    'WINRATE_DELTA_GREAT':    10.0,
    'WINRATE_DELTA_GOOD':      3.0,
    'WINRATE_DELTA_BAD':      -8.0,
    'WINRATE_DELTA_TERRIBLE': -15.0,
}

# ==================== WEEKLY AWARDS ====================

# Sent to LEADERBOARD_WEEKLY_CHANNEL_ID every Monday alongside the retrospective
WEEKLY_AWARDS = {
    'inter':    {'name': 'Inter de la semaine',  'stat': 'deaths',        'order': 'desc'},  # most deaths
    'kaizen':   {'name': 'Prix Kaizen',          'stat': 'lp_gain',       'order': 'desc'},  # most LP gained
    'tapis':    {'name': 'Tapis rouge',          'stat': 'loss_streak',   'order': 'desc'},  # longest loss streak
    'jeudi':    {'name': 'Prix Jeudi Noir',      'stat': 'lp_loss',       'order': 'asc'},   # most LP lost
    'larbin':   {'name': 'Larbin de Riot',       'stat': 'games_played',  'order': 'desc'},  # most games played
    'kda':      {'name': 'KDA player',           'stat': 'avg_kda',       'order': 'desc'},  # best avg KDA (5+ games)
}

# ==================== TILT DETECTOR ====================

# Channel where tilt/win streak notifications are sent
TILT_CHANNEL_ID = 1470464009877717022

# Minimum streak count before notifying
TILT_MIN_STREAK = 3
