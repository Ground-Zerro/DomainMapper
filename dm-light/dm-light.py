import glob
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import dns.resolver

# Сброс счетчиков, объявление переменных
successful_resolutions = 0
failed_resolutions = 0
unresolved_domains = set()
unresolved_domains_file_name = "unresolved_domains.txt"  # Имя файла с необработанными доменами
result_file_name = "result.txt"  # Имя файла результатов
domain_files_pattern = "domain/*.txt"  # Имя папки с txt файлами DNS
pub_dns_primary = "8.8.8.8"  # Публичный DNS № 1
pub_dns_secondary = "8.8.4.4"  # Публичный DNS № 2
max_requests = 20  # Максимальное число запросов к DNS


# Постобработка файла вывода
def post_process_output(input_file, output_file):
    unique_addresses = set()
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for line in lines:
            ip_address = line.strip()  # удаление повторов IP адресов
            if ip_address not in unique_addresses:
                unique_addresses.add(ip_address)
                f.write(
                    f"route add {ip_address} mask 255.255.255.255 0.0.0.0\n")  # Запись результатов в заданном формате


# Функция записи необработанных доменов в файл
def write_unresolved_domains(unresolved_domains):
    with open(unresolved_file, 'w', encoding='utf-8-sig') as f:
        for domain in unresolved_domains:
            f.write(domain + '\n')


# Функция записи IP обработанных доменов в файл
def write_resolved_ip(resolved_ips):
    with open(result_file, 'w', encoding='utf-8-sig') as f:
        for ip_address in resolved_ips:
            f.write(ip_address + '\n')


# Функция для контроля числа запросов
class RateLimitedResolver:
    def __init__(self, primary_dns, secondary_dns, max_requests):
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = [primary_dns, secondary_dns]
        self.max_requests = max_requests
        self.request_count = 0
        self.lock = threading.Lock()

    def resolve(self, domain):
        with self.lock:
            if self.request_count >= self.max_requests:
                print("Достигнуто максимальное число запросов, приостановка выполнения.")
                time.sleep(1)  # Пауза перед следующим запросом
                self.request_count = 0  # Сброс счетчика после паузы
            self.request_count += 1

        try:
            answers = self.resolver.resolve(domain, 'A')
            return [rdata.address for rdata in answers]
        except Exception as e:
            print(f"Ошибка при разрешении домена {domain}: {e}")
            return None


# Функция разрешения DNS-имени с использованием заданного DNS-сервера
def resolve_dns(domain, rate_limited_resolver):
    global successful_resolutions, failed_resolutions, unresolved_domains
    ip_addresses = []  # Изменение на список для хранения нескольких IP-адресов
    try:
        ip_addresses = rate_limited_resolver.resolve(domain)
        if ip_addresses:
            successful_resolutions += 1
            print(f"{domain} IP адрес(а): {', '.join(ip_addresses)}")
        else:
            failed_resolutions += 1
            unresolved_domains.add(domain)
            print(f"Не удалось обработать домен: {domain}")
    except Exception as e:
        failed_resolutions += 1
        unresolved_domains.add(domain)
        print(f"Не удалось обработать домен: {domain}, Ошибка: {e}")
    return (domain, ip_addresses)  # Возвращаем кортеж


# Основная
def resolve_dns_in_threads(domain_files, result_file, num_threads=20):
    global successful_resolutions, failed_resolutions, unresolved_domains
    resolved_ips = set()  # Создание множества для хранения IP обработанных доменов

    rate_limited_resolver = RateLimitedResolver(pub_dns_primary, pub_dns_secondary, max_requests)

    # Выполнение резолва в нескольких потоках
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for domain_file in domain_files:
            if os.path.isfile(domain_file):
                with open(domain_file, 'r', encoding='utf-8-sig') as f:
                    domains = [line.strip() for line in f]
                for domain in domains:
                    futures.append(executor.submit(resolve_dns, domain, rate_limited_resolver))

        # Обработка результатов
        with open(result_file, 'a', encoding='utf-8-sig') as result_f:
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    domain, ip_addresses = result
                    if ip_addresses:
                        resolved_ips.update(ip_addresses)  # Добавление всех IP-адресов в множество
                        for ip_address in ip_addresses:
                            result_f.write(f"{domain} IP адрес: {ip_address}\n")  # Запись каждого IP-адреса
                    else:
                        unresolved_domains.add(domain)  # Добавление необработанных доменов в множество

    # Запись множеств в соответствующие файлы
    write_resolved_ip(resolved_ips)  # Запись IP обработанных доменов в файл
    write_unresolved_domains(unresolved_domains)  # Запись необработанных доменов в файл
    post_process_output(result_file, result_file)  # Вызов функции постобработки файла результатов

    print(f"\nСопоставлено IP адресов доменам: {successful_resolutions}")
    print(f"Не удалось обработать доменных имен: {failed_resolutions}")
    if os.name == 'nt':  # Для пользователей Windows при запуске из проводника
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.abspath(__file__))  # Получение пути к директории с исполняемым файлом
    result_file = os.path.join(script_directory, result_file_name)  # Формирование пути к файлу результатов
    unresolved_file = os.path.join(script_directory,
                                   unresolved_domains_file_name)  # Формирование пути к файлу с необработанными доменами
    domain_files = glob.glob(
        os.path.join(script_directory, domain_files_pattern))  # Создание списка txt файлов в директории "domain"
    resolve_dns_in_threads(domain_files, result_file)  # Вызов основной функции
