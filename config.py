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
