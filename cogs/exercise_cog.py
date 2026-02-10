"""
Cog pour les commandes d'exercices d'entrainement
"""
import traceback
import discord
from discord import app_commands
from discord.ext import commands
import config


class ExerciseCog(commands.Cog):
    """Commandes pour les exercices d'entrainement"""

    def __init__(self, bot, exercises_module):
        self.bot = bot
        self.exercises = exercises_module

    exercises_group = app_commands.Group(name="exercises", description="Exercices d'entrainement per-game")

    @exercises_group.command(name="list", description="Voir tous les exercices disponibles")
    async def exercise_list(self, interaction: discord.Interaction):
        """Affiche la liste des exercices"""
        embed = self.exercises.generate_exercise_list_embed()
        await interaction.response.send_message(embed=embed)

    @exercises_group.command(name="enable", description="Activer le tracking d'un exercice")
    @app_commands.describe(exercise_id="ID de l'exercice a activer")
    async def enable(self, interaction: discord.Interaction, exercise_id: str):
        """Active un exercice"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Validate exercise exists
            if exercise_id not in config.TRAINING_EXERCISES:
                available = ', '.join(f'`{k}`' for k in config.TRAINING_EXERCISES)
                await interaction.followup.send(
                    f"Exercice inconnu: `{exercise_id}`\nDisponibles: {available}",
                    ephemeral=True
                )
                return

            # Get user
            discord_id = str(interaction.user.id)
            user = await self.bot.db_manager.get_user(discord_id)
            if not user:
                await interaction.followup.send(
                    "Aucun compte lie. Utilisez `/link` d'abord.",
                    ephemeral=True
                )
                return

            success = await self.bot.db_manager.enable_exercise(user['riot_puuid'], exercise_id)
            ex_name = config.TRAINING_EXERCISES[exercise_id]['name']

            if success:
                await interaction.followup.send(
                    f"Exercice **{ex_name}** active ! Le tracking commencera au prochain check.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"L'exercice **{ex_name}** est deja active.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"[Exercises] Erreur enable: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"Erreur: {e}", ephemeral=True)

    @enable.autocomplete('exercise_id')
    async def exercise_id_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete pour les IDs d'exercices"""
        choices = []
        for ex_id, ex in config.TRAINING_EXERCISES.items():
            if current.lower() in ex_id.lower() or current.lower() in ex['name'].lower():
                choices.append(app_commands.Choice(name=f"{ex['name']} ({ex_id})", value=ex_id))
        return choices[:25]

    @exercises_group.command(name="disable", description="Desactiver le tracking d'un exercice")
    @app_commands.describe(exercise_id="ID de l'exercice a desactiver")
    async def disable(self, interaction: discord.Interaction, exercise_id: str):
        """Desactive un exercice"""
        await interaction.response.defer(ephemeral=True)

        try:
            discord_id = str(interaction.user.id)
            user = await self.bot.db_manager.get_user(discord_id)
            if not user:
                await interaction.followup.send(
                    "Aucun compte lie. Utilisez `/link` d'abord.",
                    ephemeral=True
                )
                return

            success = await self.bot.db_manager.disable_exercise(user['riot_puuid'], exercise_id)
            ex_def = config.TRAINING_EXERCISES.get(exercise_id)
            ex_name = ex_def['name'] if ex_def else exercise_id

            if success:
                await interaction.followup.send(
                    f"Exercice **{ex_name}** desactive.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"L'exercice **{ex_name}** n'etait pas active.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"[Exercises] Erreur disable: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"Erreur: {e}", ephemeral=True)

    @disable.autocomplete('exercise_id')
    async def disable_exercise_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete pour les exercices actives du joueur"""
        choices = []
        try:
            discord_id = str(interaction.user.id)
            user = await self.bot.db_manager.get_user(discord_id)
            if user:
                enabled = await self.bot.db_manager.get_enabled_exercises(user['riot_puuid'])
                for ex in enabled:
                    ex_id = ex['exercise_id']
                    ex_def = config.TRAINING_EXERCISES.get(ex_id)
                    name = ex_def['name'] if ex_def else ex_id
                    if current.lower() in ex_id.lower() or current.lower() in name.lower():
                        choices.append(app_commands.Choice(name=f"{name} ({ex_id})", value=ex_id))
        except Exception:
            pass
        return choices[:25]

    @exercises_group.command(name="stats", description="Voir tes stats d'exercices")
    @app_commands.describe(user="Utilisateur cible (optionnel)")
    async def stats(self, interaction: discord.Interaction, user: discord.Member = None):
        """Affiche les stats d'exercices"""
        await interaction.response.defer()

        try:
            target = user or interaction.user
            discord_id = str(target.id)
            embed = await self.exercises.generate_exercise_stats_embed(discord_id)

            if user and user != interaction.user:
                embed.title = f"Exercices de {user.display_name}"

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[Exercises] Erreur stats: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"Erreur: {e}", ephemeral=True)


async def setup(bot):
    """Charge le cog"""
    cog = ExerciseCog(bot, bot.exercises_module)
    await bot.add_cog(cog)
