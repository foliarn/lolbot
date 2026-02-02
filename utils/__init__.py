"""
Utilitaires pour le bot
"""
from .embeds import create_stats_embed, create_patch_embed, create_clash_embed
from .scraper import get_latest_patch_note_url
from .helpers import parse_riot_id, format_rank, calculate_kda

__all__ = [
    'create_stats_embed',
    'create_patch_embed',
    'create_clash_embed',
    'get_latest_patch_note_url',
    'parse_riot_id',
    'format_rank',
    'calculate_kda'
]
