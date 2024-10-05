import argparse
import asyncio
import configparser
import ipaddress
import os
from asyncio import Semaphore
from collections import defaultdict

import dns.asyncresolver
import httpx
from colorama import Fore, Style, init

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
def read_config(cfg_file):
    try:
        config = configparser.ConfigParser()
        with open(cfg_file, 'r', encoding='utf-8-sig') as file:
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
        subnet = config.get('subnet') or ''
        cfginfo = config.get('cfginfo') or 'yes'  # Не возвращаем его в main
        ken_gateway = config.get('keenetic') or ''
        localplatform = config.get('localplatform') or ''
        localdns = config.get('localdns') or ''

        if cfginfo in ['yes', 'y']:
            print(f"{yellow(f'Загружена конфигурация из {cfg_file}:')}")
            print(
                f"{Style.BRIGHT}Сервисы для проверки:{Style.RESET_ALL} {service if service else 'спросить у пользователя'}")
            print(
                f"{Style.BRIGHT}Использовать DNS сервер:{Style.RESET_ALL} {dns_server_indices if dns_server_indices else 'спросить у пользователя'}")
            print(
                f"{Style.BRIGHT}Количество одновременных запросов к одному DNS серверу:{Style.RESET_ALL} {request_limit}")
            print(
                f"{Style.BRIGHT}Фильтрация IP-адресов Cloudflare:{Style.RESET_ALL} {'включена' if cloudflare in ['y', 'yes'] else 'вЫключена' if cloudflare in ['n', 'no'] else 'спросить у пользователя'}")
            print(
                f"{Style.BRIGHT}Агрегация IP-адресов:{Style.RESET_ALL} {'mix режим /24 (255.255.255.0) + /32 (255.255.255.255)' if subnet == 'mix' else 'до /16 подсети (255.255.0.0)' if subnet == '16' else 'до /24 подсети (255.255.255.0)' if subnet == '24' else 'вЫключена' if subnet in ['n', 'no'] else 'спросить у пользователя'}")
            print(
                f"{Style.BRIGHT}Формат сохранения:{Style.RESET_ALL} {'только IP' if filetype == 'ip' else 'Linux route' if filetype == 'unix' else 'CIDR-нотация' if filetype == 'cidr' else 'Windows route' if filetype == 'win' else 'Mikrotik CLI' if filetype == 'mikrotik' else 'open vpn' if filetype == 'ovpn' else 'Keenetic CLI' if filetype == 'keenetic' else 'Wireguard' if filetype == 'wireguard' else 'спросить у пользователя'}")
            if filetype in ['win', 'unix', '']:
                print(
                    f"{Style.BRIGHT}Шлюз/Имя интерфейса для Windows и Linux route:{Style.RESET_ALL} {gateway if gateway else 'спросить у пользователя'}")
            if filetype in ['keenetic', '']:
                print(
                    f"{Style.BRIGHT}Шлюз/Имя интерфейса для Keenetic CLI:{Style.RESET_ALL} {ken_gateway if ken_gateway else 'спросить у пользователя'}")
            if filetype in ['mikrotik', '']:
                print(
                    f"{Style.BRIGHT}Имя списка для Mikrotik firewall:{Style.RESET_ALL} {mk_list_name if mk_list_name else 'спросить у пользователя'}")
            print(f"{Style.BRIGHT}Сохранить результат в файл:{Style.RESET_ALL} {filename}")
            print(
                f"{Style.BRIGHT}Выполнить по завершению:{Style.RESET_ALL} {run_command if run_command else 'не указано'}")
        if localplatform in ['yes', 'y'] or localdns in ['yes', 'y']:
            print(f"\n{red('!!! Включен локальный режим !!!')}")
            print(
                f"{Style.BRIGHT}Список сервисов будет загружен из:{Style.RESET_ALL} {'файла platformdb' if localplatform in ['yes', 'y'] else 'сети'}")
            print(
                f"{Style.BRIGHT}Список DNS серверов будет загружен из:{Style.RESET_ALL} {'файла dnsdb' if localdns in ['yes', 'y'] else 'сети'}")

        return service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices, mk_list_name, subnet, ken_gateway, localplatform, localdns

    except Exception as e:
        print(
            f"{yellow(f'Ошибка загрузки {cfg_file}:')} {e}\n{Style.BRIGHT}Используются настройки 'по умолчанию'.{Style.RESET_ALL}")
        return '', 20, 'domain-ip-resolve.txt', '', '', '', '', [], '', '', '', '', ''


# IP шлюза для win и unix
def gateway_input(gateway):
    if not gateway:
        input_gateway = input(f"Укажите {green('IP шлюза')} или {green('имя интерфейса')}: ")
        return input_gateway.strip() if input_gateway else None
    else:
        return gateway


# IP шлюза и имя интерфейса для keenetic
def ken_gateway_input(ken_gateway):
    if not ken_gateway:
        input_ken_gateway = input(
            f"Укажите {green('IP шлюза')} или {green('имя интерфейса')} или {green('IP шлюза')} и через пробел {green('имя интерфейса')}: ")
        return input_ken_gateway.strip() if input_ken_gateway else None
    else:
        return ken_gateway


# Ограничение числа запросов
def get_semaphore(request_limit):
    return defaultdict(lambda: Semaphore(request_limit))


# Инициализация semaphore для ограничения запросов
def init_semaphores(request_limit):
    return get_semaphore(request_limit)


# Загрузка списка платформ из сети
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


# Загрузка списка платформ из локального файла
async def load_urls_from_file():
    try:
        with open('platformdb', 'r') as file:
            urls = {}
            for line in file:
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


# Загрузка списка DNS серверов из локального файла
async def load_dns_from_file():
    try:
        with open('dnsdb', 'r') as file:
            dns_servers = {}
            for line in file:
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
            for line in text.splitlines():
                line = line.strip()
                if '/' in line:
                    try:
                        ip_network = ipaddress.ip_network(line)
                        for ip in ip_network:
                            cloudflare_ips.add(str(ip))
                    except ValueError:
                        continue
            return cloudflare_ips
    except Exception as e:
        print("Ошибка при получении IP адресов Cloudflare:", e)
        return set()


# Загрузка списков DNS имен из сети и локальных файлов
async def load_dns_names(url_or_file):
    if url_or_file.startswith("http"):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url_or_file)
                response.raise_for_status()
                return response.text.splitlines()
            except httpx.HTTPStatusError as e:
                print(f"Ошибка при загрузке DNS имен: {e}")
                return []
    else:
        # Локальный файл
        with open(url_or_file, 'r', encoding='utf-8') as file:
            return file.read().splitlines()


async def resolve_domain(domain, resolver, semaphore, dns_server_name, null_ips_count, cloudflare_ips,
                         cloudflare_ips_count, total_domains_processed, include_cloudflare):
    async with semaphore:
        try:
            total_domains_processed[0] += 1
            response = await resolver.resolve(domain)
            ips = [ip.address for ip in response]
            filtered_ips = []
            for ip_address in ips:
                if ip_address in ('127.0.0.1', '0.0.0.0') or ip_address in resolver.nameservers:
                    null_ips_count[0] += 1
                elif include_cloudflare and ip_address in cloudflare_ips:
                    cloudflare_ips_count[0] += 1
                else:
                    filtered_ips.append(ip_address)
                    print(f"{Fore.BLUE}{domain} IP-адрес: {ip_address} - {dns_server_name}{Style.RESET_ALL}")
            return filtered_ips
        except Exception as e:  # Ловим все ошибки чтобы код не прервался
            print(f"{Fore.RED}Не удалось получить IP-адрес: {domain} - {dns_server_name}{Style.RESET_ALL}")
            return []


async def resolve_dns(service, dns_names, dns_servers, cloudflare_ips, unique_ips_all_services, semaphore,
                      null_ips_count, cloudflare_ips_count, total_domains_processed, include_cloudflare):
    try:
        print(f"{Fore.YELLOW}Загрузка DNS имен платформы {service}...{Style.RESET_ALL}")

        tasks = []
        for server_name, servers in dns_servers:
            resolver = dns.asyncresolver.Resolver()
            resolver.nameservers = servers
            for domain in dns_names:
                domain = domain.strip()
                if domain:
                    tasks.append(resolve_domain(domain, resolver, semaphore[server_name], server_name, null_ips_count,
                                                cloudflare_ips, cloudflare_ips_count, total_domains_processed,
                                                include_cloudflare))

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

            selection = input(f"\nУкажите {green('номера')} платформ через пробел и нажмите {green('Enter')}: ")
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


# Промт cloudflare фильтр
def check_include_cloudflare(cloudflare):
    if cloudflare in ['yes', 'y', 'no', 'n']:
        return cloudflare in ['yes', 'y']
    return input(f"\n{yellow('Исключить IP адреса Cloudflare из итогового списка?')}"
                 f"\n{green('yes')} - исключить"
                 f"\n{green('Enter')} - оставить: ").strip().lower() in ['yes', 'y']

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

        selection = input(f"\nУкажите {green('номера')} DNS серверов через пробел и нажмите {green('Enter')}: ")
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


# комментарй для microtik firewall
def mk_list_name_input(mk_list_name):
    if not mk_list_name:
        input_mk_list_name = input(f"Введите {green('LIST_NAME')} для Mikrotik firewall: ")
        return input_mk_list_name.strip() if input_mk_list_name else None
    else:
        return mk_list_name


# Уплотняем имена сервисов
def mk_comment(selected_service):
    return ",".join(["".join(word.title() for word in s.split()) for s in selected_service])


# Промт на объединение IP в подсети
def subnet_input(subnet):
    if not subnet:  # Проверяем, является ли значение пустым
        subnet = input(
            f"\n{yellow('Объединить IP-адреса в подсети?')} "
            f"\n{green('16')} - сократить до /16 (255.255.0.0)"
            f"\n{green('24')} - сократить до /24 (255.255.255.0)"
            f"\n{green('mix')} - сократить до /24 (255.255.255.0) и /32 (255.255.255.255)"
            f"\n{green('Enter')} - пропустить: "
        ).strip().lower()

    return subnet if subnet in {'16', '24', 'mix'} else '32'


# Агрегация маршрутов
def group_ips_in_subnets(filename, subnet):
    try:
        with open(filename, 'r', encoding='utf-8-sig') as file:
            ips = {line.strip() for line in file if line.strip()}  # Собираем уникальные IP адреса

        subnets = set()

        def process_ips(subnet):
            for ip in ips:
                try:
                    if subnet == "16":
                        # Преобразуем в /16 (два последних октета заменяются на 0.0)
                        network = ipaddress.IPv4Network(f"{ip}/16", strict=False)
                        subnets.add(f"{network.network_address}")
                    elif subnet == "24":
                        # Преобразуем в /24 (последний октет заменяется на 0)
                        network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                        subnets.add(f"{network.network_address}")
                except ValueError as e:
                    print(f"Ошибка в IP адресе: {ip} - {e}")

        if subnet in ["24", "16"]:
            process_ips(subnet)
            print(f"{Style.BRIGHT}IP-адреса агрегированы до /{subnet} подсети{Style.RESET_ALL}")

        elif subnet == "mix":
            octet_groups = {}
            for ip in ips:
                key = '.'.join(ip.split('.')[:3])  # Группировка по первым трем октетам
                if key not in octet_groups:
                    octet_groups[key] = []
                octet_groups[key].append(ip)

            # IP-адреса с совпадающими первыми тремя октетами
            network_24 = {key + '.0' for key, group in octet_groups.items() if
                          len(group) > 1}  # Базовый IP для /24 подсетей
            # Удаляем IP с совпадающими первыми тремя октетами из множества
            ips -= {ip for group in octet_groups.values() if len(group) > 1 for ip in group}
            # Оставляем только IP без указания маски для /24 и одиночных IP
            subnets.update(ips)  # IP без маски для одиночных IP
            subnets.update(network_24)  # Базовые IP для /24 подсетей
            print(f"{Style.BRIGHT}IP-адреса агрегированы до масок /24 и /32{Style.RESET_ALL}")

        with open(filename, 'w', encoding='utf-8-sig') as file:
            for subnet in sorted(subnets):
                file.write(subnet + '\n')

    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")


# Выбор формата сохранения результатов
def process_file_format(filename, filetype, gateway, selected_service, mk_list_name, subnet, ken_gateway):
    def read_file(filename):
        try:
            with open(filename, 'r', encoding='utf-8-sig') as file:
                return file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return None

    def write_file(filename, ips, formatter):
        formatted_ips = [formatter(ip.strip()) for ip in ips]
        with open(filename, 'w', encoding='utf-8-sig') as file:
            if filetype.lower() == 'wireguard':
                file.write(', '.join(formatted_ips))
            else:
                file.write('\n'.join(formatted_ips))

    # Определение маски подсети
    net_mask = subnet if subnet == "mix" else "255.255.0.0" if subnet == "16" else "255.255.255.0" if subnet == "24" else "255.255.255.255"

    if not filetype:
        filetype = input(f"""
{yellow('В каком формате сохранить файл?')}
{green('win')} - route add {cyan('IP')} mask {net_mask} {cyan('GATEWAY')}
{green('unix')} - ip route {cyan('IP')}/{subnet} {cyan('GATEWAY')}
{green('keenetic')} - ip route {cyan('IP')}/{subnet} {cyan('GATEWAY GATEWAY_NAME')} auto !{mk_comment(selected_service)}
{green('cidr')} - {cyan('IP')}/{subnet}
{green('mikrotik')} - /ip/firewall/address-list add list={cyan("LIST_NAME")} comment="{mk_comment(selected_service)}" address={cyan("IP")}/{subnet}
{green('ovpn')} - push "route {cyan('IP')} {net_mask}"
{green('wireguard')} - {cyan('IP')}/{subnet}, {cyan('IP')}/{subnet}, и т.д...
{green('Enter')} - {cyan('IP')}
Ваш выбор: """)

    ips = read_file(filename)
    if not ips:
        return

    # Дополнительные запросы в зависимости от формата файла
    if filetype in ['win', 'unix']:  # Запрашиваем IP шлюза для win и unix
        gateway = gateway_input(gateway)
    elif filetype == 'keenetic':  # Запрашиваем IP шлюза и имя интерфейса для keenetic
        ken_gateway = ken_gateway_input(ken_gateway)
    elif filetype == 'mikrotik':  # Запрашиваем ввод комментария для microtik firewall
        mk_list_name = mk_list_name_input(mk_list_name)

    # обычный формат
    formatters = {
        'win': lambda ip: f"route add {ip} mask {net_mask} {gateway}",
        'unix': lambda ip: f"ip route {ip}/{subnet} {gateway}",
        'keenetic': lambda ip: f"ip route {ip}/{subnet} {ken_gateway} auto !{mk_comment(selected_service)}",
        'cidr': lambda ip: f"{ip}/{subnet}",
        'ovpn': lambda ip: f'push "route {ip} {net_mask}"',
        'mikrotik': lambda
            ip: f'/ip/firewall/address-list add list={mk_list_name} comment="{mk_comment(selected_service)}" address={ip}/{subnet}',
        'wireguard': lambda ip: f"{ip}/{subnet}"
    }

    # mix формат
    if subnet == "mix":
        if filetype.lower() == 'win':  # Обработка для win
            mix_formatter = lambda ip: f"{ip.strip()} mask 255.255.255.0" if ip.endswith(
                '.0') else f"{ip.strip()} mask 255.255.255.255"
        elif filetype.lower() == 'ovpn':  # Обработка для ovpn
            mix_formatter = lambda ip: f"{ip.strip()} 255.255.255.0" if ip.endswith(
                '.0') else f"{ip.strip()} 255.255.255.255"
        else:  # Обработка для остальных форматов
            mix_formatter = lambda ip: f"{ip.strip()}/24" if ip.endswith('.0') else f"{ip.strip()}/32"

        formatters.update({
            'win': lambda ip: f"route add {mix_formatter(ip)} {gateway}",
            'unix': lambda ip: f"ip route {mix_formatter(ip)} {gateway}",
            'keenetic': lambda ip: f"ip route {mix_formatter(ip)} {ken_gateway} auto !{mk_comment(selected_service)}",
            'cidr': lambda ip: f"{mix_formatter(ip)}",
            'ovpn': lambda ip: f'push "route {mix_formatter(ip)}"',
            'mikrotik': lambda
                ip: f'/ip/firewall/address-list add list={mk_list_name} comment="{mk_comment(selected_service)}" address={mix_formatter(ip)}',
            'wireguard': lambda ip: f"{mix_formatter(ip)}"
        })

    # Запись в файл
    if filetype.lower() in formatters:
        write_file(filename, ips, formatters[filetype.lower()])


# Стартуем
async def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="DNS resolver script with custom config file.")
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.ini',
        help='Путь к конфигурационному файлу (по умолчанию: config.ini)'
    )
    args = parser.parse_args()

    # Инициализация настроек из переданного конфигурационного файла
    config_file = args.config
    service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices, mk_list_name, subnet, ken_gateway, localplatform, localdns = read_config(
        config_file)

    # Загрузка списка платформ
    if localplatform in ['yes', 'y']:
        urls = await load_urls_from_file()

    else:
        platform_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platformdb"
        urls = await load_urls(platform_db_url)

    # Подхват "custom-dns-list.txt" если существует
    local_dns_names = []
    if os.path.exists('custom-dns-list.txt'):
        with open('custom-dns-list.txt', 'r', encoding='utf-8-sig') as file:
            local_dns_names = [line.strip() for line in file if line.strip()]

    # Выбор платформ
    selected_services = check_service_config(service, urls, local_dns_names)

    # Загрузка списка DNS-серверов
    if localdns in ['yes', 'y']:
        dns_servers = await load_dns_from_file()

    else:
        dns_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/dnsdb"
        dns_servers = await load_dns_servers(dns_db_url)

    # Выбор DNS-серверов
    selected_dns_servers = check_dns_servers(dns_servers, dns_server_indices)

    # Фильтр Cloudflare
    include_cloudflare = check_include_cloudflare(cloudflare)
    if include_cloudflare:  # Загрузка IP-адресов Cloudflare
        cloudflare_ips = await get_cloudflare_ips()
    else:
        cloudflare_ips = set()

    unique_ips_all_services = set()
    semaphore = init_semaphores(request_limit)
    null_ips_count = [0]
    cloudflare_ips_count = [0]
    total_domains_processed = [0]
    tasks = []

    for service in selected_services:
        if service == 'Custom DNS list':
            tasks.append(resolve_dns(service, local_dns_names, selected_dns_servers, cloudflare_ips,
                                     unique_ips_all_services, semaphore, null_ips_count, cloudflare_ips_count,
                                     total_domains_processed, include_cloudflare))

        else:
            url_or_file = urls[service]
            dns_names = await load_dns_names(url_or_file)
            tasks.append(resolve_dns(service, dns_names, selected_dns_servers, cloudflare_ips, unique_ips_all_services,
                                     semaphore, null_ips_count, cloudflare_ips_count, total_domains_processed,
                                     include_cloudflare))

    results = await asyncio.gather(*tasks)

    with open(filename, 'w', encoding='utf-8-sig') as file:
        for result in results:
            file.write(result)

    print(f"\n{yellow('Проверка завершена.')}")
    print(f"{Style.BRIGHT}Использовались DNS сервера:{Style.RESET_ALL} " + ', '.join(
        [f'{pair[0]} ({", ".join(pair[1])})' for pair in selected_dns_servers]))
    print(f"{Style.BRIGHT}Всего обработано DNS имен:{Style.RESET_ALL} {total_domains_processed[0]}")
    if include_cloudflare:
        print(f"{Style.BRIGHT}Исключено IP-адресов Cloudflare:{Style.RESET_ALL} {cloudflare_ips_count[0]}")
    print(f"{Style.BRIGHT}Исключено IP-адресов 'заглушек':{Style.RESET_ALL} {null_ips_count[0]}")
    print(f"{Style.BRIGHT}Разрешено IP-адресов из DNS имен:{Style.RESET_ALL} {len(unique_ips_all_services)}")

    # Группировка IP-адресов в подсети
    subnet = subnet_input(subnet)
    if subnet != '32':  # Если не '32', вызываем функцию для агрегации
        group_ips_in_subnets(filename, subnet)

    process_file_format(filename, filetype, gateway, selected_services, mk_list_name, subnet, ken_gateway)

    if run_command:
        print("\nВыполнение команды после завершения скрипта...")
        os.system(run_command)
    else:
        print(f"\n{Style.BRIGHT}Результаты сохранены в файл:{Style.RESET_ALL}", filename)
        if os.name == 'nt':
            input(f"Нажмите {green('Enter')} для выхода...")


if __name__ == "__main__":
    asyncio.run(main())
