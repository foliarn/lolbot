"""
Schéma de la base de données SQLite
"""

SCHEMA = """
-- Table des utilisateurs Discord avec leurs comptes Riot
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT NOT NULL,
    riot_puuid TEXT NOT NULL,
    summoner_id TEXT,
    game_name TEXT NOT NULL,
    tag_line TEXT NOT NULL,
    region TEXT DEFAULT 'EUW1',
    is_primary BOOLEAN DEFAULT 0,
    account_alias TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(discord_id, riot_puuid)
);

-- Table de cache pour les requêtes API
CREATE TABLE IF NOT EXISTS api_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    response_data TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Table pour l'historique des rangs (pour le leaderboard)
CREATE TABLE IF NOT EXISTS rank_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    riot_puuid TEXT NOT NULL,
    queue_type TEXT NOT NULL,
    tier TEXT,
    rank TEXT,
    league_points INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);
CREATE INDEX IF NOT EXISTS idx_users_primary ON users(discord_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_cache_key ON api_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_rank_history_puuid ON rank_history(riot_puuid);
CREATE INDEX IF NOT EXISTS idx_rank_history_date ON rank_history(recorded_at);
CREATE INDEX IF NOT EXISTS idx_rank_history_queue ON rank_history(queue_type);
"""
