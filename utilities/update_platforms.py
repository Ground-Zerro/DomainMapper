import asyncio
import re
import sys
from collections.abc import Iterator, Sequence
from itertools import product
from pathlib import Path
from re import _constants as sre
from re import _parser

import httpx

from domainmapper.catalog import Catalog, http_client
from domainmapper.console import green, red, yellow
from domainmapper.files import PROJECT_ROOT, read_text

TAG_MAP = "platformtags"
SOURCES = (
    "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat",
    "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat",
)
EXCLUDED_REGIONS = frozenset({"cn", "hk", "mo", "tw", "jp"})
HOSTNAME = re.compile(r"[a-z0-9_-]+(?:\.[a-z0-9_-]+)+")
REGEX_VARIANTS_LIMIT = 256
REGEX_SUFFIX_MIN_LABELS = 3
VARINT = 0
LENGTH_DELIMITED = 2
ENTRY_FIELD = 1
CODE_FIELD = 1
DOMAIN_FIELD = 2
TYPE_FIELD = 1
VALUE_FIELD = 2
ATTRIBUTE_FIELD = 3
ATTRIBUTE_KEY_FIELD = 1
REGEX_TYPE = 1
ROOT_DOMAIN_TYPE = 2
FULL_TYPE = 3


def hostname(raw: str) -> str | None:
    name = raw.strip().lower().strip(".")
    return name if HOSTNAME.fullmatch(name) else None


def foreign_hostname(raw: str) -> str | None:
    name = hostname(raw)
    return name if name and name.rsplit(".", 1)[1] not in EXCLUDED_REGIONS else None


def read_varint(data: memoryview, position: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = data[position]
        position += 1
        result |= (byte & 0x7F) << shift
        if byte < 0x80:
            return result, position
        shift += 7


def fields(data: memoryview) -> Iterator[tuple[int, int | memoryview]]:
    position, end = 0, len(data)
    while position < end:
        key, position = read_varint(data, position)
        wire_type = key & 7
        if wire_type == VARINT:
            value, position = read_varint(data, position)
            yield key >> 3, value
        elif wire_type == LENGTH_DELIMITED:
            size, position = read_varint(data, position)
            yield key >> 3, data[position:position + size]
            position += size
        else:
            raise ValueError(f"неподдерживаемый тип поля protobuf: {wire_type}")


class RegexHosts:
    def __init__(self, limit: int):
        self._limit = limit

    def __call__(self, pattern: str) -> list[str]:
        try:
            items = list(_parser.parse(pattern))
        except re.error:
            return []
        return self._sequence(items) or [self._literal_suffix(items)]

    def _sequence(self, items: Sequence[tuple]) -> list[str] | None:
        variants = [""]
        for op, argument in items:
            options = self._item(op, argument)
            if options is None or len(variants) * len(options) > self._limit:
                return None
            variants = [head + tail for head, tail in product(variants, options)]
        return variants

    def _item(self, op, argument) -> list[str] | None:
        if op is sre.LITERAL:
            return [chr(argument)]
        if op is sre.AT:
            return [""]
        if op is sre.IN:
            return self._charset(argument)
        if op is sre.SUBPATTERN:
            return self._sequence(list(argument[-1]))
        if op is sre.BRANCH:
            return self._branch(argument[1])
        if op in (sre.MAX_REPEAT, sre.MIN_REPEAT):
            return self._repeat(*argument)
        return None

    def _charset(self, members: Sequence[tuple]) -> list[str] | None:
        chars: list[str] = []
        for op, argument in members:
            if op is sre.LITERAL:
                chars.append(chr(argument))
            elif op is sre.RANGE:
                chars.extend(map(chr, range(argument[0], argument[1] + 1)))
            else:
                return None
        return chars if len(chars) <= self._limit else None

    def _branch(self, alternatives: Sequence) -> list[str] | None:
        variants: list[str] = []
        for alternative in alternatives:
            options = self._sequence(list(alternative))
            if options is None:
                return None
            variants.extend(options)
        return variants if len(variants) <= self._limit else None

    def _repeat(self, low: int, high: int, body) -> list[str] | None:
        if high == sre.MAXREPEAT:
            return None
        options = self._sequence(list(body))
        if options is None:
            return None
        variants: list[str] = []
        for count in range(low, high + 1):
            variants.extend("".join(parts) for parts in product(options, repeat=count))
            if len(variants) > self._limit:
                return None
        return variants

    @staticmethod
    def _literal_suffix(items: Sequence[tuple]) -> str:
        chars: list[str] = []
        for op, argument in reversed(items):
            if op is sre.AT and not chars:
                continue
            if op is not sre.LITERAL:
                break
            chars.append(chr(argument))
        suffix = "".join(reversed(chars))
        suffix = suffix[suffix.find(".") + 1:]
        return suffix if suffix.count(".") + 1 >= REGEX_SUFFIX_MIN_LABELS else ""


class GeoSite:
    def __init__(self, tags: frozenset[str]):
        self.domains: dict[str, set[str]] = {tag: set() for tag in tags}
        self._regex_hosts = RegexHosts(REGEX_VARIANTS_LIMIT)

    def load(self, data: bytes) -> None:
        for field, entry in fields(memoryview(data)):
            if field != ENTRY_FIELD:
                continue
            target = self.domains.get(self._code(entry))
            if target is not None:
                self._collect(entry, target)

    @staticmethod
    def _code(entry: memoryview) -> str:
        for field, value in fields(entry):
            if field == CODE_FIELD:
                return bytes(value).decode().lower()
        return ""

    def _collect(self, entry: memoryview, target: set[str]) -> None:
        for field, rule in fields(entry):
            if field == DOMAIN_FIELD:
                target.update(filter(None, map(foreign_hostname, self._rule_hosts(rule))))

    def _rule_hosts(self, rule: memoryview) -> list[str]:
        rule_type, value = 0, ""
        for field, content in fields(rule):
            if field == TYPE_FIELD:
                rule_type = content
            elif field == VALUE_FIELD:
                value = bytes(content).decode()
            elif field == ATTRIBUTE_FIELD and self._attribute_key(content) in EXCLUDED_REGIONS:
                return []
        if rule_type in (ROOT_DOMAIN_TYPE, FULL_TYPE):
            return [value]
        if rule_type == REGEX_TYPE:
            return self._regex_hosts(value)
        return []

    @staticmethod
    def _attribute_key(attribute: memoryview) -> str:
        for field, value in fields(attribute):
            if field == ATTRIBUTE_KEY_FIELD:
                return bytes(value).decode().lower()
        return ""


def merge_platform(path: Path, domains: set[str]) -> tuple[int, int]:
    original = read_text(path) if path.is_file() else ""
    current = set(filter(None, map(hostname, original.splitlines())))
    merged = current | domains
    text = "".join(f"{name}\n" for name in sorted(merged))
    if text != original:
        path.write_text(text, encoding="utf-8", newline="\n")
    return len(merged - current), len(merged)


async def download(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as error:
        print(red(f"Ошибка загрузки {url}: {error}"))
        return None
    return response.content


async def update() -> int:
    async with http_client() as client:
        mapping = await Catalog(client).entries(TAG_MAP, local=True)
        platforms = {location: [tag.strip().lower() for tag in tags.split(",") if tag.strip()] for location, tags in mapping.items()}
        geosite = GeoSite(frozenset(tag for tags in platforms.values() for tag in tags))
        sources = await asyncio.gather(*(download(client, url) for url in SOURCES))
    loaded = 0
    for url, data in zip(SOURCES, sources):
        if data is None:
            continue
        try:
            geosite.load(data)
        except (ValueError, IndexError, UnicodeDecodeError) as error:
            print(red(f"Ошибка разбора {url}: {error}"))
            continue
        loaded += 1
    if not loaded:
        print(red("Ни один источник не загружен - списки не изменены."))
        return 1
    for tag, domains in sorted(geosite.domains.items()):
        if not domains:
            print(yellow(f"Тег {tag} не найден в источниках."))
    for location, tags in platforms.items():
        domains = set().union(*(geosite.domains[tag] for tag in tags))
        added, total = merge_platform(PROJECT_ROOT / location, domains)
        print(f"{location}: {green(f'+{added}') if added else '+0'} (всего {total})")
    return 0


def main() -> None:
    sys.exit(asyncio.run(update()))


if __name__ == "__main__":
    main()
