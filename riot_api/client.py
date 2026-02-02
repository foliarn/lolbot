"""
Client HTTP asynchrone avec rate limiting pour l'API Riot
"""
import aiohttp
import asyncio
import time
from typing import Optional, Dict, Any
from config import RATE_LIMIT


class RateLimiter:
    """Gestionnaire de rate limiting avec Token Bucket"""

    def __init__(self):
        self.tokens_per_second = RATE_LIMIT['REQUESTS_PER_SECOND']
        self.tokens_per_two_minutes = RATE_LIMIT['REQUESTS_PER_TWO_MINUTES']

        # Token bucket pour 1 seconde
        self.tokens_1s = self.tokens_per_second
        self.last_update_1s = time.time()

        # Token bucket pour 2 minutes
        self.tokens_2m = self.tokens_per_two_minutes
        self.last_update_2m = time.time()

        self.lock = asyncio.Lock()

    async def acquire(self):
        """Attend qu'un token soit disponible"""
        async with self.lock:
            while True:
                now = time.time()

                # Recharger les tokens pour la limite 1s
                elapsed_1s = now - self.last_update_1s
                if elapsed_1s >= 1.0:
                    self.tokens_1s = self.tokens_per_second
                    self.last_update_1s = now

                # Recharger les tokens pour la limite 2m
                elapsed_2m = now - self.last_update_2m
                if elapsed_2m >= 120.0:
                    self.tokens_2m = self.tokens_per_two_minutes
                    self.last_update_2m = now

                # Vérifier si on peut consommer un token
                if self.tokens_1s > 0 and self.tokens_2m > 0:
                    self.tokens_1s -= 1
                    self.tokens_2m -= 1
                    return

                # Calculer le temps d'attente
                wait_time = min(
                    1.0 - elapsed_1s if self.tokens_1s <= 0 else 0,
                    120.0 - elapsed_2m if self.tokens_2m <= 0 else 0
                )

                if wait_time > 0:
                    await asyncio.sleep(wait_time)


class RiotAPIClient:
    """Client HTTP pour l'API Riot avec rate limiting et cache"""

    def __init__(self, api_key: str, db_manager=None):
        self.api_key = api_key
        self.db_manager = db_manager
        self.rate_limiter = RateLimiter()
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """Initialise la session HTTP"""
        self.session = aiohttp.ClientSession(
            headers={"X-Riot-Token": self.api_key}
        )

    async def close(self):
        """Ferme la session HTTP"""
        if self.session:
            await self.session.close()

    async def request(
        self,
        url: str,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
        use_rate_limit: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Effectue une requête HTTP avec cache et rate limiting

        Args:
            url: URL complète de la requête
            cache_key: Clé pour le cache (optionnel)
            cache_ttl: Durée de vie du cache en secondes (optionnel)
            use_rate_limit: Utiliser le rate limiter (défaut: True)

        Returns:
            Réponse JSON ou None en cas d'erreur
        """
        # Vérifier le cache
        if cache_key and self.db_manager:
            cached = await self.db_manager.get_cache(cache_key)
            if cached:
                print(f"[API] Cache hit: {cache_key}")
                return cached

        # Attendre le rate limiter
        if use_rate_limit:
            await self.rate_limiter.acquire()

        # Effectuer la requête
        print(f"[API] Requête: {url}")

        if not self.session:
            print("[API] ERREUR: Session HTTP non initialisée!")
            return None

        try:
            async with self.session.get(url) as response:
                print(f"[API] Status: {response.status}")
                if response.status == 200:
                    data = await response.json()

                    # Stocker en cache
                    if cache_key and self.db_manager:
                        await self.db_manager.set_cache(cache_key, data, cache_ttl)

                    return data

                elif response.status == 429:
                    # Rate limit dépassé, attendre
                    retry_after = int(response.headers.get('Retry-After', 1))
                    await asyncio.sleep(retry_after)
                    return await self.request(url, cache_key, cache_ttl, use_rate_limit=False)

                elif response.status == 404:
                    return None

                else:
                    print(f"Erreur API Riot: {response.status} - {url}")
                    return None

        except Exception as e:
            print(f"Exception lors de la requête: {e}")
            return None

    async def request_bulk(self, urls: list[str], use_rate_limit: bool = True) -> list[Optional[Dict[str, Any]]]:
        """
        Effectue plusieurs requêtes en parallèle

        Args:
            urls: Liste d'URLs à requêter
            use_rate_limit: Utiliser le rate limiter

        Returns:
            Liste de réponses JSON
        """
        tasks = [self.request(url, use_rate_limit=use_rate_limit) for url in urls]
        return await asyncio.gather(*tasks)
