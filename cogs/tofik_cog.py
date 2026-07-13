import discord
from discord import app_commands
from discord.ext import commands
import os

class TofikCog(commands.Cog):
    """Cog for Tofik's oversight and interaction"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tofik", description="Demander l'avis de Tofik sur la situation")
    async def tofik_status(self, interaction: discord.Interaction):
        """Donne un aperçu de l'état du serveur et de l'humeur de Tofik"""
        await interaction.response.defer()

        uptime = os.popen("uptime -p").read().strip()

        users = await self.bot.db_manager.get_all_primary_users()

        playing_users = []
        for user in users:
            try:
                live_game = await self.bot.riot_api.get_active_game(user['riot_puuid'])
                if live_game:
                    playing_users.append(user['game_name'])
            except Exception:
                continue

        reputations = None
        try:
            reputations = await self.bot.db_manager.get_all_reputations()
        except Exception:
            pass

        if hasattr(self.bot, 'commentary') and self.bot.commentary:
            response = await self.bot.commentary.tofik_status(
                players_in_game=playing_users,
                total_players=len(users),
                uptime=uptime,
                reputations=reputations,
            )
        else:
            players_str = f" ({', '.join(playing_users)})" if playing_users else ""
            response = (
                f"Le serveur est stable (Uptime : `{uptime}`).\n"
                f"Je surveille `{len(users)}` joueurs, dont `{len(playing_users)}` sur la Faille{players_str}."
            )

        await interaction.followup.send(response)

async def setup(bot):
    await bot.add_cog(TofikCog(bot))
