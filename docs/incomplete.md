# Incomplete Features & Known Issues

This file documents unfinished work, debug code left in production, missing features, and known edge cases. Intended for future AI development.

---

## Planned But Not Yet Implemented

### Patch Watcher (from original spec)
Entire feature planned in `CLAUDE.md` (Section 6) but never built:
- No `modules/patch_watcher.py`
- No patch version diff algorithm
- No champion subscription system (`subscriptions` DB table from spec never created)
- No `/subscribe` / `/unsubscribe` commands

### `/livegame` command
Mentioned in spec (Section 10), never implemented. Would show all 10 players in an active game with their champions, ranks, and recent winrates. `riot_api/endpoints.py` has `get_active_game()` which is used in `tofik_cog.py` but there's no `/livegame` command.

### `/review` command
Mentioned in spec (Section 10), never implemented. Would analyze the last match with vision score, CS/min, comparison vs. opponent.

---

## Debug Code Left in Production

### `database/manager.py` — debug prints in `get_user()`
Lines 61–68 and 74 print every user lookup to stdout:
```python
print(f"[DB] Query: SELECT * FROM users WHERE discord_id = {repr(discord_id)} AND account_alias = {repr(alias)}")
# ...
print(f"[DB] Result: {dict(row) if row else None}")
```
These run on every `/stats`, `/leaderboard`, `/link`, `/unlink`, and most slash commands. They will spam logs in production.

### `cogs/account_cog.py` — debug prints throughout `link()`
Lines 34, 39, 42, 63, 80, 86, 98 print debug info including the raw API response:
```python
print(f"[Link] Tentative de liaison: {riot_id}#{tag}")
print(f"[Link] Réponse API account: {account}")
print(f"[Link] Réponse API summoner: {summoner}")
```

### `cogs/utility_cog.py` — debug print in `stats()`
Line 35: `print(f"[Stats] Discord user ID: {discord_id}, riot_id: {riot_id}, tag: {tag}, alias: {alias}")` — runs on every `/stats` call.

---

## Non-Atomic Operations

### Primary account promotion (`manager.py:remove_user`)
Delete + promote is two separate DB operations. If the process dies between them, the user is left with no primary account. Mitigation: wrap in a single connection with both statements.

### Challenge completion + points award (`weekly_challenges.py`)
Checking whether a challenge is completed and recording the completion + awarding points happens in multiple `await` calls. A crash between them could award points without recording completion (or vice versa). Should be wrapped in a transaction.

---

## Missing Permission Guards

### `/update_ranks`
Any user can force a full rank update for all registered players, triggering potentially 100+ API calls. No cooldown or permission check.

### `/challenges resetscore`
Correctly checks `interaction.user.guild_permissions.administrator`. This is the only admin-guarded command.

---

## Edge Cases & Gotchas

### Cache timezone bug (FIXED)
`get_rank_at_time()` in `leaderboard.py` compares UTC-naive strings. If you ever pass a timezone-aware isoformat (Paris timezone, `+01:00`), string comparison breaks. The fix converts to UTC-naive `strftime('%Y-%m-%d %H:%M:%S')` before the call. Don't revert this.

### `tilt_check` processes all accounts, not just primary
`check_all_players()` calls `get_all_primary_users()` — so only primary accounts get tilt-checked. If a user plays on a smurf, their smurf streaks are not detected.

### `weekly_challenges` won't initialize if `CHALLENGE_ANNOUNCEMENTS_CHANNEL_ID` is 0
`challenges_check` returns early if channel not configured, but `before_challenges_check` (startup init) still runs. If the init itself raises, weekly challenges silently fail to start.

### `monday_challenge_leaderboard` runs daily, not weekly
The task is scheduled daily (`@tasks.loop(time=...)`) and manually checks `if now.weekday() != 0: return`. This is correct but non-obvious. It does NOT use a weekly loop.

### `clear_old_weekly_stats(weeks_to_keep=0)` deletes everything
Monday task calls this with `weeks_to_keep=0`, which generates `date('now', '-0 days')` = today. All rows where `week_start < today` get deleted — including previous weeks. This is intentional but could lose data if the retrospective runs after the cleanup. The current order is: retrospective → cleanup → new challenges. This is correct order.

### `tofik_cog.py` uses `os.popen()` synchronously
`os.popen("uptime -p").read()` is a blocking synchronous call inside an async handler. It's fast enough not to matter in practice but technically blocks the event loop.

### Clash team comparison requires the team creator
`/clash scout our_team:myteam` looks up the team by `(team_name, interaction.user.id)`. If another team member uses it, the lookup returns `None` and the comparison is silently skipped.

### `get_active_game()` in `tofik_cog` swallows all exceptions
```python
try:
    live_game = await self.bot.riot_api.get_active_game(user['riot_puuid'])
except:
    continue
```
Bare `except:` — any error (including API key expiry) is silently ignored.
