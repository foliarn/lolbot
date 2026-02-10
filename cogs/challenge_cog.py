"""
Cog pour les commandes de challenges hebdomadaires
"""
import traceback
import discord
from discord import app_commands
from discord.ext import commands
import config


class ChallengeCog(commands.Cog):
    """Commandes pour les challenges hebdomadaires"""

    def __init__(self, bot, challenges_module):
        self.bot = bot
        self.challenges = challenges_module

    # Group: /challenges
    challenges_group = app_commands.Group(name="challenges", description="Commandes challenges hebdomadaires")

    @challenges_group.command(name="view", description="Voir tes challenges de la semaine")
    @app_commands.describe(user="Utilisateur cible (optionnel)")
    async def view(self, interaction: discord.Interaction, user: discord.Member = None):
        """Affiche les challenges actifs"""
        await interaction.response.defer()

        try:
            target = user or interaction.user
            discord_id = str(target.id)
            embed = await self.challenges.generate_challenges_embed(discord_id)

            if user and user != interaction.user:
                embed.title = f"Challenges de {user.display_name}"

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[Challenges] Erreur: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"Erreur: {e}", ephemeral=True)

    @challenges_group.command(name="leaderboard", description="Classement des points challenges")
    async def leaderboard(self, interaction: discord.Interaction):
        """Affiche le leaderboard des points"""
        await interaction.response.defer()

        try:
            embed = await self.challenges.generate_leaderboard_embed()
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[Leaderboard] Erreur: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"Erreur: {e}", ephemeral=True)

    @challenges_group.command(name="resetscore", description="[Admin] Reset tous les scores a 0")
    async def resetscore(self, interaction: discord.Interaction):
        """Reset tous les scores de challenges a 0 (debug)"""
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(
                "Cette action necessite les permissions administrateur.",
                ephemeral=True
            )
            return

        try:
            await self.bot.db_manager.reset_all_challenge_points(config.CURRENT_SEASON_SPLIT)
            await interaction.followup.send(
                f"Tous les scores ont ete remis a 0 pour {config.CURRENT_SEASON_SPLIT}.",
                ephemeral=True
            )

        except Exception as e:
            print(f"[ResetScore] Erreur: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"Erreur: {e}", ephemeral=True)


async def setup(bot):
    """Charge le cog"""
    cog = ChallengeCog(bot, bot.challenges_module)
    await bot.add_cog(cog)
