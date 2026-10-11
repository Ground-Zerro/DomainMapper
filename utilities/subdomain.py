import asyncio
import re
import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path

import httpx

from domainmapper.console import bright, green, red, wait_for_exit, yellow

TARGET = Path("result.txt")
REQUEST_TIMEOUT = 60.0
ATTEMPTS = 3
RETRY_DELAY = 5
TOO_MANY_REQUESTS = 429
SERVER_ERROR = 500
HOSTNAME = re.compile(r"[a-z0-9_-]+(?:\.[a-z0-9_-]+)+")
TOKEN = re.compile(r"[\w.-]+")


class Subdomains:
    def __init__(self, domain: str):
        self.domain = domain
        self._suffix = f".{domain}"
        self.by_source: dict[str, set[str]] = defaultdict(set)

    def add(self, source: str, names: Iterable[str]) -> None:
        self.by_source[source].update(name for name in map(self._normalize, names) if name)

    def all(self) -> list[str]:
        return sorted(set().union(*self.by_source.values()))

    def _normalize(self, raw: str) -> str | None:
        name = raw.strip().lower().removeprefix("*.").rstrip(".")
        inside = name == self.domain or name.endswith(self._suffix)
        return name if inside and HOSTNAME.fullmatch(name) else None


class Source(ABC):
    name: str

    async def run(self, client: httpx.AsyncClient, subdomains: Subdomains) -> None:
        try:
            await self.collect(client, subdomains)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            print(red(f"{self.name}: ошибка обработки ответа: {error}"))

    @abstractmethod
    async def collect(self, client: httpx.AsyncClient, subdomains: Subdomains) -> None:
        ...

    async def _get(self, client: httpx.AsyncClient, url: str, params: Mapping[str, str] | None = None) -> httpx.Response | None:
        attempt = 0
        while attempt < ATTEMPTS:
            try:
                response = await client.get(url, params=params)
            except httpx.HTTPError as error:
                attempt += 1
                print(yellow(f"{self.name}: {type(error).__name__}, попытка {attempt} из {ATTEMPTS}"))
                await asyncio.sleep(RETRY_DELAY)
                continue
            if response.status_code == TOO_MANY_REQUESTS:
                retry_after = response.headers.get("retry-after", "")
                delay = int(retry_after) if retry_after.isdigit() else RETRY_DELAY
                print(yellow(f"{self.name}: превышена квота запросов, ожидание {delay} с (Ctrl+C - сохранить найденное и выйти)"))
                await asyncio.sleep(delay)
                continue
            if response.status_code >= SERVER_ERROR:
                attempt += 1
                print(yellow(f"{self.name}: HTTP {response.status_code}, попытка {attempt} из {ATTEMPTS}"))
                await asyncio.sleep(RETRY_DELAY)
                continue
            if response.is_error:
                print(red(f"{self.name}: HTTP {response.status_code}"))
                return None
            return response
        print(red(f"{self.name}: источник недоступен"))
        return None


class CertSpotter(Source):
    name = "certspotter"
    URL = "https://api.certspotter.com/v1/issuances"

    async def collect(self, client: httpx.AsyncClient, subdomains: Subdomains) -> None:
        params = {"domain": subdomains.domain, "include_subdomains": "true", "expand": "dns_names"}
        while (response := await self._get(client, self.URL, params)) is not None:
            issuances = response.json()
            if not issuances:
                return
            subdomains.add(self.name, (name for issuance in issuances for name in issuance["dns_names"]))
            params["after"] = issuances[-1]["id"]


class CrtSh(Source):
    name = "crt.sh"
    URL = "https://crt.sh/"

    async def collect(self, client: httpx.AsyncClient, subdomains: Subdomains) -> None:
        response = await self._get(client, self.URL, {"q": f"%.{subdomains.domain}", "output": "json"})
        if response is not None:
            subdomains.add(self.name, (name for entry in response.json() for name in entry["name_value"].splitlines()))


class SubdomainCenter(Source):
    name = "subdomain.center"
    URL = "https://api.subdomain.center/"

    async def collect(self, client: httpx.AsyncClient, subdomains: Subdomains) -> None:
        response = await self._get(client, self.URL, {"domain": subdomains.domain})
        if response is not None:
            subdomains.add(self.name, response.json())


class HackerTarget(Source):
    name = "hackertarget"
    URL = "https://api.hackertarget.com/hostsearch/"

    async def collect(self, client: httpx.AsyncClient, subdomains: Subdomains) -> None:
        response = await self._get(client, self.URL, {"q": subdomains.domain})
        if response is not None:
            subdomains.add(self.name, (line.split(",", 1)[0] for line in response.text.splitlines()))


class RapidDns(Source):
    name = "rapiddns"
    URL = "https://rapiddns.io/subdomain/{domain}"

    async def collect(self, client: httpx.AsyncClient, subdomains: Subdomains) -> None:
        response = await self._get(client, self.URL.format(domain=subdomains.domain))
        if response is not None:
            subdomains.add(self.name, TOKEN.findall(response.text))


SOURCES: tuple[Source, ...] = (CertSpotter(), CrtSh(), SubdomainCenter(), HackerTarget(), RapidDns())


async def collect(subdomains: Subdomains) -> None:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        await asyncio.gather(*(source.run(client, subdomains) for source in SOURCES))


def requested_domain() -> str:
    value = sys.argv[1] if len(sys.argv) > 1 else input("Введите домен: ")
    return value.strip().lower().split("://")[-1].split("/")[0]


def save(subdomains: Subdomains) -> None:
    for source in SOURCES:
        print(f"{bright(source.name + ':')} {len(subdomains.by_source[source.name])}")
    names = subdomains.all()
    TARGET.write_text("".join(f"{name}\n" for name in names), encoding="utf-8")
    print(f"{green(f'Уникальных субдоменов найдено: {len(names)}.')}\nРезультаты сохранены в {TARGET}.")


def main() -> None:
    subdomains = Subdomains(requested_domain())
    print(yellow(f"Поиск субдоменов {subdomains.domain}: {', '.join(source.name for source in SOURCES)}..."))
    try:
        asyncio.run(collect(subdomains))
    except KeyboardInterrupt:
        print(red("\nПоиск прерван пользователем, сохраняем найденное."))
    save(subdomains)
    wait_for_exit()


if __name__ == "__main__":
    main()
