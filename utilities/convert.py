import asyncio
import ipaddress
import os
import re
from collections import defaultdict

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

def gateway_input(gateway):
    if not gateway:
        input_gateway = input(f"Укажите {green('IP шлюза')} или {green('имя интерфейса')}: ")
        return input_gateway.strip() if input_gateway else None
    else:
        return gateway

def ken_gateway_input(ken_gateway):
    if not ken_gateway:
        input_ken_gateway = input(
            f"Укажите {green('IP шлюза')} или {green('имя интерфейса')} или {green('IP шлюза')} и через пробел {green('имя интерфейса')}: ")
        return input_ken_gateway.strip() if input_ken_gateway else None
    else:
        return ken_gateway

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
    filename = "ip.txt"
    cloudflare = None
    subnet = None
    filetype = None
    gateway = None
    selected_services = ["Service"]
    mk_list_name = None
    mk_comment = 'off'
    ken_gateway = None

    if not os.path.exists(filename):
        print(f"\n{red(f'Ошибка: файл {filename} не найден!')}")
        print(f"{yellow('Инструкция:')}")
        print(f"1. Создайте файл {green(filename)} в текущей директории")
        print(f"2. Добавьте в него IP-адреса (по одному на строку) или текст содержащий IP-адреса")
        print(f"3. Запустите скрипт снова")
        return

    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

    with open(filename, 'r') as file:
        ips = set()
        for line in file:
            found_ips = ip_pattern.findall(line)
            ips.update(found_ips)

    include_cloudflare = check_include_cloudflare(cloudflare)
    if include_cloudflare:
        cloudflare_ips = await get_cloudflare_ips()
    else:
        cloudflare_ips = set()

    ips -= cloudflare_ips

    with open(filename, 'w', encoding='utf-8') as file:
        for ip in sorted(ips):
            file.write(ip + '\n')

    subnet = subnet_input(subnet)
    if subnet != '32':
        group_ips_in_subnets_optimized(filename, subnet)

    file_was_split = process_file_format(filename, filetype, gateway, selected_services, mk_list_name, mk_comment, subnet, ken_gateway)

    if not file_was_split:
        print(f"\n{Style.BRIGHT}Результаты сохранены в файл:{Style.RESET_ALL} {filename}")


if __name__ == "__main__":
    asyncio.run(main())
