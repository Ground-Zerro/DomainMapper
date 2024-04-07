import configparser
import ipaddress
import os
import re
from concurrent.futures import ThreadPoolExecutor

import dns.resolver
import requests

# URLs
urls = {
    'Antifilter community edition': "https://community.antifilter.download/list/domains.lst",
    'Youtube': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-youtube.txt",
    'Facebook': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-facebook.txt",
    'Openai': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-openai.txt",
    'Tik-Tok': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-tiktok.txt",
    'Instagram': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-instagram.txt",
    'Twitter': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-twitter.txt",
    'Netflix': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-netflix.txt",
    'Bing': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-bing.txt",
    'Adobe': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-adobe.txt",
    'Apple': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-apple.txt",
    'Google': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-google.txt",
    'Tor-Truckers': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-ttruckers.txt",
    'Search-engines': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-search-engines"
                      ".txt",
}


# Function to resolve DNS
def resolve_dns_and_write(service, url, unique_ips_all_services, include_cloudflare, threads):
    try:
        print(f"Загрузка данных - {service}")
        response = requests.get(url)
        response.raise_for_status()
        dns_names = response.text.split('\n')

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ['8.8.8.8', '8.8.4.4', '208.67.222.222', '208.67.220.220', '4.2.2.1', '4.2.2.2',
                                '149.112.112.112']  # Public DNS servers
        resolver.rotate = True
        resolver.timeout = 1
        resolver.lifetime = 1

        if include_cloudflare:
            cloudflare_ips = get_cloudflare_ips()
        else:
            cloudflare_ips = set()

        unique_ips_current_service = set()  # Set to store unique IP addresses for the current service

        print(f"Анализ DNS имен платформы: {service}")

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for domain in dns_names:
                if domain.strip():
                    future = executor.submit(resolve_domain, resolver, domain, unique_ips_current_service,
                                             unique_ips_all_services, cloudflare_ips)
                    futures.append(future)

            # Дождаться завершения всех задач
            for future in futures:
                future.result()

        print(f"Список IP-адресов для платформы {service} создан.")
        return '\n'.join(unique_ips_current_service) + '\n'
    except Exception as e:
        print(f"Не удалось сопоставить IP адреса {service} его доменным именам.", e)
        return ""


# Function to get Cloudflare IP addresses
def get_cloudflare_ips():
    try:
        response = requests.get("https://www.cloudflare.com/ips-v4/")
        response.raise_for_status()
        cloudflare_ips = set()

        # Extract CIDR blocks from the response text using regular expressions
        cidr_blocks = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})', response.text)

        for cidr in cidr_blocks:
            ip_network = ipaddress.ip_network(cidr)
            for ip in ip_network:
                cloudflare_ips.add(str(ip))

        return cloudflare_ips
    except Exception as e:
        print("Ошибка при получении IP адресов Cloudflare:", e)
        return set()


# Function resolve domain
def resolve_domain(resolver, domain, unique_ips_current_service, unique_ips_all_services, cloudflare_ips):
    try:
        ips = resolver.resolve(domain)
        for ip in ips:
            ip_address = ip.address
            if (ip_address not in ('127.0.0.1', '0.0.0.1') and
                    ip_address not in resolver.nameservers and
                    ip_address not in cloudflare_ips and
                    ip_address not in unique_ips_all_services):  # Check for uniqueness
                unique_ips_current_service.add(ip_address)
                unique_ips_all_services.add(ip_address)
                print(f"\033[36m{domain} IP адрес: {ip_address}\033[0m")
    except Exception as e:
        print(f"\033[31mНе удалось обработать: {domain}\033[0m - {e}")


# Function to read configuration file
def read_config(filename):
    try:
        config = configparser.ConfigParser()
        with open(filename, 'r', encoding='utf-8-sig') as file:
            config.read_file(file)
        if 'DomainMapper' in config:
            config = config['DomainMapper']
        service = config.get('service') or ''
        threads = int(config.get('threads') or 20)
        filename = config.get('filename') or 'domain-ip-resolve.txt'
        cloudflare = config.get('cloudflare') or ''
        filetype = config.get('filetype') or ''
        gateway = config.get('gateway') or ''
        run_command = config.get('run') or ''

        print("Загружена конфигурация из config.ini.")
        return service, threads, filename, cloudflare, filetype, gateway, run_command

    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        service = ''
        threads = int(20)
        filename = 'domain-ip-resolve.txt'
        cloudflare = ''
        filetype = ''
        gateway = ''
        run_command = ''

        return service, threads, filename, cloudflare, filetype, gateway, run_command


def gateway_input(gateway):
    if not gateway:
        input_gateway = input(f"Укажите \033[32mшлюз\033[0m или \033[32mимя интерфейса\033[0m: ")
        if input_gateway:
            return input_gateway.strip()
    else:
        return gateway


# Function to check if 'service' is specified in the configuration file
def check_service_config(service):
    if service:
        if service.strip().lower() == "all":
            return list(urls.keys())  # Select all available services
        else:
            return [s.strip() for s in service.split(',')]
    else:
        selected_services = []
        while True:
            if os.name == 'nt':  # Для пользователей Windows
                os.system('cls')  # Очистить экран
            else:
                os.system('clear')
            print("\nВыберите сервисы:\n")
            print("0 - Отметить все")
            for idx, (service, url) in enumerate(urls.items(), 1):
                checkbox = "[*]" if service in selected_services else "[ ]"
                print(f"{idx}. {service.capitalize()}  {checkbox}")

            selection = input("\n\033[32mВведите номер сервиса\033[0m и нажмите Enter (Пустая строка "
                              "и \033[32mEnter\033[0m для старта): ")
            if selection == "0":
                selected_services = list(urls.keys())
            elif selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(urls):
                    service = list(urls.keys())[idx]
                    if service in selected_services:
                        selected_services.remove(service)
                    else:
                        selected_services.append(service)
            elif selection == "":
                break
        return selected_services


# Function to check if to include Cloudflare IPs based on configuration or user input
def check_include_cloudflare(cloudflare):
    if cloudflare.lower() == 'yes':
        return True
    elif cloudflare.lower() == 'no':
        return False
    else:
        return input("Исключить IP адреса Cloudflare из итогового списка? (\033[32myes\033[0m "
                     "- исключить, \033[32mEnter\033[0m - оставить): ").strip().lower() == "yes"


# Function to process file format
def process_file_format(filename, filetype, gateway):
    if not filetype:
        filetype = input("\nВыберите в каком формате сохранить файл: \n\033[32mwin\033[0m"
                         " - 'route add %IP% mask %mask% %gateway%', \033[32munix\033[0m"
                         " - 'ip route %IP%/%mask% %gateway%', \033[32mcidr\033[0m"
                         " - 'IP/mask', \033[32mEnter\033[0m - только IP: ")

    if filetype.lower() in ['win', 'unix']:
        # Обработка файлов разных форматов
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
        # Обработка CIDR формата
        try:
            with open(filename, 'r', encoding='utf-8-sig') as file:
                ips = file.readlines()
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return

        if ips:
            with open(filename, 'w', encoding='utf-8-sig') as file:
                for ip in ips:
                    file.write(f"{ip.strip()}/32\n")  # Assuming /32 subnet mask for all IPs
    else:
        # Сохранить только IP адреса
        pass


def main():
    # Read parameters from the configuration file
    service, threads, filename, cloudflare, filetype, gateway, run_command = read_config('config.ini')

    total_resolved_domains = 0
    selected_services = check_service_config(service)

    # Check if to include Cloudflare IPs based on configuration or user input
    include_cloudflare = check_include_cloudflare(cloudflare)

    # Set to store unique IP addresses across all services
    unique_ips_all_services = set()

    # DNS resolution for selected services
    with open(filename, 'w', encoding='utf-8-sig') as file:  # Open file for writing
        for service in selected_services:
            result = resolve_dns_and_write(service, urls[service], unique_ips_all_services, include_cloudflare, threads)
            file.write(result)  # Write unique IPs directly to the file
            total_resolved_domains += len(result.split('\n')) - 1

    print("\nПроверка завершена.")
    print(f"Сопоставлено IP адресов доменам: {total_resolved_domains}")

    # Asking for file format if filetype is not specified in the configuration file
    process_file_format(filename, filetype, gateway)

    # Executing the command after the program is completed, if it is specified in the configuration file
    if run_command is not None and run_command.strip():
        print("\nВыполнение команды после завершения скрипта...")
        os.system(run_command)
    else:
        print("Результаты сохранены в файл:", filename)
        if os.name == 'nt':  # Для пользователей Windows при запуске из проводника
            input("Нажмите \033[32mEnter\033[0m для выхода...")


if __name__ == "__main__":
    main()
