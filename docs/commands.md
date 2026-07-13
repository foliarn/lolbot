# Commands

All commands use Discord slash commands (`app_commands`). Responses are ephemeral (`ephemeral=True`) where indicated; otherwise visible to the channel.

---

## Account Management — `account_cog.py`

### `/link`
Links a Riot account to the caller's Discord account.

| Param | Required | Description |
|-------|----------|-------------|
| `riot_id` | Yes | RiotID name (e.g. `Faker`) |
| `tag` | Yes | Tag (e.g. `KR1`) |
| `alias` | No | Nickname for this account (e.g. `main`, `smurf1`) |

- First account linked automatically becomes the primary account (`is_primary = 1`).
- Subsequent accounts are secondary by default.
- Calls `ACCOUNT-V1` (RiotID → PUUID) then `SUMMONER-V4` (PUUID → summoner_id).
- Fails if the same Riot account is already linked to the same Discord user.
- Response: ephemeral.

### `/unlink`
Removes a linked Riot account.

| Param | Required | Description |
|-------|----------|-------------|
| `alias` | No | Account alias to remove. Omit to remove the primary account. |

- If the primary account is removed, the oldest remaining account is auto-promoted to primary.
- Response: ephemeral.

### `/accounts`
Shows all linked accounts for the caller.

- Displays an embed with each account: `game_name#tag`, alias, primary/secondary status.
- Response: ephemeral.

---

## Stats & Leaderboard — `utility_cog.py`

### `/stats`
Shows a player's Solo/Flex rank and top 3 champion masteries.

| Param | Required | Description |
|-------|----------|-------------|
| `riot_id` | No | Look up by RiotID directly (bypasses linked account) |
| `tag` | No | Tag, required if `riot_id` is provided |
| `alias` | No | Use a specific linked smurf instead of primary |

- If no params: uses the caller's primary linked account.
- If `riot_id` + `tag`: direct lookup without a linked account.
- Calls `LEAGUE-V4` (rank) + `CHAMPION-MASTERY-V4` (top 3 champions).
- Response: public embed.

### `/leaderboard`
Shows the ranked leaderboard for all linked users.

| Param | Required | Description |
|-------|----------|-------------|
| `queue` | No | `solo` / `flex` / `both` (default: `both`) |

- LP delta over 24h and week are displayed for each player.
- Response: public embed(s).

### `/update_ranks`
Forces an immediate rank snapshot refresh for all registered PUUIDs.

- No params. Returns how many snapshots were recorded.
- Response: ephemeral. No permission check — any user can trigger this.

---

## Clash — `clash_cog.py`

### `/clash scout`
Scouts an enemy Clash team via the Riot Clash API.

| Param | Required | Description |
|-------|----------|-------------|
| `riot_id` | Yes | RiotID of any player in the enemy team |
| `tag` | Yes | Tag |
| `our_team` | No | Name of your saved team (for comparison) |

- Resolves the player → their Clash team → all 5 members.
- For each player: fetches rank, top masteries, last 20 match details, and scrapes LeagueOfGraphs for season champion stats.
- Returns: team analysis embed + players embed + optimal bans embed + alternative bans embed.
- If `our_team` is provided and found: computes a threat ratio and adds it to the analysis embed.
- Shows a loading message during processing (~10–30s for dev API keys).
- Error states: `error` (player not found), `no_clash` (not in Clash), `no_team` (team fetch failed).
- Response: public embeds.

### `/clash analyze`
Same analysis as `/clash scout` but for a manually specified list of players (without needing Clash API).

| Param | Required | Description |
|-------|----------|-------------|
| `players` | Yes | Comma-separated `RiotID#TAG` list (max 5). Example: `Player1#EUW, Player2#TAG` |

- Resolves each RiotID to PUUID, then runs the full player analysis.
- Response: public embeds.

### `/clash team create`
Creates a saved Clash team (5 linked Discord members).

| Param | Required | Description |
|-------|----------|-------------|
| `team_name` | Yes | Name for the team |
| `p1`–`p5` | Yes | 5 Discord member mentions |

- All 5 members must have a linked Riot account (`/link`). If any are missing, returns an error listing who needs to link.
- Unique per `(team_name, creator_discord_id)`.
- Response: ephemeral.

### `/clash team list`
Shows all Clash teams the caller created or is a member of.

- Returns up to 10 team embeds. Creator teams shown in green, member teams in blue.
- Response: ephemeral.

### `/clash team delete`
Deletes a Clash team the caller created.

| Param | Required | Description |
|-------|----------|-------------|
| `team_name` | Yes | Name of the team to delete |

- Only the creator can delete their own team.
- Response: ephemeral.

---

## Challenges — `challenge_cog.py`

### `/challenges view`
Shows the current week's challenges for a player.

| Param | Required | Description |
|-------|----------|-------------|
| `user` | No | Target Discord member. Defaults to caller. |

- Displays global challenges (visible to everyone) and personal challenges (assigned to this user).
- Shows progress toward each challenge target.
- Response: public embed.

### `/challenges leaderboard`
Shows the season challenge points leaderboard.

- Sorted by total points descending.
- Response: public embed.

### `/challenges resetscore`
[Admin only] Resets all challenge points to 0 for the current week.

- Requires `administrator` Discord permission.
- Response: ephemeral.

---

## Tofik Status — `tofik_cog.py`

### `/tofik`
Displays the current server state from "Tofik's perspective".

- Shows: server uptime, number of registered players, who is currently in-game (via `SPECTATOR-V5`).
- Also logs command errors to `tofik_oversight.log`.
- Response: public message.

> **Note:** This command's message is hardcoded. The LLM integration (feeding live data + reputation into an AI prompt) is planned but not yet implemented.

---

## Summary Table

| Command | Cog | Ephemeral | Notes |
|---------|-----|-----------|-------|
| `/link` | account_cog | Yes | |
| `/unlink` | account_cog | Yes | |
| `/accounts` | account_cog | Yes | |
| `/stats` | utility_cog | Error only | |
| `/leaderboard` | utility_cog | Error only | |
| `/update_ranks` | utility_cog | Yes | No permission check |
| `/clash scout` | clash_cog | Error only | Heavy API usage |
| `/clash analyze` | clash_cog | Error only | |
| `/clash team create` | clash_cog | Yes | |
| `/clash team list` | clash_cog | Yes | |
| `/clash team delete` | clash_cog | Yes | |
| `/challenges view` | challenge_cog | Error only | |
| `/challenges leaderboard` | challenge_cog | Error only | |
| `/challenges resetscore` | challenge_cog | Yes | Admin only |
| `/tofik` | tofik_cog | No | Hardcoded response |
