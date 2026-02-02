"""
Cog pour la gestion des comptes Riot
"""
import discord
from discord import app_commands
from discord.ext import commands


class AccountCog(commands.Cog):
    """Commandes pour gérer les comptes Riot liés"""

    def __init__(self, bot, riot_api, db_manager):
        self.bot = bot
        self.api = riot_api
        self.db = db_manager

    @app_commands.command(name="link", description="Lie un compte Riot à ton compte Discord")
    @app_commands.describe(
        riot_id="Ton RiotID (ex: Faker)",
        tag="Ton tag (ex: KR1)",
        alias="Nom du compte (optionnel, ex: main, smurf1)"
    )
    async def link(
        self,
        interaction: discord.Interaction,
        riot_id: str,
        tag: str,
        alias: str = None
    ):
        """Lie un compte Riot au compte Discord"""
        await interaction.response.defer(ephemeral=True)

        print(f"[Link] Tentative de liaison: {riot_id}#{tag}")

        # Récupérer le compte Riot
        try:
            account = await self.api.get_account_by_riot_id(riot_id, tag)
            print(f"[Link] Réponse API account: {account}")
        except Exception as e:
            print(f"[Link] Erreur API account: {e}")
            await interaction.followup.send(
                f"Erreur lors de la récupération du compte: {e}",
                ephemeral=True
            )
            return

        if not account:
            await interaction.followup.send(
                f"Compte Riot **{riot_id}#{tag}** introuvable.",
                ephemeral=True
            )
            return

        puuid = account['puuid']
        game_name = account['gameName']
        tag_line = account['tagLine']

        # Récupérer le summoner
        try:
            summoner = await self.api.get_summoner_by_puuid(puuid)
            print(f"[Link] Réponse API summoner: {summoner}")
        except Exception as e:
            print(f"[Link] Erreur API summoner: {e}")
            await interaction.followup.send(
                f"Erreur lors de la récupération du summoner: {e}",
                ephemeral=True
            )
            return

        if not summoner:
            await interaction.followup.send(
                "Impossible de récupérer les informations du summoner.",
                ephemeral=True
            )
            return

        summoner_id = summoner.get('id')
        if not summoner_id:
            print(f"[Link] ATTENTION: pas d'ID dans summoner: {summoner}")
            # Utiliser le PUUID comme fallback
            summoner_id = puuid

        discord_id = str(interaction.user.id)

        print(f"[Link] Ajout en DB: discord_id={discord_id}, summoner_id={summoner_id}")

        # Ajouter à la base de données
        try:
            success = await self.db.add_user(
                discord_id=discord_id,
                riot_puuid=puuid,
                summoner_id=summoner_id,
                game_name=game_name,
                tag_line=tag_line,
                account_alias=alias
            )
            print(f"[Link] Résultat DB add_user: {success}")
        except Exception as e:
            print(f"[Link] Erreur DB: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                f"Erreur lors de l'enregistrement: {e}",
                ephemeral=True
            )
            return

        if not success:
            await interaction.followup.send(
                "Ce compte est déjà lié.",
                ephemeral=True
            )
            return

        # Message de confirmation
        alias_text = f" (alias: `{alias}`)" if alias else " (compte principal)"
        await interaction.followup.send(
            f"✅ Compte **{game_name}#{tag_line}** lié avec succès{alias_text}!",
            ephemeral=True
        )

    @app_commands.command(name="unlink", description="Supprime un compte Riot lié")
    @app_commands.describe(alias="Alias du compte à supprimer (laisser vide pour le compte principal)")
    async def unlink(
        self,
        interaction: discord.Interaction,
        alias: str = None
    ):
        """Supprime un compte lié"""
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)

        # Vérifier que le compte existe
        user = await self.db.get_user(discord_id, alias)
        if not user:
            await interaction.followup.send(
                "Aucun compte trouvé avec cet alias.",
                ephemeral=True
            )
            return

        # Supprimer
        await self.db.remove_user(discord_id, alias)

        account_name = f"{user['game_name']}#{user['tag_line']}"
        await interaction.followup.send(
            f"✅ Compte **{account_name}** supprimé.",
            ephemeral=True
        )

    @app_commands.command(name="accounts", description="Affiche tous tes comptes Riot liés")
    async def accounts(self, interaction: discord.Interaction):
        """Affiche tous les comptes liés"""
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)
        users = await self.db.get_all_users(discord_id)

        if not users:
            await interaction.followup.send(
                "Tu n'as aucun compte lié. Utilise `/link` pour en ajouter un.",
                ephemeral=True
            )
            return

        # Créer l'embed
        embed = discord.Embed(
            title="Tes comptes Riot",
            color=discord.Color.blue()
        )

        for user in users:
            name = f"{user['game_name']}#{user['tag_line']}"
            alias = user.get('account_alias') or "Non défini"
            is_primary = "⭐ Principal" if user['is_primary'] else "Secondaire"

            embed.add_field(
                name=name,
                value=f"**Alias:** {alias}\n**Type:** {is_primary}",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Charge le cog"""
    cog = AccountCog(bot, bot.riot_api, bot.db_manager)
    await bot.add_cog(cog)
