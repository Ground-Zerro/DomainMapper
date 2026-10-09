from pathlib import Path

import httpx

from .console import red
from .files import PROJECT_ROOT, decode, read_text

REMOTE_ROOT = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/"
HTTP_TIMEOUT = 20.0


def http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True)


class Catalog:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def read(self, location: str, local: bool) -> str:
        if location.startswith(("http://", "https://")):
            return await self._download(location)
        if local or Path(location).is_absolute():
            return read_text(PROJECT_ROOT / location)
        return await self._download(REMOTE_ROOT + location)

    async def entries(self, name: str, local: bool) -> dict[str, str]:
        if local and not (PROJECT_ROOT / name).is_file():
            print(red(f"\nЛокальный файл {name} не найден - загружаем из сети."))
            local = False
        try:
            text = await self.read(name, local)
        except (httpx.HTTPError, OSError) as error:
            print(red(f"Ошибка при загрузке {name}: {error}"))
            return {}
        pairs = (line.split(": ", 1) for line in text.splitlines() if ": " in line)
        return {key.strip(): value.strip() for key, value in pairs}

    async def domains(self, location: str, local: bool) -> list[str]:
        try:
            text = await self.read(location, local)
        except (httpx.HTTPError, OSError) as error:
            print(red(f"Ошибка при загрузке DNS имен {location}: {error}"))
            return []
        return [line for line in map(str.strip, text.splitlines()) if line and not line.startswith("#")]

    async def _download(self, url: str) -> str:
        response = await self._client.get(url)
        response.raise_for_status()
        return decode(response.content)
