from collections import ChainMap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from ipaddress import IPv4Network
from pathlib import Path

from .console import ask_until_filled, choose_one, cyan, green

ADDRESS_FIELDS = {"ip": "{ip}", "mask": "{mask}", "cidr": "{cidr}"}


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    title: str
    prompt: str
    placeholder: str


@dataclass(frozen=True, slots=True)
class RouteFormat:
    title: str
    template: str
    parameters: tuple[Parameter, ...] = ()
    separator: str = "\n"
    chunk_size: int | None = None

    def example(self, placeholders: Mapping[str, str], values: Mapping[str, str]) -> str:
        line = self.template.format_map(ChainMap(placeholders, {parameter.name: cyan(parameter.placeholder) for parameter in self.parameters}, values))
        return line if self.separator == "\n" else f"{line}{self.separator}{line}{self.separator}..."

    def complete(self, values: Mapping[str, str]) -> dict[str, str]:
        return {**values, **{parameter.name: ask_until_filled(values[parameter.name], parameter.prompt) for parameter in self.parameters}}

    def render(self, networks: Sequence[IPv4Network], values: Mapping[str, str]) -> list[str]:
        escaped = {name: value.replace("{", "{{").replace("}", "}}") for name, value in values.items()}
        template = self.template.format_map(ChainMap(ADDRESS_FIELDS, escaped))
        return [template.format(ip=network.network_address, mask=network.netmask, cidr=network.with_prefixlen) for network in networks]

    def write(self, path: Path, lines: Sequence[str]) -> list[tuple[Path, int]]:
        if self.chunk_size is None or len(lines) <= self.chunk_size:
            path.write_text(self.separator.join(lines), encoding="utf-8")
            return [(path, len(lines))]
        path.unlink(missing_ok=True)
        parts = []
        for number, start in enumerate(range(0, len(lines), self.chunk_size), 1):
            part = path.with_name(f"{path.stem}_p{number}{path.suffix or '.txt'}")
            chunk = lines[start:start + self.chunk_size]
            part.write_text(self.separator.join(chunk), encoding="utf-8")
            parts.append((part, len(chunk)))
        return parts


GATEWAY = Parameter(
    "gateway",
    "Шлюз/Имя интерфейса для Windows и Linux route",
    f"Укажите {green('IP шлюза')} или {green('имя интерфейса')}: ",
    "GATEWAY",
)
KEENETIC_GATEWAY = Parameter(
    "keenetic",
    "Шлюз/Имя интерфейса для Keenetic CLI",
    f"Укажите {green('IP шлюза')} или {green('имя интерфейса')} или {green('IP шлюза')} и через пробел {green('имя интерфейса')}: ",
    "GATEWAY GATEWAY_NAME",
)
LIST_NAME = Parameter(
    "listname",
    "Имя списка для Mikrotik firewall",
    f"Введите {green('LIST_NAME')} для Mikrotik firewall: ",
    "LIST_NAME",
)

PLAIN = "ip"

FORMATS: dict[str, RouteFormat] = {
    "win": RouteFormat("Windows route", "route add {ip} mask {mask} {gateway}", (GATEWAY,)),
    "unix": RouteFormat("Linux route", "ip route {cidr} {gateway}", (GATEWAY,)),
    "keenetic bat": RouteFormat("Keenetic BAT", "route add {ip} mask {mask} 0.0.0.0", chunk_size=999),
    "keenetic cli": RouteFormat("Keenetic CLI", "ip route {cidr} {keenetic} auto !{comment}", (KEENETIC_GATEWAY,)),
    "cidr": RouteFormat("CIDR-нотация", "{cidr}"),
    "mikrotik": RouteFormat("Mikrotik CLI", "/ip/firewall/address-list add list={listname}{mikrotik_comment} address={cidr}", (LIST_NAME,)),
    "ovpn": RouteFormat("OpenVPN", 'push "route {ip} {mask}"'),
    "wireguard": RouteFormat("Wireguard", "{cidr}", separator=", "),
    PLAIN: RouteFormat("только IP", "{ip}"),
}

PARAMETERS = tuple(dict.fromkeys(parameter for route_format in FORMATS.values() for parameter in route_format.parameters))

MENU = tuple(key for key in FORMATS if key != PLAIN)


def route_values(services: Sequence[str], gateway: str = "", keenetic: str = "", listname: str = "", mikrotik_comment: bool = False) -> dict[str, str]:
    comment = ",".join("".join(word.title() for word in service.split()) for service in services)
    return {
        "gateway": gateway,
        "keenetic": keenetic,
        "listname": listname,
        "comment": comment,
        "mikrotik_comment": f' comment="{comment}"' if mikrotik_comment else "",
    }


def choose_format(key: str, placeholders: Mapping[str, str], values: Mapping[str, str]) -> RouteFormat:
    if not key:
        labels = [f"{green(item)} - {FORMATS[item].example(placeholders, values)}" for item in MENU]
        index = choose_one("В каком формате сохранить файл?", labels, cyan("IP"))
        key = PLAIN if index is None else MENU[index]
    return FORMATS[key]
