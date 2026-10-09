import configparser
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .aggregation import AGGREGATIONS, NO_AGGREGATION
from .console import bright, red, yellow
from .files import read_text
from .formats import FORMATS, LIST_NAME, PARAMETERS

SECTION = "DomainMapper"
DEFAULT_RATE_LIMIT = 100
DEFAULT_TOTAL_RATE_LIMIT = 200
DEFAULT_FILENAME = "domain-ip-resolve.txt"
ASK = "спросить у пользователя"
YES = frozenset({"yes", "y", "on"})
NO = frozenset({"no", "n", "off"})
AGGREGATION_ALIASES = {**{key: key for key in AGGREGATIONS}, "no": NO_AGGREGATION, "n": NO_AGGREGATION}
FORMAT_ALIASES = {key: key for key in FORMATS}


def flag(value: str) -> bool | None:
    value = value.lower()
    if value in YES:
        return True
    if value in NO:
        return False
    return None


def switch(enabled: bool, ending: str = "") -> str:
    return ("включен" if enabled else "выключен") + ending


class _Section:
    def __init__(self, section: configparser.SectionProxy):
        self._section = section

    def text(self, key: str) -> str:
        return self._section.get(key, "").strip()

    def known(self, key: str, aliases: Mapping[str, str]) -> str:
        value = self.text(key).lower()
        if value and value not in aliases:
            print(red(f"Неизвестное значение {key} = {value}: будет запрошено у пользователя."))
        return aliases.get(value, "")


@dataclass(frozen=True, slots=True)
class AppConfig:
    services: tuple[str, ...] = ()
    dns_servers: tuple[int, ...] = ()
    rate_limit: int = DEFAULT_RATE_LIMIT
    total_rate_limit: int = DEFAULT_TOTAL_RATE_LIMIT
    exclude_cloudflare: bool | None = None
    aggregation: str = ""
    filename: str = DEFAULT_FILENAME
    filetype: str = ""
    gateway: str = ""
    keenetic: str = ""
    listname: str = ""
    mikrotik_comment: bool = False
    local_platform: bool = False
    local_dns: bool = False
    run: str = ""

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read_string(read_text(path), str(path))
            section = _Section(parser[SECTION])
            config = cls._parse(section)
        except (OSError, KeyError, ValueError, configparser.Error) as error:
            print(f"{yellow(f'Ошибка загрузки {path}:')} {error}\n{bright('Используются настройки по умолчанию.')}")
            return cls()
        if flag(section.text("cfginfo") or "yes"):
            config.describe(path)
        return config

    @classmethod
    def _parse(cls, section: _Section) -> "AppConfig":
        return cls(
            services=tuple(name.strip().lower() for name in section.text("service").split(",") if name.strip()),
            dns_servers=tuple(map(int, section.text("dnsserver").split())),
            rate_limit=max(1, int(section.text("rate_limit") or DEFAULT_RATE_LIMIT)),
            total_rate_limit=max(1, int(section.text("total_rate_limit") or DEFAULT_TOTAL_RATE_LIMIT)),
            exclude_cloudflare=flag(section.text("cloudflare")),
            aggregation=section.known("subnet", AGGREGATION_ALIASES),
            filename=section.text("filename") or DEFAULT_FILENAME,
            filetype=section.known("filetype", FORMAT_ALIASES),
            gateway=section.text("gateway"),
            keenetic=section.text("keenetic"),
            listname=section.text("listname"),
            mikrotik_comment=flag(section.text("mk_comment")) is True,
            local_platform=flag(section.text("localplatform")) is True,
            local_dns=flag(section.text("localdns")) is True,
            run=section.text("run"),
        )

    def describe(self, path: Path) -> None:
        parameters = FORMATS[self.filetype].parameters if self.filetype else PARAMETERS
        rows = [
            ("Сервисы для проверки", ", ".join(self.services) or ASK),
            ("Использовать DNS сервер", " ".join(map(str, self.dns_servers)) or ASK),
            ("Лимит запросов к каждому DNS серверу (запросов/сек)", self.rate_limit),
            ("Общий лимит запросов ко всем DNS серверам (запросов/сек)", self.total_rate_limit),
            ("Фильтрация IP-адресов Cloudflare", ASK if self.exclude_cloudflare is None else switch(self.exclude_cloudflare, "а")),
            ("Агрегация IP-адресов", AGGREGATIONS[self.aggregation].title if self.aggregation else ASK),
            ("Формат сохранения", FORMATS[self.filetype].title if self.filetype else ASK),
            *((parameter.title, getattr(self, parameter.name) or ASK) for parameter in parameters),
        ]
        if LIST_NAME in parameters:
            rows.append(("'comment=' в Mikrotik firewall", switch(self.mikrotik_comment)))
        rows += [
            ("Сохранить результат в файл", self.filename),
            ("Выполнить по завершению", self.run or "не указано"),
            ("Локальный список платформ", switch(self.local_platform)),
            ("Локальный список DNS серверов", switch(self.local_dns)),
        ]
        print(yellow(f"Загружена конфигурация из {path}:"))
        for label, value in rows:
            print(f"{bright(label + ':')} {value}")
