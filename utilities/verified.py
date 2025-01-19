import asyncio
from concurrent.futures import ThreadPoolExecutor

import dns.resolver

# DNS сервера для проверки
dns_servers = {
    'Google Public DNS': ['8.8.8.8', '8.8.4.4'],
    'Cloudflare DNS': ['1.1.1.1', '1.0.0.1'],
    'Yandex': ['77.88.8.8', '77.88.8.1']
}


# Функция для проверки домена на определенном DNS-сервере
def check_domain(domain, resolver):
    try:
        answers = resolver.resolve(domain, 'A')
        if answers:
            return domain, 'Делегирован'
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return domain, 'Припаркован или неактивен'
    except Exception as e:
        return domain, f'Ошибка: {e}'


# Асинхронная функция для проверки домена с использованием всех DNS-серверов
async def verify_domain_async(domain, dns_servers):
    loop = asyncio.get_running_loop()
    unverified_domains = set()

    with ThreadPoolExecutor(max_workers=40) as executor:
        futures = []
        for dns_name, servers in dns_servers.items():
            resolver = dns.resolver.Resolver()
            resolver.nameservers = servers

            # Добавляем задачи для каждого домена с каждым DNS-сервером
            futures.append(loop.run_in_executor(executor, check_domain, domain, resolver))

        results = await asyncio.gather(*futures)

    # Фильтруем результаты и записываем во множество unverified_domains домены с ошибками или не делегированные
    delegated = False
    for domain, status in results:
        if status == 'Делегирован':
            delegated = True
            print(f"{domain} {status}.")
            break  # Если домен делегирован хотя бы на одном сервере, прекращаем проверку
        else:
            print(f"{domain} {status}.")
            unverified_domains.add(domain)

    # Если домен не был подтвержден как делегированный, записываем его в список для повторной проверки
    if not delegated:
        return domain, unverified_domains
    return domain, None


# Функция для проверки всех доменов
async def verify_all_domains(domain_list, dns_servers):
    unverified_domains_set = set()
    verified_domains = set()

    print("Код запущен, но консоль может долго молчать. Терпи...")

    # Асинхронная проверка всех доменов в первом прогоне
    tasks = [verify_domain_async(domain, dns_servers) for domain in domain_list]
    results = await asyncio.gather(*tasks)

    # Обрабатываем результаты первого прогона
    for domain, unverified in results:
        if unverified:
            unverified_domains_set.update(unverified)
        else:
            verified_domains.add(domain)

    # Повторная проверка для unverified_domains_set
    if unverified_domains_set:
        print("\nЗапуск контрольной проверки неактивных доменов...\n")
        second_check_tasks = [verify_domain_async(domain, dns_servers) for domain in unverified_domains_set]
        second_check_results = await asyncio.gather(*second_check_tasks)

        # Обрабатываем результаты второго прогона
        for domain, unverified in second_check_results:
            if not unverified:
                verified_domains.add(domain)

    return verified_domains


# Чтение доменов из файла result.txt
with open('result.txt', 'r') as file:
    domain_list = [line.strip() for line in file.readlines()]

# Запуск асинхронной проверки доменов
verified_domains = asyncio.run(verify_all_domains(domain_list, dns_servers))

# Преобразование списка проверенных доменов в множество для исключения дубликатов и сортировка
unique_sorted_domains = sorted(set(verified_domains))

# Запись результатов в новый файл
with open('verified_domains.txt', 'w') as file:
    for domain in unique_sorted_domains:
        file.write(f"{domain}\n")

print(f"Проверенные домены сохранены в verified_domains.txt.\n Найдено {len(unique_sorted_domains)} уникальных активных доменов.")
