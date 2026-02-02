"""
Cog pour les commandes utilitaires (stats, livegame, review, clash)
"""
import discord
from discord import app_commands
from discord.ext import commands


class UtilityCog(commands.Cog):
    """Commandes utilitaires du bot"""

    def __init__(self, bot, stats_module, livegame_module, review_module, clash_scout):
        self.bot = bot
        self.stats = stats_module
        self.livegame = livegame_module
        self.review = review_module
        self.clash = clash_scout

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

    @app_commands.command(name="livegame", description="Affiche la partie en cours d'un joueur")
    @app_commands.describe(
        riot_id="RiotID du joueur (optionnel si compte lié)",
        tag="Tag du joueur",
        alias="Alias du smurf (si compte lié)"
    )
    async def livegame(
        self,
        interaction: discord.Interaction,
        riot_id: str = None,
        tag: str = None,
        alias: str = None
    ):
        """Affiche la partie en cours"""
        await interaction.response.defer()

        discord_id = str(interaction.user.id) if not riot_id else None

        embed, error = await self.livegame.get_live_game(
            discord_id=discord_id,
            riot_id=riot_id,
            tag=tag,
            alias=alias
        )

        if error:
            await interaction.followup.send(error, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="review", description="Analyse ta dernière partie")
    @app_commands.describe(alias="Alias du smurf (optionnel)")
    async def review(
        self,
        interaction: discord.Interaction,
        alias: str = None
    ):
        """Analyse la dernière partie"""
        await interaction.response.defer()

        discord_id = str(interaction.user.id)

        embed, error = await self.review.review_last_game(
            discord_id=discord_id,
            alias=alias
        )

        if error:
            await interaction.followup.send(error, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="clash", description="Scout une équipe Clash et recommande des bans")
    @app_commands.describe(
        riot_id="RiotID d'un membre de l'équipe adverse (optionnel si compte lié)",
        tag="Tag du joueur",
        alias="Alias du smurf (si compte lié)"
    )
    async def clash(
        self,
        interaction: discord.Interaction,
        riot_id: str = None,
        tag: str = None,
        alias: str = None
    ):
        """Scout une équipe Clash"""
        await interaction.response.defer()

        discord_id = str(interaction.user.id) if not riot_id else None

        embed, error = await self.clash.scout_team(
            discord_id=discord_id,
            riot_id=riot_id,
            tag=tag,
            alias=alias
        )

        if error:
            await interaction.followup.send(error, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot):
    """Charge le cog"""
    cog = UtilityCog(
        bot,
        bot.stats_module,
        bot.livegame_module,
        bot.review_module,
        bot.clash_scout
    )
    await bot.add_cog(cog)
