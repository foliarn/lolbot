"""
Cog pour les commandes utilitaires (stats, leaderboard)
"""
import discord
from discord import app_commands
from discord.ext import commands


class UtilityCog(commands.Cog):
    """Commandes utilitaires du bot"""

    def __init__(self, bot, stats_module, leaderboard_module):
        self.bot = bot
        self.stats = stats_module
        self.leaderboard = leaderboard_module

    @app_commands.command(name="stats", description="Affiche les stats d'un joueur")
    @app_commands.describe(
        riot_id="RiotID du joueur (optionnel si compte lié)",
        tag="Tag du joueur",
        alias="Alias du smurf (si compte lié)"
    )
    async def stats(
        self,
        interaction: discord.Interaction,
        riot_id: str = None,
        tag: str = None,
        alias: str = None
    ):
        """Affiche les stats d'un joueur"""
        await interaction.response.defer()

        discord_id = str(interaction.user.id) if not riot_id else None
        print(f"[Stats] Discord user ID: {discord_id}, riot_id: {riot_id}, tag: {tag}, alias: {alias}")

        embed, error = await self.stats.get_stats(
            discord_id=discord_id,
            riot_id=riot_id,
            tag=tag,
            alias=alias
        )

        if error:
            await interaction.followup.send(error, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="Affiche le leaderboard")
    @app_commands.describe(
        queue="Type de queue (solo ou flex)"
    )
    @app_commands.choices(queue=[
        app_commands.Choice(name="Solo/Duo", value="solo"),
        app_commands.Choice(name="Flex", value="flex"),
        app_commands.Choice(name="Les deux", value="both")
    ])
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        queue: str = "both"
    ):
        """Affiche le leaderboard"""
        await interaction.response.defer()

        try:
            if queue == "both":
                embeds, messages = await self.leaderboard.generate_full_leaderboard()
                for embed in embeds:
                    await interaction.followup.send(embed=embed)
                if messages:
                    await interaction.followup.send("\n".join(messages))
            else:
                queue_type = "RANKED_SOLO_5x5" if queue == "solo" else "RANKED_FLEX_SR"
                players = await self.leaderboard.get_leaderboard_data(queue_type)
                embed, messages = self.leaderboard.create_leaderboard_embed(queue_type, players)
                await interaction.followup.send(embed=embed)
                if messages:
                    await interaction.followup.send("\n".join(messages))

        except Exception as e:
            print(f"[Leaderboard] Erreur: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"Erreur lors de la generation du leaderboard: {e}", ephemeral=True)

    @app_commands.command(name="update_ranks", description="Force la mise a jour des rangs (admin)")
    async def update_ranks(self, interaction: discord.Interaction):
        """Force la mise a jour des rangs"""
        await interaction.response.defer(ephemeral=True)

        try:
            count = await self.leaderboard.update_all_ranks()
            await interaction.followup.send(f"Mise a jour terminee: {count} rangs enregistres.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Erreur: {e}", ephemeral=True)


async def setup(bot):
    """Charge le cog"""
    cog = UtilityCog(bot, bot.stats_module, bot.leaderboard_module)
    await bot.add_cog(cog)
