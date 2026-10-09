import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

import dns.asyncresolver
import dns.exception
import dns.resolver

SOURCE = Path("result.txt")
TARGET = Path("verified_domains.txt")
CONCURRENCY = 40
DELEGATED = "Делегирован"
DNS_SERVERS = (
    ("8.8.8.8", "8.8.4.4"),
    ("1.1.1.1", "1.0.0.1"),
    ("77.88.8.8", "77.88.8.1"),
)


def build_resolvers() -> list[dns.asyncresolver.Resolver]:
    resolvers = []
    for nameservers in DNS_SERVERS:
        resolver = dns.asyncresolver.Resolver(configure=False)
        resolver.nameservers = list(nameservers)
        resolvers.append(resolver)
    return resolvers


async def status(resolver: dns.asyncresolver.Resolver, domain: str) -> str:
    try:
        await resolver.resolve(domain, "A")
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return "Припаркован или неактивен"
    except (dns.exception.DNSException, OSError) as error:
        return f"Ошибка: {error}"
    return DELEGATED


async def is_delegated(domain: str, resolvers: Sequence[dns.asyncresolver.Resolver], limiter: asyncio.Semaphore) -> bool:
    async with limiter:
        statuses = await asyncio.gather(*(status(resolver, domain) for resolver in resolvers))
    result = DELEGATED if DELEGATED in statuses else statuses[-1]
    print(f"{domain} {result}.")
    return result == DELEGATED


async def select_delegated(domains: Sequence[str], resolvers: Sequence[dns.asyncresolver.Resolver], limiter: asyncio.Semaphore) -> set[str]:
    flags = await asyncio.gather(*(is_delegated(domain, resolvers, limiter) for domain in domains))
    return {domain for domain, delegated in zip(domains, flags) if delegated}


async def verify(domains: Sequence[str]) -> set[str]:
    resolvers = build_resolvers()
    limiter = asyncio.Semaphore(CONCURRENCY)
    verified = await select_delegated(domains, resolvers, limiter)
    unverified = [domain for domain in domains if domain not in verified]
    if unverified:
        print("\nЗапуск контрольной проверки неактивных доменов...\n")
        verified |= await select_delegated(unverified, resolvers, limiter)
    return verified


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    domains = list(dict.fromkeys(filter(None, map(str.strip, SOURCE.read_text(encoding="utf-8-sig").splitlines()))))
    verified = sorted(asyncio.run(verify(domains)))
    TARGET.write_text("".join(f"{domain}\n" for domain in verified), encoding="utf-8")
    print(f"Проверенные домены сохранены в {TARGET}.\nНайдено {len(verified)} уникальных активных доменов.")


if __name__ == "__main__":
    main()
