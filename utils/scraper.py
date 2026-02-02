"""
Web scraper pour récupérer les liens des patch notes
"""
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional
from config import PATCH_NOTES_URL


async def get_latest_patch_note_url() -> Optional[str]:
    """
    Scrape le site officiel LoL pour récupérer l'URL du dernier patch note

    Returns:
        URL complète du patch note ou None en cas d'erreur
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PATCH_NOTES_URL) as response:
                if response.status != 200:
                    return PATCH_NOTES_URL

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Chercher le premier article de patch note
                # La structure peut varier, adapter selon le HTML réel
                article_link = soup.find('a', class_=['style__Wrapper-sc-106zuld-0', 'ArticleLink'])

                if article_link and article_link.get('href'):
                    url = article_link['href']
                    # Ajouter le domaine si c'est un chemin relatif
                    if url.startswith('/'):
                        url = f"https://www.leagueoflegends.com{url}"
                    return url

                # Fallback: chercher dans les liens contenant "patch"
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    if 'patch' in href.lower() and 'notes' in href.lower():
                        if href.startswith('/'):
                            href = f"https://www.leagueoflegends.com{href}"
                        return href

                return PATCH_NOTES_URL

    except Exception as e:
        print(f"Erreur lors du scraping des patch notes: {e}")
        return PATCH_NOTES_URL
