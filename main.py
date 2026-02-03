"""
Point d'entree principal du bot Discord LoL
"""
import argparse
import discord
from discord.ext import commands, tasks
import asyncio
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from database import DatabaseManager
from riot_api import RiotAPIClient, RiotEndpoints, DataDragon
from modules.stats import StatsModule
from modules.leaderboard import LeaderboardModule
import config


# Charger les variables d'environnement
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
RIOT_API_KEY = os.getenv('RIOT_API_KEY')

PARIS_TZ = ZoneInfo("Europe/Paris")


class LoLBot(commands.Bot):
    """Bot Discord principal pour League of Legends"""

    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        # Initialiser les composants
        self.db_manager = DatabaseManager()
        self.data_dragon = DataDragon()

        # Client API Riot
        self.riot_client = RiotAPIClient(RIOT_API_KEY, self.db_manager)
        self.riot_api = RiotEndpoints(self.riot_client)

        # Modules
        self.stats_module = StatsModule(self.riot_api, self.data_dragon, self.db_manager)
        self.leaderboard_module = LeaderboardModule(self.riot_api, self.data_dragon, self.db_manager)

    async def setup_hook(self):
        """Configuration initiale du bot"""
        print("[Setup] Initialisation de la base de donnees...")
        await self.db_manager.initialize()

        print("[Setup] Initialisation du client API Riot...")
        await self.riot_client.start()

        print("[Setup] Chargement des donnees Data Dragon...")
        await self.data_dragon.load_champions()

        print("[Setup] Chargement des cogs...")
        await self.load_extension('cogs.account_cog')
        await self.load_extension('cogs.utility_cog')

        print("[Setup] Synchronisation des commandes slash...")
        # Sync global
        synced = await self.tree.sync()
        print(f"[Setup] {len(synced)} commandes globales: {[c.name for c in synced]}")

        # Demarrer les taches planifiees
        self.daily_leaderboard.start()
        self.hourly_rank_update.start()

        print("[Setup] Bot pret!")

    async def on_ready(self):
        """Appele quand le bot est connecte"""
        print(f"[Bot] Connecte en tant que {self.user} (ID: {self.user.id})")
        print(f"[Bot] Serveurs: {len(self.guilds)}")

        # Sync commands to each guild for instant registration
        for guild in self.guilds:
            print(f"[Bot] Sync guild {guild.name} ({guild.id})...")
            try:
                synced = await self.tree.sync(guild=guild)
                print(f"[Bot] {len(synced)} commandes guild: {[c.name for c in synced]}")
            except Exception as e:
                print(f"[Bot] Erreur sync guild: {e}")

        if config.LEADERBOARD_CHANNEL_ID:
            print(f"[Bot] Leaderboard channel: {config.LEADERBOARD_CHANNEL_ID}")
        else:
            print("[Bot] ATTENTION: LEADERBOARD_CHANNEL_ID non configure dans config.py")

        # Definir le statut
        await self.change_presence(
            activity=discord.Game(name="League of Legends"),
            status=discord.Status.online
        )

    @tasks.loop(time=time(hour=10, minute=0, tzinfo=PARIS_TZ))
    async def daily_leaderboard(self):
        """Envoie le leaderboard quotidien a 10h Paris"""
        if not config.LEADERBOARD_CHANNEL_ID:
            print("[Leaderboard] Channel non configure, skip")
            return

        channel = self.get_channel(config.LEADERBOARD_CHANNEL_ID)
        if not channel:
            print(f"[Leaderboard] Channel {config.LEADERBOARD_CHANNEL_ID} introuvable")
            return

        print(f"[Leaderboard] Envoi du leaderboard quotidien...")

        try:
            # Mettre a jour les rangs avant d'envoyer
            await self.leaderboard_module.update_all_ranks()

            # Generer le leaderboard
            embeds, messages = await self.leaderboard_module.generate_full_leaderboard()

            # Envoyer les embeds
            for embed in embeds:
                await channel.send(embed=embed)

            # Envoyer les messages speciaux
            if messages:
                await channel.send("\n".join(messages))

            print(f"[Leaderboard] Envoye avec succes!")

        except Exception as e:
            print(f"[Leaderboard] Erreur: {e}")
            import traceback
            traceback.print_exc()

    @daily_leaderboard.before_loop
    async def before_daily_leaderboard(self):
        """Attend que le bot soit pret"""
        await self.wait_until_ready()

    @tasks.loop(hours=1)
    async def hourly_rank_update(self):
        """Met a jour les rangs toutes les heures"""
        try:
            count = await self.leaderboard_module.update_all_ranks()
            print(f"[RankUpdate] {count} rangs mis a jour")
        except Exception as e:
            print(f"[RankUpdate] Erreur: {e}")

    @hourly_rank_update.before_loop
    async def before_hourly_rank_update(self):
        """Attend que le bot soit pret"""
        await self.wait_until_ready()

    async def close(self):
        """Nettoyage lors de la fermeture"""
        print("[Bot] Arret du bot...")
        self.daily_leaderboard.cancel()
        self.hourly_rank_update.cancel()
        await self.riot_client.close()
        await super().close()


async def run_discord_bot():
    """Lance le bot Discord"""
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN doit etre defini dans .env")

    bot = LoLBot()

    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n[Bot] Interruption detectee")
    finally:
        await bot.close()


async def run_cli_mode():
    """Lance le mode CLI"""
    from cli import run_cli
    await run_cli(RIOT_API_KEY)


def main():
    """Point d'entree principal"""
    parser = argparse.ArgumentParser(description="LoLBot - Bot Discord pour League of Legends")
    parser.add_argument(
        '--cli',
        action='store_true',
        help="Lance en mode CLI interactif (sans Discord)"
    )
    args = parser.parse_args()

    if not RIOT_API_KEY:
        print("Erreur: RIOT_API_KEY doit etre defini dans .env")
        return

    if args.cli:
        print("Lancement en mode CLI...")
        asyncio.run(run_cli_mode())
    else:
        if not DISCORD_TOKEN:
            print("Erreur: DISCORD_BOT_TOKEN doit etre defini dans .env")
            print("Utilisez --cli pour le mode CLI sans Discord.")
            return
        asyncio.run(run_discord_bot())


if __name__ == "__main__":
    main()
