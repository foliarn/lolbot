"""
Point d'entrée principal du bot Discord LoL
"""
import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

from database import DatabaseManager
from riot_api import RiotAPIClient, RiotEndpoints, DataDragon
from modules.patch_watcher import PatchWatcher
from modules.stats import StatsModule
from modules.livegame import LiveGameModule
from modules.review import ReviewModule
from modules.clash_scout import ClashScout


# Charger les variables d'environnement
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
RIOT_API_KEY = os.getenv('RIOT_API_KEY')

if not DISCORD_TOKEN or not RIOT_API_KEY:
    raise ValueError("DISCORD_BOT_TOKEN et RIOT_API_KEY doivent être définis dans .env")


class LoLBot(commands.Bot):
    """Bot Discord principal pour League of Legends"""

    def __init__(self):
        intents = discord.Intents.default()
        # Pas besoin de message_content pour les slash commands
        # intents.message_content = True

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
        self.livegame_module = LiveGameModule(self.riot_api, self.data_dragon, self.db_manager)
        self.review_module = ReviewModule(self.riot_api, self.data_dragon, self.db_manager)
        self.clash_scout = ClashScout(self.riot_api, self.data_dragon, self.db_manager)

        # Patch Watcher
        self.patch_watcher = PatchWatcher(self, self.db_manager, self.data_dragon)

    async def setup_hook(self):
        """Configuration initiale du bot"""
        print("[Setup] Initialisation de la base de données...")
        await self.db_manager.initialize()

        print("[Setup] Initialisation du client API Riot...")
        await self.riot_client.start()

        print("[Setup] Chargement des données Data Dragon...")
        await self.data_dragon.load_champions()

        print("[Setup] Chargement des cogs...")
        await self.load_extension('cogs.account_cog')
        await self.load_extension('cogs.subscription_cog')
        await self.load_extension('cogs.utility_cog')

        print("[Setup] Synchronisation des commandes slash...")
        await self.tree.sync()

        print("[Setup] Démarrage du Patch Watcher...")
        self.patch_watcher.start()

        print("[Setup] ✅ Bot prêt!")

    async def on_ready(self):
        """Appelé quand le bot est connecté"""
        print(f"[Bot] Connecté en tant que {self.user} (ID: {self.user.id})")
        print(f"[Bot] Serveurs: {len(self.guilds)}")

        # Définir le statut
        await self.change_presence(
            activity=discord.Game(name="League of Legends"),
            status=discord.Status.online
        )

    async def close(self):
        """Nettoyage lors de la fermeture"""
        print("[Bot] Arrêt du bot...")
        self.patch_watcher.stop()
        await self.riot_client.close()
        await super().close()


async def main():
    """Fonction principale"""
    bot = LoLBot()

    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n[Bot] Interruption détectée")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
