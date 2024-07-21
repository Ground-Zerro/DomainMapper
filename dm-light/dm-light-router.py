import asyncio
import configparser
import logging
import os
import socket
from typing import List, Optional, Dict

import asyncssh
from dnslib import DNSRecord


# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Множество для хранения уникальных IP-адресов
unique_ip_addresses = set()


# Чтение конфигурационного файла
def read_config(filename: str) -> Optional[configparser.SectionProxy]:
    config = configparser.ConfigParser()
    try:
        config.read(filename)
        logging.info(f"Файл конфигурации {filename} загружен.")
        return config['Router']
    except KeyError:
        logging.error(f"Секция 'Router' отсутствует в файле конфигурации {filename}.")
        return None
    except Exception as e:
        logging.error(f"Ошибка загрузки файла конфигурации {filename}: {e}")
        return None


# Загрузка доменных имен из файлов в папке
def load_domain_names_from_folder(folder: str) -> List[str]:
    domains = []
    try:
        for filename in os.listdir(folder):
            if filename.endswith('.txt'):
                with open(os.path.join(folder, filename), 'r', encoding='utf-8-sig') as file:
                    domains.extend([line.strip() for line in file if line.strip()])
        logging.info(f"Доменные имена загружены из папки {folder}.")
    except Exception as e:
        logging.error(f"Ошибка загрузки доменных имен из папки {folder}: {e}")
    return domains


# Отправка DNS запроса к публичному DNS серверу
async def send_dns_query(domain: str, dns_servers: List[str]) -> List[str]:
    loop = asyncio.get_event_loop()
    resolved_addresses = []
    for current_dns in dns_servers:
        try:
            query = DNSRecord.question(domain)
            data = query.pack()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
                client_socket.settimeout(2)
                await loop.run_in_executor(None, client_socket.sendto, data, (current_dns, 53))
                response, _ = await loop.run_in_executor(None, client_socket.recvfrom, 1024)
                dns_record = DNSRecord.parse(response)
                for r in dns_record.rr:
                    if r.rtype == 1:  # A record
                        resolved_addresses.append(str(r.rdata))
        except socket.timeout:
            logging.warning(f"Тайм-аут при отправке DNS запроса к {current_dns}")
        except Exception as e:
            logging.error(f"Ошибка отправки DNS запроса: {e}")
    return resolved_addresses


# Поиск DNS имени в фильтре
def compare_dns(f_domain: str, domain_list: List[str]) -> bool:
    name_parts = f_domain.rstrip('.').split('.')
    for filter_domain in domain_list:
        filter_domain_parts = filter_domain.split('.')
        if len(name_parts) < len(filter_domain_parts):
            continue
        match = all(name_parts[i] == filter_domain_parts[i] for i in range(-1, -len(filter_domain_parts) - 1, -1))
        if match:
            return True
    return False


# Класс для пула SSH соединений
class SSHConnectionPool:
    def __init__(self, max_size: int):
        self.pool = asyncio.Queue(max_size)
        self.max_size = max_size
        self.size = 0

    async def get_connection(self, router_ip: str, ssh_port: int, login: str,
                             password: str) -> asyncssh.SSHClientConnection:
        if self.pool.empty() and self.size < self.max_size:
            connection = await asyncssh.connect(
                router_ip, port=ssh_port, username=login, password=password, known_hosts=None
            )
            self.size += 1
            return connection
        else:
            return await self.pool.get()

    async def release_connection(self, connection: asyncssh.SSHClientConnection):
        await self.pool.put(connection)

    async def close_all(self):
        while not self.pool.empty():
            connection = await self.pool.get()
            connection.close()
            self.size -= 1


# Инициализация пула SSH соединений
ssh_pool = SSHConnectionPool(max_size=5)


# Отправка команд через SSH с повторными попытками
async def send_commands_via_ssh(router_ip: str, ssh_port: int, login: str, password: str, commands: List[str]) -> None:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            connection = await ssh_pool.get_connection(router_ip, ssh_port, login, password)
            for command in commands:
                logging.info(f"Executing command: {command}")
                result = await connection.run(command)
                logging.info(f"Command result: {result.stdout}")
                if result.stderr:
                    logging.error(f"Command error: {result.stderr}")
            await ssh_pool.release_connection(connection)
            break  # Выход из цикла после успешного выполнения команд
        except (asyncssh.Error, asyncio.TimeoutError, OSError) as e:
            logging.error(f"Ошибка при выполнении команд через SSH: {e}. Попытка {attempt + 1} из {max_retries}.")
            if attempt + 1 == max_retries:
                raise
            await asyncio.sleep(5)  # Подождать 5 секунд перед повторной попыткой


# Основная функция
async def execute_tasks() -> None:
    config_data = read_config('config.ini')
    if not config_data:
        return

    try:
        router_ip = config_data['router_ip']
        router_port = int(config_data['router_port'])
        login = config_data['login']
        password = config_data['password']
        eth_id = config_data['eth_id']
        domain_folder = config_data['domain_folder']
        public_dns_1 = config_data['public_dns_1']
        public_dns_2 = config_data['public_dns_2']

        # Загрузка доменных имен из папки
        domain_list = load_domain_names_from_folder(domain_folder)

        # Инициализация списка DNS серверов
        dns_servers = [public_dns_1, public_dns_2]

    except KeyError as e:
        logging.error(f"Ошибка чтения параметров конфигурации: отсутствует ключ {e}")
        return

    # Этап 1: Разрешение всех DNS имен
    domain_to_addresses: Dict[str, List[str]] = {}
    for domain in domain_list:
        resolved_addresses = await send_dns_query(domain, dns_servers)
        if resolved_addresses:
            logging.info(f"Resolved {domain} to {resolved_addresses}")
            domain_to_addresses[domain] = resolved_addresses

    # Этап 2: Отправка команд SSH для добавления маршрутов
    commands = []
    for domain, addresses in domain_to_addresses.items():
        for address in addresses:
            if address.rstrip('.') not in unique_ip_addresses:
                commands.append(f"ip route {address.rstrip('.')}/32 {eth_id}")
                unique_ip_addresses.add(address.rstrip('.'))

    if commands:
        # Разделение команд на блоки по 5 штук
        command_chunks = [commands[i:i + 5] for i in range(0, len(commands), 5)]
        for chunk in command_chunks:
            try:
                await asyncio.wait_for(
                    send_commands_via_ssh(router_ip, router_port, login, password, chunk), timeout=5
                )
            except (asyncssh.Error, asyncio.TimeoutError, OSError) as e:
                logging.error(f"Ошибка при выполнении команд через SSH: {e}")

    await ssh_pool.close_all()


async def main() -> None:
    while True:
        await execute_tasks()
        logging.info("Ожидание 30 минут до следующего выполнения...")
        await asyncio.sleep(1800)  # Ожидание 30 минут (1800 секунд)

if __name__ == "__main__":
    asyncio.run(main())
