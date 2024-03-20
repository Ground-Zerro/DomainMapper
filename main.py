import os
import time
import requests
import dns.resolver
from concurrent.futures import ThreadPoolExecutor
from progress.bar import Bar
from io import StringIO

# URLs
urls = {
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
    'Truckers': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-ttruckers.txt",
    'Antifilter community edition': "https://community.antifilter.download/list/domains.lst"
}

# Function to display interactive service selection
def display_service_selection(selected_services):
    os.system('clear')
    print("Выберите сервисы:")
    for idx, (service, url) in enumerate(urls.items(), 1):
        checkbox = "[*]" if service in selected_services else "[ ]"
        print(f"{idx}. {service.capitalize()}  {checkbox}")

# Function to resolve DNS and write to file
def resolve_dns_and_write(service, url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        dns_names = response.text.split('\n')

        resolver = dns.resolver.Resolver()
        resolver.timeout = 1
        resolver.lifetime = 1

        output_string = StringIO()

        resolved_domains = 0
        errors = 0

        with Bar(f"Scanning: {service}", max=len(dns_names)) as bar:
            with ThreadPoolExecutor(max_workers=20) as executor:
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
        print(f"Не удалось получить список доменных имен для сервиса: {service}.")
        return "", 0, 0

# Function to resolve domain and write result to file
def resolve_domain(resolver, domain, output_string):
    try:
        ips = resolver.resolve(domain)
        unique_ips = set(ip.address for ip in ips)
        for ip in unique_ips:
            output_string.write(ip + '\n')
        return len(unique_ips), 0
    except Exception as e:
        return 0, 1  # Return 0 for resolved and 1 for error

# Main function
def main():
    start_time = time.time()
    total_resolved_domains = 0
    total_errors = 0
    selected_services = []

    # Interactive service selection
    while True:
        display_service_selection(selected_services)
        selection = input("Введите номер сервиса и нажмите Enter (Пустая срока и Enter для старта): ")
        if selection.isdigit():
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

# Open the file for reading
with open("domain-ip-resolve.txt", "r") as file:
    lines = file.readlines()

# Remove duplicate lines by creating a set from the list of lines
unique_lines = set(lines)

# Open the file for writing
with open("domain-ip-resolve.txt", "w") as file:
    # Writing the unique strings back to the file
    file.writelines(unique_lines)