#!/bin/bash

# Функция для проверки наличия Docker
check_docker() {
    if command -v docker >/dev/null 2>&1; then
        echo "Docker уже установлен. Версия: $(docker --version)"
        return 0  # Docker установлен
    else
        echo "Docker не найден. Устанавливаем Docker..."
        return 1  # Docker не установлен
    fi
}

# Обновляем список пакетов и устанавливаем git, если его нет
echo "Обновляем список пакетов и устанавливаем git..."
apt update && apt install -y git

# Проверяем и устанавливаем Docker, если его нет
if ! check_docker; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh ./get-docker.sh
    rm get-docker.sh  # Удаляем установочный скрипт после установки
fi

# Клонируем репозиторий, если его нет
if [ ! -d "./DomainMapper" ]; then
    echo "Клонируем репозиторий DomainMapper..."
    git clone https://github.com/Ground-Zerro/DomainMapper.git
else
    echo "Репозиторий DomainMapper уже клонирован."
fi

# Создаём Dockerfile с установкой Python 3.12
echo "Создаём Dockerfile..."
cat > Dockerfile <<EOL
FROM ubuntu:jammy

# Устанавливаем Python 3.12 и необходимые пакеты
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.12 python3.12-venv python3.12-distutils && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем pip для Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

WORKDIR /app
ADD ./DomainMapper /app

# Устанавливаем зависимости проекта
RUN python3.12 -m pip install --upgrade pip && \
    python3.12 -m pip install -r requirements.txt

CMD ["python3.12", "main.py"]
EOL

# Создаём файл domain-ip-resolve.txt, если его нет
if [ ! -f "./domain-ip-resolve.txt" ]; then
    echo "Создаём файл domain-ip-resolve.txt..."
    touch domain-ip-resolve.txt
    echo "Файл domain-ip-resolve.txt создан."
else
    echo "Файл domain-ip-resolve.txt уже существует."
fi

# Собираем Docker образ, если его нет
if ! docker image inspect domainmapper >/dev/null 2>&1; then
    echo "Собираем Docker образ..."
    docker build -t domainmapper .
else
    echo "Docker образ domainmapper уже существует."
fi

# Проверяем наличие контейнера и запускаем его
if docker ps -a | grep -q domainmapper_container; then
    echo "Контейнер уже существует. Перезапускаем его..."
    docker rm -f domainmapper_container  # Удаляем старый контейнер
fi

echo "Запускаем Docker контейнер..."
docker run --name domainmapper_container -v "$(pwd)/domain-ip-resolve.txt:/app/domain-ip-resolve.txt" -it domainmapper

# Сообщаем пользователю о местонахождении файла
echo "Контейнер завершил работу. Файл domain-ip-resolve.txt находится в $(pwd)/domain-ip-resolve.txt"

# Удаляем скрипт после выполнения
echo "Скрипт завершен, удаляю себя..."
rm -- "$0"
