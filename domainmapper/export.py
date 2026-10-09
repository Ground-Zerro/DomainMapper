from collections.abc import Collection, Mapping
from pathlib import Path

from .aggregation import choose_aggregation
from .console import bright
from .formats import choose_format


def export(addresses: Collection[int], path: Path, aggregation_key: str, format_key: str, values: Mapping[str, str]) -> None:
    aggregation = choose_aggregation(aggregation_key)
    print(f"{bright('Агрегация IP-адресов:')} {aggregation.title}")
    route_format = choose_format(format_key, aggregation.placeholders(), values)
    lines = route_format.render(aggregation.apply(addresses), route_format.complete(values))
    files = route_format.write(path, lines)
    if len(files) == 1:
        print(f"\n{bright('Результаты сохранены в файл:')} {files[0][0]}")
        return
    print(f"\n{bright('Результаты сохранены в файлы:')}")
    for part, count in files:
        print(f"{bright(part)} ({count} строк)")
