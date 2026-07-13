"""
Client LLM OpenAI-compatible — appelle /v1/chat/completions via aiohttp.
Configuré via .env : LLM_BASE_URL, LLM_API_KEY, LLM_MODEL.
"""
import asyncio
import os
from typing import Optional

import aiohttp


class LLMClient:
    """Async HTTP client pour un endpoint OpenAI-compatible (llama-server, etc.)."""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url: Optional[str] = None
        self._model: Optional[str] = None

    async def start(self):
        # Read env vars here so load_dotenv() has already run in main.py
        base_url = os.getenv('LLM_BASE_URL', 'http://localhost:8080/v1')
        api_key = os.getenv('LLM_API_KEY', 'none')
        self._base_url = base_url
        self._model = os.getenv('LLM_MODEL', 'default')

        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {api_key}"}
        )

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def generate(self, system: str, user: str, max_tokens: int = 300) -> Optional[str]:
        """
        Envoie une requête chat/completions avec system + user en rôles séparés.
        Retourne le texte généré, ou None en cas d'erreur.
        """
        if not self._session:
            print("[LLM] Session non initialisée")
            return None

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.85,
        }

        try:
            async with self._session.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"[LLM] HTTP {resp.status}: {text[:200]}")
                    return None

                data = await resp.json()
                return data["choices"][0]["message"]["content"].strip() or None

        except asyncio.TimeoutError:
            print("[LLM] Timeout (30s)")
            return None
        except Exception as e:
            print(f"[LLM] Exception: {e}")
            return None
