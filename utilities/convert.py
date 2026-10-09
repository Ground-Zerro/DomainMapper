import asyncio
import re
from ipaddress import IPv4Address
from pathlib import Path

from domainmapper.catalog import http_client
from domainmapper.console import green, red, yellow
from domainmapper.export import export
from domainmapper.files import read_text
from domainmapper.filters import RangeFilter, ask_exclude_cloudflare, cloudflare_filter
from domainmapper.formats import route_values

SOURCE = Path("ip.txt")
OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IP_PATTERN = re.compile(rf"\b{OCTET}(?:\.{OCTET}){{3}}\b")
SERVICE_NAME = "Service"


def read_addresses(path: Path) -> set[int]:
    return {int(IPv4Address(match)) for match in IP_PATTERN.findall(read_text(path))}


async def load_cloudflare() -> RangeFilter:
    async with http_client() as client:
        return await cloudflare_filter(client)


def main() -> None:
    if not SOURCE.is_file():
        print(f"\n{red(f'Ошибка: файл {SOURCE} не найден!')}")
        print(yellow("Инструкция:"))
        print(f"1. Создайте файл {green(SOURCE)} в текущей директории")
        print("2. Добавьте в него IP-адреса (по одному на строку) или текст содержащий IP-адреса")
        print("3. Запустите скрипт снова")
        return
    addresses = read_addresses(SOURCE)
    if ask_exclude_cloudflare(None):
        cloudflare = asyncio.run(load_cloudflare())
        addresses = {address for address in addresses if address not in cloudflare}
    export(addresses, SOURCE, "", "", route_values([SERVICE_NAME]))


if __name__ == "__main__":
    main()
