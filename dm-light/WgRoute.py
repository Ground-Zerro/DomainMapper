import dns.resolver
import os
from concurrent.futures import ThreadPoolExecutor
import glob

routerconf = "work.conf"

# Сброс счетчиков, объявление переменных
successful_resolutions = 0
failed_resolutions = 0
unresolved_domains_file_name = "unresolved_domains.txt"  # Имя файла с необработанными доменами
result_file_name = "result.txt"  # Имя файла результатов
domain_files_pattern = "domain/*.txt"  # Имя папки с txt файлами DNS
pub_dns = "8.8.8.8"  # Публичный DNS № 1


# Функция записи разрешенных IP-адресов в файл .conf
def write_allowed_ips(resolved_ips):
    # Открываем файл routerconf для чтения и чтения содержимого
    with open(routerconf, 'r') as f:
        lines = f.readlines()

    # Находим строку с "AllowedIPs = " и удаляем имеющиеся IP-адреса после нее
    for i, line in enumerate(lines):
        if line.startswith("AllowedIPs = "):
            ips = ", ".join(resolved_ips) + "/32\n"
            lines[i] = "AllowedIPs = " + ips
            break

    # Записываем обновленное содержимое в файл
    with open(routerconf, 'w') as f:
        f.writelines(lines)


# Функция разрешения DNS-имени с использованием заданного DNS-сервера
def resolve_dns(domain):
    global successful_resolutions, failed_resolutions
    ip_addresses = []  # Изменение на список для хранения нескольких IP-адресов
    try:
        answers = dns.resolver.resolve(domain, 'A')
        for rdata in answers:
            ip_address = rdata.address
            successful_resolutions += 1
            print(f"{domain} IP адрес: {ip_address}")
            ip_addresses.append(ip_address)  # Добавление IP-адреса в список
        return domain, ip_addresses  # Возвращаем домен и список IP-адресов
    except dns.resolver.NXDOMAIN:
        failed_resolutions += 1
        print(f"Не удалось обработать домен: {domain}, Не существует")
        return None, None
    except dns.resolver.NoAnswer:
        failed_resolutions += 1
        print(f"Не удалось обработать домен: {domain}, Нет ответа")
        return None, None
    except dns.resolver.Timeout:
        failed_resolutions += 1
        print(f"Не удалось обработать домен: {domain}, Тайм-аут")
        return None, None


# Основная
def resolve_dns_in_threads(domain_files, num_threads=20):
    global successful_resolutions, failed_resolutions
    resolved_ips = set()  # Создание множества для хранения IP обработанных доменов

    # Выполнение резолва в нескольких потоках
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for domain_file in domain_files:
            if os.path.isfile(domain_file):
                with open(domain_file, 'r', encoding='utf-8-sig') as f:
                    domains = [line.strip() for line in f]
                for domain in domains:
                    future = executor.submit(resolve_dns, domain)
                    futures.append(future)

        for future in futures:
            domain, ip_addresses = future.result()
            if ip_addresses:
                resolved_ips.update(ip_addresses)  # Добавление всех IP-адресов в множество

    # Запись разрешенных IP-адресов в файл routerconf
    write_allowed_ips(resolved_ips)  # Запись разрешенных IP-адресов в файл routerconf

    print(f"\nСопоставлено IP адресов доменам:", successful_resolutions)
    print(f"Не удалось обработать доменных имен:", failed_resolutions)


if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.abspath(__file__))  # Получение пути к директории с исполняемым файлом
    domain_files = glob.glob(os.path.join(script_directory, domain_files_pattern))  # Создание списка txt файлов в директории "domain"
    resolve_dns_in_threads(domain_files)  # Вызов основной функции
