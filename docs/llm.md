# LLM Integration

All AI-generated messages go through a two-layer stack: `LLMClient` (transport) → `BotCommentary` (prompt builder).

---

## Stack

```
BotCommentary          — builds prompts, handles fallbacks
  └─ LLMClient         — calls `openclaw agent --json` subprocess
       └─ openclaw CLI — routes to the configured agent (default: main)
```

---

## `modules/llm_client.py` — `LLMClient`

Thin async wrapper around the `openclaw agent` CLI.

```python
await client.generate(system: str, user: str, max_tokens: int = 300) -> Optional[str]
```

- Spawns `openclaw agent --agent <OPENCLAW_AGENT_ID> -m <message> --json`
- Injects the system prompt as a `[SYSTEM]` prefix in the message body
- Parses `result.payloads[0].text` from the JSON response
- 30s timeout; returns `None` on any error (timeout, non-zero exit, parse failure)
- `start()` and `close()` are no-ops (kept for interface symmetry with other modules)

**Config (`.env`):**

| Var | Default | Description |
|-----|---------|-------------|
| `OPENCLAW_AGENT_ID` | `main` | Agent ID to route messages to |

---

## `modules/bot_commentary.py` — `BotCommentary`

Builds prompts and calls `LLMClient`. Every method has a static fallback string used when the LLM returns `None`.

### Base system prompt

Injected on every call. Includes:
- Tofik persona (Discord bot, LoL server, entre amis)
- Contents of `player_context.md` (player nicknames, running jokes, context)
- Rules: French only, 2–3 sentences max, no markdown, cite stats when relevant

### Methods

#### `tilt_message(player_name, streak_type, streak_count, reputation)`
Called by `TiltDetector` on every streak notification.

User prompt includes: streak type + count, last 3 reputation events (KDA, LP change, winrate), reputation tier + tone hint.

Fallback: `"{name} est en lose/win streak de {n}..."`

#### `award_message(award_name, player_name, stat_label, stat_value, reputation)`
Called by the Monday task for each of the 6 weekly awards.

User prompt includes: award name, winner, stat value, reputation tier + tone hint, last 3 events.

Fallback: `"**{award}** → {name} ({stat}: {value})"`

#### `tofik_status(players_in_game, total_players, uptime, reputations)`
Called by `/tofik`.

User prompt includes: server uptime, total registered players, who's currently in-game, best/worst reputation scores.

Fallback: plain text summary without LLM.

### `reload_player_context()`
Reloads `player_context.md` from disk without restarting the bot. Call this after editing the file.

```python
bot.commentary.reload_player_context()
```

---

## `player_context.md`

Markdown file at the repo root. Maintained by you, injected into every LLM prompt.

Write one block per player:
```markdown
**RiotName** (alias: discord_nickname)
- Rôle principal : Mid
- Champion signature : Zed, Yasuo
- Running jokes : ...
- Contexte : ...
```

The agent reads this on every message — no restart needed after `reload_player_context()`.

---

## Wiring

| Trigger | Method called | Data passed |
|---------|--------------|-------------|
| Tilt check (every 20min) — new streak | `tilt_message()` | streak info + reputation |
| Monday task — 6 awards | `award_message()` × 6 | award name, stat, reputation |
| `/tofik` command | `tofik_status()` | live game, uptime, all reputations |

`bot.commentary` is instantiated in `main.py` and passed to `TiltDetector`. `tofik_cog.py` accesses it via `self.bot.commentary`.

---

## Adding a New Message Type

1. Add a method to `BotCommentary` with a descriptive user prompt and a static fallback.
2. Call `self.llm.generate(self._system, user_prompt)`.
3. Return fallback if result is `None`.

The system prompt (persona + player context) is already set — you only need to write the user prompt for each use case.

---

## Gotchas

- **Session continuity**: each `openclaw agent` call is stateless from the CLI's perspective unless OpenClaw's session routing binds it. Messages are not part of a running conversation — each call is independent.
- **Concurrency**: multiple awards fire back-to-back in the Monday task. Each spawns a subprocess. `asyncio` handles this fine but they run sequentially (not parallelized) due to `await` chaining.
- **Latency**: the CLI adds ~1–2s overhead vs a direct HTTP call. Acceptable for Discord bots since responses are already deferred.
- **`os.popen("uptime -p")` in `tofik_cog`**: blocks the event loop briefly. Low impact but worth noting.
