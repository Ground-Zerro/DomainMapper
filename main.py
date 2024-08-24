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
        subnet = config.get('subnet') or ''

        print(f"{yellow('Загружена конфигурация из config.ini:')}")
        print(f"{Style.BRIGHT}Сервисы для проверки:{Style.RESET_ALL} {service if service else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Использовать DNS сервер:{Style.RESET_ALL} {dns_server_indices if dns_server_indices else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Количество одновременных запросов к одному DNS серверу:{Style.RESET_ALL} {request_limit}")
        print(f"{Style.BRIGHT}Фильтр IP-адресов Cloudflare:{Style.RESET_ALL} {'включен' if cloudflare == 'yes' else 'выключен' if cloudflare == 'no' else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Агрегация IP-адресов:{Style.RESET_ALL} {'до /16 подсети' if subnet == '16' else 'до /24 подсети' if subnet == '24' else 'вЫключена' if subnet == 'no' else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Сохранить результаты в файл:{Style.RESET_ALL} {filename}")
        print(f"{Style.BRIGHT}Формат сохранения:{Style.RESET_ALL} {'только IP' if filetype == 'ip' else 'Linux route' if filetype == 'unix' else 'CIDR-нотация' if filetype == 'cidr' else 'Windows route' if filetype == 'win' else 'CLI Mikrotik firewall' if filetype == 'mikrotik' else 'open vpn' if filetype == 'ovpn' else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Шлюз/Имя интерфейса для маршрутов:{Style.RESET_ALL} {gateway if gateway else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Имя списка для Mikrotik firewall:{Style.RESET_ALL} {mk_list_name if mk_list_name else 'спросить у пользователя'}")
        print(f"{Style.BRIGHT}Выполнить по завершению:{Style.RESET_ALL} {run_command if run_command else 'не указано'}")
        return service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices, mk_list_name, subnet

    except Exception as e:
        print(f"{yellow('Ошибка загрузки config.ini:')} {e}\n{Style.BRIGHT}Используются настройки 'по умолчанию'.{Style.RESET_ALL}")
        return '', 20, 'domain-ip-resolve.txt', '', '', '', '', [], '', ''


def gateway_input(gateway):
    if not gateway:
        input_gateway = input(f"Укажите {green('шлюз')} или {green('имя интерфейса')}: ")
        return input_gateway.strip() if input_gateway else None
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


async def resolve_domain(domain, resolver, semaphore, dns_server_name, null_ips_count, cloudflare_ips, cloudflare_ips_count, total_domains_processed):
    async with semaphore:
        try:
            total_domains_processed[0] += 1
            response = await resolver.resolve(domain)
            ips = [ip.address for ip in response]
            filtered_ips = []
            for ip_address in ips:
                if ip_address in ('127.0.0.1', '0.0.0.0') or ip_address in resolver.nameservers:
                    null_ips_count[0] += 1
                elif ip_address in cloudflare_ips:
                    cloudflare_ips_count[0] += 1
                else:
                    filtered_ips.append(ip_address)
                    print(f"{Fore.BLUE}{domain} IP-адрес: {ip_address} - {dns_server_name}{Style.RESET_ALL}")
            return filtered_ips
        except Exception as e:  # Ловим все ошибки чтобы код не прервался
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


# Промт на исключение IP-адресов cloudflare
def check_include_cloudflare(cloudflare):
    if cloudflare.lower() == 'yes':
        return True
    elif cloudflare.lower() == 'no':
        return False
    else:
        return input(f"\n{yellow('Исключить IP адреса Cloudflare из итогового списка?')} ({green('yes')} "
                     f"- исключить, {green('Enter')} - оставить): ").strip().lower() == "yes"


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


# Для microtik ввод комментария comment для firewall
def mk_list_name_input(mk_list_name):
    if not mk_list_name:
        input_mk_list_name = input(f"Введите {green('LIST_NAME')} для Mikrotik firewall: ")
        return input_mk_list_name.strip() if input_mk_list_name else None
    else:
        return mk_list_name


# Для mikrotik уплотняем имена сервисов
def mk_comment(selected_service):
    return ",".join(["".join(word.title() for word in s.split()) for s in selected_service])


# Выбор формата сохранения списка разрешенных DNS имен
def subnetting(subnet):
    # Если значение пустое, запрашиваем ввод от пользователя
    if subnet.lower() == '':
        subnet = input(f"\n{yellow('Объединить IP-адреса в подсети?')} "
                       f"\n{green('16')} - сократить до /16 (255.255.0.0)"
                       f"\n{green('24')} - сократить до /24 (255.255.255.0)"
                       f"\n{green('Enter')} - пропустить: ").strip().lower()

    # Обрабатываем ввод или параметр
    if subnet == '16':
        return "16", "255.255.0.0"
    elif subnet == '24':
        return "24", "255.255.255.0"
    else:
        return "32", "255.255.255.255"


def group_ips_in_subnets(filename, submask):
    try:
        # Чтение всех IP-адресов из файла
        with open(filename, 'r', encoding='utf-8-sig') as file:
            ips = {line.strip() for line in file if line.strip()}  # Собираем уникальные IP адреса

        # Обработка подсетей в зависимости от маски
        if submask == "24":
            # Множество для хранения всех подсетей /24
            subnets = set()

            # Преобразование всех IP в их подсети /24
            for ip in ips:
                try:
                    # Преобразуем IP в сеть /24 (маска 255.255.255.0)
                    network_24 = ipaddress.ip_network(f"{ip}/24", strict=False)
                    subnets.add(str(network_24.network_address))
                except ValueError as e:
                    print(f"{red('Ошибка в IP адресе:')} {ip} - {e}")

            # Перезаписываем файл с уникальными подсетями /24
            with open(filename, 'w', encoding='utf-8-sig') as file:
                for subnet in sorted(subnets):
                    file.write(subnet + '\n')

            print(f"{Style.BRIGHT}IP-адреса агрегированы до /{submask} подсети{Style.RESET_ALL}")

        elif submask == "16":
            # Множество для хранения всех объединенных подсетей /16
            subnets = set()

            # Преобразование всех IP в их подсети /16
            for ip in ips:
                try:
                    # Преобразуем IP в сеть /16 (маска 255.255.0.0)
                    network_16 = ipaddress.ip_network(f"{ip}/16", strict=False)
                    subnets.add(str(network_16.network_address))
                except ValueError as e:
                    print(f"{red('Ошибка в IP адресе:')} {ip} - {e}")

            # Перезаписываем файл с уникальными подсетями /16
            with open(filename, 'w', encoding='utf-8-sig') as file:
                for subnet in sorted(subnets):
                    file.write(subnet + '\n')

            print(f"{Style.BRIGHT}IP-адреса агрегированы до /{submask} подсети{Style.RESET_ALL}")

        else:
            print(f"{red('Неправильная маска подсети:')} {submask}")

    except Exception as e:
        print(f"{red('Ошибка при обработке файла:')} {e}")


# Выбор формата сохранения списка разрешенных DNS имен
def process_file_format(filename, filetype, gateway, selected_service, mk_list_name, submask):
    def read_file(filename):
        try:
            with open(filename, 'r', encoding='utf-8-sig') as file:
                return file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return None

    def write_file(filename, ips, formatter):
        with open(filename, 'w', encoding='utf-8-sig') as file:
            for ip in ips:
                file.write(formatter(ip.strip()) + '\n')

    # Определение маски подсети для отображения пользователю и ее корректной записи в файл
    display_submask = "255.255.0.0" if submask == "16" else "255.255.255.0" if submask == "24" else "255.255.255.255"

    if not filetype:
        filetype = input(f"""
{yellow('В каком формате сохранить файл?')}
{green('win')} - route add {cyan('IP')} mask {display_submask} {cyan('GATEWAY')}
{green('unix')} - ip route {cyan('IP')}/{submask} {cyan('GATEWAY')}
{green('cidr')} - {cyan('IP')}/{submask}
{green('mikrotik')} - /ip/firewall/address-list add list={cyan("LIST_NAME")} comment="{mk_comment(selected_service)}" address={cyan("IP")}/{submask}
{green('ovpn')} - push "route {cyan('IP')} {display_submask}"
{green('Enter')} - {cyan('IP')}
Ваш выбор: """)

    ips = read_file(filename)
    if not ips:
        return

    # Если формат требует указания шлюза, запрашиваем его
    if filetype.lower() in ['win', 'unix']:
        gateway = gateway_input(gateway)  # Сохраняем значение шлюза после ввода

    # Если выбран формат Mikrotik, запрашиваем mk_list_name
    if filetype.lower() == 'mikrotik':
        mk_list_name = mk_list_name_input(mk_list_name)  # Сохраняем значение mk_list_name после ввода

    formatters = {
        'win': lambda ip: f"route add {ip} mask {display_submask} {gateway}",
        'unix': lambda ip: f"ip route {ip}/{submask} {gateway}",
        'cidr': lambda ip: f"{ip}/{submask}",
        'ovpn': lambda ip: f'push "route {ip} {display_submask}"',
        'mikrotik': lambda ip: f'/ip/firewall/address-list add list={mk_list_name} comment="{mk_comment(selected_service)}" address={ip}/{submask}'
    }

    if filetype.lower() in formatters:
        write_file(filename, ips, formatters[filetype.lower()])


# Ну чо, погнали?!
async def main():
    # Инициализация настроек из config.ini
    service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices, mk_list_name, subnet = read_config('config.ini')

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
    print(f"{Style.BRIGHT}Всего обработано DNS имен:{Style.RESET_ALL} {total_domains_processed[0]}")
    if include_cloudflare:
        print(f"{Style.BRIGHT}Исключено IP-адресов Cloudflare:{Style.RESET_ALL} {cloudflare_ips_count[0]}")
    print(f"{Style.BRIGHT}Исключено IP-адресов 'заглушек':{Style.RESET_ALL} {null_ips_count[0]}")
    print(f"{Style.BRIGHT}Разрешено IP-адресов из DNS имен:{Style.RESET_ALL} {len(unique_ips_all_services)}")

    # Группировка IP-адресов в подсети
    submask, _ = subnetting(subnet)
    group_ips_in_subnets(filename, submask)

    process_file_format(filename, filetype, gateway, selected_services, mk_list_name, submask)

    if run_command:
        print("\nВыполнение команды после завершения скрипта...")
        os.system(run_command)
    else:
        print(f"\n{Style.BRIGHT}Результаты сохранены в файл:{Style.RESET_ALL}", filename)
        if os.name == 'nt':
            input(f"Нажмите {green('Enter')} для выхода...")


if __name__ == "__main__":
    asyncio.run(main())