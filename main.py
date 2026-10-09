import argparse
import asyncio
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

from domainmapper.catalog import Catalog, http_client
from domainmapper.config import AppConfig
from domainmapper.console import ask, bright, choose_many, green, red, yellow
from domainmapper.export import export
from domainmapper.filters import ask_exclude_cloudflare, cloudflare_filter, stub_filter
from domainmapper.formats import route_values
from domainmapper.limits import QueryBudget
from domainmapper.progress import ResolveProgress
from domainmapper.resolver import AddressCollector, DnsServer, ServerResolver, report, system_dns_server

CUSTOM_LIST = Path("custom-dns-list.txt")
CUSTOM_SERVICE = "Custom DNS list"
CUSTOM_ALIAS = "custom"
ALL_ALIAS = "all"
DONATION_URL = "https://boosty.to/ground_zerro"


def select_services(platforms: dict[str, str], requested: Sequence[str]) -> list[str]:
    names = list(platforms)
    if ALL_ALIAS in requested:
        return names
    aliases = {name.lower(): name for name in names}
    if CUSTOM_SERVICE in platforms:
        aliases[CUSTOM_ALIAS] = CUSTOM_SERVICE
    unknown = [name for name in requested if name not in aliases]
    if unknown:
        print(red(f"Неизвестные сервисы в конфигурации: {', '.join(unknown)}"))
    chosen = list(dict.fromkeys(aliases[name] for name in requested if name in aliases))
    return chosen or [names[index] for index in choose_many("Выберите сервисы:", names, "платформ")]


def select_servers(servers: Sequence[DnsServer], requested: Sequence[int]) -> list[DnsServer]:
    if 0 in requested:
        return list(servers)
    chosen = [servers[number - 1] for number in dict.fromkeys(requested) if 1 <= number <= len(servers)]
    labels = [f"{server.name}: {', '.join(server.nameservers) or 'не определен'}" for server in servers]
    return chosen or [servers[index] for index in choose_many("Какие DNS серверы использовать?", labels, "DNS серверов")]


async def load_domains(catalog: Catalog, platforms: dict[str, str], services: Sequence[str], local: bool) -> list[str]:
    for service in services:
        print(f"{bright('Загрузка DNS имен платформы')} {service}...")
    lists = await asyncio.gather(*(catalog.domains(platforms[service], local) for service in services))
    return list(dict.fromkeys(domain for domains in lists for domain in domains))


async def run(config: AppConfig) -> None:
    async with http_client() as client:
        catalog = Catalog(client)
        platforms = await catalog.entries("platformdb", config.local_platform)
        if CUSTOM_LIST.is_file():
            platforms[CUSTOM_SERVICE] = str(CUSTOM_LIST.resolve())
        services = select_services(platforms, config.services)
        dns_entries = await catalog.entries("dnsdb", config.local_dns)
        servers = select_servers(
            [system_dns_server(), *(DnsServer(name, tuple(value.split())) for name, value in dns_entries.items())],
            config.dns_servers,
        )
        filters = [stub_filter(nameserver for server in servers for nameserver in server.nameservers)]
        if ask_exclude_cloudflare(config.exclude_cloudflare):
            filters.append(await cloudflare_filter(client))
        domains = await load_domains(catalog, platforms, services, config.local_platform)

    print(f"{bright(f'Загружено {len(domains)} DNS имен.')}\n{yellow('Резолвинг...')}")
    collector = AddressCollector(filters)
    budget = QueryBudget(config.total_rate_limit)
    expected_rate = min(config.rate_limit, config.total_rate_limit / len(servers))
    async with ResolveProgress(len(servers), len(domains), expected_rate) as progress:
        await asyncio.gather(*(
            ServerResolver(server, config.rate_limit, budget).resolve(domains, collector, tracker)
            for server, tracker in zip(servers, progress.servers)
        ))
    report(progress, collector)
    print(f"{bright('Использовались DNS серверы:')} {', '.join(server.name for server in servers)}")

    print(f"\n{yellow('Обработка результатов...')}")
    values = route_values(services, config.gateway, config.keenetic, config.listname, config.mikrotik_comment)
    export(collector.addresses, Path(config.filename), config.aggregation, config.filetype, values)

    if config.run:
        print("\nВыполнение команды после завершения скрипта...", flush=True)
        subprocess.run(config.run, shell=True, check=False)
    print(f"\n{bright('Если есть желание, можно угостить автора чашечкой какао:')} {green(DONATION_URL)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="DNS resolver script with custom config file.")
    parser.add_argument("-c", "--config", type=Path, default=Path("config.ini"), help="Путь к конфигурационному файлу (по умолчанию: config.ini)")
    config = AppConfig.load(parser.parse_args().config)
    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        print(f"\n{red('Программа прервана пользователем')}")
        return
    except Exception as error:
        print(f"\n{red('Критическая ошибка:')} {error}")
    if os.name == "nt" and not config.run:
        ask(f"\nНажмите {green('Enter')} для выхода...")


if __name__ == "__main__":
    main()
