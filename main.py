import asyncio
import configparser
import ipaddress
import os
import re
from asyncio import Semaphore
from collections import defaultdict

import dns.asyncresolver
import httpx


# Read configuration file
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

        print("\033[33mЗагружена конфигурация из config.ini:\033[0m")
        print(f"Сервисы для проверки: {service if service else 'не указаны'}")
        print(f"Использовать DNS сервер: {dns_server_indices if dns_server_indices else 'не указано'}")
        print(f"Количество потоков: {request_limit}")
        print(f"Фильтр Cloudflare: {'включен' if cloudflare == 'yes' else 'вЫключен' if cloudflare == 'no' else 'не указано'}")
        print(f"Файл результатов: {filename}")
        print(f"Формат сохранения: {'только IP' if filetype == 'ip' else 'Linux route' if filetype == 'unix' else 'CIDR-нотация' if filetype == 'cidr' else 'Windows route' if filetype == 'win' else 'не указан'}")
        print(f"Шлюз для маршрутов: {gateway if gateway else 'не указан'}")
        print(f"Выполнить при заврешении: {run_command if run_command else 'не указано'}")
        return service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices

    except Exception as e:
        print(f"\033[33mОшибка загрузки config.ini:\033[0m {e}\nИспользуются настройки 'по умолчанию'.")
        return '', 20, 'domain-ip-resolve.txt', '', '', '', '', []


def gateway_input(gateway):
    if not gateway:
        input_gateway = input(f"Укажите \033[32mшлюз\033[0m или \033[32mимя интерфейса\033[0m: ")
        if input_gateway:
            return input_gateway.strip()
    else:
        return gateway


# Function to limit requests
def get_semaphore(request_limit):
    return defaultdict(lambda: Semaphore(request_limit))


# Initialize semaphore for limiting requests
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
                    print(f"\033[36m{domain} IP адрес: {ip_address} получен от {dns_server_name}\033[0m")
            return ips
        except Exception as e:
            print(f"\033[31mНе удалось разрешить {domain} через {dns_server_name}\033[0m")
            return []


async def resolve_dns(service, url, dns_servers, cloudflare_ips, unique_ips_all_services, semaphore, null_ips_count,
                      cloudflare_ips_count):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            dns_names = response.text.split('\n')

        print(f"\033[33mАнализ DNS имен платформы {service}...\033[0m")

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


def check_service_config(service, urls):
    if service:
        if service.strip().lower() == "all":
            return list(urls.keys())
        else:
            return [s.strip() for s in service.split(',')]
    else:
        selected_services = []
        while True:
            print("\n\033[33mВыберите сервисы:\033[0m")
            print("0. Выбрать все")
            for idx, (service, url) in enumerate(urls.items(), 1):
                print(f"{idx}. {service.capitalize()}")

            selection = input("\nУкажите номера сервисов через пробел и нажмите \033[32mEnter\033[0m: ")
            if selection.strip():
                selections = selection.split()
                if '0' in selections:  # User selected all services
                    selected_services = list(urls.keys())
                    break
                else:
                    selected_services = [list(urls.keys())[int(sel) - 1] for sel in selections if sel.isdigit()
                                         and 1 <= int(sel) <= len(urls)]
                    break
        return selected_services


def check_include_cloudflare(cloudflare):
    if cloudflare.lower() == 'yes':
        return True
    elif cloudflare.lower() == 'no':
        return False
    else:
        return input("\nИсключить IP адреса Cloudflare из итогового списка? (\033[32myes\033[0m "
                     "- исключить, \033[32mEnter\033[0m - оставить): ").strip().lower() == "yes"


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
        print("\n\033[33mКакие DNS сервера использовать?\033[0m")
        print("0. Выбрать все")
        for idx, (name, servers) in enumerate(dns_server_options, 1):
            print(f"{idx}. {name}: {', '.join(servers)}")

        selection = input("\nУкажите номера DNS серверов через пробел и нажмите \033[32mEnter\033[0m: ")
        if selection.strip():
            selections = selection.split()
            if '0' in selections:  # User selected all DNS servers
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


def process_file_format(filename, filetype, gateway, selected_services):
    if not filetype:
        filetype = input("\n\033[33mВ каком формате сохранить файл?\033[0m"
                         "\n\033[32mwin\033[0m - route add IP mask MASK GATEWAY"
                         "\n\033[32munix\033[0m - ip route IP/MASK GATEWAY"
                         "\n\033[32mcidr\033[0m - IP/MASK"
                         "\n\033[32mmt-al\033[0m - Mikrotik ip/firewall/address-list add syntax"
                         "\n\033[32mПустое значение\033[0m - только IP"
                         "\nВаш выбор: ")

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
    elif filetype.lower() == 'mt-al':
        try:
            with open(filename, 'r', encoding='utf-8-sig') as file:
                ips = file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return

        if ips:
            address_list_name = input("\nВведите название списка адресов (address-list): ")
            selected_service = ','.join(selected_services)
            if not address_list_name:
                address_list_name = 'address-list-name'
            with open(filename, 'w', encoding='utf-8-sig') as file:
                for ip in ips:
                    file.write(f"ip/firewall/address-list add list={address_list_name} comment={selected_service} address={ip.strip()}/32\n")
    else:
        pass


async def main():
    # Load configuration
    service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices = read_config('config.ini')

    # Load URLs
    platform_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platformdb"
    urls = await load_urls(platform_db_url)

    # Get selected services from user
    selected_services = check_service_config(service, urls)

    # Load DNS servers
    dns_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/dnsdb"
    dns_servers = await load_dns_servers(dns_db_url)

    # Get selected DNS servers from config or user
    selected_dns_servers = check_dns_servers(dns_servers, dns_server_indices)

    # Get Cloudflare IP addresses
    cloudflare_ips = await get_cloudflare_ips()

    # Check if Cloudflare IPs should be included or excluded
    include_cloudflare = check_include_cloudflare(cloudflare)

    unique_ips_all_services = set()
    semaphore = init_semaphores(request_limit)
    null_ips_count = [0]
    cloudflare_ips_count = [0]
    tasks = []

    for service in selected_services:
        tasks.append(resolve_dns(service, urls[service], selected_dns_servers, cloudflare_ips, unique_ips_all_services,
                                 semaphore, null_ips_count, cloudflare_ips_count))

    results = await asyncio.gather(*tasks)

    with open(filename, 'w', encoding='utf-8-sig') as file:
        for result in results:
            file.write(result)

    print("\n\033[33mПроверка завершена.\033[0m")
    print("Использовались DNS сервера: " + ', '.join(
        [f'{pair[0]} ({", ".join(pair[1])})' for pair in selected_dns_servers]))
    if include_cloudflare:
        print(f"Исключено IP-адресов Cloudflare: {cloudflare_ips_count[0]}")
    print(f"Исключено IP-адресов 'заглушек': {null_ips_count[0]}")
    print(f"Разрешено IP-адресов из DNS имен: {len(unique_ips_all_services)}")

    process_file_format(filename, filetype, gateway, selected_services)

    if run_command:
        print("\nВыполнение команды после завершения скрипта...")
        os.system(run_command)
    else:
        print("\nРезультаты сохранены в файл:", filename)
        if os.name == 'nt':
            input("Нажмите \033[32mEnter\033[0m для выхода...")


if __name__ == "__main__":
    asyncio.run(main())
