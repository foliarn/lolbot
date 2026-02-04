"""
Generateurs d'embeds Discord
"""
import discord
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.clash_scout import PlayerData, DangerScore


def create_stats_embed(
    game_name: str,
    tag_line: str,
    level: int,
    ranks: List[Dict[str, Any]],
    masteries: List[Dict[str, Any]],
    champion_names: Dict[int, str]
) -> discord.Embed:
    """Crée un embed pour la commande /stats"""
    embed = discord.Embed(
        title=f"Stats de {game_name}#{tag_line}",
        color=discord.Color.blue()
    )

    embed.add_field(name="Niveau", value=str(level), inline=True)

    # Parse ranks by queue type
    solo_rank = None
    flex_rank = None

    for rank_data in ranks:
        queue = rank_data.get('queueType', '')
        if 'RANKED_SOLO' in queue:
            solo_rank = rank_data
        elif 'RANKED_FLEX' in queue:
            flex_rank = rank_data

    # Solo/Duo Rank
    if solo_rank:
        tier = solo_rank.get('tier', 'UNRANKED')
        rank = solo_rank.get('rank', '')
        lp = solo_rank.get('leaguePoints', 0)
        wins = solo_rank.get('wins', 0)
        losses = solo_rank.get('losses', 0)
        total_games = wins + losses
        wr = int((wins / total_games) * 100) if total_games > 0 else 0

        solo_text = f"**{tier} {rank}** ({lp} LP)\n{wins}W {losses}L • **{wr}% WR**"
        embed.add_field(name="Solo/Duo", value=solo_text, inline=True)
    else:
        embed.add_field(name="Solo/Duo", value="Non classé", inline=True)

    # Flex Rank
    if flex_rank:
        tier = flex_rank.get('tier', 'UNRANKED')
        rank = flex_rank.get('rank', '')
        lp = flex_rank.get('leaguePoints', 0)
        wins = flex_rank.get('wins', 0)
        losses = flex_rank.get('losses', 0)
        total_games = wins + losses
        wr = int((wins / total_games) * 100) if total_games > 0 else 0

        flex_text = f"**{tier} {rank}** ({lp} LP)\n{wins}W {losses}L • **{wr}% WR**"
        embed.add_field(name="Flex", value=flex_text, inline=True)
    else:
        embed.add_field(name="Flex", value="Non classé", inline=True)

    # Maîtrises
    if masteries:
        mastery_text = ""
        for mastery in masteries[:3]:
            champ_id = mastery.get('championId')
            champ_name = champion_names.get(champ_id, f"Champion {champ_id}")
            points = mastery.get('championPoints', 0)
            level = mastery.get('championLevel', 0)
            mastery_text += f"**{champ_name}** - Niveau {level} ({points:,} pts)\n"

        embed.add_field(name="Top Maitrises", value=mastery_text, inline=False)

    return embed


# ==================== Clash Scout Embeds ====================

ROLE_EMOJIS = {
    'TOP': ':shield:',
    'JUNGLE': ':evergreen_tree:',
    'MIDDLE': ':zap:',
    'BOTTOM': ':bow_and_arrow:',
    'UTILITY': ':heart:',
    'UNKNOWN': ':question:'
}

ROLE_NAMES = {
    'TOP': 'Top',
    'JUNGLE': 'Jungle',
    'MIDDLE': 'Mid',
    'BOTTOM': 'ADC',
    'UTILITY': 'Support',
    'UNKNOWN': '?'
}


def format_rank_display(rank) -> str:
    """Formate le rang pour affichage"""
    if not rank or not rank.tier:
        return "Unranked"

    tier_short = {
        'IRON': 'I', 'BRONZE': 'B', 'SILVER': 'S', 'GOLD': 'G',
        'PLATINUM': 'P', 'EMERALD': 'E', 'DIAMOND': 'D',
        'MASTER': 'M', 'GRANDMASTER': 'GM', 'CHALLENGER': 'C'
    }.get(rank.tier.upper(), rank.tier[0])

    if rank.tier.upper() in ('MASTER', 'GRANDMASTER', 'CHALLENGER'):
        return f"{tier_short} {rank.lp}LP"

    rank_num = {'IV': '4', 'III': '3', 'II': '2', 'I': '1'}.get(rank.rank, rank.rank)
    return f"{tier_short}{rank_num} {rank.lp}LP"


def create_clash_players_embed(players: List['PlayerData']) -> discord.Embed:
    """Cree un embed montrant les joueurs de l'equipe adverse"""
    embed = discord.Embed(
        title=":crossed_swords: Equipe Adverse",
        color=discord.Color.red(),
        description="Joueurs detectes dans l'equipe Clash"
    )

    for player in players:
        if player.is_private or player.error:
            embed.add_field(
                name=f":lock: {player.game_name}",
                value="Profil prive ou erreur",
                inline=False
            )
            continue

        role_emoji = ROLE_EMOJIS.get(player.main_role, ':question:')
        role_name = ROLE_NAMES.get(player.main_role, '?')
        rank_str = format_rank_display(player.rank)

        # Top 3 champions — priorise season_games si disponible
        top_champs = sorted(
            [c for c in player.top_champions if c.season_games > 0 or c.games_played > 0],
            key=lambda c: c.season_games if c.season_games > 0 else c.games_played,
            reverse=True
        )[:3]

        champ_text = ""
        for c in top_champs:
            if c.season_games > 0:
                champ_text += f"`{c.champion_name}` ({c.season_games}g, {c.season_winrate:.0f}% WR)\n"
            else:
                champ_text += f"`{c.champion_name}` ({c.games_played}g, {c.winrate:.0f}%)\n"

        if not champ_text:
            # Fallback to mastery champions
            top_mastery = sorted(
                player.top_champions,
                key=lambda c: c.mastery_points,
                reverse=True
            )[:3]
            for c in top_mastery:
                pts = c.mastery_points
                if pts >= 1000000:
                    pts_str = f"{pts/1000000:.1f}M"
                elif pts >= 1000:
                    pts_str = f"{pts/1000:.0f}k"
                else:
                    pts_str = str(pts)
                champ_text += f"`{c.champion_name}` ({pts_str} pts)\n"

        if not champ_text:
            champ_text = "Aucun champion"

        # Season WR (Solo + Flex)
        season_parts = []
        if player.rank.wins + player.rank.losses > 0:
            season_parts.append(f"Solo {player.rank.winrate:.0f}%")
        if player.flex_rank.wins + player.flex_rank.losses > 0:
            season_parts.append(f"Flex {player.flex_rank.winrate:.0f}%")
        season_wr = " | ".join(season_parts) if season_parts else "Pas de données"

        # Winrate et KDA recents
        stats_line = f"WR: **{player.recent_winrate:.0f}%** | KDA: **{player.recent_kda:.2f}**"

        value = f"{role_emoji} **{role_name}** | {rank_str}\nSeason: **{season_wr}**\n{stats_line}\n{champ_text}"

        # op.gg link
        opgg_name = player.game_name.replace(' ', '%20')
        opgg_link = f"[op.gg](https://www.op.gg/summoners/euw/{opgg_name}-{player.tag_line})"
        value += opgg_link

        embed.add_field(
            name=f"{player.game_name}#{player.tag_line}",
            value=value,
            inline=True
        )

    return embed


def create_optimal_bans_embed(bans: List['DangerScore']) -> discord.Embed:
    """Cree un embed montrant les bans optimaux recommandes"""
    embed = discord.Embed(
        title=":no_entry_sign: Bans Recommandes",
        color=discord.Color.gold(),
        description="Champions a ban en priorite"
    )

    if not bans:
        embed.description = "Aucun ban recommande (pas assez de donnees)"
        return embed

    for i, ban in enumerate(bans[:5], 1):
        # Medal emoji for top 3
        medal = {1: ':first_place:', 2: ':second_place:', 3: ':third_place:'}.get(i, f'**{i}.**')

        reasons_text = " + ".join(ban.reasons) if ban.reasons else "Stats generales"

        # Format mastery/games
        if ban.mastery_points >= 1000000:
            mastery_str = f"{ban.mastery_points/1000000:.1f}M pts"
        elif ban.mastery_points >= 1000:
            mastery_str = f"{ban.mastery_points/1000:.0f}k pts"
        else:
            mastery_str = f"{ban.mastery_points} pts"

        games_str = f"{ban.games_played}g" if ban.games_played > 0 else ""
        wr_str = f"{ban.winrate:.0f}%" if ban.games_played >= 3 else ""

        stats = " | ".join(filter(None, [mastery_str, games_str, wr_str]))

        value = (
            f"**Score: {ban.total_score}** pts\n"
            f"Joue par: `{ban.player_name}`\n"
            f"Raisons: {reasons_text}\n"
            f"{stats}"
        )

        embed.add_field(
            name=f"{medal} {ban.champion_name}",
            value=value,
            inline=True
        )

    return embed


def create_alternative_bans_embed(bans: List['DangerScore']) -> discord.Embed:
    """Cree un embed montrant les bans alternatifs"""
    embed = discord.Embed(
        title=":warning: Bans Alternatifs",
        color=discord.Color.orange(),
        description="Champions a considerer si les bans principaux ne sont pas disponibles"
    )

    if not bans:
        embed.description = "Aucun ban alternatif"
        return embed

    for i, ban in enumerate(bans[:5], 1):
        reasons_text = " + ".join(ban.reasons) if ban.reasons else "Stats"

        value = (
            f"Score: **{ban.total_score}** | `{ban.player_name}`\n"
            f"{reasons_text}"
        )

        embed.add_field(
            name=f"{i}. {ban.champion_name}",
            value=value,
            inline=True
        )

    return embed


def create_team_analysis_embed(
    composition: str,
    avg_elo: int,
    player_count: int,
    our_team_name: str = None
) -> discord.Embed:
    """Cree un embed montrant l'analyse globale de l'equipe"""
    embed = discord.Embed(
        title=":bar_chart: Analyse de l'Equipe",
        color=discord.Color.blue()
    )

    # Convertir l'elo moyen en rang
    def elo_to_rank(elo: int) -> str:
        tiers = [
            (3600, 'Challenger'), (3200, 'Grandmaster'), (2800, 'Master'),
            (2400, 'Diamond'), (2000, 'Emerald'), (1600, 'Platinum'),
            (1200, 'Gold'), (800, 'Silver'), (400, 'Bronze'), (0, 'Iron')
        ]
        for threshold, name in tiers:
            if elo >= threshold:
                return name
        return 'Iron'

    avg_rank = elo_to_rank(avg_elo)

    embed.add_field(
        name="Joueurs scouts",
        value=f"**{player_count}/5** detectes",
        inline=True
    )

    embed.add_field(
        name="Elo Moyen",
        value=f"**{avg_rank}** (~{avg_elo} LP total)",
        inline=True
    )

    embed.add_field(
        name="Composition",
        value=composition,
        inline=True
    )

    if our_team_name:
        embed.set_footer(text=f"Scouting pour: {our_team_name}")

    return embed


def create_clash_team_embed(team_data: Dict[str, Any]) -> discord.Embed:
    """Cree un embed pour afficher une equipe Clash locale"""
    embed = discord.Embed(
        title=f":shield: Equipe: {team_data['team_name']}",
        color=discord.Color.green()
    )

    members = team_data.get('members', [])
    member_text = ""

    for i, member in enumerate(members, 1):
        game_name = member.get('game_name')
        tag_line = member.get('tag_line')
        discord_id = member.get('discord_id')

        if game_name and tag_line:
            member_text += f"{i}. **{game_name}#{tag_line}** (<@{discord_id}>)\n"
        else:
            member_text += f"{i}. <@{discord_id}> (compte non lie)\n"

    if not member_text:
        member_text = "Aucun membre"

    embed.add_field(name="Membres", value=member_text, inline=False)
    embed.set_footer(text=f"Creee par: {team_data.get('created_by_discord_id', 'Inconnu')}")

    return embed
