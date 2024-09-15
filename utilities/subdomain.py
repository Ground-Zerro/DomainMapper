import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup


def parse_page(url):
    for attempt in range(5):  # До 5 попыток для одной страницы
        try:
            response = requests.get(url)
            if response.status_code == 404:  # Проверка на несуществующую страницу
                return None
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            data = set()  # Используем множество для уникальных доменов
            rows = soup.select('table tbody tr')

            if not rows:  # Если на странице нет строк, возвращаем None
                return None

            for row in rows:
                columns = row.find_all('td')
                if len(columns) > 3 and columns[2].text.strip() == 'A':  # Проверка на тип записи 'A'
                    domain = columns[0].text.strip()  # Извлечение столбца 'Domain'
                    data.add(domain)  # Добавляем в множество

            time.sleep(random.uniform(1, 3))  # Задержка между запросами
            return data

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print(f"Ошибка загрузки {url}. Пробуем еще раз...")
                time.sleep(3)  # Фиксированная задержка перед повторной попыткой
            else:
                raise e


def parse_all_pages(base_url):
    all_domains = set()  # Используем множество для уникальных доменов
    page = 1  # Всегда начинаем с первой страницы
    keep_parsing = True

    empty_page_attempts = 0  # Счётчик пустых страниц
    recent_pages_data = []  # Список для хранения данных последних страниц

    while keep_parsing:
        print(f"Парсим страницы с {page} по {page + 2}")
        pages = [f"{base_url}?page={p}" for p in range(page, page + 3)]

        try:
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_url = {executor.submit(parse_page, url): url for url in pages}
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        if result is None:  # Если страница пуста или не существует
                            print(f"Страница {url.split('=')[-1]} не существует или пуста. Проверяем еще раз...")
                            empty_page_attempts += 1
                            time.sleep(3)  # Ожидание перед повторной проверкой
                            if empty_page_attempts >= 3:
                                print(f"Страница {url.split('=')[-1]} пуста после 3 попыток. Остановка.")
                                keep_parsing = False
                                break
                            else:
                                continue  # Переходим к следующей попытке
                        else:
                            empty_page_attempts = 0  # Обнуляем счётчик, если нашли данные
                            all_domains.update(result)  # Добавляем новые домены в множество
                            print(f"Разбор {url} завершен.")

                            # Добавляем данные страницы в список для сравнения
                            recent_pages_data.append(result)
                            if len(recent_pages_data) > 3:  # Храним данные только последних 3 страниц
                                recent_pages_data.pop(0)

                            # Проверяем, повторяются ли данные на последних трёх страницах
                            if len(recent_pages_data) == 3 and recent_pages_data[0] == recent_pages_data[1] == recent_pages_data[2]:
                                print(f"Данные на последних трёх страницах одинаковы. Остановка парсинга.")
                                keep_parsing = False
                                break
                    except Exception as e:
                        print(f"Ошибка парсинга {url}: {e}")
                        raise e
        except requests.exceptions.HTTPError as e:
            if '429' in str(e):
                print("Ошибка 429. Пауза 4 секунды.")
                time.sleep(3)  # Пауза 3 секунды при ошибке 429
            else:
                raise e  # Пробрасываем другие ошибки, если они не 429

        page += 3  # Переход к следующему набору страниц

    return all_domains


def get_subdomain_url():
    base_url = 'https://rapiddns.io/subdomain/{url}'
    url = input("Введите URL: ")
    full_url = base_url.format(url=url)
    return full_url  # Возвращаем полный URL


base_url = get_subdomain_url()  # Вызов функции для получения полного URL

domains = parse_all_pages(base_url)

# Запись результата в файл
with open('result.txt', 'w') as file:
    for domain in sorted(domains):  # Сортируем домены перед записью
        file.write(f"{domain}\n")

print(f"Найдено {len(domains)} A записей. \nРезультаты сохранены в result.txt.")
