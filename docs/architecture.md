# Architecture

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Discord | discord.py 2.x (slash commands via `app_commands`) |
| HTTP | aiohttp (async, non-blocking) |
| Database | SQLite via aiosqlite |
| Riot API | Official Riot Games API + Data Dragon CDN |
| Scraping | cloudscraper + BeautifulSoup4 (LeagueOfGraphs) |
| Timezone | All scheduled tasks use `Europe/Paris` via `zoneinfo` |

---

## Project Structure

```
lolbot/
├── main.py                  # Bot entry point, all scheduled tasks
├── config.py                # All tunable values (weights, thresholds, IDs)
├── cli.py                   # Admin CLI mode (no Discord, for testing)
├── database/
│   ├── models.py            # SQLite schema (single SCHEMA string)
│   └── manager.py           # All DB queries (DatabaseManager class)
├── riot_api/
│   ├── client.py            # HTTP client with rate limiter (token bucket)
│   ├── endpoints.py         # One method per Riot endpoint
│   └── data_dragon.py       # Champion static data + patch version
├── modules/
│   ├── stats.py             # /stats logic
│   ├── clash_scout.py       # Clash team analysis + danger score
│   ├── leaderboard.py       # Daily/weekly leaderboard generation
│   ├── weekly_challenges.py # Challenge system logic
│   ├── tilt_detector.py     # Win/loss streak detection
│   ├── reputation.py        # Player reputation scoring (0–100)
│   ├── llm_client.py        # OpenClaw CLI wrapper (subprocess)
│   ├── bot_commentary.py    # LLM message builder (tilt, awards, /tofik)
│   └── weekly_awards.py     # Weekly award winner computation
├── cogs/
│   ├── account_cog.py       # /link /unlink /accounts
│   ├── utility_cog.py       # /stats /leaderboard /update_ranks
│   ├── clash_cog.py         # /clash team /clash scout
│   ├── challenge_cog.py     # /challenges
│   └── tofik_cog.py         # /tofik (oversight/status)
├── utils/
│   ├── embeds.py            # Discord embed builders
│   ├── scraper.py           # LeagueOfGraphs season stats scraper
│   └── helpers.py           # Empty placeholder
└── docs/                    # This folder
```

---

## Module Responsibilities

### `main.py` — `LoLBot`
Owns the bot lifecycle and all background tasks. Instantiates every module and passes them into cogs via `bot.*_module` attributes. Loads 5 cogs on startup.

### `config.py`
Single source of truth for all numeric constants. Nothing is hardcoded in logic files — always reference `config.X`. Key sections: `CACHE_TTL`, `DANGER_SCORE`, `REPUTATION`, `GLOBAL_CHALLENGES`, `PERSONAL_CHALLENGES`.

### `database/manager.py` — `DatabaseManager`
All SQL is here. No raw queries anywhere else. Every method is async and opens its own connection (aiosqlite connection-per-operation pattern). See `docs/database.md` for full schema.

### `riot_api/client.py` — `RiotAPIClient` + `RateLimiter`
Sliding window rate limiter: 20 req/s and 100 req/2min. `acquire()` blocks until a slot is available. Cache check happens before every request — cache hit skips both rate limiter and HTTP. Failed requests (non-200) are not cached.

### `riot_api/endpoints.py` — `RiotEndpoints`
Thin wrappers. Each method builds the URL, sets a cache key + TTL, and delegates to `client.request()`. No business logic here.

### `modules/leaderboard.py` — `LeaderboardModule`
Handles rank snapshots and LP delta calculation. Converts all datetimes to UTC-naive strings before SQLite comparison (SQLite stores `CURRENT_TIMESTAMP` as UTC without timezone, so Paris-aware isoformat strings would break string comparison).

### `modules/clash_scout.py` — `ClashScoutModule`
Most complex module. Fetches parallel data for 5 players, computes danger scores, detects roles, identifies smurfs. Uses `asyncio.gather` for parallelism. Scrapes LeagueOfGraphs for season champion stats per player.

### `modules/reputation.py` — `ReputationManager`
See `docs/reputation.md` for full details. Provides `get_reputation(discord_id)` → structured dict for injection into AI prompts.

---

## Scheduled Tasks

All defined in `main.py` as `@tasks.loop(...)` methods. All wait for `bot.wait_until_ready()` before first execution.

| Task | Schedule | What it does |
|------|----------|-------------|
| `daily_leaderboard` | Daily 10:00 Paris | Refresh all ranks → post leaderboard embed → update LP reputation |
| `hourly_rank_update` | Every 1h (immediate start) | Save rank snapshots to `rank_history` → clear expired cache |
| `challenges_check` | Every 30min (immediate start) | Check challenge progress for all users → announce completions |
| `monday_challenge_leaderboard` | Monday 10:00 Paris | End-of-week retrospective + new challenges + winrate reputation update |
| `tilt_check` | Every 20min (immediate start) | Detect streaks → notify → update KDA reputation per new game |

`hourly_rank_update` runs immediately on startup, so `rank_history` is populated from the first minute.

---

## Data Flows

### `/stats` command

```
User → /stats
  → StatsModule.get_stats(discord_id or riot_id)
    → [linked] db.get_user(discord_id, alias)
    → [direct] api.get_account_by_riot_id(name, tag)
  → api.get_league_entries_by_puuid()   # Solo + Flex ranks
  → api.get_champion_masteries()         # Top 3 champions
  → data_dragon.get_champion_id_to_name_map()
  → embeds.create_stats_embed()
→ Discord embed
```

### `/clash scout`

```
User → /clash scout [name tag]
  → api.get_account_by_riot_id()        # → puuid
  → api.get_clash_player_by_puuid()     # → teamId
  → api.get_clash_team(teamId)          # → 5 player puuids

  For each of 5 players (parallel):
    → api.get_league_entries_by_puuid() # rank
    → api.get_champion_masteries(15)    # top champs
    → api.get_match_history(20)         # recent matches
    → api.get_match(each id)            # KDA, champion, role, win
    → scraper.scrape_champion_season_stats() # season WR per champ

  → Calculate danger score per champion per player
  → Aggregate: top 5 bans + top 5 alternates
  → Detect team composition & average elo
→ Discord embeds (bans + analysis)
```

### Daily leaderboard (10:00 Paris)

```
Timer fires
  → update_all_ranks()
      → For each registered PUUID:
          api.get_league_entries_by_puuid()
          db.save_rank_snapshot(tier, rank, lp, wins, losses)

  → generate_full_leaderboard()
      → For each PUUID:
          api.get_league_entries_by_puuid()   # current rank (cached)
          db.get_rank_at_time(24h_ago_utc)    # baseline snapshot
          compute lp_change_24h, lp_change_week

  → For each player:
      reputation.update_lp_change(discord_id, lp_change_24h)

  → channel.send(embed)
```

### Tilt check (every 20min)

```
Timer fires
  → For each primary user:
      api.get_match_history(last 10 ranked)
      Compare to stored last_match_id

      For each NEW match:
          api.get_match(id)               # cached permanently
          reputation.update_game_kda(kills, deaths, assists, champion)

      _compute_streak(all 10 matches)     # consecutive W or L from most recent
      If streak >= TILT_MIN_STREAK AND > last_notified_count:
          db.update_tilt_state()
          _generate_streak_message()      # TODO: LLM hook
          channel.send(@mention + embed)
```

### Monday end-of-week (10:00 Paris)

```
Timer fires (only runs if weekday == 0)
  → challenges.process_week_end()         # apply penalties
  → db.clear_old_weekly_stats()           # reset weekly stats cache
  → leaderboard.generate_weekly_retrospective(prev_week_start)

  → For each primary user:
      db.get_all_weekly_stats(puuid, prev_week_start)
      reputation.update_weekly_winrate(wins, losses)

  → challenges.initialize_weekly_challenges()  # new week setup
  → channel.send(retrospective + challenge leaderboard + new challenges)
```

---

## Multi-account System

Users can link multiple Riot accounts (smurfs). Each account has an optional `alias`. One account per Discord user is marked `is_primary = 1`.

- Commands default to the primary account.
- Pass `alias` param to target a specific smurf.
- When the primary account is deleted, the oldest remaining account auto-promotes to primary.
- All reputation and leaderboard data is per `discord_id`, not per `riot_puuid` — so a player's score represents them regardless of which account they're playing on.

---

## Environment Variables

```env
DISCORD_BOT_TOKEN=...
RIOT_API_KEY=...
```

---

## Startup Sequence

1. `DatabaseManager.initialize()` — creates all tables if not exist
2. `RiotAPIClient.start()` — opens aiohttp session
3. `DataDragon.load_champions()` — loads champion ID→name map
4. Load 5 cogs (registers slash commands)
5. `tree.sync()` — sync commands globally (NOT per-guild, avoids Discord 429)
6. Start all 5 background tasks
7. `on_ready()` fires — set bot status to "Playing League of Legends"
8. `challenges_check.before_loop` initializes weekly challenges if none exist

---

## API Rate Limits

Riot dev key: **20 req/s** and **100 req/2min**. The `RateLimiter` in `client.py` uses a sliding window (deque of timestamps). `acquire()` blocks until both windows have room. Cache hits bypass the rate limiter entirely — match details are cached permanently, so clash scouts don't re-fetch known matches.

The `/clash scout` command is the most API-intensive operation: up to 5 players × (1 rank + 1 mastery + 1 history + ~20 match details + 1 scrape) = ~115 API calls minimum. This will trigger rate limit waits for dev keys.
