import asyncio
import configparser
import ipaddress
import os
import re
from asyncio import Semaphore
from collections import defaultdict

import dns.asyncresolver
import httpx
from colorama import Fore, Style
from colorama import init

# Цвета
init(autoreset=True)
def yellow(text):
    return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"

def green(text):
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}"

def cyan(text):
    return f"{Fore.CYAN}{text}{Style.RESET_ALL}"

def red(text):
    return f"{Fore.RED}{text}{Style.RESET_ALL}"


# Читаем конфигурацию
def read_config(filename):
    try:
        config = configparser.ConfigParser()
        with open(filename, 'r', encoding='utf-8-sig') as file:
            config.read_file(file)
        if 'DomainMapper' in config:
            config = config['DomainMapper']
        service = config.get('service') or ''
        request_limit = int(config.get('threads') or 20)
        filename = config.get('filename') or 'domain-ip-resolve.txt'
        cloudflare = config.get('cloudflare') or ''
        filetype = config.get('filetype') or ''
        gateway = config.get('gateway') or ''
        run_command = config.get('run') or ''
        dns_server_indices = list(map(int, config.get('dnsserver', '').split())) if config.get('dnsserver') else []

        print(f"{yellow('Загружена конфигурация из config.ini:')}")
        print(f"Сервисы для проверки: {service if service else 'не указаны'}")
        print(f"Использовать DNS сервер: {dns_server_indices if dns_server_indices else 'не указано'}")
        print(f"Количество потоков: {request_limit}")
        print(f"Фильтр Cloudflare: {'включен' if cloudflare == 'yes' else 'выключен' if cloudflare == 'no' else 'не указано'}")
        print(f"Файл результатов: {filename}")
        print(f"Формат сохранения: {'только IP' if filetype == 'ip' else 'Linux route' if filetype == 'unix' else 'CIDR-нотация' if filetype == 'cidr' else 'Windows route' if filetype == 'win' else 'не указан'}")
        print(f"Шлюз для маршрутов: {gateway if gateway else 'не указан'}")
        print(f"Выполнить по завершению: {run_command if run_command else 'не указано'}")
        return service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices

    except Exception as e:
        print(f"{yellow('Ошибка загрузки config.ini:')} {e}\nИспользуются настройки 'по умолчанию'.")
        return '', 20, 'domain-ip-resolve.txt', '', '', '', '', []


def gateway_input(gateway):
    if not gateway:
        input_gateway = input(f"Укажите {green('шлюз')} или {green('имя интерфейса')}: ")
        if input_gateway:
            return input_gateway.strip()
    else:
        return gateway


# Ограничение числа запросов
def get_semaphore(request_limit):
    return defaultdict(lambda: Semaphore(request_limit))


# Инициализация semaphore для ограничения запросов
def init_semaphores(request_limit):
    return get_semaphore(request_limit)


async def load_urls(url):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            text = response.text
            lines = text.split('\n')
            urls = {}
            for line in lines:
                if line.strip():
                    service, url = line.split(': ', 1)
                    urls[service.strip()] = url.strip()
            return urls
    except Exception as e:
        print(f"Ошибка при загрузке списка платформ: {e}")
        return {}


# Загрузка списка DNS серверов
async def load_dns_servers(url):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            text = response.text
            lines = text.split('\n')
            dns_servers = {}
            for line in lines:
                if line.strip():
                    service, servers = line.split(': ', 1)
                    dns_servers[service.strip()] = servers.strip().split()
            return dns_servers
    except Exception as e:
        print(f"Ошибка при загрузке списка DNS серверов: {e}")
        return {}


# Загрузка IP-адресов cloudflare
async def get_cloudflare_ips():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://www.cloudflare.com/ips-v4/")
            response.raise_for_status()
            text = response.text
            cloudflare_ips = set()
            cidr_blocks = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})', text)
            for cidr in cidr_blocks:
                ip_network = ipaddress.ip_network(cidr)
                for ip in ip_network:
                    cloudflare_ips.add(str(ip))
            return cloudflare_ips
    except Exception as e:
        print("Ошибка при получении IP адресов Cloudflare:", e)
        return set()


async def resolve_domain(domain, resolver, semaphore, dns_server_name, null_ips_count, cloudflare_ips,
                         cloudflare_ips_count):
    async with semaphore:
        try:
            response = await resolver.resolve(domain)
            ips = [ip.address for ip in response]
            for ip_address in ips:
                if ip_address in ('127.0.0.1', '0.0.0.0') or ip_address in resolver.nameservers:
                    null_ips_count[0] += 1
                elif ip_address in cloudflare_ips:
                    cloudflare_ips_count[0] += 1
                else:
                    print(f"{Fore.CYAN}{domain} IP-адрес: {ip_address} - {dns_server_name}{Style.RESET_ALL}")
            return ips
        except Exception as e:
            print(f"{Fore.RED}Не удалось получить IP-адрес: {domain} - {dns_server_name}{Style.RESET_ALL}")
            return []


async def resolve_dns(service, dns_names, dns_servers, cloudflare_ips, unique_ips_all_services, semaphore, null_ips_count,
                      cloudflare_ips_count):
    try:
        print(f"{Fore.YELLOW}Анализ DNS имен платформы {service}...{Style.RESET_ALL}")

        tasks = []
        for server_name, servers in dns_servers:
            resolver = dns.asyncresolver.Resolver()
            resolver.nameservers = servers
            for domain in dns_names:
                domain = domain.strip()
                if domain:
                    tasks.append(resolve_domain(domain, resolver, semaphore[server_name], server_name, null_ips_count,
                                                cloudflare_ips, cloudflare_ips_count))

        results = await asyncio.gather(*tasks)

        unique_ips_current_service = set()
        for result in results:
            for ip_address in result:
                if ip_address not in unique_ips_all_services:
                    unique_ips_current_service.add(ip_address)
                    unique_ips_all_services.add(ip_address)

        return '\n'.join(unique_ips_current_service) + '\n'
    except Exception as e:
        print(f"Не удалось сопоставить IP адреса {service} его доменным именам.", e)
        return ""


def check_service_config(service, urls, local_dns_names):
    if service:
        if service.strip().lower() == "all":
            services = list(urls.keys())
            if local_dns_names:
                services.append("Мой список DNS")
            return services
        else:
            return [s.strip() for s in service.split(',')]
    else:
        selected_services = []
        while True:
            print(f"\n{yellow('Выберите сервисы:')}")
            print("0. Выбрать все")
            for idx, (service, url) in enumerate(urls.items(), 1):
                print(f"{idx}. {service.capitalize()}")
            if local_dns_names:
                print(f"{len(urls) + 1}. Мой список DNS")

            selection = input(f"\nУкажите номера сервисов через пробел и нажмите {green('Enter')}: ")
            if selection.strip():
                selections = selection.split()
                if '0' in selections:  # User selected all services
                    selected_services = list(urls.keys())
                    if local_dns_names:
                        selected_services.append('Мой список DNS')
                    break
                else:
                    selected_services = [list(urls.keys())[int(sel) - 1] for sel in selections if sel.isdigit()
                                         and 1 <= int(sel) <= len(urls)]
                    if str(len(urls) + 1) in selections and local_dns_names:
                        selected_services.append('Мой список DNS')
                    break
        return selected_services


# Промт на исключение IP-адресов cloudflare
def check_include_cloudflare(cloudflare):
    if cloudflare.lower() == 'yes':
        return True
    elif cloudflare.lower() == 'no':
        return False
    else:
        return input(f"\nИсключить IP адреса Cloudflare из итогового списка? ({green('yes')} "
                     f"- исключить, ({green('Enter')} - оставить): ").strip().lower() == "yes"


def check_dns_servers(dns_servers, dns_server_indices):
    system_dns_servers = dns.asyncresolver.Resolver().nameservers
    selected_dns_servers = []

    dns_server_options = [('Системный DNS', system_dns_servers)] + list(dns_servers.items())

    if dns_server_indices:
        for idx in dns_server_indices:
            if 0 <= idx <= len(dns_server_options):
                selected_dns_servers.append((dns_server_options[idx][0], dns_server_options[idx][1]))
        return selected_dns_servers

    while True:
        print(f"\n{yellow('Какие DNS сервера использовать?')}")
        print("0. Выбрать все")
        for idx, (name, servers) in enumerate(dns_server_options, 1):
            print(f"{idx}. {name}: {', '.join(servers)}")

        selection = input(f"\nУкажите номера DNS серверов через пробел и нажмите {green('Enter')}: ")
        if selection.strip():
            selections = selection.split()
            if '0' in selections:
                selected_dns_servers = dns_server_options
                break
            else:
                for sel in selections:
                    if sel.isdigit():
                        sel = int(sel)
                        if 1 <= sel <= len(dns_server_options):
                            selected_dns_servers.append(
                                (dns_server_options[sel - 1][0], dns_server_options[sel - 1][1]))
                break

    return selected_dns_servers


# Выбор формата сохранения списка разрешенных DNS имен
def process_file_format(filename, filetype, gateway):
    if not filetype:
        filetype = input(f"\n{yellow('В каком формате сохранить файл?')}"
                         f"\n{green('win')} - route add IP mask MASK GATEWAY"
                         f"\n{green('unix')} - ip route IP/MASK GATEWAY"
                         f"\n{green('cidr')} - IP/MASK"
                         f"\n{green('Пустое значение')} - только IP"
                         f"\nВаш выбор: ")

    if filetype.lower() in ['win', 'unix']:
        gateway = gateway_input(gateway)

        try:
            with open(filename, 'r', encoding='utf-8-sig') as file:
                ips = file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return

        if ips:
            with open(filename, 'w', encoding='utf-8-sig') as file:
                for ip in ips:
                    if filetype.lower() == 'win':
                        file.write(f"route add {ip.strip()} mask 255.255.255.255 {gateway}\n")
                    elif filetype.lower() == 'unix':
                        file.write(f"ip route {ip.strip()}/32 {gateway}\n")
    elif filetype.lower() == 'cidr':
        try:
            with open(filename, 'r', encoding='utf-8-sig') as file:
                ips = file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return

        if ips:
            with open(filename, 'w', encoding='utf-8-sig') as file:
                for ip in ips:
                    file.write(f"{ip.strip()}/32\n")
    else:
        pass


# Ну чо, погнали?!
async def main():
    # Инициализация настроек из config.ini
    service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices = read_config('config.ini')

    # Load URLs
    platform_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platformdb"
    urls = await load_urls(platform_db_url)

    # Load local DNS names from "my-dns-list.txt" if it exists
    local_dns_names = []
    if os.path.exists('my-dns-list.txt'):
        with open('my-dns-list.txt', 'r', encoding='utf-8-sig') as file:
            local_dns_names = [line.strip() for line in file if line.strip()]

    # Выбор сервисов
    selected_services = check_service_config(service, urls, local_dns_names)

    # Загрузка списка DNS-серверов
    dns_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/dnsdb"
    dns_servers = await load_dns_servers(dns_db_url)

    # Выбор DNS-серверов
    selected_dns_servers = check_dns_servers(dns_servers, dns_server_indices)

    # Инициализация IP-адресов Cloudflare
    cloudflare_ips = await get_cloudflare_ips()


    # Фильтр Cloudflare
    include_cloudflare = check_include_cloudflare(cloudflare)

    unique_ips_all_services = set()
    semaphore = init_semaphores(request_limit)
    null_ips_count = [0]
    cloudflare_ips_count = [0]
    tasks = []

    for service in selected_services:
        if service == 'Мой список DNS':
            tasks.append(resolve_dns(service, local_dns_names, selected_dns_servers, cloudflare_ips, unique_ips_all_services,
                                     semaphore, null_ips_count, cloudflare_ips_count))
        else:
            # Загрузка DNS имен сервисов
            dns_names_url = urls[service]
            async with httpx.AsyncClient() as client:
                response = await client.get(dns_names_url)
                response.raise_for_status()
                dns_names = response.text.splitlines()
            tasks.append(resolve_dns(service, dns_names, selected_dns_servers, cloudflare_ips, unique_ips_all_services,
                                     semaphore, null_ips_count, cloudflare_ips_count))

    results = await asyncio.gather(*tasks)

    with open(filename, 'w', encoding='utf-8-sig') as file:
        for result in results:
            file.write(result)

    print(f"\n{yellow('Проверка завершена.')}")
    print("Использовались DNS сервера: " + ', '.join(
        [f'{pair[0]} ({", ".join(pair[1])})' for pair in selected_dns_servers]))
    if include_cloudflare:
        print(f"Исключено IP-адресов Cloudflare: {cloudflare_ips_count[0]}")
    print(f"Исключено IP-адресов 'заглушек': {null_ips_count[0]}")
    print(f"Разрешено IP-адресов из DNS имен: {len(unique_ips_all_services)}")

    process_file_format(filename, filetype, gateway)

    if run_command:
        print("\nВыполнение команды после завершения скрипта...")
        os.system(run_command)
    else:
        print("\nРезультаты сохранены в файл:", filename)
        if os.name == 'nt':
            input(f"Нажмите {green('Enter')} для выхода...")


if __name__ == "__main__":
    asyncio.run(main())