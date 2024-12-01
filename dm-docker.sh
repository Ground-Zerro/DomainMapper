#!/bin/bash

# Путь к файлу, который проверим на наличие
FILE="./domain-ip-resolve.txt"
DOCKER_IMAGE="domainmapper"
DOCKER_CONTAINER="domainmapper_container"

# Обновление списка пакетов и установка git
echo "Обновляем список пакетов и устанавливаем git..."
sudo apt update
sudo apt install -y git

# Установка Docker, если он не установлен
if ! command -v docker &> /dev/null
then
    echo "Docker не найден. Устанавливаем Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh ./get-docker.sh
else
    echo "Docker уже установлен."
fi

# Клонирование репозитория, если папка DomainMapper не существует
if [ ! -d "DomainMapper" ]; then
    echo "Клонируем репозиторий DomainMapper..."
    git clone https://github.com/Ground-Zerro/DomainMapper.git
else
    echo "Репозиторий уже клонирован."
fi

# Проверяем наличие Dockerfile и создаем его, если он отсутствует
if [ ! -f "Dockerfile" ]; then
    echo "Создаём Dockerfile..."
    cat <<EOF > Dockerfile
FROM ubuntu:jammy
WORKDIR /app
ADD ./DomainMapper /app
RUN apt-get update -y
RUN apt-get install python3-pip -y
RUN pip3 install -r requirements.txt
CMD ["python3", "main.py"]
EOF
else
    echo "Dockerfile уже существует."
fi

# Сборка Docker образа, если образ ещё не был собран
if ! sudo docker images | grep -q "$DOCKER_IMAGE"; then
    echo "Собираем Docker образ..."
    sudo docker build -t $DOCKER_IMAGE .
else
    echo "Docker образ уже существует."
fi

# Проверяем, существует ли уже контейнер с данным именем
if sudo docker ps -a --filter "name=$DOCKER_CONTAINER" | grep -q "$DOCKER_CONTAINER"; then
    # Останавливаем и удаляем старый контейнер, если он существует
    echo "Контейнер с именем $DOCKER_CONTAINER уже существует. Останавливаем и удаляем его..."
    sudo docker stop $DOCKER_CONTAINER
    sudo docker rm $DOCKER_CONTAINER
fi

# Запуск Docker контейнера
echo "Запускаем Docker контейнер..."
sudo docker run -d --name $DOCKER_CONTAINER -v $FILE:/app/domain-ip-resolve.txt -it $DOCKER_IMAGE

# Сообщение для повторного запуска
echo "Для повторного запуска используйте команду:"
echo "sudo docker run -d --name $DOCKER_CONTAINER -v $FILE:/app/domain-ip-resolve.txt -it $DOCKER_IMAGE"

# Удаление самого скрипта
echo "Скрипт завершен, удаляю себя..."
rm -- "$0"
