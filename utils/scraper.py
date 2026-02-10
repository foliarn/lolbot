"""
Web scraping utilitaires
"""
import cloudscraper
from bs4 import BeautifulSoup
from typing import Dict


def scrape_champion_season_stats(game_name: str, tag_line: str, region: str = "euw") -> Dict[str, Dict]:
    """
    Scrape leagueofgraphs pour les stats de champions de la saison.
    Synchrone — à appeler via asyncio.to_thread().

    Returns: {champion_name: {'games': int, 'winrate': float}}
    """
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        scraper.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.leagueofgraphs.com/',
        })
        url_name = game_name.replace(' ', '+')
        url = f"https://www.leagueofgraphs.com/summoner/champions/{region}/{url_name}-{tag_line}"

        resp = scraper.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"[Scraper] leagueofgraphs {game_name}#{tag_line}: status {resp.status_code}")
            return {}

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Première table = "all champions" (page dédiée aux stats)
        table = soup.find('table', class_='summoner_champions_details_table')
        if table:
            return _parse_champion_table(table)

        return {}

    except Exception as e:
        print(f"[Scraper] Erreur scraping {game_name}#{tag_line}: {e}")
        return {}


def _parse_champion_table(table) -> Dict[str, Dict]:
    """Parse la table des stats de champions leagueofgraphs"""
    stats = {}
    for row in table.find_all('tr')[1:]:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue

        # Nom du champion
        name_el = cells[0].find(class_='name')
        if not name_el:
            continue
        champ_name = name_el.get_text(strip=True)

        # Games played — data-value sur le progressbar
        played_bar = cells[1].find('progressbar')
        if not played_bar or not played_bar.get('data-value'):
            continue
        games = int(played_bar['data-value'])

        # Winrate — data-value entre 0 et 1
        wr_bar = cells[2].find('progressbar')
        if not wr_bar or not wr_bar.get('data-value'):
            continue
        winrate = float(wr_bar['data-value']) * 100

        if games > 0:
            stats[champ_name] = {
                'games': games,
                'winrate': winrate
            }

    return stats
