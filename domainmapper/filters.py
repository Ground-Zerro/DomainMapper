from abc import ABC, abstractmethod
from bisect import bisect_right
from collections.abc import Iterable
from ipaddress import IPv4Network, ip_address, ip_network

import httpx

from .console import choose_one, red

CLOUDFLARE_URL = "https://www.cloudflare.com/ips-v4/"
STUB_ADDRESSES = ("127.0.0.1", "0.0.0.0")


class AddressFilter(ABC):
    def __init__(self, label: str):
        self.label = label
        self.rejected = 0

    @abstractmethod
    def __contains__(self, address: int) -> bool:
        ...

    def reject(self, address: int) -> bool:
        if address in self:
            self.rejected += 1
            return True
        return False


class SetFilter(AddressFilter):
    def __init__(self, label: str, addresses: Iterable[str]):
        super().__init__(label)
        self._addresses = frozenset(int(address) for address in map(ip_address, addresses) if address.version == 4)

    def __contains__(self, address: int) -> bool:
        return address in self._addresses


class RangeFilter(AddressFilter):
    def __init__(self, label: str, networks: Iterable[IPv4Network]):
        super().__init__(label)
        bounds = sorted((int(network.network_address), int(network.broadcast_address)) for network in networks)
        self._starts = [start for start, _ in bounds]
        self._ends = [end for _, end in bounds]

    def __contains__(self, address: int) -> bool:
        index = bisect_right(self._starts, address) - 1
        return index >= 0 and address <= self._ends[index]


def stub_filter(nameservers: Iterable[str]) -> SetFilter:
    return SetFilter("Исключено IP-адресов 'заглушек'", (*STUB_ADDRESSES, *nameservers))


async def cloudflare_filter(client: httpx.AsyncClient) -> RangeFilter:
    try:
        response = await client.get(CLOUDFLARE_URL)
        response.raise_for_status()
        networks = [ip_network(line.strip()) for line in response.text.splitlines() if "/" in line]
    except (httpx.HTTPError, ValueError) as error:
        print(red(f"Ошибка при получении IP адресов Cloudflare: {error}"))
        networks = []
    return RangeFilter("Исключено IP-адресов Cloudflare", networks)


def ask_exclude_cloudflare(configured: bool | None) -> bool:
    if configured is not None:
        return configured
    return choose_one("Исключить IP адреса Cloudflare из итогового списка?", ["исключить"], "оставить") == 0
