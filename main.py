import os
import time
import requests
import dns.resolver
from concurrent.futures import ThreadPoolExecutor
from progress.bar import Bar
import ipaddress
import re

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
    'Search-engines': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-search-engines.txt",
}

# Function to resolve DNS and write to file
def resolve_dns_and_write(service, url, unique_ips_all_services, include_cloudflare):
    try:
        response = requests.get(url)
        response.raise_for_status()
        dns_names = response.text.split('\n')

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ['9.9.9.9', '149.112.112.112', '8.8.8.8', '8.8.4.4', '208.67.222.222', '208.67.220.220', '1.1.1.1', '1.0.0.1', '91.239.100.100', '89.233.43.71', '4.2.2.1', '4.2.2.2', '4.2.2.3', '4.2.2.4', '4.2.2.5', '4.2.2.6'] # Public DNS servers
        resolver.timeout = 1
        resolver.lifetime = 1

        if include_cloudflare:
            cloudflare_ips = get_cloudflare_ips()
        else:
            cloudflare_ips = set()

        unique_ips_current_service = set()  # Set to store unique IP addresses for the current service

        with Bar(f"Scanning: {service}", max=len(dns_names)) as bar:
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = []
                for domain in dns_names:
                    if domain.strip():
                        futures.append(executor.submit(resolve_domain, resolver, domain, unique_ips_current_service, unique_ips_all_services, cloudflare_ips))
                for future in futures:
                    bar.next()

        bar.finish()

        return '\n'.join(unique_ips_current_service) + '\n'
    except Exception as e:
        print(f"Не удалось загрузить список доменных имен сервиса: {service}.\n")
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

# Function to resolve domain and write result to file
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
    except dns.resolver.NoAnswer:
        pass
    except dns.resolver.NXDOMAIN:
        pass
    except dns.resolver.Timeout:
        pass
    except Exception as e:
        print(f"Ошибка при разрешении доменного имени {domain}: {e}")

# Main function
def main():
    start_time = time.time()
    total_resolved_domains = 0
    total_errors = 0
    selected_services = []

    # Interactive service selection
    while True:
        os.system('clear')
        print("Выберите сервисы:\n")
        print("0 - Отметить все")
        for idx, (service, url) in enumerate(urls.items(), 1):
            checkbox = "[*]" if service in selected_services else "[ ]"
            print(f"{idx}. {service.capitalize()}  {checkbox}")

        selection = input("\nВведите номер сервиса и нажмите Enter (Пустая строка и Enter для старта): ")
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

    include_cloudflare = input("Исключить IP адреса Cloudflare из итогового списка? (yes - исключить, Enter - оставить): ").strip().lower() == "yes"

    unique_ips_all_services = set()  # Set to store unique IP addresses across all services

    # Check if domain-ip-resolve.txt exists and clear it if it does
    if os.path.exists('domain-ip-resolve.txt'):
        os.remove('domain-ip-resolve.txt')

    # DNS resolution for selected services
    with open('domain-ip-resolve.txt', 'w') as file:  # Open file for writing
        for service in selected_services:
            result = resolve_dns_and_write(service, urls[service], unique_ips_all_services, include_cloudflare)
            file.write(result)  # Write unique IPs directly to the file
            total_resolved_domains += len(result.split('\n')) - 1

    end_time = time.time()
    elapsed_time = end_time - start_time

    print("\nСканирование заняло {:.2f} секунд".format(elapsed_time))
    print(f"Проверено DNS имен: {total_resolved_domains + total_errors}")
    print(f"Сопоставлено IP адресов доменам: {total_resolved_domains}")
    print(f"Не удалось сопоставить доменов IP адресу: {total_errors}")
    print("Результаты сканирования записаны в файл: domain-ip-resolve.txt")

if __name__ == "__main__":
    main()
