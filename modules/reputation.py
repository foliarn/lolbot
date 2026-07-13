"""
Module de réputation des joueurs.
Score 0-100 (start 50). Plus bas = plus on se moque.
Alimenté par : LP daily, KDA par game, winrate hebdo.
"""
from typing import Optional, Dict, Any, List

import config


# Tiers used by BotCommentary to calibrate LLM tone
REPUTATION_TIERS = [
    (80, "RESPECT",    "Ce joueur joue bien cette semaine. Légère taquinerie au max."),
    (60, "CHILL",      "Niveau normal de vannes entre amis. Rien d'agressif."),
    (40, "NEUTRAL",    "Quelques piques bien placés. Il mérite d'entendre la vérité."),
    (20, "SOFT_ROAST", "Sans pitié. Cite ses stats si ça aide. Il le sait lui-même."),
    (0,  "ROAST",      "Full roast. Pas de pitié. Cite ses pires stats et games exactes. C'est mérité."),
]


def get_tier(score: float) -> tuple[str, str]:
    for threshold, tier, hint in REPUTATION_TIERS:
        if score >= threshold:
            return tier, hint
    return REPUTATION_TIERS[-1][1], REPUTATION_TIERS[-1][2]


class ReputationManager:
    """Gère les scores de réputation et les événements associés."""

    def __init__(self, db_manager):
        self.db = db_manager

    async def get_reputation(self, discord_id: str) -> Dict[str, Any]:
        """Retourne le score, le tier et les derniers événements d'un joueur."""
        score = await self.db.get_reputation_score(discord_id)
        if score is None:
            score = 50.0
        tier, tone_hint = get_tier(score)
        events = await self.db.get_recent_reputation_events(discord_id, limit=5)
        return {
            "score": round(score, 1),
            "tier": tier,
            "tone_hint": tone_hint,
            "recent_events": events,
        }

    async def update_lp_change(self, discord_id: str, lp_change: int):
        """Met à jour la réputation en fonction du gain/perte de LP quotidien."""
        r = config.REPUTATION
        if lp_change >= r['LP_GAIN_BIG']:
            delta = r['LP_DELTA_BIG_GAIN']
        elif lp_change >= r['LP_GAIN']:
            delta = r['LP_DELTA_GAIN']
        elif lp_change <= r['LP_LOSS_BIG']:
            delta = r['LP_DELTA_BIG_LOSS']
        elif lp_change <= r['LP_LOSS']:
            delta = r['LP_DELTA_LOSS']
        else:
            return  # neutral range, no change

        await self._apply(discord_id, "lp_change", delta, {"lp_change": lp_change})

    async def update_game_kda(
        self,
        discord_id: str,
        kills: int,
        deaths: int,
        assists: int,
        champion: Optional[str] = None,
        match_id: Optional[str] = None,
    ):
        """Met à jour la réputation en fonction du KDA d'une game."""
        r = config.REPUTATION
        kda = (kills + assists) / deaths if deaths > 0 else float(kills + assists)

        if kda >= r['KDA_GREAT']:
            delta = r['KDA_DELTA_GREAT']
        elif kda >= r['KDA_GOOD']:
            delta = r['KDA_DELTA_GOOD']
        elif kda < r['KDA_TERRIBLE']:
            delta = r['KDA_DELTA_TERRIBLE']
        elif kda < r['KDA_BAD']:
            delta = r['KDA_DELTA_BAD']
        else:
            return  # neutral range

        context: Dict[str, Any] = {
            "kills": kills, "deaths": deaths, "assists": assists,
            "kda": round(kda, 2),
        }
        if champion:
            context["champion"] = champion
        if match_id:
            context["match_id"] = match_id

        await self._apply(discord_id, "game_kda", delta, context)

    async def update_weekly_winrate(self, discord_id: str, wins: int, losses: int):
        """Met à jour la réputation en fonction du winrate de la semaine."""
        r = config.REPUTATION
        total = wins + losses
        if total < r['WINRATE_MIN_GAMES']:
            return

        wr = wins / total * 100

        if wr >= r['WINRATE_GREAT']:
            delta = r['WINRATE_DELTA_GREAT']
        elif wr >= r['WINRATE_GOOD']:
            delta = r['WINRATE_DELTA_GOOD']
        elif wr < r['WINRATE_TERRIBLE']:
            delta = r['WINRATE_DELTA_TERRIBLE']
        elif wr < r['WINRATE_BAD']:
            delta = r['WINRATE_DELTA_BAD']
        else:
            return  # neutral range

        await self._apply(
            discord_id, "weekly_winrate", delta,
            {"wins": wins, "losses": losses, "winrate": round(wr, 1)}
        )

    async def _apply(self, discord_id: str, event_type: str, delta: float, context: dict):
        current = await self.db.get_reputation_score(discord_id)
        if current is None:
            current = 50.0
        new_score = max(0.0, min(100.0, current + delta))
        await self.db.set_reputation(discord_id, new_score)
        await self.db.add_reputation_event(discord_id, event_type, delta, context)
        print(f"[Reputation] {discord_id} {event_type}: {current:.1f} → {new_score:.1f} ({delta:+.1f})")
