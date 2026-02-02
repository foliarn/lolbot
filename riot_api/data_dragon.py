"""
Gestion de Data Dragon pour les données statiques
"""
import aiohttp
import json
import os
from typing import Optional, Dict, Any, List
from config import DATA_DRAGON_BASE_URL, DATA_DRAGON_CDN


class DataDragon:
    """Gestionnaire pour Data Dragon (données statiques LoL)"""

    def __init__(self):
        self.cache_dir = "data_dragon_cache"
        self.current_version: Optional[str] = None
        self.champions: Optional[Dict[str, Any]] = None
        os.makedirs(self.cache_dir, exist_ok=True)

    async def get_latest_version(self) -> Optional[str]:
        """Récupère la dernière version du jeu"""
        url = f"{DATA_DRAGON_BASE_URL}/api/versions.json"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        versions = await response.json()
                        return versions[0] if versions else None
        except Exception as e:
            print(f"Erreur lors de la récupération de la version: {e}")
            return None

    async def fetch_champion_data(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Télécharge les données des champions pour une version donnée

        Returns: {'data': {'Aatrox': {...}, 'Ahri': {...}, ...}}
        """
        url = f"{DATA_DRAGON_CDN}/{version}/data/fr_FR/champion.json"
        cache_file = os.path.join(self.cache_dir, f"champion_{version}.json")

        # Vérifier le cache local
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Télécharger si pas en cache
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Sauvegarder en cache
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)

                        return data
        except Exception as e:
            print(f"Erreur lors du téléchargement des données champions: {e}")
            return None

    async def get_champion_name_by_id(self, champion_id: int) -> Optional[str]:
        """Récupère le nom d'un champion à partir de son ID"""
        if not self.champions:
            await self.load_champions()

        if self.champions:
            for name, data in self.champions['data'].items():
                if int(data['key']) == champion_id:
                    return name
        return None

    async def get_champion_id_by_name(self, champion_name: str) -> Optional[int]:
        """Récupère l'ID d'un champion à partir de son nom"""
        if not self.champions:
            await self.load_champions()

        if self.champions:
            champion_data = self.champions['data'].get(champion_name)
            if champion_data:
                return int(champion_data['key'])
        return None

    async def load_champions(self):
        """Charge les données des champions de la version actuelle"""
        if not self.current_version:
            self.current_version = await self.get_latest_version()

        if self.current_version:
            self.champions = await self.fetch_champion_data(self.current_version)

    async def get_all_champion_names(self) -> List[str]:
        """Récupère la liste de tous les noms de champions"""
        if not self.champions:
            await self.load_champions()

        if self.champions:
            return list(self.champions['data'].keys())
        return []

    async def compare_versions(self, old_version: str, new_version: str) -> Dict[str, Dict[str, Any]]:
        """
        Compare deux versions de champion.json et retourne les différences

        Returns: {
            'Aatrox': {'stats': {'attackdamage': {'old': 60, 'new': 65}}, ...},
            'Ahri': {...}
        }
        """
        old_data = await self.fetch_champion_data(old_version)
        new_data = await self.fetch_champion_data(new_version)

        if not old_data or not new_data:
            return {}

        changes = {}

        for champ_name, new_champ in new_data['data'].items():
            if champ_name not in old_data['data']:
                # Nouveau champion
                changes[champ_name] = {'type': 'new_champion'}
                continue

            old_champ = old_data['data'][champ_name]
            champ_changes = self._compare_champion_stats(old_champ, new_champ)

            if champ_changes:
                changes[champ_name] = champ_changes

        return changes

    def _compare_champion_stats(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Compare les stats entre deux versions d'un champion"""
        changes = {}

        # Comparer les stats de base
        if 'stats' in old and 'stats' in new:
            stat_changes = {}
            for stat_key, new_value in new['stats'].items():
                old_value = old['stats'].get(stat_key)
                if old_value != new_value:
                    stat_changes[stat_key] = {'old': old_value, 'new': new_value}

            if stat_changes:
                changes['stats'] = stat_changes

        # Comparer les sorts (spells)
        if 'spells' in old and 'spells' in new:
            spell_changes = {}
            for i, new_spell in enumerate(new['spells']):
                if i < len(old['spells']):
                    old_spell = old['spells'][i]
                    spell_diff = self._compare_spell(old_spell, new_spell)
                    if spell_diff:
                        spell_changes[new_spell.get('name', f'Spell_{i}')] = spell_diff

            if spell_changes:
                changes['spells'] = spell_changes

        return changes

    def _compare_spell(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Compare les détails d'un sort"""
        changes = {}

        # Cooldown
        if old.get('cooldown') != new.get('cooldown'):
            changes['cooldown'] = {'old': old.get('cooldown'), 'new': new.get('cooldown')}

        # Coût
        if old.get('cost') != new.get('cost'):
            changes['cost'] = {'old': old.get('cost'), 'new': new.get('cost')}

        # Description (changement de dégâts dans la description)
        if old.get('description') != new.get('description'):
            changes['description'] = 'Modified'

        return changes
