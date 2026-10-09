#!/bin/sh
set -e

REPOSITORY_URL="https://github.com/Ground-Zerro/DomainMapper.git"
REPOSITORY_DIR="./DomainMapper"
OUTPUT_DIR="$(pwd)/domainmapper-output"
IMAGE="domainmapper"

if command -v docker >/dev/null 2>&1; then
    echo "Docker уже установлен. Версия: $(docker --version)"
else
    echo "Docker не найден. Устанавливаем Docker..."
    apt update && apt install -y curl
    curl -fsSL https://get.docker.com | sh
fi

if ! command -v git >/dev/null 2>&1; then
    apt update && apt install -y git
fi

if [ -d "$REPOSITORY_DIR/.git" ]; then
    echo "Обновляем репозиторий DomainMapper..."
    git -C "$REPOSITORY_DIR" pull --ff-only
else
    echo "Клонируем репозиторий DomainMapper..."
    git clone "$REPOSITORY_URL" "$REPOSITORY_DIR"
fi

echo "Собираем Docker образ..."
docker build -t "$IMAGE" "$REPOSITORY_DIR"

mkdir -p "$OUTPUT_DIR"
docker run --rm -it -v "$OUTPUT_DIR:/data" "$IMAGE"

echo "Контейнер завершил работу. Результаты находятся в $OUTPUT_DIR"
rm -- "$0"
