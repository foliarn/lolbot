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

from database import DatabaseManager
from riot_api import RiotAPIClient, RiotEndpoints, DataDragon
from modules.stats import StatsModule
from modules.leaderboard import LeaderboardModule
from modules.tilt_detector import TiltDetector
from modules.weekly_challenges import WeeklyChallenges
from modules.training_exercises import TrainingExercises
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
        self.tilt_detector = TiltDetector(self.riot_api, self.db_manager, self)
        self.challenges_module = WeeklyChallenges(self.riot_api, self.db_manager, self)
        self.exercises_module = TrainingExercises(self.riot_api, self.db_manager, self)

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
        await self.load_extension('cogs.clash_cog')
        await self.load_extension('cogs.challenge_cog')
        await self.load_extension('cogs.exercise_cog')

        print("[Setup] Synchronisation des commandes slash...")
        # Sync global
        synced = await self.tree.sync()
        print(f"[Setup] {len(synced)} commandes globales: {[c.name for c in synced]}")

        # Demarrer les taches planifiees
        self.daily_leaderboard.start()
        self.hourly_rank_update.start()
        self.tilt_and_challenges_check.start()
        self.monday_challenge_leaderboard.start()

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

    @tasks.loop(minutes=config.TILT_CHECK_INTERVAL_MINUTES)
    async def tilt_and_challenges_check(self):
        """Verifie les tilts et challenges toutes les 30 minutes"""
        # Skip if no channels configured at all
        if not config.TILT_CHANNEL_ID and not config.CHALLENGE_ANNOUNCEMENTS_CHANNEL_ID:
            return

        for guild in self.guilds:
            try:
                # Tilt detection (online users only)
                if config.TILT_CHANNEL_ID:
                    tilt_channel = self.get_channel(config.TILT_CHANNEL_ID)
                    if tilt_channel:
                        notifications = await self.tilt_detector.check_all_players(guild)
                        for notif in notifications:
                            embed = self.tilt_detector.create_tilt_embed(notif)
                            await tilt_channel.send(embed=embed)
                            print(f"[Tilt] Notification envoyee pour {notif['game_name']}")

                # Training exercises check (silent, no announcements)
                try:
                    await self.exercises_module.check_all_players()
                except Exception as e:
                    print(f"[Exercises] Erreur check: {e}")
                    traceback.print_exc()

                # Challenge progress check (all registered users)
                completions = await self.challenges_module.check_all_players()
                if config.CHALLENGE_ANNOUNCEMENTS_CHANNEL_ID:
                    announce_channel = self.get_channel(config.CHALLENGE_ANNOUNCEMENTS_CHANNEL_ID)
                    if announce_channel:
                        for completion in completions:
                            embed = self.challenges_module.create_completion_embed(completion)
                            await announce_channel.send(embed=embed)
                            print(f"[Challenges] Completion envoyee: {completion['game_name']} - {completion['challenge_name']}")

            except Exception as e:
                print(f"[TiltChallenges] Erreur pour guild {guild.name}: {e}")
                traceback.print_exc()

    @tilt_and_challenges_check.before_loop
    async def before_tilt_check(self):
        """Attend que le bot soit pret"""
        await self.wait_until_ready()
        # Initialize weekly challenges on startup
        try:
            _, is_new = await self.challenges_module.initialize_weekly_challenges()
            if is_new:
                print("[Challenges] Challenges hebdomadaires initialises")
            else:
                print("[Challenges] Challenges hebdomadaires deja existants")
        except Exception as e:
            print(f"[Challenges] Erreur initialisation: {e}")

    @tasks.loop(time=time(hour=config.CHALLENGE_LEADERBOARD_HOUR, minute=config.CHALLENGE_LEADERBOARD_MINUTE, tzinfo=PARIS_TZ))
    async def monday_challenge_leaderboard(self):
        """Envoie le leaderboard des challenges le lundi"""
        # Check if it's Monday
        now = datetime.now(PARIS_TZ)
        if now.weekday() != 0:  # 0 = Monday
            return

        if not config.CHALLENGE_LEADERBOARD_CHANNEL_ID:
            print("[Challenges] Channel non configure, skip leaderboard")
            return

        channel = self.get_channel(config.CHALLENGE_LEADERBOARD_CHANNEL_ID)
        if not channel:
            print(f"[Challenges] Channel {config.CHALLENGE_LEADERBOARD_CHANNEL_ID} introuvable")
            return

        try:
            # Process end of previous week
            result = await self.challenges_module.process_week_end()

            # Send penalty notification if any
            penalties = result.get('penalties', [])
            if penalties:
                penalty_msg = "**Challenges non completes - Penalites appliquees:**\n"
                for p in penalties:
                    penalty_msg += f"- {p['challenge_name']}: {p['penalty']} pts pour tous\n"
                await channel.send(penalty_msg)

            # Weekly retrospective (previous week's stats)
            now = datetime.now(PARIS_TZ)
            prev_monday = now - timedelta(days=7)
            prev_week_start = prev_monday.strftime('%Y-%m-%d')
            retro_embed = await self.leaderboard_module.generate_weekly_retrospective(prev_week_start)
            await channel.send(embed=retro_embed)

            # Send leaderboard with header
            today = now.strftime('%d/%m/%Y')
            await channel.send(f"**Classement de la semaine ({today})**")
            embed = await self.challenges_module.generate_leaderboard_embed()
            await channel.send(embed=embed)

            # Initialize new week's challenges
            _, _ = await self.challenges_module.initialize_weekly_challenges()

            # Announce new challenges
            await channel.send("**Nouveaux challenges de la semaine disponibles!** Utilisez `/challenges` pour voir vos defis.")

            print("[Challenges] Leaderboard hebdomadaire envoye")

        except Exception as e:
            print(f"[Challenges] Erreur leaderboard hebdomadaire: {e}")
            traceback.print_exc()

    @monday_challenge_leaderboard.before_loop
    async def before_monday_leaderboard(self):
        """Attend que le bot soit pret"""
        await self.wait_until_ready()

    async def close(self):
        """Nettoyage lors de la fermeture"""
        print("[Bot] Arret du bot...")
        self.daily_leaderboard.cancel()
        self.hourly_rank_update.cancel()
        self.tilt_and_challenges_check.cancel()
        self.monday_challenge_leaderboard.cancel()
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
