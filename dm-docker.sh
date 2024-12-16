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

# Проверяем и устанавливаем Docker, если его нет
if ! check_docker; then
    echo "Обновляем список пакетов и устанавливаем необходимые компоненты..."
    apt update && apt install -y git curl

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

# Проверяем наличие Docker образа
if ! docker image inspect domainmapper >/dev/null 2>&1; then
    echo "Docker образ не найден. Собираем новый образ..."

    echo "Устанавливаем только необходимые для работы компоненты..."
    apt update && apt install -y software-properties-common wget build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev \
        liblzma-dev tzdata && \
        rm -rf /var/lib/apt/lists/*

    # Создаём Dockerfile с исправлениями
    echo "Создаём Dockerfile..."
    cat > Dockerfile <<EOL
FROM ubuntu:jammy

# Устанавливаем необходимые пакеты для сборки Python
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN apt-get update && \
    apt-get install -y wget build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev tzdata && \
    ln -fs /usr/share/zoneinfo/\$TZ /etc/localtime && \
    echo \$TZ > /etc/timezone && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

# Скачиваем и устанавливаем Python 3.12
RUN wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz && \
    tar -xvf Python-3.12.0.tgz && \
    cd Python-3.12.0 && \
    ./configure --enable-optimizations && \
    make -j$(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.12.0 Python-3.12.0.tgz

# Устанавливаем pip для Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

WORKDIR /app
ADD ./DomainMapper /app

# Устанавливаем зависимости проекта, если они указаны
RUN if [ -f "requirements.txt" ]; then \
        python3.12 -m pip install --upgrade pip && \
        python3.12 -m pip install -r requirements.txt; \
    fi

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

    # Собираем Docker образ
    echo "Собираем Docker образ..."
    docker build -t domainmapper .

    # Очищаем кеш Docker после сборки
    echo "Очищаем build cache Docker..."
    docker builder prune -f
else
    echo "Docker образ domainmapper уже существует."
fi

# Проверяем наличие контейнера и запускаем main.py из существующего контейнера
if docker ps -a | grep -q domainmapper_container; then
    echo "Контейнер уже существует. Запускаем main.py..."
    docker start -i domainmapper_container
else
    echo "Создаем и запускаем новый контейнер..."
    docker run --name domainmapper_container -v "$(pwd)/domain-ip-resolve.txt:/app/domain-ip-resolve.txt" -it domainmapper
fi

# Сообщаем пользователю о местонахождении файла
echo "Контейнер завершил работу. Файл domain-ip-resolve.txt находится в $(pwd)/domain-ip-resolve.txt"

# Удаляем скрипт после выполнения
echo "Скрипт завершен."
rm -- "$0"
