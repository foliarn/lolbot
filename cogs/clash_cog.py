"""
Cog pour les commandes Clash (team management et scouting)
"""
import traceback
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from utils.embeds import (
    create_clash_players_embed,
    create_optimal_bans_embed,
    create_alternative_bans_embed,
    create_team_analysis_embed,
    create_clash_team_embed
)


class ClashCog(commands.Cog):
    """Commandes pour le Clash scouting"""

    def __init__(self, bot, clash_scout, db_manager):
        self.bot = bot
        self.scout = clash_scout
        self.db = db_manager

    # Group: /clash
    clash_group = app_commands.Group(name="clash", description="Commandes Clash")

    # Subgroup: /clash team
    team_group = app_commands.Group(
        name="team",
        description="Gestion des equipes Clash",
        parent=clash_group
    )

    @team_group.command(name="create", description="Cree une equipe Clash avec 5 joueurs")
    @app_commands.describe(
        team_name="Nom de l'equipe",
        p1="Joueur 1 (Top)",
        p2="Joueur 2 (Jungle)",
        p3="Joueur 3 (Mid)",
        p4="Joueur 4 (ADC)",
        p5="Joueur 5 (Support)"
    )
    async def team_create(
        self,
        interaction: discord.Interaction,
        team_name: str,
        p1: discord.Member,
        p2: discord.Member,
        p3: discord.Member,
        p4: discord.Member,
        p5: discord.Member
    ):
        """Cree une equipe Clash"""
        await interaction.response.defer(ephemeral=True)

        creator_id = str(interaction.user.id)
        member_ids = [str(p.id) for p in [p1, p2, p3, p4, p5]]

        # Verifier que tous les membres ont un compte lie
        missing_links = []
        for member in [p1, p2, p3, p4, p5]:
            user = await self.db.get_user(str(member.id))
            if not user:
                missing_links.append(member.display_name)

        if missing_links:
            await interaction.followup.send(
                f":warning: Les joueurs suivants n'ont pas de compte Riot lie: "
                f"**{', '.join(missing_links)}**\n"
                f"Ils doivent utiliser `/link` avant de pouvoir etre ajoutes a une equipe.",
                ephemeral=True
            )
            return

        # Creer l'equipe
        team_id = await self.db.create_clash_team(team_name, creator_id, member_ids)

        if not team_id:
            await interaction.followup.send(
                f":x: Une equipe avec le nom **{team_name}** existe deja.",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            f":white_check_mark: Equipe **{team_name}** creee avec succes!\n"
            f"Membres: {p1.mention}, {p2.mention}, {p3.mention}, {p4.mention}, {p5.mention}",
            ephemeral=True
        )

    @team_group.command(name="list", description="Affiche tes equipes Clash")
    async def team_list(self, interaction: discord.Interaction):
        """Liste les equipes Clash de l'utilisateur"""
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)
        teams = await self.db.get_user_clash_teams(discord_id)

        if not teams:
            await interaction.followup.send(
                ":information_source: Tu n'as aucune equipe Clash.\n"
                "Utilise `/clash team create` pour en creer une.",
                ephemeral=True
            )
            return

        embeds = []
        for team in teams:
            embed = create_clash_team_embed(team)
            if team.get('role') == 'creator':
                embed.color = discord.Color.green()
                embed.set_footer(text="Tu es le createur de cette equipe")
            else:
                embed.color = discord.Color.blue()
                embed.set_footer(text="Tu es membre de cette equipe")
            embeds.append(embed)

        await interaction.followup.send(embeds=embeds[:10], ephemeral=True)

    @team_group.command(name="delete", description="Supprime une equipe Clash")
    @app_commands.describe(team_name="Nom de l'equipe a supprimer")
    async def team_delete(
        self,
        interaction: discord.Interaction,
        team_name: str
    ):
        """Supprime une equipe Clash"""
        await interaction.response.defer(ephemeral=True)

        creator_id = str(interaction.user.id)

        # Verifier que l'equipe existe et appartient a l'utilisateur
        team = await self.db.get_clash_team(team_name, creator_id)
        if not team:
            await interaction.followup.send(
                f":x: Equipe **{team_name}** introuvable ou tu n'es pas le createur.",
                ephemeral=True
            )
            return

        # Supprimer
        success = await self.db.delete_clash_team(team['id'])

        if success:
            await interaction.followup.send(
                f":white_check_mark: Equipe **{team_name}** supprimee.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f":x: Erreur lors de la suppression de l'equipe.",
                ephemeral=True
            )

    @clash_group.command(name="scout", description="Scout une equipe adverse en Clash")
    @app_commands.describe(
        riot_id="RiotID d'un joueur de l'equipe adverse (ex: Faker)",
        tag="Tag du joueur (ex: KR1)",
        our_team="Nom de ton equipe (optionnel, pour comparaison)"
    )
    async def scout(
        self,
        interaction: discord.Interaction,
        riot_id: str,
        tag: str,
        our_team: Optional[str] = None
    ):
        """Scout une equipe Clash adverse"""
        await interaction.response.defer()

        # Message de chargement
        loading_msg = await interaction.followup.send(
            ":hourglass: Scouting en cours... Cela peut prendre jusqu'a 30 secondes.",
            wait=True
        )

        try:
            # Scout l'equipe adverse
            result = await self.scout.scout_enemy_team(riot_id, tag)

            # Verifier les erreurs
            if result.team_composition == "error":
                await loading_msg.edit(
                    content=f":x: Erreur: Impossible de trouver le joueur **{riot_id}#{tag}**"
                )
                return

            if result.team_composition == "no_clash":
                await loading_msg.edit(
                    content=f":x: **{riot_id}#{tag}** n'est pas inscrit dans un Clash actuellement."
                )
                return

            if result.team_composition == "no_team":
                await loading_msg.edit(
                    content=f":x: Impossible de trouver l'equipe Clash de **{riot_id}#{tag}**"
                )
                return

            if not result.players:
                await loading_msg.edit(
                    content=":x: Aucun joueur trouve dans l'equipe adverse."
                )
                return

            # Creer les embeds
            embeds = []

            # 1. Analyse globale
            analysis_embed = create_team_analysis_embed(
                composition=result.team_composition,
                avg_elo=result.average_elo,
                player_count=len(result.players),
                our_team_name=our_team
            )
            embeds.append(analysis_embed)

            # 2. Joueurs
            players_embed = create_clash_players_embed(result.players)
            embeds.append(players_embed)

            # 3. Bans optimaux
            if result.optimal_bans:
                bans_embed = create_optimal_bans_embed(result.optimal_bans)
                embeds.append(bans_embed)

            # 4. Bans alternatifs (si disponibles)
            if result.alternative_bans:
                alt_bans_embed = create_alternative_bans_embed(result.alternative_bans)
                embeds.append(alt_bans_embed)

            # Comparer avec notre equipe si specifiee
            if our_team:
                creator_id = str(interaction.user.id)
                our_team_data = await self.db.get_clash_team(our_team, creator_id)

                if our_team_data:
                    members_data = await self.db.get_clash_team_members_data(our_team_data['id'])
                    if members_data:
                        our_puuids = [m['riot_puuid'] for m in members_data if m.get('riot_puuid')]
                        our_result = await self.scout.scout_team_by_players(our_puuids)

                        if our_result.players:
                            comparison = self.scout.calculate_team_comparison(
                                our_result.players,
                                result.players
                            )

                            comparison_text = ""
                            if comparison < 0.8:
                                comparison_text = ":green_circle: Avantage pour vous!"
                            elif comparison > 1.2:
                                comparison_text = ":red_circle: Avantage pour l'adversaire"
                            else:
                                comparison_text = ":yellow_circle: Match equilibre"

                            analysis_embed.add_field(
                                name="Comparaison",
                                value=f"{comparison_text}\nRatio: {comparison:.2f}",
                                inline=True
                            )

            # Supprimer le message de chargement et envoyer les embeds
            await loading_msg.edit(content=None, embeds=embeds)

        except Exception as e:
            print(f"[ClashScout] Erreur: {e}")
            traceback.print_exc()
            await loading_msg.edit(
                content=f":x: Erreur lors du scouting: {str(e)}"
            )

    @clash_group.command(name="analyze", description="Analyse une liste de joueurs (sans Clash)")
    @app_commands.describe(
        players="Liste de joueurs separes par des virgules (ex: Player1#TAG1, Player2#TAG2)"
    )
    async def analyze(
        self,
        interaction: discord.Interaction,
        players: str
    ):
        """Analyse une liste de joueurs manuellement"""
        await interaction.response.defer()

        # Parser les joueurs
        player_list = [p.strip() for p in players.split(',')]
        if len(player_list) > 5:
            await interaction.followup.send(
                ":x: Maximum 5 joueurs a analyser.",
                ephemeral=True
            )
            return

        loading_msg = await interaction.followup.send(
            f":hourglass: Analyse de {len(player_list)} joueur(s)...",
            wait=True
        )

        try:
            # Recuperer les PUUIDs
            puuids = []
            for player_str in player_list:
                if '#' not in player_str:
                    await loading_msg.edit(
                        content=f":x: Format invalide: **{player_str}**. Utilise le format `RiotID#TAG`"
                    )
                    return

                parts = player_str.rsplit('#', 1)
                riot_id = parts[0].strip()
                tag = parts[1].strip()

                account = await self.scout.api.get_account_by_riot_id(riot_id, tag)
                if not account:
                    await loading_msg.edit(
                        content=f":x: Joueur introuvable: **{riot_id}#{tag}**"
                    )
                    return

                puuids.append(account['puuid'])

            # Scout les joueurs
            result = await self.scout.scout_team_by_players(puuids)

            if not result.players:
                await loading_msg.edit(
                    content=":x: Aucune donnee recuperee pour ces joueurs."
                )
                return

            # Creer les embeds
            embeds = []

            # Analyse
            analysis_embed = create_team_analysis_embed(
                composition=f"{len(result.players)} joueurs",
                avg_elo=result.average_elo,
                player_count=len(result.players)
            )
            embeds.append(analysis_embed)

            # Joueurs
            players_embed = create_clash_players_embed(result.players)
            embeds.append(players_embed)

            # Bans
            if result.optimal_bans:
                bans_embed = create_optimal_bans_embed(result.optimal_bans)
                embeds.append(bans_embed)

            await loading_msg.edit(content=None, embeds=embeds)

        except Exception as e:
            print(f"[ClashAnalyze] Erreur: {e}")
            traceback.print_exc()
            await loading_msg.edit(
                content=f":x: Erreur lors de l'analyse: {str(e)}"
            )


async def setup(bot):
    """Charge le cog"""
    from modules.clash_scout import ClashScoutModule

    clash_scout = ClashScoutModule(bot.riot_api, bot.data_dragon, bot.db_manager)
    cog = ClashCog(bot, clash_scout, bot.db_manager)
    await bot.add_cog(cog)
