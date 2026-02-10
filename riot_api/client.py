"""
Client HTTP asynchrone avec rate limiting pour l'API Riot
"""
import aiohttp
import asyncio
import time
from collections import deque
from typing import Optional, Dict, Any
from config import RATE_LIMIT


class RateLimiter:
    """
    Gestionnaire de rate limiting avec sliding window.

    Tracks actual API call timestamps and waits when approaching limits.
    - 20 requests per second
    - 100 requests per 2 minutes
    """

    def __init__(self):
        self.limit_per_second = RATE_LIMIT['REQUESTS_PER_SECOND']  # 20
        self.limit_per_two_minutes = RATE_LIMIT['REQUESTS_PER_TWO_MINUTES']  # 100

        # Sliding window: store timestamps of all calls
        self.call_timestamps: deque = deque()
        self.lock = asyncio.Lock()

        # Stats
        self.total_calls = 0
        self.total_waits = 0

    def _cleanup_old_calls(self, now: float):
        """Remove calls older than 2 minutes"""
        cutoff = now - 120.0
        while self.call_timestamps and self.call_timestamps[0] < cutoff:
            self.call_timestamps.popleft()

    def _count_calls_in_window(self, now: float, window_seconds: float) -> int:
        """Count calls in the last N seconds"""
        cutoff = now - window_seconds
        count = 0
        # Count from the end (most recent) backwards
        for ts in reversed(self.call_timestamps):
            if ts >= cutoff:
                count += 1
            else:
                break
        return count

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        now = time.time()
        self._cleanup_old_calls(now)

        calls_1s = self._count_calls_in_window(now, 1.0)
        calls_2m = len(self.call_timestamps)

        return {
            'calls_last_second': calls_1s,
            'calls_last_2min': calls_2m,
            'limit_per_second': self.limit_per_second,
            'limit_per_2min': self.limit_per_two_minutes,
            'available_1s': self.limit_per_second - calls_1s,
            'available_2m': self.limit_per_two_minutes - calls_2m,
            'total_calls': self.total_calls,
            'total_waits': self.total_waits,
        }

    async def acquire(self):
        """
        Wait until we can make a call without exceeding rate limits.
        Returns immediately if under limits, waits if at limit.
        """
        async with self.lock:
            while True:
                now = time.time()
                self._cleanup_old_calls(now)

                calls_1s = self._count_calls_in_window(now, 1.0)
                calls_2m = len(self.call_timestamps)

                # Check if we can make a call
                if calls_1s < self.limit_per_second and calls_2m < self.limit_per_two_minutes:
                    # Record this call
                    self.call_timestamps.append(now)
                    self.total_calls += 1
                    return

                # Need to wait - calculate how long
                wait_time = 0.0

                if calls_1s >= self.limit_per_second:
                    # Wait until oldest call in last second expires
                    oldest_in_1s = None
                    cutoff_1s = now - 1.0
                    for ts in self.call_timestamps:
                        if ts >= cutoff_1s:
                            oldest_in_1s = ts
                            break
                    if oldest_in_1s:
                        wait_time = max(wait_time, (oldest_in_1s + 1.0) - now + 0.01)

                if calls_2m >= self.limit_per_two_minutes:
                    # Wait until oldest call expires from 2min window
                    if self.call_timestamps:
                        oldest = self.call_timestamps[0]
                        wait_time = max(wait_time, (oldest + 120.0) - now + 0.01)

                if wait_time > 0:
                    self.total_waits += 1
                    remaining_2m = self.limit_per_two_minutes - calls_2m
                    print(f"[RateLimit] Waiting {wait_time:.1f}s... ({calls_2m}/100 calls in 2min, {remaining_2m} remaining)")
                    await asyncio.sleep(wait_time)
                else:
                    # Small sleep to prevent tight loop
                    await asyncio.sleep(0.05)


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
        use_rate_limit: bool = True,
        _retries: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Effectue une requête HTTP avec cache et rate limiting

        Args:
            url: URL complète de la requête
            cache_key: Clé pour le cache (optionnel)
            cache_ttl: Durée de vie du cache en secondes (optionnel)
            use_rate_limit: Utiliser le rate limiter (défaut: True)
            _retries: Compteur interne de retries (ne pas utiliser directement)

        Returns:
            Réponse JSON ou None en cas d'erreur
        """
        MAX_RETRIES = 3

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
                    if _retries >= MAX_RETRIES:
                        print(f"[API] Rate limit: max retries ({MAX_RETRIES}) atteint pour {url}")
                        return None
                    # Rate limit dépassé, attendre
                    retry_after = int(response.headers.get('Retry-After', 1))
                    print(f"[API] Rate limit 429, retry dans {retry_after}s (tentative {_retries + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(retry_after)
                    return await self.request(url, cache_key, cache_ttl, use_rate_limit=False, _retries=_retries + 1)

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

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        return self.rate_limiter.get_status()
