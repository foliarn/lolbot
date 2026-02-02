"""
Module de surveillance des patchs LoL
"""
import asyncio
from datetime import datetime, time as dt_time
from typing import Dict, Any, List
from discord.ext import tasks
import discord

from config import PATCH_CHECK_HOURS
from utils.embeds import create_patch_embed, create_patch_summary_embed
from utils.scraper import get_latest_patch_note_url


class PatchWatcher:
    """Surveille les patchs LoL et notifie les utilisateurs abonnés"""

    def __init__(self, bot, db_manager, data_dragon):
        self.bot = bot
        self.db = db_manager
        self.data_dragon = data_dragon
        self.checking = False

    def start(self):
        """Démarre la tâche de surveillance"""
        self.check_patch.start()

    def stop(self):
        """Arrête la tâche de surveillance"""
        self.check_patch.cancel()

    @tasks.loop(hours=1)
    async def check_patch(self):
        """Vérifie s'il y a un nouveau patch (tous les mercredis aux heures définies)"""
        now = datetime.now()

        # Vérifier si c'est mercredi (weekday 2)
        if now.weekday() != 2:
            return

        # Vérifier si c'est une des heures de check
        if now.hour not in PATCH_CHECK_HOURS:
            return

        # Éviter les checks multiples dans la même heure
        if self.checking:
            return

        self.checking = True
        try:
            await self._check_for_new_patch()
        finally:
            self.checking = False

    async def _check_for_new_patch(self):
        """Vérifie et traite un nouveau patch"""
        print(f"[PatchWatcher] Vérification du patch à {datetime.now()}")

        # Récupérer la version actuelle en base
        current_version = await self.db.get_patch_version()

        # Récupérer la dernière version disponible
        latest_version = await self.data_dragon.get_latest_version()

        if not latest_version:
            print("[PatchWatcher] Impossible de récupérer la dernière version")
            return

        # Pas de nouveau patch
        if current_version == latest_version:
            print(f"[PatchWatcher] Pas de nouveau patch (version actuelle: {current_version})")
            return

        print(f"[PatchWatcher] Nouveau patch détecté: {current_version} -> {latest_version}")

        # Comparer les versions
        if current_version:
            changes = await self.data_dragon.compare_versions(current_version, latest_version)
        else:
            # Première initialisation
            changes = {}

        # Mettre à jour la version en base
        await self.db.update_patch_version(latest_version)

        # Notifier les utilisateurs
        if changes:
            await self._notify_users(changes, latest_version)

    async def _notify_users(self, changes: Dict[str, Dict[str, Any]], version: str):
        """Notifie les utilisateurs des changements de patch"""
        # Récupérer l'URL du patch note
        patch_url = await get_latest_patch_note_url()

        # Récupérer les abonnés au récap complet
        all_subscribers = await self.db.get_all_subscribers()

        # Envoyer le récap complet
        if all_subscribers:
            buffs = []
            nerfs = []

            for champion, champion_changes in changes.items():
                # Déterminer si c'est un buff ou nerf (simplifié)
                is_buff = self._is_buff(champion_changes)
                if is_buff:
                    buffs.append(champion)
                else:
                    nerfs.append(champion)

            summary_embed = create_patch_summary_embed(buffs, nerfs, patch_url)

            for discord_id in all_subscribers:
                try:
                    user = await self.bot.fetch_user(int(discord_id))
                    await user.send(embed=summary_embed)
                    await asyncio.sleep(1)  # Éviter le rate limit Discord
                except Exception as e:
                    print(f"[PatchWatcher] Erreur lors de l'envoi à {discord_id}: {e}")

        # Envoyer les notifications par champion
        for champion_name, champion_changes in changes.items():
            # Récupérer les abonnés à ce champion
            subscribers = await self.db.get_subscribers(champion_name)

            if not subscribers:
                continue

            # Créer l'embed de notification
            embed = create_patch_embed(champion_name, champion_changes, patch_url)

            # Envoyer à chaque abonné
            for discord_id in subscribers:
                try:
                    user = await self.bot.fetch_user(int(discord_id))
                    await user.send(embed=embed)
                    await asyncio.sleep(1)  # Éviter le rate limit Discord
                except Exception as e:
                    print(f"[PatchWatcher] Erreur lors de l'envoi à {discord_id}: {e}")

        print(f"[PatchWatcher] Notifications envoyées pour {len(changes)} champions")

    def _is_buff(self, changes: Dict[str, Any]) -> bool:
        """Détermine si les changements sont globalement un buff (heuristique simplifiée)"""
        if 'stats' not in changes:
            return False

        buffs = 0
        nerfs = 0

        for stat_name, change in changes['stats'].items():
            old = change.get('old', 0)
            new = change.get('new', 0)

            # Stats positives (augmentation = buff)
            if stat_name in ['hp', 'hpperlevel', 'movespeed', 'attackdamage', 'armor', 'spellblock']:
                if new > old:
                    buffs += 1
                else:
                    nerfs += 1

        return buffs > nerfs

    @check_patch.before_loop
    async def before_check_patch(self):
        """Attend que le bot soit prêt"""
        await self.bot.wait_until_ready()
