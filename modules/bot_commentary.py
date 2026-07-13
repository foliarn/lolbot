"""
BotCommentary - Génère tous les messages Discord via LLM.
Fallback sur messages statiques si le LLM est indisponible.
"""
import os
from typing import Optional, Dict, Any, List

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modules.clash_scout import ScoutResult

from .llm_client import LLMClient

# Chemin du fichier de contexte joueurs (relatif à la racine du projet)
_PLAYER_CONTEXT_PATH = os.path.join(os.path.dirname(__file__), '..', 'player_context.md')

_SYSTEM_PROMPT = """Tu es Tofik, le bot Discord d'un serveur League of Legends entre amis.
Tu commentes les performances des joueurs avec humour, sans filtre, parfois brutal selon leur niveau.
Ton ton s'adapte à leur score de réputation : plus il est bas, plus tu es sans pitié.

{player_context}

Règles :
- Réponds UNIQUEMENT en français
- Maximum 2-3 phrases courtes
- Pas de markdown, pas d'emojis sauf si vraiment pertinent
- Cite les stats si ça appuie le message
- Ton style : entre potes, vanne directe, pas de condescendance générique"""


def _load_player_context() -> str:
    try:
        with open(_PLAYER_CONTEXT_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Only include the players section
            if '## Joueurs' in content:
                return content[content.index('## Joueurs'):]
            return content
    except FileNotFoundError:
        return "(aucun contexte joueur configuré)"


class BotCommentary:
    """Génère les messages Discord via LLM avec fallback statique."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self._player_context = _load_player_context()
        self._system = _SYSTEM_PROMPT.format(player_context=self._player_context)

    def reload_player_context(self):
        """Recharge player_context.md sans redémarrer le bot."""
        self._player_context = _load_player_context()
        self._system = _SYSTEM_PROMPT.format(player_context=self._player_context)

    # ==================== Tilt / Streak ====================

    async def tilt_message(
        self,
        player_name: str,
        streak_type: str,
        streak_count: int,
        reputation: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Message pour une notification de streak (win ou loss)."""
        type_fr = "défaite" if streak_type == 'loss' else "victoire"
        type_fr_pl = "défaites" if streak_type == 'loss' else "victoires"

        rep_block = _format_reputation(reputation)
        recent = _format_recent_events(reputation.get('recent_events', []) if reputation else [])

        user_prompt = (
            f"{player_name} vient d'enchaîner sa {streak_count}e {type_fr} consécutive "
            f"({streak_count} {type_fr_pl} d'affilée).\n"
            f"{rep_block}"
            f"{recent}"
            f"Génère un message de notification pour le canal Discord."
        )

        result = await self.llm.generate(self._system, user_prompt)
        if result:
            return result

        # Fallback
        if streak_type == 'loss':
            return f"{player_name} est en lose streak de {streak_count}... Quelqu'un appelle une ambulance."
        return f"{player_name} est en win streak de {streak_count} ! Incroyable !"

    # ==================== Weekly Awards ====================

    async def award_message(
        self,
        award_name: str,
        player_name: str,
        stat_label: str,
        stat_value: str,
        reputation: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Message pour l'annonce d'un award hebdomadaire."""
        rep_block = _format_reputation(reputation)
        recent = _format_recent_events(reputation.get('recent_events', []) if reputation else [])

        user_prompt = (
            f"Annonce le gagnant du \"{award_name}\" de la semaine.\n"
            f"Gagnant : {player_name}\n"
            f"Stat : {stat_label} = {stat_value}\n"
            f"{rep_block}"
            f"{recent}"
            f"Génère une annonce courte et percutante (2 phrases max)."
        )

        result = await self.llm.generate(self._system, user_prompt)
        if result:
            return result

        # Fallback
        return f"**{award_name}** → {player_name} ({stat_label} : {stat_value})"

    # ==================== /tofik status ====================

    async def tofik_status(
        self,
        players_in_game: List[str],
        total_players: int,
        uptime: str,
        reputations: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Message pour la commande /tofik."""
        in_game_str = (
            f"{len(players_in_game)} joueur(s) actuellement sur la Faille : {', '.join(players_in_game)}"
            if players_in_game
            else "Personne sur la Faille en ce moment."
        )

        rep_summary = ""
        if reputations:
            worst = reputations[0]  # sorted ASC = worst first
            best = reputations[-1]
            rep_summary = (
                f"Réputation : meilleur joueur cette semaine = {best.get('game_name', '?')} ({best.get('score', 50):.0f}/100), "
                f"plus mauvais = {worst.get('game_name', '?')} ({worst.get('score', 50):.0f}/100).\n"
            )

        user_prompt = (
            f"Uptime serveur : {uptime}. {total_players} joueurs enregistrés.\n"
            f"{in_game_str}\n"
            f"{rep_summary}"
            f"Donne un bref compte-rendu de la situation, dans ton style."
        )

        result = await self.llm.generate(self._system, user_prompt, max_tokens=200)
        if result:
            return result

        # Fallback
        players_str = f" ({', '.join(players_in_game)})" if players_in_game else ""
        return (
            f"Le serveur est stable (Uptime : `{uptime}`).\n"
            f"Je surveille `{total_players}` joueurs, dont `{len(players_in_game)}` sont sur la Faille{players_str}."
        )


    # ==================== Clash Scout ====================

    async def clash_commentary(self, result: "ScoutResult") -> str:
        """Analyse LLM complète d'une équipe adverse après scouting."""

        # Build bans summary
        bans_lines = []
        for i, ban in enumerate(result.optimal_bans[:5], 1):
            reasons = ", ".join(ban.reasons) if ban.reasons else "aucune raison"
            bans_lines.append(
                f"  {i}. {ban.champion_name} ({ban.total_score} pts) - {ban.player_name} - {reasons}"
                + (f" - {ban.winrate:.0f}% WR sur {ban.games_played}g" if ban.games_played > 0 else "")
            )

        # Build players summary
        players_lines = []
        for p in result.players:
            rank_str = f"{p.rank.tier} {p.rank.rank} {p.rank.lp}LP" if p.rank.tier else "Unranked"
            role_str = p.main_role if p.main_role != "UNKNOWN" else "rôle inconnu"
            champs = ", ".join(
                f"{c.champion_name}"
                + (f" ({c.season_games}g {c.season_winrate:.0f}%WR)" if c.season_games >= 3 else
                   f" ({c.games_played}g {c.winrate:.0f}%WR)" if c.games_played > 0 else "")
                for c in p.top_champions[:3]
            )
            players_lines.append(
                f"  - {p.game_name}#{p.tag_line} | {rank_str} | {role_str} | "
                f"WR récent {p.recent_winrate:.0f}% KDA {p.recent_kda:.1f} | Champs: {champs}"
            )

        user_prompt = (
            f"Voici le rapport de scouting d'une équipe adverse en Clash.\n\n"
            f"Composition: {result.team_composition} | Elo moyen: {result.average_elo} LP\n\n"
            f"Joueurs:\n" + "\n".join(players_lines) + "\n\n"
            f"Bans recommandés:\n" + "\n".join(bans_lines) + "\n\n"
            f"Fais un résumé stratégique percutant pour le canal Discord : "
            f"qui sont les menaces, quoi baner en priorité et pourquoi, "
            f"et si l'équipe adverse est vraiment dangereuse ou pas. "
            f"Sois direct, utilise les stats pour appuyer, parle comme entre potes."
        )

        result_text = await self.llm.generate(self._system, user_prompt, max_tokens=500)
        if result_text:
            return result_text

        # Fallback
        if result.optimal_bans:
            top = result.optimal_bans[0]
            return (
                f"**Scout terminé.** Elo moyen adverse : {result.average_elo} LP.\n"
                f"Ban prioritaire : **{top.champion_name}** ({', '.join(top.reasons)})."
            )
        return f"**Scout terminé.** Elo moyen adverse : {result.average_elo} LP."


# ==================== Helpers ====================

def _format_reputation(rep: Optional[Dict[str, Any]]) -> str:
    if not rep:
        return ""
    return (
        f"Score de réputation : {rep.get('score', 50):.0f}/100 "
        f"({rep.get('tier', 'NEUTRAL')}) — {rep.get('tone_hint', '')}\n"
    )


def _format_recent_events(events: List[Dict[str, Any]]) -> str:
    if not events:
        return ""
    lines = []
    for e in events[:3]:
        ctx = e.get('context', {})
        etype = e.get('event_type', '')
        delta = e.get('delta', 0)
        sign = '+' if delta >= 0 else ''

        if etype == 'game_kda':
            lines.append(
                f"- Game {ctx.get('champion', '?')} : {ctx.get('kills', 0)}/{ctx.get('deaths', 0)}/{ctx.get('assists', 0)} "
                f"(KDA {ctx.get('kda', 0):.1f}) → {sign}{delta:.0f} pts réputation"
            )
        elif etype == 'lp_change':
            lines.append(f"- LP hier : {ctx.get('lp_change', 0):+d} LP → {sign}{delta:.0f} pts réputation")
        elif etype == 'weekly_winrate':
            lines.append(
                f"- Winrate semaine : {ctx.get('wins', 0)}W/{ctx.get('losses', 0)}L "
                f"({ctx.get('winrate', 0):.1f}%) → {sign}{delta:.0f} pts réputation"
            )

    if not lines:
        return ""
    return "Historique récent :\n" + "\n".join(lines) + "\n"
