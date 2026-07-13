# Database

SQLite file: `lolbot.db` (created at repo root on first run).

All queries live in `database/manager.py`. No raw SQL anywhere else.
Connection-per-operation pattern: every method opens its own `aiosqlite.connect()`.
All timestamps written by SQLite's `CURRENT_TIMESTAMP` are UTC, stored as `"YYYY-MM-DD HH:MM:SS"` (no timezone suffix).

---

## Tables

### `users`

One row per (Discord user × Riot account). Supports multi-account (smurfs).

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `discord_id` | TEXT | Discord snowflake as string |
| `riot_puuid` | TEXT | Riot PUUID (78-char string) |
| `summoner_id` | TEXT | Riot summoner ID (used for Clash API) |
| `game_name` | TEXT | RiotID name part |
| `tag_line` | TEXT | RiotID tag part |
| `region` | TEXT | Default `EUW1` |
| `is_primary` | BOOLEAN | `1` for the default account, `0` for smurfs |
| `account_alias` | TEXT | Optional nickname (e.g. "main", "smurf1") |
| `created_at` | TIMESTAMP | UTC, set on insert |

**Unique constraint:** `(discord_id, riot_puuid)` — same Riot account can't be linked twice to the same Discord user.

**Primary promotion logic:** When `remove_user()` deletes the primary account, the oldest remaining account (by `created_at`) is automatically promoted to `is_primary = 1`. This is NOT atomic — it's two separate SQL statements.

**First account = primary:** `add_user()` checks `COUNT(*)` first; if 0 accounts exist for this Discord user, sets `is_primary = 1`.

---

### `api_cache`

Generic HTTP cache for all Riot API responses.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `cache_key` | TEXT UNIQUE | Format: `"endpoint:param1:param2"` |
| `response_data` | TEXT | JSON-serialized response |
| `cached_at` | TIMESTAMP | UTC |
| `expires_at` | TIMESTAMP | NULL = permanent; ISO format string set at write time |

**Expiry check happens at read time:** `get_cache()` checks `datetime.now() > expiry` and deletes the row inline if expired.

**TTL values** (from `config.CACHE_TTL`):
| Key | TTL |
|-----|-----|
| `MATCH_HISTORY` | 300s (5 min) |
| `MATCH_DETAIL` | None (permanent) |
| `MATCH_TIMELINE` | 604800s (7 days) |
| `LIVE_GAME` | 60s |
| `MASTERY` | 3600s (1h) |
| `RANK` | 1800s (30 min) |
| `REGISTERED_USER` | None (permanent) |

Match details are permanently cached because match results are immutable. This is critical for `/clash scout` and `tilt_check` performance.

Expired rows are cleaned up lazily (on read) and batch-cleaned by `hourly_rank_update` calling `clear_expired_cache()`.

---

### `rank_history`

Append-only log of rank snapshots. Never updated, only inserted.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `riot_puuid` | TEXT | |
| `queue_type` | TEXT | `RANKED_SOLO_5x5` or `RANKED_FLEX_SR` |
| `tier` | TEXT | `GOLD`, `PLATINUM`, etc. |
| `rank` | TEXT | `I`, `II`, `III`, `IV` |
| `league_points` | INTEGER | 0–100 |
| `wins` | INTEGER | Cumulative season wins |
| `losses` | INTEGER | Cumulative season losses |
| `recorded_at` | TIMESTAMP | UTC, set by SQLite |

**LP delta calculation:** `get_rank_at_time(puuid, queue, target_time)` returns the most recent snapshot at or before `target_time` using `recorded_at <= target_time ORDER BY recorded_at DESC LIMIT 1`.

**IMPORTANT — timezone gotcha:** `target_time` MUST be a UTC-naive string in format `"YYYY-MM-DD HH:MM:SS"`. If you pass a Paris-timezone isoformat string like `"2026-03-08T10:00:00+01:00"`, string comparison breaks because SQLite compares `"2026-03-08 09:00:00"` (space, 0x20) vs `"2026-03-08T10:00:00+01:00"` (T, 0x54), causing all same-day snapshots to match.

Snapshots accumulate indefinitely — no cleanup. Could grow large over time.

---

### `clash_teams` + `clash_team_members`

User-created teams stored in the bot (separate from Riot's Clash API).

**`clash_teams`:**
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `team_name` | TEXT | |
| `created_by_discord_id` | TEXT | |
| `created_at` | TIMESTAMP | |

Unique: `(team_name, created_by_discord_id)`.

**`clash_team_members`:**
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `team_id` | INTEGER | FK → `clash_teams(id) ON DELETE CASCADE` |
| `discord_id` | TEXT | |
| `position` | INTEGER | 0–4 (Top/Jungle/Mid/ADC/Support order) |

Unique: `(team_id, discord_id)`.

Members are joined with `users` (where `is_primary = 1`) to get `riot_puuid` and `game_name` for scouting.

---

### `tilt_tracker`

Tracks the current win/loss streak state per player to avoid duplicate notifications.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `riot_puuid` | TEXT UNIQUE | One row per player |
| `streak_type` | TEXT | `'win'` or `'loss'` |
| `streak_count` | INTEGER | Current consecutive streak length |
| `last_notified_count` | INTEGER | Streak count at last notification |
| `last_match_id` | TEXT | Most recent match processed |
| `updated_at` | TIMESTAMP | |

**Notification logic:** A notification fires only if `streak_count > last_notified_count`. After notifying, `last_notified_count` is set to `streak_count`. Row is deleted (via `reset_tilt_state`) when streak drops below `config.TILT_MIN_STREAK`.

---

### `weekly_challenges`

Active challenges for the current week, one row per (challenge × week × assignee).

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `challenge_id` | TEXT | Key into `config.GLOBAL_CHALLENGES` or `PERSONAL_CHALLENGES` |
| `challenge_type` | TEXT | `'global'` or `'personal'` |
| `week_start` | DATE | Monday of the week (`YYYY-MM-DD`) |
| `assigned_to` | TEXT | `discord_id` for personal; NULL for global |
| `is_active` | BOOLEAN | Set to 0 at end of week |
| `created_at` | TIMESTAMP | |

Unique: `(challenge_id, week_start, assigned_to)`.

---

### `challenge_completions`

Records who completed which challenge.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `challenge_id` | TEXT | |
| `week_start` | DATE | |
| `discord_id` | TEXT | |
| `completed_at` | TIMESTAMP | |
| `is_first` | BOOLEAN | First to complete a global challenge (1.5× bonus) |
| `points_awarded` | INTEGER | Points actually awarded (post-multiplier) |

Unique: `(challenge_id, week_start, discord_id)` — a player completes a challenge at most once per week.

---

### `challenge_points`

Cumulative season-split points per player.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `discord_id` | TEXT | |
| `season_split` | TEXT | e.g. `"2024_split1"` |
| `total_points` | INTEGER | Can be negative (penalties) |
| `updated_at` | TIMESTAMP | |

Unique: `(discord_id, season_split)`. Uses `ON CONFLICT DO UPDATE SET total_points = total_points + ?` for atomic increments.

---

### `weekly_stats_cache`

Accumulated per-player stat totals for the current week, used to track challenge progress.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `riot_puuid` | TEXT | |
| `week_start` | DATE | |
| `stat_type` | TEXT | e.g. `'kills'`, `'gold_earned'`, `'avg_kda'` |
| `stat_value` | REAL | Running total or computed value |
| `games_counted` | INTEGER | How many games contributed |
| `last_match_id` | TEXT | Cursor — last match processed for this stat |
| `updated_at` | TIMESTAMP | |

Unique: `(riot_puuid, week_start, stat_type)`. Uses `ON CONFLICT DO UPDATE SET stat_value = ?, games_counted = ?`.

Reset: `clear_old_weekly_stats(weeks_to_keep=0)` is called on Monday morning to wipe all rows.

---

### `player_reputation`

Current reputation score per Discord user.

| Column | Type | Notes |
|--------|------|-------|
| `discord_id` | TEXT PRIMARY KEY | |
| `score` | REAL | 0.0 – 100.0, default 50.0 |
| `updated_at` | TIMESTAMP | |

Upsert pattern: `INSERT ... ON CONFLICT(discord_id) DO UPDATE SET score = excluded.score`.

---

### `reputation_events`

Append-only log of score changes.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `discord_id` | TEXT | |
| `event_type` | TEXT | `'lp_change'`, `'game_kda'`, `'weekly_winrate'` |
| `delta` | REAL | Score change (can be negative) |
| `context` | TEXT | JSON string with event details |
| `recorded_at` | TIMESTAMP | |

The last 5 events per player are fetched by `get_recent_reputation_events()` for injection into AI prompts. Context is deserialized from JSON on read.

---

## Key Query Patterns

| Pattern | Method | Notes |
|---------|--------|-------|
| Get primary account | `get_user(discord_id)` | `is_primary = 1` |
| Get smurf | `get_user(discord_id, alias)` | `account_alias = ?` |
| All primary users | `get_all_primary_users()` | Used by all scheduled tasks |
| Closest rank before T | `get_rank_at_time(puuid, queue, utc_str)` | Must pass UTC-naive string |
| Cache read+check | `get_cache(key)` | Deletes expired rows inline |
| Cache write | `set_cache(key, data, ttl)` | `expires_at` = now + ttl if ttl else NULL |
| Atomic score increment | `add_challenge_points(id, split, pts)` | `ON CONFLICT DO UPDATE SET total + ?` |
| Reputation upsert | `set_reputation(id, score)` | `ON CONFLICT DO UPDATE` |
