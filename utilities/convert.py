import asyncio
import ipaddress
import re

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


# Промт cloudflare фильтр
def check_include_cloudflare(cloudflare):
    if cloudflare in ['yes', 'y', 'no', 'n']:
        return cloudflare in ['yes', 'y']
    return input(f"\n{yellow('Исключить IP адреса Cloudflare из итогового списка?')}"
                 f"\n{green('yes')} - исключить"
                 f"\n{green('Enter')} - оставить: ").strip().lower() in ['yes', 'y']


# комментарий для microtik firewall
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
    if not subnet:
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
    filename = "ip.txt"
    cloudflare = None
    subnet = None
    filetype = None
    gateway = None
    selected_services = ["service1", "service2"]  # Пример данных
    mk_list_name = None
    ken_gateway = None

    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

    # Открываем файл и читаем строки
    with open(filename, 'r') as file:
        # Создаем множество для хранения уникальных IP-адресов
        ips = set()

        # Проходим по каждой строке файла
        for line in file:
            # Ищем все IP-адреса в строке
            found_ips = ip_pattern.findall(line)
            # Добавляем найденные IP-адреса в множество
            ips.update(found_ips)

    # Фильтр Cloudflare
    include_cloudflare = check_include_cloudflare(cloudflare)
    if include_cloudflare:  # Загрузка IP-адресов Cloudflare
        cloudflare_ips = await get_cloudflare_ips()
    else:
        cloudflare_ips = set()

    # Удаляем IP-адреса Cloudflare
    ips -= cloudflare_ips

    with open(filename, 'w', encoding='utf-8-sig') as file:
        for ip in sorted(ips):
            file.write(ip + '\n')

    # Группировка IP-адресов в подсети
    subnet = subnet_input(subnet)
    if subnet != '32':  # Если не '32', вызываем функцию для агрегации
        group_ips_in_subnets(filename, subnet)

    process_file_format(filename, filetype, gateway, selected_services, mk_list_name, subnet, ken_gateway)


if __name__ == "__main__":
    asyncio.run(main())
