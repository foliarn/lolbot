"""
CLI interactif pour le bot LoL
Mode watch avec commandes admin et test
"""
import asyncio
import os
import readline
import shlex
from typing import Optional, List

from database import DatabaseManager
from riot_api import RiotAPIClient, RiotEndpoints, DataDragon
from modules.stats import StatsModule
from modules.leaderboard import LeaderboardModule


# History file path
HISTORY_FILE = os.path.expanduser("~/.lolbot_history")


class CLICompleter:
    """Auto-completion pour le CLI"""

    def __init__(self, cli: 'CLI'):
        self.cli = cli
        self.commands = ['link', 'unlink', 'accounts', 'stats', 'leaderboard', 'updateranks', 'cache', 'user', 'users', 'setprimary', 'import', 'help', 'quit', 'exit']
        self.cache_subcommands = ['clear']

    def complete(self, text: str, state: int) -> Optional[str]:
        """Retourne la completion pour le texte donne"""
        buffer = readline.get_line_buffer()
        parts = buffer.split()

        # Premiere partie = commande
        if not parts or (len(parts) == 1 and not buffer.endswith(' ')):
            matches = [cmd for cmd in self.commands if cmd.startswith(text)]
        # Sous-commandes
        elif parts[0] == 'cache':
            matches = [sub for sub in self.cache_subcommands if sub.startswith(text)]
        else:
            matches = []

        try:
            return matches[state]
        except IndexError:
            return None


class CLI:
    """Interface en ligne de commande interactive"""

    def __init__(self, riot_api_key: str):
        self.riot_api_key = riot_api_key
        self.db_manager = DatabaseManager()
        self.data_dragon = DataDragon()
        self.riot_client: Optional[RiotAPIClient] = None
        self.riot_api: Optional[RiotEndpoints] = None
        self.stats_module: Optional[StatsModule] = None
        self.leaderboard_module: Optional[LeaderboardModule] = None
        self.running = False
        self.completer = CLICompleter(self)
        # Discord ID actif (par defaut cli_user, peut etre change avec 'user')
        self.current_user = "cli_user"

    def setup_readline(self):
        """Configure readline pour l'edition de ligne et l'historique"""
        # Charger l'historique si le fichier existe
        if os.path.exists(HISTORY_FILE):
            try:
                readline.read_history_file(HISTORY_FILE)
            except (IOError, OSError):
                pass

        # Configurer la taille de l'historique
        readline.set_history_length(1000)

        # Configurer l'auto-completion
        readline.set_completer(self.completer.complete)
        readline.set_completer_delims(' \t\n')

        # Activer la completion avec Tab
        readline.parse_and_bind('tab: complete')

    def save_history(self):
        """Sauvegarde l'historique dans un fichier"""
        try:
            readline.write_history_file(HISTORY_FILE)
        except (IOError, OSError):
            pass

    async def initialize(self):
        """Initialise les composants"""
        print("[CLI] Initialisation de la base de donnees...")
        await self.db_manager.initialize()

        print("[CLI] Initialisation du client API Riot...")
        self.riot_client = RiotAPIClient(self.riot_api_key, self.db_manager)
        await self.riot_client.start()
        self.riot_api = RiotEndpoints(self.riot_client)

        print("[CLI] Chargement des donnees Data Dragon...")
        await self.data_dragon.load_champions()

        # Modules
        self.stats_module = StatsModule(self.riot_api, self.data_dragon, self.db_manager)
        self.leaderboard_module = LeaderboardModule(self.riot_api, self.data_dragon, self.db_manager)

        print("[CLI] Pret!\n")

    async def cleanup(self):
        """Nettoyage des ressources"""
        self.save_history()
        if self.riot_client:
            await self.riot_client.close()

    def print_help(self):
        """Affiche l'aide"""
        print(f"""
Utilisateur actif: {self.current_user}

Commandes disponibles:
  link <RiotID> <Tag> [options]
       Options: --user <discord_id>  Lie a un utilisateur specifique
                --primary            Definit comme compte principal
                --alias <name>       Definit un alias
       Exemples: link Faker KR1
                 link Faker KR1 --user 123456789 --primary
                 link Faker KR1 --alias smurf

  unlink [alias]               - Supprime un compte lie
  accounts                     - Liste les comptes de l'utilisateur actif
  setprimary <alias>           - Definit un compte comme principal
  stats [RiotID Tag]           - Affiche les stats (compte lie ou specifie)
  leaderboard [solo|flex]      - Affiche le leaderboard
  updateranks                  - Met a jour les rangs de tous les joueurs
  import [fichier.csv]         - Importe des comptes depuis un CSV

  user [discord_id]            - Change l'utilisateur actif (ou affiche l'actuel)
  users                        - Liste tous les utilisateurs avec comptes lies

  cache clear                  - Vide le cache API
  help                         - Affiche cette aide
  quit / exit                  - Quitte le CLI

Raccourcis clavier (style bash):
  Ctrl+A/E     Debut/Fin de ligne      Ctrl+U/K     Suppr ligne
  Ctrl+W       Suppr mot               Ctrl+R       Recherche historique
  Tab          Auto-completion         Up/Down      Historique
""")

    async def cmd_link(self, args: list):
        """Lie un compte Riot"""
        if len(args) < 2:
            print("Usage: link <RiotID> <Tag> [--user <discord_id>] [--primary] [--alias <name>]")
            print("Exemple: link Faker KR1 --user 123456789 --primary")
            return

        riot_id = args[0]
        tag = args[1]
        alias = None
        discord_id = self.current_user
        force_primary = False

        # Parser les arguments optionnels
        remaining = args[2:]
        i = 0
        while i < len(remaining):
            if remaining[i] in ('--user', '-u'):
                if i + 1 < len(remaining):
                    discord_id = remaining[i + 1]
                    i += 2
                else:
                    print("Erreur: --user necessite un discord_id")
                    return
            elif remaining[i] in ('--primary', '-p'):
                force_primary = True
                i += 1
            elif remaining[i] in ('--alias', '-a'):
                if i + 1 < len(remaining):
                    alias = remaining[i + 1]
                    i += 2
                else:
                    print("Erreur: --alias necessite un nom")
                    return
            else:
                # Argument positionnel = alias (retrocompatibilite)
                alias = remaining[i]
                i += 1

        print(f"[Link] Recherche du compte {riot_id}#{tag}...")

        # Recuperer le PUUID
        account = await self.riot_api.get_account_by_riot_id(riot_id, tag)
        if not account:
            print("Erreur: Compte Riot introuvable.")
            return

        puuid = account['puuid']
        game_name = account['gameName']
        tag_line = account['tagLine']

        print(f"[Link] Compte trouve: {game_name}#{tag_line}")

        # Recuperer le summoner (pour le niveau, etc.)
        summoner = await self.riot_api.get_summoner_by_puuid(puuid)
        summoner_id = summoner.get('id') if summoner else None

        # Ajouter en base avec gestion du primary
        success, is_primary = await self._add_user_with_primary(
            discord_id=discord_id,
            riot_puuid=puuid,
            summoner_id=summoner_id,
            game_name=game_name,
            tag_line=tag_line,
            account_alias=alias,
            force_primary=force_primary
        )

        if success:
            alias_str = f" (alias: {alias})" if alias else ""
            user_str = f" pour {discord_id}" if discord_id != self.current_user else ""
            primary_str = " [Principal]" if is_primary else ""
            print(f"Compte {game_name}#{tag_line} lie avec succes{user_str}!{alias_str}{primary_str}")
        else:
            print("Erreur: Ce compte est deja lie a cet utilisateur.")

    async def _add_user_with_primary(
        self,
        discord_id: str,
        riot_puuid: str,
        summoner_id: Optional[str],
        game_name: str,
        tag_line: str,
        account_alias: Optional[str],
        force_primary: bool
    ) -> tuple[bool, bool]:
        """Ajoute un utilisateur avec gestion du statut primary"""
        import aiosqlite

        async with aiosqlite.connect(self.db_manager.db_path) as db:
            # Verifier si c'est le premier compte ou si on force primary
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE discord_id = ?",
                (discord_id,)
            )
            count = (await cursor.fetchone())[0]
            is_primary = (count == 0) or force_primary

            # Si on force primary, retirer le statut des autres comptes
            if force_primary and count > 0:
                await db.execute(
                    "UPDATE users SET is_primary = 0 WHERE discord_id = ?",
                    (discord_id,)
                )

            try:
                await db.execute(
                    """INSERT INTO users
                    (discord_id, riot_puuid, summoner_id, game_name, tag_line, region, is_primary, account_alias)
                    VALUES (?, ?, ?, ?, ?, 'EUW1', ?, ?)""",
                    (discord_id, riot_puuid, summoner_id, game_name, tag_line, 1 if is_primary else 0, account_alias)
                )
                await db.commit()
                return True, is_primary
            except aiosqlite.IntegrityError:
                return False, False

    async def cmd_unlink(self, args: list):
        """Supprime un compte lie"""
        alias = args[0] if args else None

        await self.db_manager.remove_user(self.current_user, alias)

        if alias:
            print(f"Compte avec alias '{alias}' supprime.")
        else:
            print("Compte principal supprime.")

    async def cmd_setprimary(self, args: list):
        """Definit un compte comme principal"""
        if not args:
            print("Usage: setprimary <alias>")
            print("       setprimary <RiotID#Tag>")
            return

        import aiosqlite

        identifier = args[0]

        async with aiosqlite.connect(self.db_manager.db_path) as db:
            # Chercher par alias ou par gamename#tag
            if '#' in identifier:
                game_name, tag_line = identifier.rsplit('#', 1)
                cursor = await db.execute(
                    "SELECT id, game_name, tag_line FROM users WHERE discord_id = ? AND game_name = ? AND tag_line = ?",
                    (self.current_user, game_name, tag_line)
                )
            else:
                cursor = await db.execute(
                    "SELECT id, game_name, tag_line FROM users WHERE discord_id = ? AND account_alias = ?",
                    (self.current_user, identifier)
                )

            row = await cursor.fetchone()

            if not row:
                print(f"Erreur: Compte '{identifier}' non trouve pour {self.current_user}.")
                return

            user_id, game_name, tag_line = row

            # Retirer le statut primary de tous les comptes
            await db.execute(
                "UPDATE users SET is_primary = 0 WHERE discord_id = ?",
                (self.current_user,)
            )

            # Definir le nouveau primary
            await db.execute(
                "UPDATE users SET is_primary = 1 WHERE id = ?",
                (user_id,)
            )

            await db.commit()

        print(f"Compte {game_name}#{tag_line} defini comme principal.")

    async def cmd_import(self, args: list):
        """Importe les comptes depuis pseudos.csv"""
        import csv

        filepath = args[0] if args else "pseudos.csv"

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header
                rows = list(reader)
        except FileNotFoundError:
            print(f"Erreur: Fichier '{filepath}' non trouve.")
            return

        print(f"[Import] {len(rows)} comptes a importer...")

        success_count = 0
        error_count = 0

        for row in rows:
            if len(row) < 4:
                print(f"  [Skip] Ligne invalide: {row}")
                error_count += 1
                continue

            game_name = row[0].strip()
            tag = row[1].strip()
            discord_id = row[2].strip()
            priority = row[3].strip().lower()

            is_primary = (priority == "primary")

            print(f"  [{game_name}#{tag}] -> {discord_id} ({'primary' if is_primary else 'smurf'})...", end=" ")

            # Recuperer le PUUID
            try:
                account = await self.riot_api.get_account_by_riot_id(game_name, tag)
                if not account:
                    print("ERREUR: Compte Riot introuvable")
                    error_count += 1
                    continue

                puuid = account['puuid']
                real_game_name = account['gameName']
                real_tag = account['tagLine']

                # Recuperer summoner
                summoner = await self.riot_api.get_summoner_by_puuid(puuid)
                summoner_id = summoner.get('id') if summoner else None

                # Ajouter en base
                success, was_primary = await self._add_user_with_primary(
                    discord_id=discord_id,
                    riot_puuid=puuid,
                    summoner_id=summoner_id,
                    game_name=real_game_name,
                    tag_line=real_tag,
                    account_alias=None if is_primary else "smurf",
                    force_primary=is_primary
                )

                if success:
                    print(f"OK {'[Principal]' if was_primary else ''}")
                    success_count += 1
                else:
                    print("SKIP (deja lie)")

            except Exception as e:
                print(f"ERREUR: {e}")
                error_count += 1

        print(f"\n[Import] Termine: {success_count} importes, {error_count} erreurs")

    async def cmd_accounts(self, args: list):
        """Liste les comptes lies de l'utilisateur actif"""
        accounts = await self.db_manager.get_all_users(self.current_user)

        if not accounts:
            print(f"Aucun compte lie pour {self.current_user}.")
            return

        print(f"\nComptes lies pour {self.current_user} ({len(accounts)}):")
        print("-" * 50)
        for acc in accounts:
            primary = " [Principal]" if acc['is_primary'] else ""
            alias = f" ({acc['account_alias']})" if acc['account_alias'] else ""
            print(f"  {acc['game_name']}#{acc['tag_line']}{alias}{primary}")
        print()

    async def cmd_user(self, args: list):
        """Change ou affiche l'utilisateur actif"""
        if not args:
            print(f"Utilisateur actif: {self.current_user}")
            return

        self.current_user = args[0]
        print(f"Utilisateur actif: {self.current_user}")

        # Afficher les comptes de cet utilisateur
        accounts = await self.db_manager.get_all_users(self.current_user)
        if accounts:
            print(f"  {len(accounts)} compte(s) lie(s)")
        else:
            print("  Aucun compte lie")

    async def cmd_users(self, args: list):
        """Liste tous les utilisateurs avec des comptes lies"""
        import aiosqlite

        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """SELECT discord_id, COUNT(*) as count,
                   GROUP_CONCAT(game_name || '#' || tag_line, ', ') as accounts
                   FROM users GROUP BY discord_id ORDER BY discord_id"""
            )
            rows = await cursor.fetchall()

        if not rows:
            print("Aucun utilisateur avec compte lie.")
            return

        print(f"\nUtilisateurs ({len(rows)}):")
        print("-" * 60)
        for discord_id, count, accounts in rows:
            marker = " <--" if discord_id == self.current_user else ""
            print(f"  {discord_id} ({count} compte(s)){marker}")
            print(f"    {accounts}")
        print()

    async def cmd_stats(self, args: list):
        """Affiche les stats d'un joueur"""
        if len(args) >= 2:
            # Stats pour un RiotID specifique
            riot_id = args[0]
            tag = args[1]
            embed, error = await self.stats_module.get_stats(
                riot_id=riot_id,
                tag=tag
            )
        elif len(args) == 1:
            # Stats avec alias
            alias = args[0]
            embed, error = await self.stats_module.get_stats(
                discord_id=self.current_user,
                alias=alias
            )
        else:
            # Stats du compte principal
            embed, error = await self.stats_module.get_stats(
                discord_id=self.current_user
            )

        if error:
            print(f"Erreur: {error}")
            return

        # Afficher l'embed en mode texte
        self._print_embed(embed)

    async def cmd_leaderboard(self, args: list):
        """Affiche le leaderboard"""
        queue = args[0].lower() if args else "both"

        if queue == "both":
            # Solo
            solo_players = await self.leaderboard_module.get_leaderboard_data("RANKED_SOLO_5x5")
            print(self.leaderboard_module.format_leaderboard_text("RANKED_SOLO_5x5", solo_players))

            # Flex
            flex_players = await self.leaderboard_module.get_leaderboard_data("RANKED_FLEX_SR")
            print(self.leaderboard_module.format_leaderboard_text("RANKED_FLEX_SR", flex_players))

        elif queue == "solo":
            players = await self.leaderboard_module.get_leaderboard_data("RANKED_SOLO_5x5")
            print(self.leaderboard_module.format_leaderboard_text("RANKED_SOLO_5x5", players))

        elif queue == "flex":
            players = await self.leaderboard_module.get_leaderboard_data("RANKED_FLEX_SR")
            print(self.leaderboard_module.format_leaderboard_text("RANKED_FLEX_SR", players))

        else:
            print("Usage: leaderboard [solo|flex|both]")

    async def cmd_updateranks(self, args: list):
        """Met a jour les rangs de tous les joueurs"""
        print("[UpdateRanks] Mise a jour des rangs...")
        count = await self.leaderboard_module.update_all_ranks()
        print(f"[UpdateRanks] {count} rangs mis a jour.")

    def _print_embed(self, embed):
        """Affiche un embed Discord en mode texte"""
        print()
        print("=" * 50)
        print(f"  {embed.title}")
        print("=" * 50)

        for field in embed.fields:
            print(f"\n[{field.name}]")
            for line in field.value.split('\n'):
                print(f"  {line}")

        print()

    async def cmd_cache(self, args: list):
        """Gestion du cache"""
        if not args:
            print("Usage: cache clear")
            return

        if args[0] == "clear":
            await self.db_manager.clear_expired_cache()
            print("Cache expire nettoye.")

    async def process_command(self, line: str):
        """Traite une commande"""
        line = line.strip()
        if not line:
            return

        try:
            parts = shlex.split(line)
        except ValueError:
            parts = line.split()

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ('quit', 'exit', 'q'):
            self.running = False
            print("Au revoir!")
        elif cmd == 'help':
            self.print_help()
        elif cmd == 'link':
            await self.cmd_link(args)
        elif cmd == 'unlink':
            await self.cmd_unlink(args)
        elif cmd == 'accounts':
            await self.cmd_accounts(args)
        elif cmd == 'setprimary':
            await self.cmd_setprimary(args)
        elif cmd == 'import':
            await self.cmd_import(args)
        elif cmd == 'stats':
            await self.cmd_stats(args)
        elif cmd == 'leaderboard':
            await self.cmd_leaderboard(args)
        elif cmd == 'updateranks':
            await self.cmd_updateranks(args)
        elif cmd == 'user':
            await self.cmd_user(args)
        elif cmd == 'users':
            await self.cmd_users(args)
        elif cmd == 'cache':
            await self.cmd_cache(args)
        else:
            print(f"Commande inconnue: {cmd}")
            print("Tapez 'help' pour voir les commandes disponibles.")

    def get_prompt(self):
        """Retourne le prompt avec l'utilisateur actif"""
        if self.current_user == "cli_user":
            return "lolbot> "
        else:
            # Tronquer si trop long
            user_display = self.current_user[:12] + "..." if len(self.current_user) > 15 else self.current_user
            return f"lolbot ({user_display})> "

    async def run(self):
        """Lance la boucle interactive"""
        self.setup_readline()
        await self.initialize()

        print("LoLBot CLI - Mode interactif")
        print("Tapez 'help' pour voir les commandes disponibles.\n")

        self.running = True

        while self.running:
            try:
                prompt = self.get_prompt()
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input(prompt)
                )
                await self.process_command(line)
            except EOFError:
                print("\nAu revoir!")
                break
            except KeyboardInterrupt:
                print()  # Nouvelle ligne apres ^C
                continue  # Retour au prompt

        await self.cleanup()


async def run_cli(riot_api_key: str):
    """Point d'entree pour le mode CLI"""
    cli = CLI(riot_api_key)
    await cli.run()
