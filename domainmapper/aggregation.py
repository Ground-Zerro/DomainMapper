from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Collection
from ipaddress import IPv4Network

from .console import choose_one, cyan

FULL_MASK = 0xFFFFFFFF
HOST_PREFIX = 32


def netmask(prefix: int) -> str:
    return str(IPv4Network((0, prefix)).netmask)


class Aggregation(ABC):
    def __init__(self, title: str, prefix: int):
        self.title = title
        self._prefix = prefix
        self._mask = FULL_MASK ^ (FULL_MASK >> prefix)

    @abstractmethod
    def apply(self, addresses: Collection[int]) -> list[IPv4Network]:
        ...

    @abstractmethod
    def placeholders(self) -> dict[str, str]:
        ...


class PrefixAggregation(Aggregation):
    def apply(self, addresses: Collection[int]) -> list[IPv4Network]:
        return [IPv4Network((network, self._prefix)) for network in sorted({address & self._mask for address in addresses})]

    def placeholders(self) -> dict[str, str]:
        return {"ip": cyan("IP"), "mask": netmask(self._prefix), "cidr": f"{cyan('IP')}/{self._prefix}"}


class MixAggregation(Aggregation):
    def apply(self, addresses: Collection[int]) -> list[IPv4Network]:
        sizes = Counter(address & self._mask for address in addresses)
        networks = {
            (address & self._mask, self._prefix) if sizes[address & self._mask] > 1 else (address, HOST_PREFIX)
            for address in addresses
        }
        return [IPv4Network(network) for network in sorted(networks)]

    def placeholders(self) -> dict[str, str]:
        return {
            "ip": cyan("IP"),
            "mask": f"{netmask(self._prefix)}|{netmask(HOST_PREFIX)}",
            "cidr": f"{cyan('IP')}/{self._prefix}|{HOST_PREFIX}",
        }


NO_AGGREGATION = "32"

AGGREGATIONS: dict[str, Aggregation] = {
    "16": PrefixAggregation("до /16 (255.255.0.0)", 16),
    "24": PrefixAggregation("до /24 (255.255.255.0)", 24),
    "mix": MixAggregation("до /24 + /32 (255.255.255.0 и 255.255.255.255)", 24),
    NO_AGGREGATION: PrefixAggregation("выключена", HOST_PREFIX),
}

MENU = ("16", "24", "mix")


def choose_aggregation(key: str) -> Aggregation:
    if not key:
        index = choose_one("Объединить IP-адреса в подсети?", [f"сократить {AGGREGATIONS[item].title}" for item in MENU], "пропустить")
        key = NO_AGGREGATION if index is None else MENU[index]
    return AGGREGATIONS[key]
