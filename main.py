import os
import time
import requests
import dns.resolver
from concurrent.futures import ThreadPoolExecutor
from progress.bar import Bar
from io import StringIO

# URLs
urls = {
    'youtube': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-youtube.txt",
    'facebook': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-facebook.txt",
    'openai': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-openai.txt",
    'tiktok': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-tiktok.txt",
    'instagram': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-instagram.txt",
    'twitter': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-twitter.txt",
    'Netflix': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-netflix.txt",
    'bing': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-bing.txt",
    'adobe': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-adobe.txt",
    'apple': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-apple.txt",
    'google': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-google.txt",
    'truckers': "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/platforms/dns-ttruckers.txt"
}

# Function to display interactive service selection
def display_service_selection(selected_services):
    os.system('clear')
    print("Р’С‹Р±РµСЂРёС‚Рµ СЃРµСЂРІРёСЃС‹:")
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

        with Bar(f"Scanning {service}", max=len(dns_names)) as bar:
            with ThreadPoolExecutor(max_workers=50) as executor:
                futures = []
                for domain in dns_names:
                    if domain.strip():
                        futures.append(executor.submit(resolve_domain, resolver, domain, output_string))
                for future in futures:
                    future.result()
                    resolved_domains += 1
                    bar.next()

        bar.finish()
        
        return output_string.getvalue(), resolved_domains, errors
    except Exception as e:
        print(f"РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ СЃРїРёСЃРѕРє РґРѕРјРµРЅРЅС‹С… РёРјРµРЅ РґР»СЏ СЃРµСЂРІРёСЃР° {service}.")
        return "", 0, 0

# Function to resolve domain and write result to file
def resolve_domain(resolver, domain, output_string):
    try:
        ips = resolver.resolve(domain)
        unique_ips = set(ip.address for ip in ips)
        for ip in unique_ips:
            output_string.write(ip + '\n')
    except Exception as e:
        pass  # Ignore DNS resolution errors

# Main function
def main():
    start_time = time.time()
    total_resolved_domains = 0
    total_errors = 0
    selected_services = []

    # Interactive service selection
    while True:
        display_service_selection(selected_services)
        selection = input("Р’С‹Р±РµСЂРёС‚Рµ СЃРµСЂРІРёСЃ (РЅР°Р¶РјРёС‚Рµ Enter РґР»СЏ Р·Р°РІРµСЂС€РµРЅРёСЏ): ")
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

    print("\nРЎРєР°РЅРёСЂРѕРІР°РЅРёРµ Р·Р°РЅСЏР»Рѕ {:.2f} СЃРµРєСѓРЅРґ".format(elapsed_time))
    print(f"РџСЂРѕРІРµСЂРµРЅРѕ DNS РёРјРµРЅ: {total_resolved_domains + total_errors}")
    print(f"РЎРѕРїРѕСЃС‚Р°РІР»РµРЅРѕ IP Р°РґСЂРµСЃРѕРІ РґРѕРјРµРЅР°Рј: {total_resolved_domains}")
    print(f"РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕРїРѕСЃС‚Р°РІРёС‚СЊ РґРѕРјРµРЅРѕРІ IP Р°РґСЂРµСЃСѓ: {total_errors}")
    print("Р РµР·СѓР»СЊС‚Р°С‚С‹ СЃРєР°РЅРёСЂРѕРІР°РЅРёСЏ Р·Р°РїРёСЃР°РЅС‹ РІ С„Р°Р№Р»: domain-ip-resolve.txt")

if __name__ == "__main__":
    main()
