import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "platforms"
TARGET_DIR = PROJECT_ROOT / "platforms_apex"
TWO_LEVEL_TLDS = frozenset({
    "co.uk", "co.jp", "co.kr", "co.nz", "co.za", "co.il", "co.in",
    "com.au", "com.br", "com.cn", "com.mx", "com.ar", "com.tr",
    "org.uk", "org.au", "ac.uk", "gov.uk", "net.au",
})


def extract_apex_domain(domain: str) -> str:
    parts = domain.lower().rstrip(".").split(".")
    size = 3 if len(parts) >= 3 and f"{parts[-2]}.{parts[-1]}" in TWO_LEVEL_TLDS else 2
    return ".".join(parts[-size:])


def process_file(source: Path, target: Path) -> int:
    with source.open(encoding="utf-8-sig") as file:
        apex_domains = {extract_apex_domain(fields[0]) for fields in map(str.split, file) if fields and not fields[0].startswith("#")}
    apex_domains.discard("")
    target.write_text("".join(f"{domain}\n" for domain in sorted(apex_domains)), encoding="utf-8")
    return len(apex_domains)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sources = sorted(SOURCE_DIR.glob("*.txt"))
    if not sources:
        print(f"В папке {SOURCE_DIR} не найдено txt-файлов")
        return
    TARGET_DIR.mkdir(exist_ok=True)
    print(f"Найдено {len(sources)} txt-файлов для обработки")
    print(f"Результаты будут сохранены в: {TARGET_DIR}\n")
    for source in sources:
        try:
            count = process_file(source, TARGET_DIR / source.name)
        except (OSError, UnicodeDecodeError) as error:
            print(f"Ошибка при обработке {source}: {error}")
            continue
        print(f"✓ {source.name}: {count} уникальных apex-доменов")
    print(f"\nГотово! Обработано {len(sources)} файлов")
    print(f"Результаты сохранены в папке: {TARGET_DIR}")


if __name__ == "__main__":
    main()
