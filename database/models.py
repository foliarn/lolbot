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

-- Clash teams created by users
CREATE TABLE IF NOT EXISTS clash_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL,
    created_by_discord_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_name, created_by_discord_id)
);

-- Team members (links to users table via discord_id)
CREATE TABLE IF NOT EXISTS clash_team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    discord_id TEXT NOT NULL,
    position INTEGER DEFAULT 0,
    FOREIGN KEY (team_id) REFERENCES clash_teams(id) ON DELETE CASCADE,
    UNIQUE(team_id, discord_id)
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);
CREATE INDEX IF NOT EXISTS idx_users_primary ON users(discord_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_cache_key ON api_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_rank_history_puuid ON rank_history(riot_puuid);
CREATE INDEX IF NOT EXISTS idx_rank_history_date ON rank_history(recorded_at);
CREATE INDEX IF NOT EXISTS idx_rank_history_queue ON rank_history(queue_type);
CREATE INDEX IF NOT EXISTS idx_clash_teams_creator ON clash_teams(created_by_discord_id);
CREATE INDEX IF NOT EXISTS idx_clash_team_members_team ON clash_team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_clash_team_members_discord ON clash_team_members(discord_id);

-- ==================== TILT DETECTOR ====================

-- Track player streak state to avoid duplicate notifications
CREATE TABLE IF NOT EXISTS tilt_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    riot_puuid TEXT NOT NULL,
    streak_type TEXT NOT NULL,              -- 'loss' or 'win'
    streak_count INTEGER DEFAULT 0,
    last_notified_count INTEGER DEFAULT 0,  -- Last streak count we notified for
    last_match_id TEXT,                     -- Last match we analyzed
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(riot_puuid)
);

CREATE INDEX IF NOT EXISTS idx_tilt_tracker_puuid ON tilt_tracker(riot_puuid);

-- ==================== WEEKLY CHALLENGES ====================

-- Active challenges for the current week
CREATE TABLE IF NOT EXISTS weekly_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id TEXT NOT NULL,             -- e.g., 'juif', 'rekkles', 'climb'
    challenge_type TEXT NOT NULL,           -- 'global' or 'personal'
    week_start DATE NOT NULL,               -- Monday of the week
    assigned_to TEXT,                       -- discord_id for personal challenges, NULL for global
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(challenge_id, week_start, assigned_to)
);

CREATE INDEX IF NOT EXISTS idx_weekly_challenges_week ON weekly_challenges(week_start);
CREATE INDEX IF NOT EXISTS idx_weekly_challenges_assigned ON weekly_challenges(assigned_to);

-- Track challenge completions
CREATE TABLE IF NOT EXISTS challenge_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    discord_id TEXT NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_first BOOLEAN DEFAULT 0,             -- First to complete (for global challenges)
    points_awarded INTEGER DEFAULT 0,
    UNIQUE(challenge_id, week_start, discord_id)
);

CREATE INDEX IF NOT EXISTS idx_challenge_completions_week ON challenge_completions(week_start);
CREATE INDEX IF NOT EXISTS idx_challenge_completions_discord ON challenge_completions(discord_id);

-- Cumulative challenge points per season split
CREATE TABLE IF NOT EXISTS challenge_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT NOT NULL,
    season_split TEXT NOT NULL,             -- e.g., '2024_split1'
    total_points INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(discord_id, season_split)
);

CREATE INDEX IF NOT EXISTS idx_challenge_points_discord ON challenge_points(discord_id);
CREATE INDEX IF NOT EXISTS idx_challenge_points_season ON challenge_points(season_split);

-- Weekly stats cache for challenge progress tracking
CREATE TABLE IF NOT EXISTS weekly_stats_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    riot_puuid TEXT NOT NULL,
    week_start DATE NOT NULL,
    stat_type TEXT NOT NULL,                -- 'gold', 'towers', 'kda', 'games', etc.
    stat_value REAL DEFAULT 0,
    games_counted INTEGER DEFAULT 0,
    last_match_id TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(riot_puuid, week_start, stat_type)
);

CREATE INDEX IF NOT EXISTS idx_weekly_stats_puuid ON weekly_stats_cache(riot_puuid);
CREATE INDEX IF NOT EXISTS idx_weekly_stats_week ON weekly_stats_cache(week_start);

-- Split-wide stats cache (persists across weeks within a split)
CREATE TABLE IF NOT EXISTS split_stats_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    riot_puuid TEXT NOT NULL,
    season_split TEXT NOT NULL,             -- e.g., '2025_split1'
    stat_type TEXT NOT NULL,
    stat_value REAL DEFAULT 0,
    games_counted INTEGER DEFAULT 0,
    last_match_id TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(riot_puuid, season_split, stat_type)
);

CREATE INDEX IF NOT EXISTS idx_split_stats_puuid ON split_stats_cache(riot_puuid);
CREATE INDEX IF NOT EXISTS idx_split_stats_split ON split_stats_cache(season_split);

-- ==================== TRAINING EXERCISES ====================

-- Player exercise subscriptions (which exercises are enabled)
CREATE TABLE IF NOT EXISTS exercise_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    riot_puuid TEXT NOT NULL,
    exercise_id TEXT NOT NULL,
    enabled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_match_id TEXT,
    UNIQUE(riot_puuid, exercise_id)
);

CREATE INDEX IF NOT EXISTS idx_exercise_tracking_puuid ON exercise_tracking(riot_puuid);

-- Per-game exercise results
CREATE TABLE IF NOT EXISTS exercise_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    riot_puuid TEXT NOT NULL,
    exercise_id TEXT NOT NULL,
    match_id TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    match_timestamp INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(riot_puuid, exercise_id, match_id)
);

CREATE INDEX IF NOT EXISTS idx_exercise_attempts_puuid ON exercise_attempts(riot_puuid);
CREATE INDEX IF NOT EXISTS idx_exercise_attempts_exercise ON exercise_attempts(exercise_id);
"""
