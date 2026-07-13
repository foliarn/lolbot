# Reputation System

Each player has a reputation score between **0 and 100** (default: 50).
The lower the score, the more brutal the AI-generated messages become.

---

## Score Sources

Three events update the score. All weights are editable in `config.py → REPUTATION`.

### LP Change (daily, 10am)

Triggered by the daily leaderboard task after computing 24h LP delta.

| LP Change | Delta |
|-----------|-------|
| ≥ +50     | +8    |
| ≥ +15     | +3    |
| -20 to +15 | 0 (neutral) |
| ≤ -20     | -5    |
| ≤ -50     | -12   |

### KDA per Game (real-time, every new ranked game)

Triggered by the tilt detector whenever it detects new matches (~every 20 min).
Uses `(kills + assists) / deaths`. If deaths = 0, KDA = kills + assists.

| KDA       | Delta | Notes |
|-----------|-------|-------|
| ≥ 6.0     | +5    | 12/10 territory |
| ≥ 3.0     | +2    |       |
| 1.5 – 3.0 | 0     | neutral |
| < 1.5     | -3    |       |
| < 0.8     | -7    | 1/10 territory |

### Weekly Winrate (Monday)

Triggered by the Monday task using the previous week's stats.
Ignored if fewer than 5 games played that week (`WINRATE_MIN_GAMES`).

| Winrate   | Delta |
|-----------|-------|
| ≥ 60%     | +10   |
| ≥ 52%     | +3    |
| 45 – 52%  | 0     |
| < 45%     | -8    |
| < 35%     | -15   |

---

## Roast Tiers

The score maps to a tone tier passed to the AI as a prompt hint.

| Score  | Tier        | AI tone hint |
|--------|-------------|--------------|
| 80–100 | RESPECT     | Ce joueur joue bien cette semaine. Légère taquinerie au max. |
| 60–80  | CHILL       | Niveau normal de vannes entre amis. Rien d'agressif. |
| 40–60  | NEUTRAL     | Quelques piques bien placés. Il mérite d'entendre la vérité. |
| 20–40  | SOFT_ROAST  | Sans pitié. Cite ses stats si ça aide. Il le sait lui-même. |
| 0–20   | ROAST       | Full roast. Pas de pitié. Cite ses pires stats et games exactes. C'est mérité. |

---

## Data Passed to BotCommentary

```python
{
    "score": 17.0,
    "tier": "ROAST",
    "tone_hint": "Full roast. Pas de pitié...",
    "recent_events": [
        {"event_type": "game_kda", "delta": -7.0, "context": {"kills": 1, "deaths": 10, "assists": 2, "kda": 0.3, "champion": "Zed"}},
        {"event_type": "lp_change", "delta": -12.0, "context": {"lp_change": -67}},
        {"event_type": "weekly_winrate", "delta": -8.0, "context": {"wins": 4, "losses": 9, "winrate": 30.8}}
    ]
}
```

`recent_events` contains the last 5 events — the AI can reference them directly ("tu as perdu 67 LP hier sur Zed avec un KDA de 0.3").

---

## Architecture

```
tilt_detector (every 20min)
  └─ new match detected → update_game_kda()

main.py daily_leaderboard (10am)
  └─ LP delta computed → update_lp_change()

main.py monday_challenge_leaderboard (Monday 10am)
  └─ previous week stats → update_weekly_winrate()

BotCommentary
  └─ get_reputation(discord_id) → inject into LLM prompt
```

### Key files

| File | Role |
|------|------|
| `modules/reputation.py` | `ReputationManager` — score logic |
| `database/models.py` | `player_reputation`, `reputation_events` tables |
| `database/manager.py` | `get_reputation_score`, `set_reputation`, `add_reputation_event`, `get_recent_reputation_events`, `get_all_reputations` |
| `config.py → REPUTATION` | All thresholds and deltas |

---

## Notes

- Score is clamped to [0, 100] at all times.
- No automatic decay — score reflects cumulative performance history.
- `get_all_reputations()` returns all players sorted by score ascending (most roastable first), useful for a future `/reputation` leaderboard command.
