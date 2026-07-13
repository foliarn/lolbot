"""
Point d'entree principal du bot Discord LoL
"""
import argparse
import traceback
import discord
from discord.ext import commands, tasks
import asyncio
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from database.manager import DatabaseManager
from riot_api import RiotAPIClient, RiotEndpoints, DataDragon
from modules.stats import StatsModule
from modules.leaderboard import LeaderboardModule
from modules.tilt_detector import TiltDetector
from modules.reputation import ReputationManager
from modules.llm_client import LLMClient
from modules.bot_commentary import BotCommentary
from modules.weekly_awards import WeeklyAwardsModule
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
        # No privileged intents unless user enabled them
        # intents.members = True  
        # intents.presences = True 

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
        self.reputation_module = ReputationManager(self.db_manager)
        self.awards_module = WeeklyAwardsModule(self.db_manager)


        # LLM
        self.llm_client = LLMClient()
        self.commentary = BotCommentary(self.llm_client)

        self.tilt_detector = TiltDetector(
            self.riot_api, self.db_manager, self,
            self.reputation_module, self.commentary
        )

    async def setup_hook(self):
        """Configuration initiale du bot"""
        print("[Setup] Initialisation de la base de donnees...")
        await self.db_manager.initialize()

        print("[Setup] Initialisation du client API Riot...")
        await self.riot_client.start()
        await self.llm_client.start()

        print("[Setup] Chargement des donnees Data Dragon...")
        await self.data_dragon.load_champions()

        print("[Setup] Chargement des cogs...")
        await self.load_extension('cogs.account_cog')
        await self.load_extension('cogs.utility_cog')
        await self.load_extension('cogs.clash_cog')
        await self.load_extension('cogs.tofik_cog')

        print("[Setup] Synchronisation des commandes slash...")
        # Sync global ONLY - guild sync is too heavy and hits 429
        synced = await self.tree.sync()
        print(f"[Setup] {len(synced)} commandes globales synced!")

        # Demarrer les taches planifiees
        self.daily_leaderboard.start()
        self.hourly_rank_update.start()
        self.monday_task.start()
        self.tilt_check.start()

        print("[Setup] Bot pret!")

    async def on_ready(self):
        """Appele quand le bot est connecte"""
        print(f"[Bot] Connecte en tant que {self.user} (ID: {self.user.id})")
        print(f"[Bot] Serveurs: {len(self.guilds)}")

        # Removed guild sync loop to avoid Discord 429s

        if config.LEADERBOARD_DAILY_CHANNEL_ID:
            print(f"[Bot] Leaderboard channel: {config.LEADERBOARD_DAILY_CHANNEL_ID}")
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
        if not config.LEADERBOARD_DAILY_CHANNEL_ID:
            print("[Leaderboard] Channel non configure, skip")
            return

        channel = self.get_channel(config.LEADERBOARD_DAILY_CHANNEL_ID)
        if not channel:
            print(f"[Leaderboard] Channel {config.LEADERBOARD_DAILY_CHANNEL_ID} introuvable")
            return

        print(f"[Leaderboard] Envoi du leaderboard quotidien...")

        try:
            # Mettre a jour les rangs avant d'envoyer
            await self.leaderboard_module.update_all_ranks()

            # Generer le leaderboard
            embeds, messages = await self.leaderboard_module.generate_full_leaderboard()

            # Mettre a jour la reputation (LP change du jour)
            solo_players = await self.leaderboard_module.get_leaderboard_data("RANKED_SOLO_5x5")
            for p in solo_players:
                if p.get('discord_id') and p.get('lp_change_24h') is not None:
                    await self.reputation_module.update_lp_change(p['discord_id'], p['lp_change_24h'])

            # Header avec la date du jour
            today = datetime.now(PARIS_TZ).strftime('%d/%m/%Y')
            await channel.send(f"**Classement du jour ({today})**")

            # Envoyer les embeds
            for embed in embeds:
                await channel.send(embed=embed)

            # Envoyer les messages speciaux
            if messages:
                await channel.send("\n".join(messages))

            print(f"[Leaderboard] Envoye avec succes!")

        except Exception as e:
            print(f"[Leaderboard] Erreur: {e}")
            traceback.print_exc()

    @daily_leaderboard.before_loop
    async def before_daily_leaderboard(self):
        """Attend que le bot soit pret"""
        await self.wait_until_ready()

    @tasks.loop(hours=1)
    async def hourly_rank_update(self):
        """Met a jour les rangs toutes les heures et nettoie le cache expire"""
        try:
            count = await self.leaderboard_module.update_all_ranks()
            print(f"[RankUpdate] {count} rangs mis a jour")
            await self.db_manager.clear_expired_cache()
        except Exception as e:
            print(f"[RankUpdate] Erreur: {e}")

    @hourly_rank_update.before_loop
    async def before_hourly_rank_update(self):
        """Attend que le bot soit pret"""
        await self.wait_until_ready()

    @tasks.loop(time=time(hour=config.LEADERBOARD_HOUR, minute=config.LEADERBOARD_MINUTE, tzinfo=PARIS_TZ))
    async def monday_task(self):
        """Taches du lundi : retrospective + awards"""
        now = datetime.now(PARIS_TZ)
        if now.weekday() != 0:  # 0 = Monday
            return

        if not config.LEADERBOARD_WEEKLY_CHANNEL_ID:
            return

        channel = self.get_channel(config.LEADERBOARD_WEEKLY_CHANNEL_ID)
        if not channel:
            print(f"[MondayTask] Channel {config.LEADERBOARD_WEEKLY_CHANNEL_ID} introuvable")
            return

        try:
            prev_week_start = (now - timedelta(days=7)).strftime('%Y-%m-%d')

            # Weekly retrospective
            retro_embed = await self.leaderboard_module.generate_weekly_retrospective(prev_week_start)
            await channel.send(embed=retro_embed)

            # Weekly awards
            awards = await self.awards_module.compute_awards(prev_week_start)
            if awards:
                await channel.send("🏆 **Awards de la semaine**")
                for award in awards:
                    rep = None
                    try:
                        rep = await self.reputation_module.get_reputation(award.discord_id)
                    except Exception:
                        pass
                    msg = await self.commentary.award_message(
                        award_name=award.name,
                        player_name=award.winner_name,
                        stat_label=award.stat_label,
                        stat_value=award.stat_value,
                        reputation=rep,
                    )
                    mention = f"<@{award.discord_id}>"
                    await channel.send(f"**{award.name}** — {mention}\n{msg}")
                    print(f"[Awards] {award.name} → {award.winner_name} ({award.stat_value})")

        except Exception as e:
            print(f"[MondayTask] Erreur: {e}")
            traceback.print_exc()

    @monday_task.before_loop
    async def before_monday_task(self):
        """Attend que le bot soit pret"""
        await self.wait_until_ready()

    @tasks.loop(minutes=20)
    async def tilt_check(self):
        """Verifie les streaks toutes les 20 minutes et notifie"""
        if not config.TILT_CHANNEL_ID:
            return

        channel = self.get_channel(config.TILT_CHANNEL_ID)
        if not channel:
            return

        try:
            notifications = await self.tilt_detector.check_all_players()
            for notif in notifications:
                embed = self.tilt_detector.create_tilt_embed(notif)
                mention = f"<@{notif['discord_id']}>"
                await channel.send(content=mention, embed=embed)
                print(f"[TiltDetector] Notif envoyee: {notif['game_name']} - {notif['streak_type']} x{notif['streak_count']}")
        except Exception as e:
            print(f"[TiltDetector] Erreur: {e}")

    @tilt_check.before_loop
    async def before_tilt_check(self):
        """Attend que le bot soit pret"""
        await self.wait_until_ready()

    async def close(self):
        """Nettoyage lors de la fermeture"""
        print("[Bot] Arret du bot...")
        self.daily_leaderboard.cancel()
        self.hourly_rank_update.cancel()
        self.monday_task.cancel()
        self.tilt_check.cancel()
        await self.riot_client.close()
        await self.llm_client.close()
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
