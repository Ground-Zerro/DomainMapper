# gui/domainmapper_api.py
import sys
from pathlib import Path
from typing import List, Dict, Callable, Optional, Set
import ipaddress

CURRENT_FILE = Path(__file__).resolve()
GUI_DIR = CURRENT_FILE.parent
PROJECT_ROOT = GUI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from main import (
        load_dns_names,
        resolve_dns_with_workers,
        get_cloudflare_ips,
        get_http_client,
        cleanup_http_client
    )
    DM_AVAILABLE = True
except ImportError as e:
    DM_AVAILABLE = False
    print(f"⚠️ DomainMapper модули не найдены: {e}")


class DomainMapperAPI:
    _services_cache: Optional[List[str]] = None
    _dns_cache: Optional[Dict[str, List[str]]] = None
    _urls_cache: Optional[Dict[str, str]] = None
    _cf_ips_cache: Optional[Set[str]] = None

    def __init__(self):
        self.stats: Dict[str, int] = {
            'null_ips_count': 0,
            'cloudflare_ips_count': 0,
            'total_domains_processed': 0,
            'domain_errors': 0
        }
        self.all_ips: Set[str] = set()
        self.cf_ips: Set[str] = set()

    def get_available_services(self) -> List[str]:
        if DomainMapperAPI._services_cache is not None:
            return DomainMapperAPI._services_cache
        return [
            'YouTube', 'Google', 'Telegram', 'Discord',
            'Instagram', 'Facebook', 'Twitter', 'Netflix',
            'Spotify', 'OpenAI', 'GitHub', 'Steam', 'Apple'
        ]

    def get_available_dns(self) -> Dict[str, List[str]]:
        if DomainMapperAPI._dns_cache is not None:
            return DomainMapperAPI._dns_cache
        return {
            'Google': ['8.8.8.8', '8.8.4.4'],
            'Cloudflare': ['1.1.1.1', '1.0.0.1'],
            'Quad9': ['9.9.9.9'],
            'OpenDNS': ['208.67.222.222', '208.67.220.220']
        }

    def set_services_cache(self, services: List[str]):
        DomainMapperAPI._services_cache = services

    def set_dns_cache(self, dns: Dict[str, List[str]]):
        DomainMapperAPI._dns_cache = dns

    def set_urls_cache(self, urls: Dict[str, str]):
        DomainMapperAPI._urls_cache = urls

    def get_urls_cache(self) -> Optional[Dict[str, str]]:
        return DomainMapperAPI._urls_cache

    def set_cf_ips_cache(self, cf_ips: Set[str]):
        DomainMapperAPI._cf_ips_cache = cf_ips

    def get_cf_ips_cache(self) -> Optional[Set[str]]:
        return DomainMapperAPI._cf_ips_cache

    def clear_cache(self):
        DomainMapperAPI._services_cache = None
        DomainMapperAPI._dns_cache = None
        DomainMapperAPI._urls_cache = None
        DomainMapperAPI._cf_ips_cache = None

    async def _reset_http_client(self):
        import main
        main.http_client = None
        await get_http_client()

    async def _cleanup_http_client(self):
        import main
        await cleanup_http_client()
        main.http_client = None

    def _apply_subnet_mask(self, ips: List[str], subnet: str) -> List[str]:
        if subnet == '32':
            return [f"{ip}/32" for ip in ips if ip]
        elif subnet == '24':
            result = set()
            for ip in ips:
                try:
                    if '/' in ip:
                        network = ipaddress.ip_network(ip, strict=False)
                        result.add(f"{network.network_address}/24")
                    else:
                        network = ipaddress.ip_network(f"{ip}/24", strict=False)
                        result.add(f"{network.network_address}/24")
                except ValueError:
                    result.add(f"{ip}/24")
            return sorted(result)
        elif subnet == '16':
            result = set()
            for ip in ips:
                try:
                    if '/' in ip:
                        network = ipaddress.ip_network(ip, strict=False)
                        result.add(f"{network.network_address}/16")
                    else:
                        network = ipaddress.ip_network(f"{ip}/16", strict=False)
                        result.add(f"{network.network_address}/16")
                except ValueError:
                    result.add(f"{ip}/16")
            return sorted(result)
        elif subnet == 'mix':
            result = set()
            octet_groups: Dict[str, List[str]] = {}
            for ip in ips:
                key = '.'.join(ip.split('.')[:3]) if '/' not in ip else '.'.join(ip.split('/')[0].split('.')[:3])
                if key not in octet_groups:
                    octet_groups[key] = []
                octet_groups[key].append(ip)
            for key, group in octet_groups.items():
                if len(group) > 1:
                    result.add(f"{key}.0/24")
                else:
                    ip = group[0]
                    if '/' in ip:
                        result.add(ip)
                    else:
                        result.add(f"{ip}/32")
            return sorted(result)
        return ips

    def _format_comment(self, services: List[str]) -> str:
        return ",".join(["".join(word.title() for word in s.split()) for s in services])

    def _apply_output_format(self, ips: List[str], fmt: str, format_settings: Dict, services: List[str]) -> List[str]:
        subnet = format_settings.get('subnet', '32')

        def get_mask(ip: str) -> str:
            if subnet == 'mix':
                return '255.255.255.0' if ip.endswith('.0') else '255.255.255.255'
            elif subnet == '24':
                return '255.255.255.0'
            elif subnet == '16':
                return '255.255.0.0'
            else:
                return '255.255.255.255'

        if fmt == 'wireguard':
            return ips
        elif fmt == 'cidr':
            return ips
        elif fmt == 'ip':
            return [ip.split('/')[0] for ip in ips]
        elif fmt == 'win':
            gateway = format_settings.get('gateway', '')
            return [f"route add {ip} mask {get_mask(ip.split('/')[0])} {gateway}" for ip in ips]
        elif fmt == 'unix':
            gateway = format_settings.get('gateway', '')
            return [f"ip route {ip} {gateway}" for ip in ips]
        elif fmt == 'mikrotik':
            listname = format_settings.get('mk_listname', 'DM_List')
            mk_comment = format_settings.get('mk_comment', 'off')
            comment_str = f' comment="{self._format_comment(services)}"' if mk_comment == 'on' else ''
            return [f'/ip/firewall/address-list add list={listname}{comment_str} address={ip}' for ip in ips]
        elif fmt == 'ovpn':
            return [f'push "route {ip.split("/")[0]} {get_mask(ip.split("/")[0])}"' for ip in ips]
        elif fmt == 'keenetic':
            ken_gateway = format_settings.get('keenetic', '')
            return [f"ip route {ip} {ken_gateway} auto" for ip in ips]
        return ips

    async def parse_services(
        self,
        services: List[str],
        dns_servers: List[str],
        urls: Dict[str, str],
        dns_db: Dict[str, List[str]],
        exclude_cloudflare: bool = False,
        rate_limit: int = 50,
        subnet: str = '32',
        output_format: str = 'wireguard',
        format_settings: Optional[Dict] = None,
        on_progress: Optional[Callable[[str, int], None]] = None,
        custom_services: Optional[Dict[str, Dict[str, str]]] = None,
        use_local: bool = False
    ) -> Dict:
        if not DM_AVAILABLE:
            return {'error': 'DomainMapper модули недоступны', 'success': False}

        self.stats = {
            'null_ips_count': 0,
            'cloudflare_ips_count': 0,
            'total_domains_processed': 0,
            'domain_errors': 0
        }
        self.all_ips = set()

        if format_settings is None:
            format_settings = {}
        format_settings['subnet'] = subnet

        custom_services = custom_services or {}

        try:
            await self._reset_http_client()

            cf_ips = set()
            if exclude_cloudflare:
                if DomainMapperAPI._cf_ips_cache is None:
                    cf_ips = await get_cloudflare_ips()
                    DomainMapperAPI._cf_ips_cache = cf_ips
                else:
                    cf_ips = DomainMapperAPI._cf_ips_cache

            selected_dns = [(name, dns_db[name]) for name in dns_servers if name in dns_db]
            if not selected_dns:
                return {'error': 'Не выбрано ни одного DNS-сервера', 'success': False}

            parsed_services = []

            for idx, service in enumerate(services):
                if on_progress:
                    on_progress(f"Обработка сервиса: {service}", int((idx / len(services)) * 100))

                # Обработка кастомных сервисов
                if service in custom_services:
                    data = custom_services[service]
                    if isinstance(data, dict):
                        source = data.get('source', '')
                        source_type = data.get('type', 'url')
                    else:
                        source = data
                        source_type = 'manual' if '\n' in data else 'url'

                    if source_type == 'manual':
                        domains = [line.strip() for line in source.split('\n') if line.strip()]
                    elif source_type == 'file':
                        try:
                            with open(source, 'r', encoding='utf-8') as f:
                                domains = [line.strip() for line in f if line.strip()]
                        except Exception as e:
                            if on_progress:
                                on_progress(f"❌ Ошибка чтения файла {source}: {e}", int((idx / len(services)) * 100))
                            continue
                    else:  # url
                        domains = await load_dns_names(source)
                elif service in urls:
                    try:
                        # === ЛОКАЛЬНЫЙ РЕЖИМ ===
                        if use_local:
                            # Конструируем путь к файлу в папке platforms
                            # Предполагаем имя файла dns-{service}.txt (например dns-youtube.txt)
                            file_name = f"dns-{service.lower()}.txt"
                            local_path = PROJECT_ROOT / 'platforms' / file_name
                            if local_path.exists():
                                domains = await load_dns_names(str(local_path))
                            else:
                                # Пробуем без префикса dns-
                                local_path_alt = PROJECT_ROOT / 'platforms' / f"{service.lower()}.txt"
                                if local_path_alt.exists():
                                    domains = await load_dns_names(str(local_path_alt))
                                else:
                                    if on_progress:
                                        on_progress(f"⚠️ Локальный файл не найден: {file_name}", int((idx / len(services)) * 100))
                                    continue
                        else:
                            # === СЕТЕВОЙ РЕЖИМ ===
                            domains = await load_dns_names(urls[service])
                        
                        if not domains:
                            if on_progress:
                                on_progress(f"⚠️ Нет доменов для сервиса: {service}", int((idx / len(services)) * 100))
                            continue

                        await resolve_dns_with_workers(
                            service=service,
                            dns_names=domains,
                            dns_servers=selected_dns,
                            cloudflare_ips=cf_ips,
                            unique_ips_all_services=self.all_ips,
                            stats=self.stats,
                            include_cloudflare=not exclude_cloudflare,
                            rate_limit=rate_limit
                        )
                        parsed_services.append(service)

                        if on_progress:
                            on_progress(f"Найдено IP: {len(self.all_ips)}", int((idx / len(services)) * 100))
                    except Exception as e:
                        if on_progress:
                            on_progress(f"Ошибка сервиса {service}: {str(e)[:50]}", int((idx / len(services)) * 100))
                        continue
                else:
                    if on_progress:
                        on_progress(f"⚠️ Сервис не найден: {service}", int((idx / len(services)) * 100))
                    continue

            final_ips = self._apply_subnet_mask(list(self.all_ips), subnet)
            final_ips = self._apply_output_format(final_ips, output_format, format_settings, services)

            await self._cleanup_http_client()

            return {
                'success': True,
                'ips': final_ips,
                'stats': self.stats.copy(),
                'services': parsed_services,
                'total_ips': len(final_ips)
            }

        except Exception as e:
            import traceback
            try:
                await self._cleanup_http_client()
            except:
                pass
            return {'error': str(e) + '\n' + traceback.format_exc(), 'success': False}


dm_api = DomainMapperAPI()