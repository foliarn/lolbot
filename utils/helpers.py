"""
Fonctions utilitaires diverses
"""
from typing import Tuple, Optional


def parse_riot_id(riot_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse un RiotID au format "GameName#TAG"

    Args:
        riot_id: RiotID complet (ex: "Faker#KR1")

    Returns:
        Tuple (game_name, tag_line) ou (None, None) si invalide
    """
    if '#' not in riot_id:
        return None, None

    parts = riot_id.split('#')
    if len(parts) != 2:
        return None, None

    return parts[0].strip(), parts[1].strip()


def format_rank(tier: str, rank: str, lp: int) -> str:
    """
    Formate un rang pour l'affichage

    Args:
        tier: Tier (IRON, BRONZE, SILVER, etc.)
        rank: Rank (I, II, III, IV)
        lp: League Points

    Returns:
        Rang formaté (ex: "Gold II 45 LP")
    """
    if tier == "UNRANKED":
        return "Unranked"

    tier_formatted = tier.capitalize()
    return f"{tier_formatted} {rank} {lp} LP"


def calculate_kda(kills: int, deaths: int, assists: int) -> Tuple[float, str]:
    """
    Calcule le KDA et retourne une chaîne formatée

    Args:
        kills: Nombre de kills
        deaths: Nombre de deaths
        assists: Nombre d'assists

    Returns:
        Tuple (kda_ratio, kda_string)
    """
    if deaths == 0:
        kda_ratio = kills + assists
        kda_string = f"{kills}/{deaths}/{assists} (Perfect)"
    else:
        kda_ratio = (kills + assists) / deaths
        kda_string = f"{kills}/{deaths}/{assists} ({kda_ratio:.2f})"

    return kda_ratio, kda_string


def get_queue_name(queue_id: int) -> str:
    """Retourne le nom de la queue à partir de son ID"""
    queue_names = {
        420: "Ranked Solo/Duo",
        440: "Ranked Flex",
        700: "Clash",
        400: "Draft Normal",
        430: "Blind Normal",
        450: "ARAM",
    }
    return queue_names.get(queue_id, f"Queue {queue_id}")


def get_role_emoji(role: str) -> str:
    """Retourne un emoji pour chaque rôle"""
    emojis = {
        'TOP': '⬆️',
        'JUNGLE': '🌲',
        'MIDDLE': '⭐',
        'BOTTOM': '🎯',
        'UTILITY': '🛡️',
    }
    return emojis.get(role, '❓')


def format_duration(seconds: int) -> str:
    """Formate une durée en secondes vers mm:ss"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"
