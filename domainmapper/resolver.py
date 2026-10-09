import asyncio
import math
from collections import deque
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from ipaddress import IPv4Address

import dns.asyncresolver
import dns.exception
import dns.resolver

from .console import bright, yellow
from .filters import AddressFilter
from .limits import AdaptiveRateLimiter, QueryBudget
from .progress import RETRYABLE, Outcome, ResolveProgress, ServerProgress

QUERY_TIMEOUT = 2.0
QUERY_LIFETIME = 6.0
MAX_ATTEMPTS = 2
OUTCOME_LABELS = {
    Outcome.MISSING: "Домен не существует или нет A-записи",
    Outcome.TIMEOUT: "Сбоев: DNS-сервер не ответил",
    Outcome.UNAVAILABLE: "Сбоев: DNS-сервер отказал в ответе",
    Outcome.INVALID: "Сбоев: некорректное доменное имя",
}


@dataclass(frozen=True, slots=True)
class DnsServer:
    name: str
    nameservers: tuple[str, ...]


def system_dns_server() -> DnsServer:
    try:
        nameservers = tuple(map(str, dns.asyncresolver.Resolver().nameservers))
    except (dns.exception.DNSException, OSError):
        nameservers = ()
    return DnsServer("Системный DNS", nameservers)


class AddressCollector:
    def __init__(self, filters: Sequence[AddressFilter]):
        self.filters = filters
        self.addresses: set[int] = set()

    def add(self, address: int) -> None:
        for address_filter in self.filters:
            if address_filter.reject(address):
                return
        self.addresses.add(address)


class ServerResolver:
    def __init__(self, server: DnsServer, rate_limit: int, budget: QueryBudget):
        self._resolver = dns.asyncresolver.Resolver(configure=False)
        self._resolver.nameservers = list(server.nameservers)
        self._resolver.timeout = QUERY_TIMEOUT
        self._resolver.lifetime = QUERY_LIFETIME
        self._limiter = AdaptiveRateLimiter(rate_limit)
        self._budget = budget
        self._concurrency = math.ceil(rate_limit * QUERY_TIMEOUT)

    async def resolve(self, domains: Sequence[str], collector: AddressCollector, progress: ServerProgress) -> None:
        pending = iter(domains)
        retries: deque[tuple[str, int]] = deque()
        workers = min(self._concurrency, len(domains))
        await asyncio.gather(*(self._work(pending, retries, collector, progress) for _ in range(workers)))

    async def _work(
        self,
        pending: Iterator[str],
        retries: deque[tuple[str, int]],
        collector: AddressCollector,
        progress: ServerProgress,
    ) -> None:
        while True:
            domain = next(pending, None)
            attempt = 1
            if domain is None:
                if not retries:
                    return
                domain, attempt = retries.popleft()
            outcome = await self._query(domain, collector)
            if outcome in RETRYABLE and attempt < MAX_ATTEMPTS:
                retries.append((domain, attempt + 1))
            else:
                progress.record(outcome)

    async def _query(self, domain: str, collector: AddressCollector) -> Outcome:
        await self._limiter.wait()
        await self._budget.limiter.wait()
        async with self._budget.slots:
            try:
                answer = await self._resolver.resolve(domain)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                outcome = Outcome.MISSING
            except dns.exception.Timeout:
                outcome = Outcome.TIMEOUT
            except (dns.resolver.NoNameservers, OSError):
                outcome = Outcome.UNAVAILABLE
            except dns.exception.DNSException:
                outcome = Outcome.INVALID
            else:
                outcome = Outcome.RESOLVED
                for record in answer:
                    collector.add(int(IPv4Address(record.address)))
        self._limiter.feedback(outcome is Outcome.TIMEOUT)
        return outcome


def percent(part: int, whole: int) -> float:
    return part / whole * 100 if whole else 0.0


def report(progress: ResolveProgress, collector: AddressCollector) -> None:
    found = len(collector.addresses) + sum(address_filter.rejected for address_filter in collector.filters)
    print(f"\n{yellow('Проверка завершена.')}")
    print(f"{bright('Всего выполнено DNS запросов:')} {progress.processed} из {progress.total}")
    print(f"{bright('Разрешено уникальных IP-адресов:')} {len(collector.addresses)}")
    for outcome, label in OUTCOME_LABELS.items():
        count = progress.count(outcome)
        if count:
            print(f"{bright(label + ':')} {count} ({percent(count, progress.total):.1f}%)")
    for address_filter in collector.filters:
        if address_filter.rejected:
            print(f"{bright(address_filter.label + ':')} {address_filter.rejected} ({percent(address_filter.rejected, found):.1f}%)")
