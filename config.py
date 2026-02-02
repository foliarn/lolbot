"""
Configuration centralisée pour le bot LoL
Toutes les valeurs sont éditables pour ajuster le comportement du bot
"""

# Danger Score Configuration (Clash Scout)
DANGER_SCORE = {
    'OTP_MASTERY_THRESHOLD': 250000,        # Points de maîtrise pour considérer un OTP
    'OTP_SEASON_PERCENTAGE': 50,            # % des games cette saison sur ce champion
    'OTP_SCORE': 50,                        # Points bonus OTP

    'RECENT_GAMES_COUNT': 10,               # Nombre de games récentes à analyser
    'RECENT_SPAM_THRESHOLD': 5,             # Games jouées récemment sur ce champion
    'RECENT_SPAM_SCORE': 30,                # Points bonus spam récent

    'WINRATE_NEUTRAL': 50,                  # Winrate neutre (0 points)
    'WINRATE_SCORE_PER_PERCENT': 5,         # Points par % au-dessus de 50

    'SMURF_MASTERY_MAX': 50000,             # Mastery faible = possible smurf
    'SMURF_WR_THRESHOLD': 65,               # Winrate élevé (smurf)
    'SMURF_KDA_THRESHOLD': 3.5,             # KDA élevé (smurf)
    'SMURF_SCORE': 80,                      # Points bonus smurf détecté
}

# Role Detection
ROLE_DETECTION = {
    'HISTORY_GAMES': 10,                    # Games à analyser pour détecter rôle
    'ROLE_THRESHOLD': 60,                   # % pour considérer un rôle principal
}

# Patch Watcher
PATCH_CHECK_HOURS = [8, 12, 16, 20]         # Heures de vérification (mercredi)
PATCH_NOTES_URL = "https://www.leagueoflegends.com/fr-fr/news/game-updates/"

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
