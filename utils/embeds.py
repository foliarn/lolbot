"""
Générateurs d'embeds Discord
"""
import discord
from typing import Dict, Any, List


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
