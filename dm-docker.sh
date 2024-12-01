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

# Создаём Dockerfile, если его нет
if [ ! -f "./Dockerfile" ]; then
    echo "Создаём Dockerfile..."
    cat > Dockerfile <<EOL
FROM ubuntu:jammy
WORKDIR /app
ADD ./DomainMapper /app
RUN apt-get update -y
RUN apt-get install python3-pip -y
RUN pip3 install -r requirements.txt
CMD ["python3", "main.py"]
EOL
else
    echo "Dockerfile уже существует."
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
docker run --name domainmapper_container -v ./domain-ip-resolve.txt:/app/domain-ip-resolve.txt -it domainmapper

# Удаляем скрипт после выполнения
echo "Скрипт завершен, удаляю себя..."
rm -- "$0"
