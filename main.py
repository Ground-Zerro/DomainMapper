import os
import time
import requests
import dns.resolver
from concurrent.futures import ThreadPoolExecutor
from progress.bar import Bar
from io import StringIO

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

# Function to display interactive service selection
def display_service_selection(selected_services):
    os.system('clear')
    print("Выберите сервисы:\n")
    print("0 - Отметить все")
    for idx, (service, url) in enumerate(urls.items(), 1):
        checkbox = "[*]" if service in selected_services else "[ ]"
        print(f"{idx}. {service.capitalize()}  {checkbox}")


# Function to resolve DNS and write to file
def resolve_dns_and_write(service, url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        dns_names = response.text.split('\n')

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ['9.9.9.9', '149.112.112.112', '8.8.8.8', '8.8.4.4', '208.67.222.222', '208.67.220.220', '1.1.1.1', '1.0.0.1', '91.239.100.100', '89.233.43.71', '4.2.2.1', '4.2.2.2', '4.2.2.3', '4.2.2.4', '4.2.2.5', '4.2.2.6'] # Public DNS servers
        resolver.timeout = 1
        resolver.lifetime = 1

        output_string = StringIO()

        resolved_domains = 0
        errors = 0

        with Bar(f"Scanning: {service}", max=len(dns_names)) as bar:
            with ThreadPoolExecutor(max_workers=50) as executor:
                futures = []
                for domain in dns_names:
                    if domain.strip():
                        futures.append(executor.submit(resolve_domain, resolver, domain, output_string))
                for future in futures:
                    resolved, error = future.result()
                    resolved_domains += resolved
                    errors += error
                    bar.next()

        bar.finish()
        
        return output_string.getvalue(), resolved_domains, errors
    except Exception as e:
        print(f"Не удалось загрузить список доменных имен сервиса: {service}.\n")
        return "", 0, 0

# Function to resolve domain and write result to file
def resolve_domain(resolver, domain, output_string):
    try:
        ips = resolver.resolve(domain)
        unique_ips = set(ip.address for ip in ips if ip.address not in ('127.0.0.1', '0.0.0.1') and ip.address not in resolver.nameservers)
        for ip in unique_ips:
            output_string.write(ip + '\n')
        return len(unique_ips), 0
    except dns.resolver.NoAnswer:
         return 0, 1
    except dns.resolver.NXDOMAIN:
         return 0, 1
    except dns.resolver.Timeout:
         return 0, 1
    except Exception as e:
        print(f"Ошибка при разрешении доменного имени {domain}: {e}")
        return 0, 1

# Main function
def main():
    start_time = time.time()
    total_resolved_domains = 0
    total_errors = 0
    selected_services = []

    # Interactive service selection
    while True:
        display_service_selection(selected_services)
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

    # Check if domain-ip-resolve.txt exists and clear it if it does
    if os.path.exists('domain-ip-resolve.txt'):
        os.remove('domain-ip-resolve.txt')

    # DNS resolution for selected services
    for service in selected_services:
        result, resolved_domains, errors = resolve_dns_and_write(service, urls[service])
        with open('domain-ip-resolve.txt', 'a') as file:
            file.write(result)
        total_resolved_domains += resolved_domains
        total_errors += errors

    end_time = time.time()
    elapsed_time = end_time - start_time

    print("\nСканирование заняло {:.2f} секунд".format(elapsed_time))
    print(f"Проверено DNS имен: {total_resolved_domains + total_errors}")
    print(f"Сопоставлено IP адресов доменам: {total_resolved_domains}")
    print(f"Не удалось сопоставить доменов IP адресу: {total_errors}")
    print("Результаты сканирования записаны в файл: domain-ip-resolve.txt")

if __name__ == "__main__":
    main()

# Deleting repetitions
with open("domain-ip-resolve.txt", "r+") as file:
    unique_lines = set(file.readlines())
    file.seek(0)
    file.truncate()
    file.writelines(unique_lines)
