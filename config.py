"""
Configuration centralisée pour le bot LoL
Toutes les valeurs sont éditables pour ajuster le comportement du bot
"""

# Cache TTL (secondes)
CACHE_TTL = {
    'MATCH_HISTORY': 300,      # 5 min
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
LEADERBOARD_CHANNEL_ID = 1467908501891322035  # Set to Discord channel ID (int)
LEADERBOARD_HOUR = 10  # Heure d'envoi (Paris time)
LEADERBOARD_MINUTE = 0

# Danger Score Configuration (Clash Scout)
DANGER_SCORE = {
    'OTP_MASTERY_THRESHOLD': 250000,        # Points de maitrise pour OTP
    'OTP_SEASON_PERCENTAGE': 50,            # % des games cette saison sur ce champion
    'OTP_SCORE': 50,                        # Points bonus OTP

    'RECENT_GAMES_COUNT': 10,               # Nombre de games recentes a analyser
    'RECENT_SPAM_THRESHOLD': 5,             # Games jouees recemment sur ce champion
    'RECENT_SPAM_SCORE': 30,                # Points bonus spam recent

    'WINRATE_NEUTRAL': 50,                  # Winrate neutre (0 points)
    'WINRATE_SCORE_PER_PERCENT': 5,         # Points par % au-dessus de 50

    'SMURF_MASTERY_MAX': 50000,             # Mastery faible = possible smurf
    'SMURF_WR_THRESHOLD': 65,               # Winrate eleve (smurf)
    'SMURF_KDA_THRESHOLD': 3.5,             # KDA eleve (smurf)
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
