import argparse
import asyncio
import configparser
import ipaddress
import os
import time
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional

import dns.asyncresolver
import httpx
from colorama import Fore, Style, init
from tqdm import tqdm

init(autoreset=True)

class ProgressTracker:
    def __init__(self, total: int, stats: Dict, unique_ips_set: Set[str],
                 num_dns_servers: int = 1, rate_limit: int = 10, domains_count: int = 0):
        self.total = total
        self.stats = stats
        self.unique_ips = unique_ips_set
        self.pbar = None
        self.lock = asyncio.Lock()
        self.num_dns_servers = num_dns_servers
        self.rate_limit = rate_limit
        self.domains_count = domains_count
        self.effective_rate = num_dns_servers * rate_limit
        self.start_time = time.time()
    
    def start(self):
        self.pbar = tqdm(
            total=self.total,
            bar_format='[{bar:40}] {percentage:3.1f}% | Прошло: {elapsed} | Осталось (примерно): {desc}',
            unit=' запр',
            ncols=120,
            leave=True,
            mininterval=0,
            desc='расчет...'
        )

    async def update_progress(self):
        if self.pbar:
            async with self.lock:
                processed = self.stats.get('total_domains_processed', 0)
                remaining_time = self.calculate_remaining_time()

                self.pbar.n = processed
                self.pbar.set_description_str(remaining_time)
                self.pbar.refresh()

    def format_time(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def calculate_remaining_time(self) -> str:
        processed = self.stats.get('total_domains_processed', 0)
        remaining = self.total - processed

        if self.effective_rate > 0:
            time_remaining = remaining / self.effective_rate
            return self.format_time(time_remaining)
        return "00:00"

    def close(self):
        if self.pbar:
            self.pbar.n = self.total
            self.pbar.refresh()
            self.pbar.close()

        elapsed = time.time() - self.stats['start_time']
        total = self.stats['total_domains']
        processed = self.stats['total_domains_processed']
        errors = self.stats['domain_errors']

        error_pct = (errors / total * 100) if total > 0 else 0
        total_ips_found = len(self.unique_ips) + self.stats['null_ips_count'] + self.stats.get('cloudflare_ips_count', 0)
        null_pct = (self.stats['null_ips_count'] / total_ips_found * 100) if total_ips_found > 0 else 0
        cf_pct = (self.stats.get('cloudflare_ips_count', 0) / total_ips_found * 100) if total_ips_found > 0 else 0

        print(f"\n{yellow('Проверка завершена.')}")
        print(f"{Style.BRIGHT}Всего обработано DNS имен:{Style.RESET_ALL} {processed} из {total}")
        print(f"{Style.BRIGHT}Разрешено уникальных IP-адресов:{Style.RESET_ALL} {len(self.unique_ips)}")
        print(f"{Style.BRIGHT}Ошибок разрешения доменов:{Style.RESET_ALL} {errors} ({error_pct:.1f}%)")

        if self.stats['null_ips_count'] > 0:
            print(f"{Style.BRIGHT}Исключено IP-адресов 'заглушек':{Style.RESET_ALL} {self.stats['null_ips_count']} ({null_pct:.1f}%)")

        if self.stats.get('cloudflare_ips_count', 0) > 0:
            print(f"{Style.BRIGHT}Исключено IP-адресов Cloudflare:{Style.RESET_ALL} {self.stats['cloudflare_ips_count']} ({cf_pct:.1f}%)")

class PeriodicProgressUpdater:
    def __init__(self, progress_tracker: ProgressTracker, stats: Dict):
        self.progress_tracker = progress_tracker
        self.stats = stats
        self.is_running = False
        self.task = None

    async def start(self):
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._periodic_update())

    async def stop(self):
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass

    async def _periodic_update(self):
        await asyncio.sleep(2)
        while self.is_running:
            try:
                await self.progress_tracker.update_progress()
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in periodic progress update: {e}")
                await asyncio.sleep(2)

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
        rate_limit = int(config.get('rate_limit') or 50)
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
            print(f"{Style.BRIGHT}Лимит запросов к каждому DNS серверу (запросов/сек):{Style.RESET_ALL} {rate_limit}")
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

        return service, rate_limit, filename, cloudflare, filetype, gateway, run_command, dns_server_indices, mk_list_name, subnet, ken_gateway, localplatform, localdns, mk_comment

    except Exception as e:
        print(f"{yellow(f'Ошибка загрузки {cfg_file}:')} {e}\n{Style.BRIGHT}Используются настройки 'по умолчанию'.{Style.RESET_ALL}")
        return '', 50, 'domain-ip-resolve.txt', '', '', '', '', [], '', '', '', '', '', 'off'

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

class DNSServerWorker:
    def __init__(self, name: str, nameservers: List[str], rate_limit: int = 10, stats_lock=None):
        self.name = name
        self.nameservers = nameservers
        self.rate_limit = rate_limit
        self.queue = asyncio.Queue()
        self.request_times = deque()
        self.results = []
        self.stats = {
            'processed': 0,
            'errors': 0,
            'success': 0
        }
        self.stats_lock = stats_lock or asyncio.Lock()
        self.rate_limit_lock = asyncio.Lock()

    async def add_domain(self, domain: str):
        await self.queue.put(domain)

    async def _enforce_rate_limit(self):
        async with self.rate_limit_lock:
            now = time.monotonic()

            while self.request_times and now - self.request_times[0] >= 1.0:
                self.request_times.popleft()

            if len(self.request_times) >= self.rate_limit:
                sleep_time = 1.0 - (now - self.request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    now = time.monotonic()
                    while self.request_times and now - self.request_times[0] >= 1.0:
                        self.request_times.popleft()

            self.request_times.append(now)

    async def process_queue(self, global_stats: Dict[str, int]):
        resolver = dns.asyncresolver.Resolver()
        resolver.nameservers = self.nameservers
        resolver.timeout = 10.0
        resolver.lifetime = 15.0

        domains = []
        while not self.queue.empty():
            domain = await self.queue.get()
            domains.append(domain)

        async def process_single_domain(domain):
            await self._enforce_rate_limit()

            try:
                response = await resolver.resolve(domain)
                ips = [ip.address for ip in response]

                async with self.stats_lock:
                    global_stats['total_domains_processed'] += 1
                    self.stats['processed'] += 1
                    self.stats['success'] += 1

                return ips
            except dns.resolver.NoNameservers:
                async with self.stats_lock:
                    global_stats['total_domains_processed'] += 1
                    global_stats['domain_errors'] += 1
                    self.stats['processed'] += 1
                    self.stats['errors'] += 1
                return []
            except dns.resolver.Timeout:
                async with self.stats_lock:
                    global_stats['total_domains_processed'] += 1
                    global_stats['domain_errors'] += 1
                    self.stats['processed'] += 1
                    self.stats['errors'] += 1
                return []
            except dns.resolver.NXDOMAIN:
                async with self.stats_lock:
                    global_stats['total_domains_processed'] += 1
                    global_stats['domain_errors'] += 1
                    self.stats['processed'] += 1
                    self.stats['errors'] += 1
                return []
            except dns.resolver.NoAnswer:
                async with self.stats_lock:
                    global_stats['total_domains_processed'] += 1
                    global_stats['domain_errors'] += 1
                    self.stats['processed'] += 1
                    self.stats['errors'] += 1
                return []
            except Exception:
                async with self.stats_lock:
                    global_stats['total_domains_processed'] += 1
                    global_stats['domain_errors'] += 1
                    self.stats['processed'] += 1
                    self.stats['errors'] += 1
                return []

        results = await asyncio.gather(*[process_single_domain(domain) for domain in domains], return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                self.results.extend(result)

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

async def resolve_dns_with_workers(service: str, dns_names: List[str],
                                   dns_servers: List[Tuple[str, List[str]]],
                                   cloudflare_ips: Set[str], unique_ips_all_services: Set[str],
                                   stats: Dict[str, int], include_cloudflare: bool,
                                   rate_limit: int, stats_lock: asyncio.Lock = None) -> str:
    try:
        if stats_lock is None:
            stats_lock = asyncio.Lock()

        workers = []
        for server_name, servers in dns_servers:
            worker = DNSServerWorker(server_name, servers, rate_limit, stats_lock)
            workers.append(worker)

        for domain in dns_names:
            for worker in workers:
                await worker.add_domain(domain)

        tasks = [worker.process_queue(stats) for worker in workers]

        await asyncio.gather(*tasks)

        all_nameservers = set()
        for _, servers in dns_servers:
            all_nameservers.update(servers)

        unique_ips_current_service = set()
        for worker in workers:
            for ip_address in worker.results:
                if ip_address in ('127.0.0.1', '0.0.0.0') or ip_address in all_nameservers:
                    stats['null_ips_count'] += 1
                    continue

                if include_cloudflare and ip_address in cloudflare_ips:
                    stats['cloudflare_ips_count'] += 1
                    continue

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
            f"\n{green('Enter')} - пропустить"
            f"\nВаш выбор: "
        ).strip()

        if choice == '1':
            subnet = '16'
        elif choice == '2':
            subnet = '24'
        elif choice == '3':
            subnet = 'mix'
        else:
            subnet = '32'

    return subnet if subnet in {'16', '24', 'mix'} else '32'

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

        with open(filename, 'w', encoding='utf-8') as file:
            for subnet_ip in sorted(subnets, key=lambda x: ipaddress.IPv4Address(x.split('/')[0])):
                file.write(subnet_ip + '\n')

    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")

def split_file_by_lines(filename: str, max_lines: int = 999):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        total_lines = len(lines)

        if total_lines <= max_lines:
            return False

        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        extension = '.' + filename.rsplit('.', 1)[1] if '.' in filename else '.txt'

        num_parts = (total_lines + max_lines - 1) // max_lines

        print(f"\n{Style.BRIGHT}Результаты сохранены в файлы:{Style.RESET_ALL}")
        for part in range(num_parts):
            start_index = part * max_lines
            end_index = min((part + 1) * max_lines, total_lines)

            part_filename = f"{base_name}_p{part + 1}{extension}"

            with open(part_filename, 'w', encoding='utf-8') as file:
                file.writelines(lines[start_index:end_index])

            print(f"{Style.BRIGHT}{part_filename} ({end_index - start_index} строк){Style.RESET_ALL}")

        print(f"{Style.BRIGHT}Разделение завершено. Создано {num_parts} частей{Style.RESET_ALL}")

        try:
            os.remove(filename)
        except Exception as e:
            print(f"{red('Не удалось удалить исходный файл:')} {e}")

        return True

    except Exception as e:
        print(f"{red('Ошибка при разделении файла:')} {e}")
        return False

def process_file_format(filename, filetype, gateway, selected_service, mk_list_name, mk_comment, subnet, ken_gateway):
    def read_file(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return None

    def write_file(filename, ips, formatter):
        formatted_ips = [formatter(ip.strip()) for ip in ips]
        with open(filename, 'w', encoding='utf-8') as file:
            if filetype.lower() == 'wireguard':
                file.write(', '.join(formatted_ips))
            else:
                file.write('\n'.join(formatted_ips))

    net_mask = subnet if subnet == "mix" else "255.255.0.0" if subnet == "16" else "255.255.255.0" if subnet == "24" else "255.255.255.255"

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

    if filetype.lower() in formatters:
        write_file(filename, ips, formatters[filetype.lower()])

        if filetype.lower() == 'keenetic bat':
            return split_file_by_lines(filename, max_lines=999)

    return False

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
        (service, rate_limit, filename, cloudflare, filetype, gateway, run_command, 
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

        stats = {
            'null_ips_count': 0,
            'cloudflare_ips_count': 0,
            'total_domains_processed': 0,
            'domain_errors': 0
        }

        total_domains = 0
        for service_name in selected_services:
            if service_name == 'Custom DNS list':
                total_domains += len(local_dns_names)
            else:
                url_or_file = urls[service_name]
                print(f"{Style.BRIGHT}Загрузка DNS имен платформы{Style.RESET_ALL} {service_name}...")
                dns_names = await load_dns_names(url_or_file)
                total_domains += len(dns_names)

        domains_count = total_domains
        total_domains *= len(selected_dns_servers)
        stats['total_domains'] = total_domains
        stats['start_time'] = time.time()

        print(f"{Style.BRIGHT}Загружено {domains_count} DNS имен.{Style.RESET_ALL}\n{yellow('Резолвинг...')}")

        progress_tracker = ProgressTracker(
            total=total_domains,
            stats=stats,
            unique_ips_set=unique_ips_all_services,
            num_dns_servers=len(selected_dns_servers),
            rate_limit=rate_limit,
            domains_count=domains_count
        )
        progress_tracker.start()

        stats_lock = asyncio.Lock()

        periodic_updater = PeriodicProgressUpdater(progress_tracker, stats)
        await periodic_updater.start()

        tasks = []

        for service_name in selected_services:
            if service_name == 'Custom DNS list':
                tasks.append(resolve_dns_with_workers(
                    service_name, local_dns_names, selected_dns_servers,
                    cloudflare_ips, unique_ips_all_services,
                    stats, include_cloudflare, rate_limit,
                    stats_lock
                ))
            else:
                url_or_file = urls[service_name]
                dns_names = await load_dns_names(url_or_file)
                if dns_names:
                    tasks.append(resolve_dns_with_workers(
                        service_name, dns_names, selected_dns_servers,
                        cloudflare_ips, unique_ips_all_services,
                        stats, include_cloudflare, rate_limit,
                        stats_lock
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

        await periodic_updater.stop()
        progress_tracker.close()

        print(f"{Style.BRIGHT}Использовались DNS серверы:{Style.RESET_ALL} " + ', '.join(
            [pair[0] for pair in selected_dns_servers]))

        print(f"\n{yellow('Обработка результатов...')}")

        subnet = subnet_input(subnet)
        if subnet != '32':
            group_ips_in_subnets_optimized(filename, subnet)

        file_was_split = process_file_format(filename, filetype, gateway, selected_services, mk_list_name, mk_comment, subnet, ken_gateway)

        if run_command:
            print("\nВыполнение команды после завершения скрипта...")
            os.system(run_command)
        else:
            if not file_was_split:
                print(f"\n{Style.BRIGHT}Результаты сохранены в файл:{Style.RESET_ALL}", filename)
            if os.name == 'nt':
                input(f"Нажмите {green('Enter')} для выхода...")

        print(f"\n{Style.BRIGHT}Если есть желание, можно угостить автора чашечкой какао:{Style.RESET_ALL} {green('https://boosty.to/ground_zerro')}")

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