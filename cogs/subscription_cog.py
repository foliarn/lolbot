"""
Cog pour la gestion des abonnements aux patchs
"""
import discord
from discord import app_commands
from discord.ext import commands


class SubscriptionCog(commands.Cog):
    """Commandes pour gérer les abonnements aux champions"""

    def __init__(self, bot, db_manager, data_dragon):
        self.bot = bot
        self.db = db_manager
        self.data_dragon = data_dragon

    @app_commands.command(name="subscribe", description="Abonne-toi aux notifications de patch pour un champion")
    @app_commands.describe(champion="Nom du champion (ou 'all' pour tous)")
    async def subscribe(
        self,
        interaction: discord.Interaction,
        champion: str
    ):
        """Abonne l'utilisateur à un champion"""
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)

        # Cas spécial: subscribe all
        if champion.lower() == "all":
            success = await self.db.add_subscription(discord_id, "ALL")
            if success:
                await interaction.followup.send(
                    "✅ Tu recevras un récapitulatif complet de chaque patch!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Tu es déjà abonné au récapitulatif complet.",
                    ephemeral=True
                )
            return

        # Vérifier que le champion existe
        all_champions = await self.data_dragon.get_all_champion_names()
        champion_proper = None

        for champ in all_champions:
            if champ.lower() == champion.lower():
                champion_proper = champ
                break

        if not champion_proper:
            await interaction.followup.send(
                f"Champion **{champion}** introuvable. Vérifie l'orthographe.",
                ephemeral=True
            )
            return

        # Ajouter l'abonnement
        success = await self.db.add_subscription(discord_id, champion_proper)

        if success:
            await interaction.followup.send(
                f"✅ Tu es maintenant abonné aux notifications de patch pour **{champion_proper}**!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"Tu es déjà abonné à **{champion_proper}**.",
                ephemeral=True
            )

    @app_commands.command(name="unsubscribe", description="Désabonne-toi d'un champion")
    @app_commands.describe(champion="Nom du champion (ou 'all')")
    async def unsubscribe(
        self,
        interaction: discord.Interaction,
        champion: str
    ):
        """Désabonne l'utilisateur d'un champion"""
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)

        # Gérer le cas 'all'
        if champion.lower() == "all":
            champion_name = "ALL"
        else:
            # Trouver le nom exact
            all_champions = await self.data_dragon.get_all_champion_names()
            champion_name = None
            for champ in all_champions:
                if champ.lower() == champion.lower():
                    champion_name = champ
                    break

            if not champion_name:
                await interaction.followup.send(
                    f"Champion **{champion}** introuvable.",
                    ephemeral=True
                )
                return

        # Supprimer l'abonnement
        success = await self.db.remove_subscription(discord_id, champion_name)

        if success:
            await interaction.followup.send(
                f"✅ Désabonné de **{champion_name}**.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"Tu n'es pas abonné à **{champion_name}**.",
                ephemeral=True
            )

    @app_commands.command(name="subscriptions", description="Affiche tes abonnements aux patchs")
    async def subscriptions(self, interaction: discord.Interaction):
        """Affiche tous les abonnements"""
        await interaction.response.defer(ephemeral=True)

        discord_id = str(interaction.user.id)
        subs = await self.db.get_subscriptions(discord_id)

        if not subs:
            await interaction.followup.send(
                "Tu n'as aucun abonnement. Utilise `/subscribe` pour en ajouter.",
                ephemeral=True
            )
            return

        # Créer l'embed
        embed = discord.Embed(
            title="Tes abonnements aux patchs",
            color=discord.Color.gold()
        )

        if "ALL" in subs:
            embed.add_field(
                name="Récapitulatif complet",
                value="✅ Activé",
                inline=False
            )
            subs.remove("ALL")

        if subs:
            champions_text = ", ".join(sorted(subs))
            embed.add_field(
                name="Champions",
                value=champions_text,
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Charge le cog"""
    cog = SubscriptionCog(bot, bot.db_manager, bot.data_dragon)
    await bot.add_cog(cog)
