import random
import sys
import time
from collections import deque
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://rapiddns.io/subdomain/{domain}"
TARGET = Path("result.txt")
ATTEMPTS = 5
EMPTY_PAGE_LIMIT = 3
REPEATED_PAGE_LIMIT = 3
RETRY_DELAY = 5
PAGE_DELAYS = (2, 3, 4, 5)
REQUEST_TIMEOUT = 30
NOT_FOUND = 404
TOO_MANY_REQUESTS = 429


def parse_page(session: requests.Session, url: str) -> set[str] | None:
    for attempt in range(1, ATTEMPTS + 1):
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == NOT_FOUND:
            return None
        if response.status_code == TOO_MANY_REQUESTS:
            print(f"Ошибка загрузки {url}. Пробуем еще раз... (Попытка {attempt})")
            time.sleep(RETRY_DELAY)
            continue
        response.raise_for_status()
        rows = BeautifulSoup(response.text, "html.parser").select("table tbody tr")
        if not rows:
            return None
        time.sleep(random.choice(PAGE_DELAYS))
        if attempt > 1:
            print(f"Успешная загрузка {url} после {attempt}-й попытки.")
        return {
            columns[0].text.strip()
            for columns in (row.find_all("td") for row in rows)
            if len(columns) > 3 and columns[2].text.strip() == "A"
        }
    raise RuntimeError(f"Не удалось загрузить {url} за {ATTEMPTS} попыток")


def parse_all_pages(base_url: str) -> set[str]:
    domains: set[str] = set()
    recent: deque[set[str]] = deque(maxlen=REPEATED_PAGE_LIMIT)
    empty_pages = 0
    page = 1
    with requests.Session() as session:
        while True:
            print(f"Парсим страницу {page}")
            result = parse_page(session, f"{base_url}?page={page}")
            if result is None:
                empty_pages += 1
                if empty_pages >= EMPTY_PAGE_LIMIT:
                    print(f"Страница {page} пуста после {EMPTY_PAGE_LIMIT} попыток. Остановка.")
                    return domains
                print(f"Страница {page} не существует или пуста. Проверяем еще раз...")
                time.sleep(RETRY_DELAY)
                continue
            empty_pages = 0
            domains.update(result)
            print(f"Разбор страницы {page} завершен.")
            recent.append(result)
            if len(recent) == REPEATED_PAGE_LIMIT and all(item == recent[0] for item in recent):
                print("Данные на последних трёх страницах одинаковы. Остановка парсинга.")
                return domains
            page += 1


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    domains = parse_all_pages(BASE_URL.format(domain=input("Введите URL: ").strip()))
    TARGET.write_text("".join(f"{domain}\n" for domain in sorted(domains)), encoding="utf-8")
    print(f"Найдено {len(domains)} A записей. \nРезультаты сохранены в {TARGET}.")


if __name__ == "__main__":
    main()
