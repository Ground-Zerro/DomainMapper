import argparse
import asyncio
import configparser
import ipaddress
import netaddr
import os
from asyncio import Semaphore
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

import dns.asyncresolver
import httpx
from colorama import Fore, Style, init

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

http_client = None
dns_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/dnsdb"
platform_db_url = "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platformdb"

async def get_http_client():
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(
            timeout=20.0,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
            follow_redirects=True
        )
    return http_client

async def cleanup_http_client():
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = None

def read_config(cfg_file):
    try:
        config = configparser.ConfigParser()
        with open(cfg_file, 'r', encoding='utf-8') as file:
            config.read_file(file)
        if 'DomainMapper' in config:
            config = config['DomainMapper']
        
        service = config.get('service') or ''
        request_limit = int(config.get('threads') or 15)
        filename = config.get('filename') or 'domain-ip-resolve.txt'
        cloudflare = config.get('cloudflare') or ''
        filetype = config.get('filetype') or ''
        gateway = config.get('gateway') or ''
        run_command = config.get('run') or ''
        dns_server_indices = list(map(int, config.get('dnsserver', '').split())) if config.get('dnsserver') else []
        mk_list_name = config.get('listname') or ''
        subnet = config.get('subnet') or ''
        cfginfo = config.get('cfginfo') or 'yes'
        ken_gateway = config.get('keenetic') or ''
        localplatform = config.get('localplatform') or ''
        localdns = config.get('localdns') or ''
        mk_comment = config.get('mk_comment') or 'off'

        if cfginfo in ['yes', 'y']:
            print(f"{yellow(f'Загружена конфигурация из {cfg_file}:')}")
            print(f"{Style.BRIGHT}Сервисы для проверки:{Style.RESET_ALL} {service if service else 'спросить у пользователя'}")
            print(f"{Style.BRIGHT}Использовать DNS сервер:{Style.RESET_ALL} {dns_server_indices if dns_server_indices else 'спросить у пользователя'}")
            print(f"{Style.BRIGHT}Количество одновременных запросов к одному DNS серверу:{Style.RESET_ALL} {request_limit}")
            print(f"{Style.BRIGHT}Фильтрация IP-адресов Cloudflare:{Style.RESET_ALL} {'включена' if cloudflare in ['y', 'yes'] else 'выключена' if cloudflare in ['n', 'no'] else 'спросить у пользователя'}")
            print(f"{Style.BRIGHT}Агрегация IP-адресов:{Style.RESET_ALL} {'mix режим /24 (255.255.255.0) + /32 (255.255.255.255)' if subnet == 'mix' else 'до /16 подсети (255.255.0.0)' if subnet == '16' else 'до /24 подсети (255.255.255.0)' if subnet == '24' else 'выключена' if subnet in ['n', 'no'] else 'спросить у пользователя'}")
            print(f"{Style.BRIGHT}Формат сохранения:{Style.RESET_ALL} {'только IP' if filetype == 'ip' else 'Linux route' if filetype == 'unix' else 'CIDR-нотация' if filetype == 'cidr' else 'Windows route' if filetype == 'win' else 'Mikrotik CLI' if filetype == 'mikrotik' else 'open vpn' if filetype == 'ovpn' else 'Keenetic CLI' if filetype == 'keenetic' else 'Wireguard' if filetype == 'wireguard' else 'спросить у пользователя'}")
            
            if filetype in ['win', 'unix', '']:
                print(f"{Style.BRIGHT}Шлюз/Имя интерфейса для Windows и Linux route:{Style.RESET_ALL} {gateway if gateway else 'спросить у пользователя'}")
            if filetype in ['keenetic', '']:
                print(f"{Style.BRIGHT}Шлюз/Имя интерфейса для Keenetic CLI:{Style.RESET_ALL} {ken_gateway if ken_gateway else 'спросить у пользователя'}")
            if filetype in ['mikrotik', '']:
                print(f"{Style.BRIGHT}Имя списка для Mikrotik firewall:{Style.RESET_ALL} {mk_list_name if mk_list_name else 'спросить у пользователя'}")
                print(f"{Style.BRIGHT}'comment=' в Mikrotik firewall:{Style.RESET_ALL} {'выключен' if mk_comment == 'off' else 'включен'}")
            print(f"{Style.BRIGHT}Сохранить результат в файл:{Style.RESET_ALL} {filename}")
            print(f"{Style.BRIGHT}Выполнить по завершению:{Style.RESET_ALL} {run_command if run_command else 'не указано'}")
            print(f"{Style.BRIGHT}Локальный список платформ:{Style.RESET_ALL} {'включен' if str(localplatform).strip().lower() in ('yes', 'y') else 'выключен'}")
            print(f"{Style.BRIGHT}Локальный список DNS серверов:{Style.RESET_ALL} {'включен' if str(localdns).strip().lower() in ('yes', 'y') else 'выключен'}")

        return service, request_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices, mk_list_name, subnet, ken_gateway, localplatform, localdns, mk_comment

    except Exception as e:
        print(f"{yellow(f'Ошибка загрузки {cfg_file}:')} {e}\n{Style.BRIGHT}Используются настройки 'по умолчанию'.{Style.RESET_ALL}")
        return '', 20, 'domain-ip-resolve.txt', '', '', '', '', [], '', '', '', '', '', 'off'

def gateway_input(gateway):
    if not gateway:
        input_gateway = input(f"Укажите {green('IP шлюза')} или {green('имя интерфейса')}: ")
        return input_gateway.strip() if input_gateway else None
    else:
        return gateway

def ken_gateway_input(ken_gateway):
    if not ken_gateway:
        input_ken_gateway = input(f"Укажите {green('IP шлюза')} или {green('имя интерфейса')} или {green('IP шлюза')} и через пробел {green('имя интерфейса')}: ")
        return input_ken_gateway.strip() if input_ken_gateway else None
    else:
        return ken_gateway

def get_semaphore(request_limit):
    return defaultdict(lambda: Semaphore(request_limit))

def init_semaphores(request_limit):
    return get_semaphore(request_limit)

async def load_urls(url: str) -> Dict[str, str]:
    try:
        client = await get_http_client()
        response = await client.get(url)
        response.raise_for_status()
        text = response.text
        lines = text.split('\n')
        urls = {}
        for line in lines:
            if line.strip() and ': ' in line:
                service, url_val = line.split(': ', 1)
                urls[service.strip()] = url_val.strip()
        return urls
    except Exception as e:
        print(f"Ошибка при загрузке списка платформ: {e}")
        return {}

async def load_urls_from_file() -> Dict[str, str]:
    try:
        with open('platformdb', 'r', encoding='utf-8') as file:
            urls = {}
            for line in file:
                if line.strip() and ': ' in line:
                    service, url = line.split(': ', 1)
                    urls[service.strip()] = url.strip()
            return urls
    except Exception as e:
        print(f"\n{red('Локальный список сервисов не найден - загружаем из сети.')}")
        urls = await load_urls(platform_db_url)
        return urls

async def load_dns_servers(url: str) -> Dict[str, List[str]]:
    try:
        client = await get_http_client()
        response = await client.get(url)
        response.raise_for_status()
        text = response.text
        lines = text.split('\n')
        dns_servers = {}
        for line in lines:
            if line.strip() and ': ' in line:
                service, servers = line.split(': ', 1)
                dns_servers[service.strip()] = servers.strip().split()
        return dns_servers
    except Exception as e:
        print(f"Ошибка при загрузке списка DNS серверов: {e}")
        return {}

async def load_dns_from_file() -> Dict[str, List[str]]:
    try:
        with open('dnsdb', 'r') as file:
            dns_servers = {}
            for line in file:
                if line.strip() and ': ' in line:
                    service, servers = line.split(': ', 1)
                    dns_servers[service.strip()] = servers.strip().split()
            return dns_servers
    except Exception as e:
        print(f"\n{red('Локальный список DNS серверов не найден - загружаем из сети.')}")
        dns_servers = await load_dns_servers(dns_db_url)
        return dns_servers

async def get_cloudflare_ips() -> Set[str]:
    try:
        client = await get_http_client()
        response = await client.get("https://www.cloudflare.com/ips-v4/")
        response.raise_for_status()
        text = response.text
        cloudflare_ips = set()
        
        for line in text.splitlines():
            line = line.strip()
            if '/' in line:
                try:
                    network = ipaddress.ip_network(line)
                    for ip in network:
                        cloudflare_ips.add(str(ip))
                except ValueError:
                    continue
        return cloudflare_ips
    except Exception as e:
        print("Ошибка при получении IP адресов Cloudflare:", e)
        return set()

async def load_dns_names(url_or_file: str) -> List[str]:
    if url_or_file.startswith("http"):
        client = await get_http_client()
        try:
            response = await client.get(url_or_file)
            response.raise_for_status()
            return [line.strip() for line in response.text.splitlines() if line.strip()]
        except httpx.HTTPStatusError as e:
            print(f"Ошибка при загрузке DNS имен: {e}")
            return []
    else:
        try:
            with open(url_or_file, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file.readlines() if line.strip()]
        except Exception as e:
            print(f"Ошибка при чтении файла {url_or_file}: {e}")
            return []

async def resolve_domain_batch(domains: List[str], resolver: dns.asyncresolver.Resolver, 
                              semaphore: Semaphore, dns_server_name: str, 
                              stats: Dict[str, int], cloudflare_ips: Set[str], 
                              include_cloudflare: bool) -> List[str]:
    async with semaphore:
        resolved_ips = []
        for domain in domains:
            try:
                stats['total_domains_processed'] += 1
                response = await resolver.resolve(domain)
                ips = [ip.address for ip in response]
                
                for ip_address in ips:
                    if ip_address in ('127.0.0.1', '0.0.0.0') or ip_address in resolver.nameservers:
                        stats['null_ips_count'] += 1
                    elif include_cloudflare and ip_address in cloudflare_ips:
                        stats['cloudflare_ips_count'] += 1
                    else:
                        resolved_ips.append(ip_address)
                        print(f"{Fore.BLUE}{domain} IP-адрес: {ip_address} - {dns_server_name}{Style.RESET_ALL}")
                        
            except Exception:
                stats['domain_errors'] += 1
        
        return resolved_ips

async def resolve_dns_optimized(service: str, dns_names: List[str], 
                               dns_servers: List[Tuple[str, List[str]]], 
                               cloudflare_ips: Set[str], unique_ips_all_services: Set[str],
                               semaphore_dict: Dict, stats: Dict[str, int], 
                               include_cloudflare: bool, batch_size: int = 50) -> str:
    try:
        print(f"{Fore.YELLOW}Загрузка DNS имен платформы {service}...{Style.RESET_ALL}")
        
        domain_batches = [dns_names[i:i + batch_size] for i in range(0, len(dns_names), batch_size)]
        
        tasks = []
        
        for batch in domain_batches:
            for server_name, servers in dns_servers:
                resolver = dns.asyncresolver.Resolver()
                resolver.nameservers = servers
                
                tasks.append(resolve_domain_batch(
                    batch, resolver, semaphore_dict[server_name], 
                    server_name, stats, cloudflare_ips, include_cloudflare
                ))
        
        max_concurrent_tasks = min(len(tasks), 100)
        
        results = []
        for i in range(0, len(tasks), max_concurrent_tasks):
            batch_tasks = tasks[i:i + max_concurrent_tasks]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if not isinstance(result, Exception):
                    results.extend(result)
        
        unique_ips_current_service = set()
        for ip_address in results:
            if ip_address not in unique_ips_all_services:
                unique_ips_current_service.add(ip_address)
                unique_ips_all_services.add(ip_address)
        
        return '\n'.join(sorted(unique_ips_current_service)) + '\n' if unique_ips_current_service else ''
        
    except Exception as e:
        print(f"Не удалось сопоставить IP адреса {service} его доменным именам: {e}")
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
            for idx, (service_name, url) in enumerate(urls.items(), 1):
                print(f"{idx}. {service_name.capitalize()}")
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

def check_include_cloudflare(cloudflare):
    if cloudflare in ['yes', 'y', 'no', 'n']:
        return cloudflare in ['yes', 'y']

    user_input = input(
        f"\n{yellow('Исключить IP адреса Cloudflare из итогового списка?')}"
        f"\n1. исключить"
        f"\n{green('Enter')} - оставить"
        f"\nВаш выбор: "
    ).strip()

    if user_input == '1':
        return True
    else:
        return False

def check_dns_servers(dns_servers, dns_server_indices):
    system_dns_servers = dns.asyncresolver.Resolver().nameservers
    dns_server_options = [('Системный DNS', system_dns_servers)] + list(dns_servers.items())
    selected_dns_servers = []

    if dns_server_indices:
        if 0 in dns_server_indices:
            selected_dns_servers = dns_server_options
        else:
            for idx in dns_server_indices:
                if 1 <= idx <= len(dns_server_options):
                    selected_dns_servers.append(dns_server_options[idx - 1])
        return selected_dns_servers

    while True:
        print(f"\n{yellow('Какие DNS серверы использовать?')}")
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

def mk_list_name_input(mk_list_name):
    if not mk_list_name:
        input_mk_list_name = input(f"Введите {green('LIST_NAME')} для Mikrotik firewall: ")
        return input_mk_list_name.strip() if input_mk_list_name else None
    else:
        return mk_list_name

def comment(selected_service):
    return ",".join(["".join(word.title() for word in s.split()) for s in selected_service])

def subnet_input(subnet):
    if not subnet:
        choice = input(
            f"\n{yellow('Объединить IP-адреса в подсети?')}"
            f"\n1. сократить до {green('/16')} (255.255.0.0)"
            f"\n2. сократить до {green('/24')} (255.255.255.0)"
            f"\n3. сократить до {green('/24')} + {green('/32')} (255.255.255.0 и 255.255.255.255)"
            f"\n4. сократить до {green('/24')} + {green('/32')} (255.255.255.0 и 255.255.255.255) и совместить до максимально возможного"
            f"\n{green('Enter')} - пропустить"
            f"\nВаш выбор: "
        ).strip()

        if choice == '1':
            subnet = '16'
        elif choice == '2':
            subnet = '24'
        elif choice == '3':
            subnet = 'mix'
        elif choice == '4':
            subnet = 'netaddr'
        else:
            subnet = '32'

    return subnet if subnet in {'16', '24', 'mix', 'netaddr'} else '32'

def group_ips_in_subnets_optimized(filename: str, subnet: str):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            ips = {line.strip() for line in file if line.strip()}

        subnets = set()

        if subnet == "16":
            for ip in ips:
                try:
                    network = ipaddress.IPv4Network(f"{ip}/16", strict=False)
                    subnets.add(str(network.network_address))
                except ValueError:
                    continue
            print(f"{Style.BRIGHT}IP-адреса агрегированы до /16 подсети{Style.RESET_ALL}")

        elif subnet == "24":
            for ip in ips:
                try:
                    network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                    subnets.add(str(network.network_address))
                except ValueError:
                    continue
            print(f"{Style.BRIGHT}IP-адреса агрегированы до /24 подсети{Style.RESET_ALL}")

        elif subnet == "mix":
            octet_groups = defaultdict(list)
            for ip in ips:
                key = '.'.join(ip.split('.')[:3])
                octet_groups[key].append(ip)

            for key, group in octet_groups.items():
                if len(group) > 1:
                    subnets.add(key + '.0')
                else:
                    subnets.update(group)
            print(f"{Style.BRIGHT}IP-адреса агрегированы до масок /24 и /32{Style.RESET_ALL}")

        elif subnet == "netaddr":
            octet_groups = defaultdict(list)
            for ip in ips:
                key = '.'.join(ip.split('.')[:3])
                octet_groups[key].append(ip)

            for key, group in octet_groups.items():
                if len(group) > 1:
                    subnets.add(key + '.0')
                else:
                    subnets.update(group)
            print(f"{Style.BRIGHT}IP-адреса агрегированы до максимально возможного размера масок{Style.RESET_ALL}")

        with open(filename, 'w', encoding='utf-8') as file:
            for subnet_ip in sorted(subnets, key=lambda x: ipaddress.IPv4Address(x.split('/')[0])):
                file.write(subnet_ip + '\n')

    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")

def process_file_format(filename, filetype, gateway, selected_service, mk_list_name, mk_comment, subnet, ken_gateway):
    def read_file(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return None

    def write_file(filename, ips, formatter, subnet, merged_list):
        if subnet == "netaddr":
            formatted_ips = [formatter(ip) for ip in range(len(merged_list))]
            with open(filename, 'w', encoding='utf-8') as file:
                if filetype.lower() == 'wireguard':
                    file.write(', '.join(formatted_ips))
                else:
                    file.write('\n'.join(formatted_ips))
        else:
            formatted_ips = [formatter(ip.strip()) for ip in ips]
            with open(filename, 'w', encoding='utf-8') as file:
                if filetype.lower() == 'wireguard':
                    file.write(', '.join(formatted_ips))
                else:
                    file.write('\n'.join(formatted_ips))

    net_mask = subnet if subnet == "netaddr" or "mix" else "255.255.0.0" if subnet == "16" else "255.255.255.0" if subnet == "24" else "255.255.255.255"

    if not filetype:
        user_input = input(f"""
{yellow('В каком формате сохранить файл?')}
1. {green('win')} - route add {cyan('IP')} mask {net_mask} {cyan('GATEWAY')}
2. {green('unix')} - ip route {cyan('IP')}/{subnet} {cyan('GATEWAY')}
3. {green('keenetic bat')} - route add {cyan('IP')} mask {net_mask} 0.0.0.0
4. {green('keenetic cli')} - ip route {cyan('IP')}/{subnet} {cyan('GATEWAY GATEWAY_NAME')} auto !{comment(selected_service)}
5. {green('cidr')} - {cyan('IP')}/{subnet}
6. {green('mikrotik')} - /ip/firewall/address-list add list={cyan("LIST_NAME")}{f' comment="{comment(selected_service)}"' if mk_comment != "off" else ""} address={cyan("IP")}/{subnet}
7. {green('ovpn')} - push "route {cyan('IP')} {net_mask}"
8. {green('wireguard')} - {cyan('IP')}/{subnet}, {cyan('IP')}/{subnet}, и т.д...
{green('Enter')} - {cyan('IP')}
Ваш выбор: """).strip()

        mapping = {
            '1': 'win',
            '2': 'unix',
            '3': 'keenetic bat',
            '4': 'keenetic cli',
            '5': 'cidr',
            '6': 'mikrotik',
            '7': 'ovpn',
            '8': 'wireguard'
        }
        filetype = mapping.get(user_input, '')

    ips = read_file(filename)
    if not ips:
        return

    if filetype in ['win', 'unix']:
        gateway = gateway_input(gateway)
    elif filetype == 'keenetic cli':
        ken_gateway = ken_gateway_input(ken_gateway)
    elif filetype == 'mikrotik':
        mk_list_name = mk_list_name_input(mk_list_name)

    formatters = {
        'win': lambda ip: f"route add {ip} mask {net_mask} {gateway}",
        'unix': lambda ip: f"ip route {ip}/{subnet} {gateway}",
        'keenetic bat': lambda ip: f"route add {ip} mask {net_mask} 0.0.0.0",
        'keenetic cli': lambda ip: f"ip route {ip}/{subnet} {ken_gateway} auto !{comment(selected_service)}",
        'cidr': lambda ip: f"{ip}/{subnet}",
        'ovpn': lambda ip: f'push "route {ip} {net_mask}"',
        'mikrotik': lambda ip: f'/ip/firewall/address-list add list={mk_list_name}' + (f' comment="{comment(selected_service)}"' if mk_comment != "off" else "") + f' address={ip}/{subnet}',
        'wireguard': lambda ip: f"{ip}/{subnet}"
    }

    if subnet == "mix":
        if filetype in ['win', 'keenetic bat']:
            mix_formatter = lambda ip: f"{ip.strip()} mask 255.255.255.0" if ip.endswith('.0') else f"{ip.strip()} mask 255.255.255.255"
        elif filetype.lower() == 'ovpn':
            mix_formatter = lambda ip: f"{ip.strip()} 255.255.255.0" if ip.endswith('.0') else f"{ip.strip()} 255.255.255.255"
        else:
            mix_formatter = lambda ip: f"{ip.strip()}/24" if ip.endswith('.0') else f"{ip.strip()}/32"

        formatters.update({
            'win': lambda ip: f"route add {mix_formatter(ip)} {gateway}",
            'unix': lambda ip: f"ip route {mix_formatter(ip)} {gateway}",
            'keenetic bat': lambda ip: f"route add {mix_formatter(ip)} 0.0.0.0",
            'keenetic cli': lambda ip: f"ip route {mix_formatter(ip)} {ken_gateway} auto !{comment(selected_service)}",
            'cidr': lambda ip: f"{mix_formatter(ip)}",
            'ovpn': lambda ip: f'push "route {mix_formatter(ip)}"',
            'mikrotik': lambda ip: f'/ip/firewall/address-list add list={mk_list_name}' + (f' comment="{comment(selected_service)}"' if mk_comment != "off" else "") + f' address={mix_formatter(ip)}',
            'wireguard': lambda ip: f"{mix_formatter(ip)}"
        })
    
    if subnet == "netaddr":
        list = []
        for ip in ips:
            if ip.endswith('.0\n'):
                list.append(f"{ip.strip()}/24")
            else:
                list.append(f"{ip.strip()}/32")
        merged_list = netaddr.cidr_merge(list)

        if filetype in ['win', 'keenetic bat']:
            netaddr_formatter = lambda ip: f"{merged_list[ip].ip} mask {merged_list[ip].netmask}"
        elif filetype.lower() == 'ovpn':
            netaddr_formatter = lambda ip: f"{merged_list[ip].ip} {merged_list[ip].netmask}"
        else:
            netaddr_formatter = lambda ip: f"{merged_list[ip].cidr}"

        formatters.update({
            'win': lambda ip: f"route add {netaddr_formatter(ip)} {gateway}",
            'unix': lambda ip: f"ip route {netaddr_formatter(ip)} {gateway}",
            'keenetic bat': lambda ip: f"route add {netaddr_formatter(ip)} 0.0.0.0",
            'keenetic cli': lambda ip: f"ip route {netaddr_formatter(ip)} {ken_gateway} auto !{comment(selected_service)}",
            'cidr': lambda ip: f"{netaddr_formatter(ip)}",
            'ovpn': lambda ip: f'push "route {netaddr_formatter(ip)}"',
            'mikrotik': lambda ip: f'/ip/firewall/address-list add list={mk_list_name}' + (f' comment="{comment(selected_service)}"' if mk_comment != "off" else "") + f' address={netaddr_formatter(ip)}',
            'wireguard': lambda ip: f"{netaddr_formatter(ip)}"
        })


    if filetype.lower() in formatters:
        write_file(filename, ips, formatters[filetype.lower()], subnet, merged_list="")

async def main():
    parser = argparse.ArgumentParser(description="DNS resolver script with custom config file.")
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.ini',
        help='Путь к конфигурационному файлу (по умолчанию: config.ini)'
    )
    args = parser.parse_args()

    try:
        config_file = args.config
        (service, request_limit, filename, cloudflare, filetype, gateway, run_command, 
         dns_server_indices, mk_list_name, subnet, ken_gateway, localplatform, 
         localdns, mk_comment) = read_config(config_file)

        if localplatform in ['yes', 'y']:
            urls = await load_urls_from_file()
        else:
            urls = await load_urls(platform_db_url)

        local_dns_names = []
        if os.path.exists('custom-dns-list.txt'):
            with open('custom-dns-list.txt', 'r', encoding='utf-8') as file:
                local_dns_names = [line.strip() for line in file if line.strip()]

        selected_services = check_service_config(service, urls, local_dns_names)

        if localdns in ['yes', 'y']:
            dns_servers = await load_dns_from_file()
        else:
            dns_servers = await load_dns_servers(dns_db_url)

        selected_dns_servers = check_dns_servers(dns_servers, dns_server_indices)

        include_cloudflare = check_include_cloudflare(cloudflare)
        if include_cloudflare:
            cloudflare_ips = await get_cloudflare_ips()
        else:
            cloudflare_ips = set()

        unique_ips_all_services = set()
        semaphore = init_semaphores(request_limit)
        
        stats = {
            'null_ips_count': 0,
            'cloudflare_ips_count': 0,
            'total_domains_processed': 0,
            'domain_errors': 0
        }
        
        tasks = []

        for service_name in selected_services:
            if service_name == 'Custom DNS list':
                tasks.append(resolve_dns_optimized(
                    service_name, local_dns_names, selected_dns_servers, 
                    cloudflare_ips, unique_ips_all_services, semaphore, 
                    stats, include_cloudflare
                ))
            else:
                url_or_file = urls[service_name]
                dns_names = await load_dns_names(url_or_file)
                if dns_names:
                    tasks.append(resolve_dns_optimized(
                        service_name, dns_names, selected_dns_servers, 
                        cloudflare_ips, unique_ips_all_services, semaphore, 
                        stats, include_cloudflare
                    ))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            with open(filename, 'w', encoding='utf-8') as file:
                for result in results:
                    if isinstance(result, str) and result.strip():
                        file.write(result)
        else:
            with open(filename, 'w', encoding='utf-8') as file:
                pass

        print(f"\n{yellow('Проверка завершена.')}")
        print(f"{Style.BRIGHT}Всего обработано DNS имен:{Style.RESET_ALL} {stats['total_domains_processed']}")
        print(f"{Style.BRIGHT}Разрешено IP-адресов из DNS имен:{Style.RESET_ALL} {len(unique_ips_all_services)}")
        print(f"{Style.BRIGHT}Ошибок разрешения доменов:{Style.RESET_ALL} {stats['domain_errors']}")
        if stats['null_ips_count'] > 0:
            print(f"{Style.BRIGHT}Исключено IP-адресов 'заглушек':{Style.RESET_ALL} {stats['null_ips_count']}")
        if include_cloudflare:
            print(f"{Style.BRIGHT}Исключено IP-адресов Cloudflare:{Style.RESET_ALL} {stats['cloudflare_ips_count']}")
        print(f"{Style.BRIGHT}Использовались DNS серверы:{Style.RESET_ALL} " + ', '.join(
            [f'{pair[0]} ({", ".join(pair[1])})' for pair in selected_dns_servers]))


        subnet = subnet_input(subnet)
        if subnet != '32':
            group_ips_in_subnets_optimized(filename, subnet)

        process_file_format(filename, filetype, gateway, selected_services, mk_list_name, mk_comment, subnet, ken_gateway)

        if run_command:
            print("\nВыполнение команды после завершения скрипта...")
            os.system(run_command)
        else:
            print(f"\n{Style.BRIGHT}Результаты сохранены в файл:{Style.RESET_ALL}", filename)
            if os.name == 'nt':
                input(f"Нажмите {green('Enter')} для выхода...")

    except KeyboardInterrupt:
        print(f"\n{red('Программа прервана пользователем')}")
    except Exception as e:
        print(f"\n{red('Критическая ошибка:')} {e}")
    finally:
        await cleanup_http_client()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{red('Программа прервана пользователем')}")
    except Exception as e:
        print(f"\n{red('Критическая ошибка:')} {e}")
