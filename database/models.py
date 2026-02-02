"""
Schéma de la base de données SQLite
"""

SCHEMA = """
-- Table pour stocker la version actuelle du patch
CREATE TABLE IF NOT EXISTS patch_version (
    id INTEGER PRIMARY KEY,
    version TEXT NOT NULL,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

-- Table des abonnements aux champions
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT NOT NULL,
    champion_name TEXT NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(discord_id, champion_name)
);

-- Table de cache pour les requêtes API
CREATE TABLE IF NOT EXISTS api_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    response_data TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);
CREATE INDEX IF NOT EXISTS idx_users_primary ON users(discord_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_subscriptions_discord_id ON subscriptions(discord_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_champion ON subscriptions(champion_name);
CREATE INDEX IF NOT EXISTS idx_cache_key ON api_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache(expires_at);
"""
