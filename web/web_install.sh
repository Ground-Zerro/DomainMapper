#!/bin/bash

set -e  # Завершение скрипта при ошибке
set -u  # Завершение при использовании необъявленных переменных

# Переменные
USERNAME="test123"
APP_DIR="/home/$USERNAME/dns_resolver_app"
SERVICE_FILE="/etc/systemd/system/dns_resolver.service"
NGINX_CONF="/etc/nginx/sites-available/dns_resolver"
EMAIL_ADR="email@example.com"
DOMAIN_NAME="your-domain.com"

# Проверка существования пользователя
if ! id "$USERNAME" &>/dev/null; then
    echo "Пользователь $USERNAME не существует."
    read -p "Хотите создать пользователя? (y/n): " CREATE_USER
    if [[ "$CREATE_USER" =~ ^[Yy]$ ]]; then
        sudo useradd -m -s /bin/bash "$USERNAME"
        echo "Пользователь $USERNAME успешно создан."
    else
        echo "Скрипт завершён, так как пользователь не существует."
        exit 1
    fi
fi

# Убедиться, что пользователь $USERNAME и www-data имеют общую группу
sudo usermod -aG www-data "$USERNAME"

# Обновление системы и установка зависимостей
echo "Обновляем систему и устанавливаем зависимости..."
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv gunicorn nginx certbot python3-certbot-nginx -y

# Создание директории приложения
if [[ ! -d "$APP_DIR" ]]; then
    echo "Создаем директорию приложения..."
    sudo mkdir -p "$APP_DIR"
    sudo chown -R "$USERNAME:www-data" "$APP_DIR"
    sudo chmod -R 750 "$APP_DIR"
else
    echo "Директория приложения уже существует. Пропускаем."
fi

# Создание виртуального окружения от имени www-data
if [[ ! -d "$APP_DIR/venv" ]]; then
    echo "Создаем виртуальное окружение..."
    sudo -u www-data python3 -m venv "$APP_DIR/venv"
    sudo chown -R "$USERNAME:www-data" "$APP_DIR/venv"
    sudo chmod -R 750 "$APP_DIR/venv"
else
    echo "Виртуальное окружение уже существует. Пропускаем."
fi

# Загрузка файла requirements.txt
REQUIREMENTS_URL="https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/requirements.txt"
if curl --head --fail "$REQUIREMENTS_URL" &>/dev/null; then
    curl -o "$APP_DIR/requirements.txt" "$REQUIREMENTS_URL"
    echo "Файл requirements.txt успешно загружен."
else
    echo "Ошибка: Файл requirements.txt недоступен."
    exit 1
fi

# Установка зависимостей Python от имени www-data
echo "Устанавливаем зависимости Python..."
sudo -u www-data bash -c "source $APP_DIR/venv/bin/activate && pip install -r $APP_DIR/requirements.txt fastapi uvicorn pydantic gunicorn"

# Загрузка файлов приложения
FILES=("index.html" "app.py" "main.py")
for FILE in "${FILES[@]}"; do
    URL="https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/web/$FILE"
    if curl --head --fail "$URL" &>/dev/null; then
        curl -o "$APP_DIR/$FILE" "$URL"
        echo "Файл $FILE успешно загружен."
        sudo chown "$USERNAME:www-data" "$APP_DIR/$FILE"
        sudo chmod 640 "$APP_DIR/$FILE"
    else
        echo "Ошибка: Файл $FILE недоступен."
    fi
done

# Проверка прав доступа
sudo chown -R "$USERNAME:www-data" "$APP_DIR"
sudo chmod -R 750 "$APP_DIR"

# Создание системного сервиса
echo "Создаем системный сервис..."
sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=DNS Resolver Web App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable --now dns_resolver

# Настройка Nginx
if [[ ! -f "$NGINX_CONF" ]]; then
    echo "Настраиваем Nginx..."
    sudo bash -c "cat <<EOF > $NGINX_CONF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    root $APP_DIR;
    index index.html;

    location / {
        try_files \$uri /index.html;
    }

    location /run {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    error_page 404 /index.html;
}
EOF"

    sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl restart nginx
else
    echo "Конфигурация Nginx уже существует. Пропускаем."
fi

# Настройка HTTPS
echo "Настраиваем HTTPS..."
sudo certbot --nginx -n --agree-tos --email "$EMAIL_ADR" -d "$DOMAIN_NAME"

echo "Скрипт выполнен успешно. Приложение доступно по адресу https://$DOMAIN_NAME"
