"""
Module pour le leaderboard quotidien
"""
import discord
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from zoneinfo import ZoneInfo

# Ordre des tiers (du plus bas au plus haut)
TIER_ORDER = {
    'IRON': 0, 'BRONZE': 1, 'SILVER': 2, 'GOLD': 3,
    'PLATINUM': 4, 'EMERALD': 5, 'DIAMOND': 6,
    'MASTER': 7, 'GRANDMASTER': 8, 'CHALLENGER': 9
}

RANK_ORDER = {'IV': 0, 'III': 1, 'II': 2, 'I': 3}

PARIS_TZ = ZoneInfo("Europe/Paris")

# ANSI color codes for Discord
ANSI_GREEN = "\u001b[0;32m"
ANSI_RED = "\u001b[0;31m"
ANSI_GRAY = "\u001b[0;30m"
ANSI_RESET = "\u001b[0m"
ANSI_BOLD = "\u001b[1m"


def rank_to_lp(tier: str, rank: str, lp: int) -> int:
    """Convertit un rang en LP total pour comparaison"""
    if not tier:
        return -1
    tier_value = TIER_ORDER.get(tier.upper(), 0) * 400
    rank_value = RANK_ORDER.get(rank, 0) * 100
    return tier_value + rank_value + lp


def format_rank(tier: str, rank: str, lp: int) -> str:
    """Formate le rang pour affichage"""
    if not tier:
        return "Unranked"
    # Master+ n'ont pas de division
    if tier.upper() in ('MASTER', 'GRANDMASTER', 'CHALLENGER'):
        return f"{tier.capitalize()} {lp}LP"
    return f"{tier.capitalize()} {rank} {lp}LP"


def format_rank_short(tier: str, rank: str, lp: int) -> str:
    """Formate le rang court pour tableau"""
    if not tier:
        return "Unranked"
    tier_short = {
        'IRON': 'I', 'BRONZE': 'B', 'SILVER': 'S', 'GOLD': 'G',
        'PLATINUM': 'P', 'EMERALD': 'E', 'DIAMOND': 'D',
        'MASTER': 'M', 'GRANDMASTER': 'GM', 'CHALLENGER': 'C'
    }.get(tier.upper(), tier[0])

    # Convert Roman numerals to Arabic
    rank_num = {'IV': '4', 'III': '3', 'II': '2', 'I': '1'}.get(rank, rank)

    if tier.upper() in ('MASTER', 'GRANDMASTER', 'CHALLENGER'):
        return f"{tier_short} {lp}LP"
    return f"{tier_short}{rank_num} {lp}LP"


def format_lp_change_ansi(change: int) -> str:
    """Formate le changement de LP avec couleurs ANSI"""
    if change > 0:
        return f"{ANSI_GREEN}+{change:>4}{ANSI_RESET}"
    elif change < 0:
        return f"{ANSI_RED}{change:>5}{ANSI_RESET}"
    else:
        return f"{ANSI_GRAY}   0{ANSI_RESET}"


def format_lp_change_plain(change: int) -> str:
    """Formate le changement de LP sans couleur"""
    if change > 0:
        return f"+{change}"
    elif change < 0:
        return f"{change}"
    else:
        return "0"


def get_tier_from_rank(tier: str, rank: str) -> str:
    """Retourne la division complete (ex: Diamond IV)"""
    if not tier:
        return "Unranked"
    if tier.upper() in ('MASTER', 'GRANDMASTER', 'CHALLENGER'):
        return tier.capitalize()
    return f"{tier.capitalize()} {rank}"


class LeaderboardModule:
    """Gere le leaderboard et les snapshots de rang"""

    def __init__(self, riot_api, data_dragon, db_manager):
        self.api = riot_api
        self.data_dragon = data_dragon
        self.db = db_manager

    async def update_all_ranks(self) -> int:
        """Met a jour les rangs de tous les joueurs enregistres"""
        puuids = await self.db.get_all_registered_puuids()
        updated = 0

        for puuid in puuids:
            try:
                ranks = await self.api.get_league_entries_by_puuid(puuid)
                if not ranks:
                    continue

                for rank_data in ranks:
                    queue_type = rank_data.get('queueType', '')
                    if queue_type not in ('RANKED_SOLO_5x5', 'RANKED_FLEX_SR'):
                        continue

                    await self.db.save_rank_snapshot(
                        riot_puuid=puuid,
                        queue_type=queue_type,
                        tier=rank_data.get('tier', ''),
                        rank=rank_data.get('rank', ''),
                        league_points=rank_data.get('leaguePoints', 0),
                        wins=rank_data.get('wins', 0),
                        losses=rank_data.get('losses', 0)
                    )
                    updated += 1

            except Exception as e:
                print(f"[Leaderboard] Erreur update {puuid}: {e}")

        return updated

    async def get_leaderboard_data(self, queue_type: str) -> List[Dict[str, Any]]:
        """Recupere les donnees du leaderboard pour une queue"""
        puuids = await self.db.get_all_registered_puuids()
        now = datetime.now(PARIS_TZ)

        # Il y a exactement 24 heures
        time_24h_ago = now - timedelta(hours=24)

        # Lundi de cette semaine a minuit
        days_since_monday = now.weekday()
        monday = now - timedelta(days=days_since_monday)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

        players = []

        for puuid in puuids:
            try:
                # Donnees actuelles depuis l'API
                ranks = await self.api.get_league_entries_by_puuid(puuid)
                current_rank = None
                for r in (ranks or []):
                    if r.get('queueType') == queue_type:
                        current_rank = r
                        break

                if not current_rank:
                    continue

                # Donnees utilisateur
                user = await self.db.get_user_by_puuid(puuid)
                if not user:
                    continue

                current_lp = rank_to_lp(
                    current_rank.get('tier', ''),
                    current_rank.get('rank', ''),
                    current_rank.get('leaguePoints', 0)
                )

                # Rang il y a 24h
                rank_24h_ago = await self.db.get_rank_at_time(
                    puuid, queue_type, time_24h_ago.isoformat()
                )
                lp_24h_ago = rank_to_lp(
                    rank_24h_ago.get('tier', '') if rank_24h_ago else '',
                    rank_24h_ago.get('rank', '') if rank_24h_ago else '',
                    rank_24h_ago.get('league_points', 0) if rank_24h_ago else 0
                ) if rank_24h_ago else current_lp

                # Rang du lundi
                rank_monday = await self.db.get_rank_at_time(
                    puuid, queue_type, monday.isoformat()
                )
                lp_monday = rank_to_lp(
                    rank_monday.get('tier', '') if rank_monday else '',
                    rank_monday.get('rank', '') if rank_monday else '',
                    rank_monday.get('league_points', 0) if rank_monday else 0
                ) if rank_monday else current_lp

                # Calculer les changements
                lp_change_24h = current_lp - lp_24h_ago
                lp_change_week = current_lp - lp_monday

                # Detecter promotion/demotion (changement de tier sur 24h)
                prev_tier = rank_24h_ago.get('tier', '') if rank_24h_ago else current_rank.get('tier', '')
                curr_tier = current_rank.get('tier', '')
                prev_tier_value = TIER_ORDER.get(prev_tier.upper(), 0) if prev_tier else 0
                curr_tier_value = TIER_ORDER.get(curr_tier.upper(), 0) if curr_tier else 0

                promotion = curr_tier_value > prev_tier_value
                demotion = curr_tier_value < prev_tier_value

                # Streak - commented out for now
                # streak = 0
                # if current_rank.get('hotStreak'):
                #     streak = 3

                players.append({
                    'puuid': puuid,
                    'username': f"{user['game_name']}#{user['tag_line']}",
                    'display_name': user['game_name'],
                    'tier': current_rank.get('tier', ''),
                    'rank': current_rank.get('rank', ''),
                    'lp': current_rank.get('leaguePoints', 0),
                    'total_lp': current_lp,
                    'lp_change_24h': lp_change_24h,
                    'lp_change_week': lp_change_week,
                    'wins': current_rank.get('wins', 0),
                    'losses': current_rank.get('losses', 0),
                    # 'streak': streak,
                    # 'hot_streak': current_rank.get('hotStreak', False),
                    'promotion': promotion,
                    'demotion': demotion,
                    'new_division': get_tier_from_rank(curr_tier, current_rank.get('rank', ''))
                })

            except Exception as e:
                print(f"[Leaderboard] Erreur {puuid}: {e}")

        # Trier par LP total (desc)
        players.sort(key=lambda p: p['total_lp'], reverse=True)

        return players

    def create_leaderboard_embed(
        self,
        queue_name: str,
        players: List[Dict[str, Any]]
    ) -> Tuple[discord.Embed, List[str]]:
        """Cree l'embed du leaderboard et les messages speciaux"""

        if queue_name == "RANKED_SOLO_5x5":
            title = "Leaderboard Solo/Duo"
            color = discord.Color.gold()
        else:
            title = "Leaderboard Flex"
            color = discord.Color.blue()

        embed = discord.Embed(
            title=f"🏆 {title}",
            color=color,
            timestamp=datetime.now(PARIS_TZ)
        )

        special_messages = []

        if not players:
            embed.description = "Aucun joueur classe."
            return embed, special_messages

        # Build table with ANSI colors
        # Calculate max name length
        max_name_len = max((len(p['display_name']) for p in players), default=10)
        max_name_len = max(max_name_len, 6)  # minimum "Joueur"

        # Header
        table_lines = []
        table_lines.append(f"{'#':<3} {'Joueur':<{max_name_len}} {'Rang':<10} {'W/L':>10} {'24h':>6} {'Sem.':>6}")
        table_lines.append("─" * (3 + 1 + max_name_len + 1 + 10 + 1 + 10 + 1 + 6 + 1 + 6))

        for i, p in enumerate(players, 1):
            rank_str = format_rank_short(p['tier'], p['rank'], p['lp'])
            lp_24h = format_lp_change_ansi(p['lp_change_24h'])
            lp_week = format_lp_change_ansi(p['lp_change_week'])

            # Calculate winrate and W/L string
            total_games = p['wins'] + p['losses']
            winrate = int((p['wins'] / total_games) * 100) if total_games > 0 else 0
            wl_wr_str = f"{p['wins']}W/{p['losses']}L {winrate}%"

            name = p['display_name']

            line = f"{i:<3} {name:<{max_name_len}} {rank_str:<10} {wl_wr_str:>10} {lp_24h} {lp_week}"
            table_lines.append(line)

            # Messages speciaux
            if p['promotion']:
                special_messages.append(
                    f"🎉 Bravo à **{p['display_name']}** qui est passé **{p['new_division']}** !"
                )

            if p['demotion']:
                special_messages.append(
                    f"😂 **{p['display_name']}** qui demote **{p['new_division']}**, on est tous fiers de toi"
                )

            if p['lp_change_24h'] <= -100:
                special_messages.append(
                    f"😱 **{p['display_name']}** a perdu {abs(p['lp_change_24h'])}LP hier, force"
                )

            # Win streak messages - commented out
            # if p.get('hot_streak'):
            #     special_messages.append(
            #         f"🔥 **{p['display_name']}** est en win streak, GG !"
            #     )

        # Use ANSI code block for colors
        table_text = "\n".join(table_lines)
        embed.description = f"```ansi\n{table_text}\n```"

        return embed, special_messages

    async def generate_full_leaderboard(self) -> Tuple[List[discord.Embed], List[str]]:
        """Genere le leaderboard complet (Solo + Flex)"""
        embeds = []
        all_messages = []

        # Solo Queue
        solo_players = await self.get_leaderboard_data("RANKED_SOLO_5x5")
        solo_embed, solo_msgs = self.create_leaderboard_embed("RANKED_SOLO_5x5", solo_players)
        embeds.append(solo_embed)
        all_messages.extend(solo_msgs)

        # Flex Queue
        flex_players = await self.get_leaderboard_data("RANKED_FLEX_SR")
        flex_embed, flex_msgs = self.create_leaderboard_embed("RANKED_FLEX_SR", flex_players)
        embeds.append(flex_embed)
        all_messages.extend(flex_msgs)

        return embeds, all_messages

    def format_leaderboard_text(self, queue_name: str, players: List[Dict[str, Any]]) -> str:
        """Formate le leaderboard en texte pour CLI"""
        if queue_name == "RANKED_SOLO_5x5":
            title = "LEADERBOARD SOLO/DUO"
        else:
            title = "LEADERBOARD FLEX"

        # Calculate max name length
        max_name_len = max((len(p['display_name']) for p in players), default=10)
        max_name_len = max(max_name_len, 6)  # minimum "Joueur"
        name_col = max_name_len + 2

        total_width = 4 + name_col + 12 + 14 + 10 + 10

        lines = [
            "",
            "┌" + "─" * total_width + "┐",
            "│" + f" {title}".ljust(total_width) + "│",
            "├" + "─" * 4 + "┬" + "─" * name_col + "┬" + "─" * 12 + "┬" + "─" * 14 + "┬" + "─" * 10 + "┬" + "─" * 10 + "┤",
            "│" + " # ".ljust(4) + "│" + " Joueur".ljust(name_col) + "│" + " Rang".ljust(12) + "│" + " W/L".ljust(14) + "│" + " 24h".ljust(10) + "│" + " Semaine".ljust(10) + "│",
            "├" + "─" * 4 + "┼" + "─" * name_col + "┼" + "─" * 12 + "┼" + "─" * 14 + "┼" + "─" * 10 + "┼" + "─" * 10 + "┤",
        ]

        for i, p in enumerate(players, 1):
            rank_str = format_rank_short(p['tier'], p['rank'], p['lp'])
            lp_24h = format_lp_change_plain(p['lp_change_24h'])
            lp_week = format_lp_change_plain(p['lp_change_week'])
            name = p['display_name']

            # Calculate winrate and W/L string
            total_games = p['wins'] + p['losses']
            winrate = int((p['wins'] / total_games) * 100) if total_games > 0 else 0
            wl_wr_str = f"{p['wins']}W/{p['losses']}L {winrate}%"

            line = f"│ {i:<2} │ {name:<{max_name_len}} │ {rank_str:<10} │ {wl_wr_str:>12} │ {lp_24h:>8} │ {lp_week:>8} │"
            lines.append(line)

        lines.append("└" + "─" * 4 + "┴" + "─" * name_col + "┴" + "─" * 12 + "┴" + "─" * 14 + "┴" + "─" * 10 + "┴" + "─" * 10 + "┘")

        return "\n".join(lines)
