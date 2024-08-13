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

def magneta(text):
    return f"{Fore.MAGENTA}{text}{Style.RESET_ALL}"

def blue(text):
    return f"{Fore.BLUE}{text}{Style.RESET_ALL}"

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
        mk_list_name = config.get('listname') or ''

        print(f"{yellow('Загружена конфигурация из config.ini:')}")
        print(f"{Style.BRIGHT}Сервисы для проверки:{Style.RESET_ALL} {service if service else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Использовать DNS сервер:{Style.RESET_ALL} {dns_server_indices if dns_server_indices else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Количество одновременных запросов к одному DNS серверу:{Style.RESET_ALL} {request_limit}")
        print(f"{Style.BRIGHT}Фильтр IP-адресов Cloudflare:{Style.RESET_ALL} {'включен' if cloudflare == 'yes' else 'выключен' if cloudflare == 'no' else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Сохранить результаты в файл:{Style.RESET_ALL} {filename}")
        print(f"{Style.BRIGHT}Формат сохранения:{Style.RESET_ALL} {'только IP' if filetype == 'ip' else 'Linux route' if filetype == 'unix' else 'CIDR-нотация' if filetype == 'cidr' else 'Windows route' if filetype == 'win' else 'CLI Mikrotik firewall' if filetype == 'mikrotik' else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Шлюз/Имя интерфейса для маршрутов:{Style.RESET_ALL} {gateway if gateway else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Имя списка для Mikrotik firewall:{Style.RESET_ALL} {mk_list_name if mk_list_name else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Выполнить по завершению:{Style.RESET_ALL} {run_command if run_command else 'не указано'}")
        return service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices, mk_list_name

    except Exception as e:
        print(f"{yellow('Ошибка загрузки config.ini:')} {e}\n{Style.BRIGHT}Используются настройки 'по умолчанию'.{Style.RESET_ALL}")
        return '', 20, 'domain-ip-resolve.txt', '', '', '', '', [], ''


def gateway_input(gateway):
    if not gateway:
        input_gateway = input(f"Укажите {green('шлюз')} или {green('имя интерфейса')}: ")
        if input_gateway:
            return input_gateway.strip()
    else:
        return gateway

# Для microtik
def mk_list_name_input(mk_list_name):
    if not mk_list_name:
        input_mk_list_name = input(f"Введите {green('имя списка')} для firewall: ")
        if input_mk_list_name:
            return input_mk_list_name.strip()
    else:
        return mk_list_name


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


async def resolve_domain(domain, resolver, semaphore, dns_server_name, null_ips_count, cloudflare_ips, cloudflare_ips_count, total_domains_processed):
    async with semaphore:
        try:
            total_domains_processed[0] += 1
            response = await resolver.resolve(domain)
            ips = [ip.address for ip in response]
            for ip_address in ips:
                if ip_address in ('127.0.0.1', '0.0.0.0') or ip_address in resolver.nameservers:
                    null_ips_count[0] += 1
                elif ip_address in cloudflare_ips:
                    cloudflare_ips_count[0] += 1
                else:
                    print(f"{Fore.BLUE}{domain} IP-адрес: {ip_address} - {dns_server_name}{Style.RESET_ALL}")
            return ips
        except Exception as e:
            print(f"{Fore.RED}Не удалось получить IP-адрес: {domain} - {dns_server_name}{Style.RESET_ALL}")
            return []


async def resolve_dns(service, dns_names, dns_servers, cloudflare_ips, unique_ips_all_services, semaphore, null_ips_count, cloudflare_ips_count, total_domains_processed):
    try:
        print(f"{Fore.YELLOW}Анализ DNS имен платформы {service}...{Style.RESET_ALL}")

        tasks = []
        for server_name, servers in dns_servers:
            resolver = dns.asyncresolver.Resolver()
            resolver.nameservers = servers
            for domain in dns_names:
                domain = domain.strip()
                if domain:
                    tasks.append(resolve_domain(domain, resolver, semaphore[server_name], server_name, null_ips_count, cloudflare_ips, cloudflare_ips_count, total_domains_processed))

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
    services = []
    if service:
        services = [s.strip() for s in service.split(',')]
        if "custom" in services:
            services.remove("custom")
            if local_dns_names:
                services.append("Custom DNS list")
        if "all" in services:
            services = list(urls.keys())
            if local_dns_names and "Custom DNS list" not in services:
                services.append("Custom DNS list")
        elif not services:
            services = list(urls.keys())
            if local_dns_names and "Custom DNS list" not in services:
                services.append("Custom DNS list")
    else:
        while True:
            print(f"\n{yellow('Выберите сервисы:')}")
            print("0. Выбрать все")
            for idx, (service, url) in enumerate(urls.items(), 1):
                print(f"{idx}. {service.capitalize()}")
            if local_dns_names:
                print(f"{len(urls) + 1}. Custom DNS list")

            selection = input(f"\nУкажите номера платформ через пробел и нажмите {green('Enter')}: ")
            if selection.strip():
                selections = selection.split()
                if '0' in selections:
                    services = list(urls.keys())
                    if local_dns_names and "Custom DNS list" not in services:
                        services.append('Custom DNS list')
                    break
                else:
                    services = [list(urls.keys())[int(sel) - 1] for sel in selections if sel.isdigit()
                                and 1 <= int(sel) <= len(urls)]
                    if str(len(urls) + 1) in selections and local_dns_names:
                        services.append('Custom DNS list')
                    break
    return services




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
    # Получение системных DNS серверов
    system_dns_servers = dns.asyncresolver.Resolver().nameservers

    # Формирование списка всех доступных серверов
    dns_server_options = [('Системный DNS', system_dns_servers)] + list(dns_servers.items())

    selected_dns_servers = []

    # Если указаны индексы серверов в конфиге
    if dns_server_indices:
        if 0 in dns_server_indices:  # Если указано 0, выбираем все доступные DNS серверы
            selected_dns_servers = dns_server_options
        else:
            for idx in dns_server_indices:
                if 1 <= idx <= len(dns_server_options):  # Корректируем индекс на 1 меньше, чтобы соответствовать списку
                    selected_dns_servers.append(dns_server_options[idx - 1])
        return selected_dns_servers

    # Если индексы не указаны, запрашиваем у пользователя выбор серверов
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
                            selected_dns_servers.append(dns_server_options[sel - 1])
                break

    return selected_dns_servers


# Выбор формата сохранения списка разрешенных DNS имен
def process_file_format(filename, filetype, gateway, selected_service, mk_list_name):
    if not filetype:
        filetype = input(f"\n{yellow('В каком формате сохранить файл?')}"
                         f"\n{green('win')} - route add {cyan('IP')} mask {cyan('MASK GATEWAY')}"
                         f"\n{green('unix')} - ip route {cyan('IP/MASK GATEWAY')}"
                         f"\n{green('cidr')} - {cyan('IP/MASK')}"
                         f"\n{green('mikrotik')} - /ip/firewall/address-list add list={cyan('LIST_NAME')} comment={cyan('SERVICE_NAME')} address={cyan('IP/MASK')}"
                         f"\n{green('Enter')} - только {cyan('IP')}"
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

    elif filetype.lower() == 'mikrotik':
        mk_list_name = mk_list_name_input(mk_list_name)

        try:
            with open(filename, 'r', encoding='utf-8-sig') as file:
                ips = file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return

        if ips:
            with open(filename, 'w', encoding='utf-8-sig') as file:
                for ip in ips:
                    file.write(f'/ip/firewall/address-list add list={mk_list_name} comment="{",".join(["".join(word.title() for word in s.split()) for s in selected_service])}" address={ip.strip()}/32{chr(10)}')


    else:
        pass


# Ну чо, погнали?!
async def main():
    # Инициализация настроек из config.ini
    service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices, mk_list_name = read_config('config.ini')

    # Load URLs
    platform_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platformdb"
    urls = await load_urls(platform_db_url)

    # Load local DNS names from "custom-dns-list.txt" if it exists
    local_dns_names = []
    if os.path.exists('custom-dns-list.txt'):
        with open('custom-dns-list.txt', 'r', encoding='utf-8-sig') as file:
            local_dns_names = [line.strip() for line in file if line.strip()]

    # Выбор платформ
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
    total_domains_processed = [0]
    tasks = []

    for service in selected_services:
        if service == 'Custom DNS list':
            tasks.append(resolve_dns(service, local_dns_names, selected_dns_servers, cloudflare_ips, unique_ips_all_services,
                                     semaphore, null_ips_count, cloudflare_ips_count, total_domains_processed))
        else:
            dns_names_url = urls[service]
            async with httpx.AsyncClient() as client:
                response = await client.get(dns_names_url)
                response.raise_for_status()
                dns_names = response.text.splitlines()
            tasks.append(resolve_dns(service, dns_names, selected_dns_servers, cloudflare_ips, unique_ips_all_services,
                                     semaphore, null_ips_count, cloudflare_ips_count, total_domains_processed))

    results = await asyncio.gather(*tasks)

    with open(filename, 'w', encoding='utf-8-sig') as file:
        for result in results:
            file.write(result)

    print(f"\n{yellow('Проверка завершена.')}")
    print(f"{Style.BRIGHT}Использовались DNS сервера:{Style.RESET_ALL} " + ', '.join(
        [f'{pair[0]} ({", ".join(pair[1])})' for pair in selected_dns_servers]))
    print(f"{Style.BRIGHT}Всего обработано DNS имен:{Style.RESET_ALL} {total_domains_processed[0]}.")
    if include_cloudflare:
        print(f"{Style.BRIGHT}Исключено IP-адресов Cloudflare:{Style.RESET_ALL} {cloudflare_ips_count[0]}")
    print(f"{Style.BRIGHT}Исключено IP-адресов 'заглушек':{Style.RESET_ALL} {null_ips_count[0]}")
    print(f"{Style.BRIGHT}Разрешено IP-адресов из DNS имен:{Style.RESET_ALL} {len(unique_ips_all_services)}")

    process_file_format(filename, filetype, gateway, selected_services, mk_list_name)

    if run_command:
        print("\nВыполнение команды после завершения скрипта...")
        os.system(run_command)
    else:
        print(f"\n{Style.BRIGHT}Результаты сохранены в файл:{Style.RESET_ALL}", filename)
        if os.name == 'nt':
            input(f"Нажмите {green('Enter')} для выхода...")

if __name__ == "__main__":
    asyncio.run(main())
