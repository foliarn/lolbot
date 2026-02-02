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

    # Rangs
    rank_text = ""
    for rank_data in ranks:
        queue = rank_data.get('queueType', '')
        tier = rank_data.get('tier', 'UNRANKED')
        rank = rank_data.get('rank', '')
        lp = rank_data.get('leaguePoints', 0)
        wins = rank_data.get('wins', 0)
        losses = rank_data.get('losses', 0)
        wr = int((wins / (wins + losses)) * 100) if wins + losses > 0 else 0

        queue_name = "Solo/Duo" if "SOLO" in queue else "Flex"
        rank_text += f"**{queue_name}:** {tier} {rank} ({lp} LP) - {wins}W {losses}L ({wr}%)\n"

    if not rank_text:
        rank_text = "Non classé"

    embed.add_field(name="Rang", value=rank_text, inline=False)

    # Maîtrises
    if masteries:
        mastery_text = ""
        for mastery in masteries[:3]:
            champ_id = mastery.get('championId')
            champ_name = champion_names.get(champ_id, f"Champion {champ_id}")
            points = mastery.get('championPoints', 0)
            level = mastery.get('championLevel', 0)
            mastery_text += f"**{champ_name}** - Niveau {level} ({points:,} pts)\n"

        embed.add_field(name="Top Maîtrises", value=mastery_text, inline=False)

    return embed


def create_patch_embed(champion_name: str, changes: Dict[str, Any], patch_url: str) -> discord.Embed:
    """Crée un embed pour les notifications de patch"""
    embed = discord.Embed(
        title=f"Patch Notes - {champion_name}",
        color=discord.Color.gold(),
        url=patch_url
    )

    # Stats de base
    if 'stats' in changes:
        stats_text = ""
        for stat_name, change in changes['stats'].items():
            old = change['old']
            new = change['new']
            arrow = "↑" if new > old else "↓"
            stats_text += f"**{stat_name}:** {old} → {new} {arrow}\n"

        embed.add_field(name="Stats de base", value=stats_text, inline=False)

    # Sorts
    if 'spells' in changes:
        for spell_name, spell_changes in changes['spells'].items():
            spell_text = ""

            if 'cooldown' in spell_changes:
                old_cd = spell_changes['cooldown']['old']
                new_cd = spell_changes['cooldown']['new']
                spell_text += f"**Cooldown:** {old_cd} → {new_cd}\n"

            if 'cost' in spell_changes:
                old_cost = spell_changes['cost']['old']
                new_cost = spell_changes['cost']['new']
                spell_text += f"**Coût:** {old_cost} → {new_cost}\n"

            if 'description' in spell_changes:
                spell_text += "**Description modifiée** (voir patch notes)\n"

            if spell_text:
                embed.add_field(name=f"🔸 {spell_name}", value=spell_text, inline=False)

    embed.add_field(
        name="Patch Notes complet",
        value=f"[Lire sur le site officiel]({patch_url})",
        inline=False
    )

    return embed


def create_patch_summary_embed(buffs: List[str], nerfs: List[str], patch_url: str) -> discord.Embed:
    """Crée un embed récapitulatif pour /subscribe all"""
    embed = discord.Embed(
        title="Récapitulatif du Patch",
        color=discord.Color.purple(),
        url=patch_url
    )

    if buffs:
        embed.add_field(
            name="🔼 Buffs",
            value=", ".join(buffs),
            inline=False
        )

    if nerfs:
        embed.add_field(
            name="🔽 Nerfs",
            value=", ".join(nerfs),
            inline=False
        )

    embed.add_field(
        name="Patch Notes complet",
        value=f"[Lire sur le site officiel]({patch_url})",
        inline=False
    )

    return embed


def create_clash_embed(
    team_name: str,
    bans: List[Dict[str, Any]],
    player_analysis: List[Dict[str, Any]]
) -> discord.Embed:
    """Crée un embed pour le Clash Scout"""
    embed = discord.Embed(
        title=f"Clash Scout - {team_name}",
        description="Analyse prédictive de l'équipe adverse",
        color=discord.Color.red()
    )

    # Top 3 bans recommandés
    if bans:
        bans_text = ""
        for i, ban in enumerate(bans[:3], 1):
            champion = ban['champion']
            score = ban['score']
            reason = ban['reason']
            bans_text += f"**{i}. {champion}** ({score} pts) - {reason}\n"

        embed.add_field(name="🚫 Bans Recommandés", value=bans_text, inline=False)

    # Analyse par joueur/rôle
    for player in player_analysis:
        role = player.get('role', 'Unknown')
        player_name = player.get('name', 'Unknown')
        champions = player.get('champions', [])
        profile = player.get('profile', '')

        player_text = ""
        if profile:
            player_text += f"*{profile}*\n"

        if champions:
            champ_list = ", ".join([f"{c['name']} ({c['games']})" for c in champions[:3]])
            player_text += f"Champions: {champ_list}"

        if player_text:
            embed.add_field(
                name=f"{role} - {player_name}",
                value=player_text,
                inline=False
            )

    return embed


def create_livegame_embed(
    game_mode: str,
    game_length: int,
    teams: Dict[str, List[Dict[str, Any]]]
) -> discord.Embed:
    """Crée un embed pour la commande /livegame"""
    embed = discord.Embed(
        title=f"Partie en cours - {game_mode}",
        description=f"Durée: {game_length // 60}m {game_length % 60}s",
        color=discord.Color.green()
    )

    for team_name, players in teams.items():
        team_text = ""
        for player in players:
            name = player['name']
            champion = player['champion']
            rank = player.get('rank', 'Unranked')
            wr = player.get('winrate', 'N/A')
            team_text += f"**{champion}** - {name} ({rank}) - {wr}% WR\n"

        embed.add_field(name=team_name, value=team_text, inline=True)

    return embed


def create_review_embed(
    game_name: str,
    champion: str,
    result: str,
    kda: str,
    stats: Dict[str, Any]
) -> discord.Embed:
    """Crée un embed pour la commande /review"""
    color = discord.Color.green() if result == "Victory" else discord.Color.red()

    embed = discord.Embed(
        title=f"Review - {game_name}",
        description=f"**{champion}** - {result}",
        color=color
    )

    embed.add_field(name="KDA", value=kda, inline=True)
    embed.add_field(name="CS", value=f"{stats.get('cs', 0)} ({stats.get('cs_per_min', 0)}/min)", inline=True)
    embed.add_field(name="Vision Score", value=str(stats.get('vision_score', 0)), inline=True)
    embed.add_field(name="Dégâts", value=f"{stats.get('damage', 0):,}", inline=True)
    embed.add_field(name="Or", value=f"{stats.get('gold', 0):,}", inline=True)
    embed.add_field(name="Durée", value=stats.get('duration', 'N/A'), inline=True)

    return embed
