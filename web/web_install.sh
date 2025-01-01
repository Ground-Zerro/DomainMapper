#!/bin/bash

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

# Обновление системы и установка зависимостей
echo "Обновляем систему и устанавливаем зависимости..."
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv gunicorn nginx certbot python3-certbot-nginx -y

# Создание директории приложения
echo "Создаем директорию приложения..."
sudo -u $USERNAME mkdir -p $APP_DIR

# Перемещение в директорию приложения
cd $APP_DIR

# Создание виртуального окружения
echo "Создаем виртуальное окружение..."
sudo -u $USERNAME python3 -m venv venv

# Активация виртуального окружения и установка библиотек
echo "Устанавливаем зависимости Python..."

# Загрузка файла requirements.txt
curl -o $APP_DIR/requirements.txt https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/requirements.txt

# Установка зависимостей из requirements.txt и добавление необходимых библиотек
sudo -u $USERNAME bash -c "source $APP_DIR/venv/bin/activate && pip install -r $APP_DIR/requirements.txt fastapi uvicorn pydantic gunicorn"

# Загрузка файлов приложения
echo "Загружаем файлы приложения..."
curl -o "$APP_DIR/index.html" -L "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/web/index.html"
curl -o "$APP_DIR/app.py" -L "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/web/app.py"
curl -o "$APP_DIR/main.py" -L "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/main.py"

chown "$USERNAME":"$USERNAME" "$APP_DIR/main.py"

# Создание системного сервиса
echo "Создаем системный сервис..."
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=DNS Resolver Web App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app

[Install]
WantedBy=multi-user.target
EOF

# Активация и запуск сервиса
echo "Активируем и запускаем сервис..."
sudo systemctl daemon-reload
sudo systemctl start dns_resolver
sudo systemctl enable dns_resolver

# Настройка Nginx
echo "Настраиваем Nginx..."
sudo rm -f /etc/nginx/sites-enabled/default  # Удаляем стандартный конфиг

# Конфигурация Nginx для работы с FastAPI
sudo tee $NGINX_CONF > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    # Проксируем запросы на FastAPI сервер
    location / {
        proxy_pass http://127.0.0.1:8000;  # Uvicorn запускается на порту 8000 через Gunicorn
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Обработка ошибки 404
    error_page 404 /index.html;
    location = /index.html {
        root $APP_DIR;
        internal;
    }
}
EOF

# Создаем символическую ссылку для конфигурации
sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/

# Проверяем конфигурацию Nginx
sudo nginx -t

# Перезапускаем Nginx
sudo systemctl restart nginx

# Настройка прав доступа к директории приложения
echo "Настраиваем права доступа для Nginx..."
sudo chown -R www-data:www-data $APP_DIR
sudo chmod -R 755 $APP_DIR

# Настраиваем доступ к домашней директории пользователя, если это требуется
HOME_DIR=$(dirname "$APP_DIR")
sudo chmod 755 $HOME_DIR

echo "Права доступа к директории приложения настроены."

# Открытие портов для Nginx
echo "Открываем порты для Nginx..."
sudo ufw allow 'Nginx Full'
sudo ufw reload

echo "Конфигурация Nginx завершена."

# Настройка HTTPS с помощью Certbot
echo "Настраиваем HTTPS с помощью Certbot..."
sudo certbot --nginx -n --agree-tos --email $EMAIL_ADR -d $DOMAIN_NAME

# Завершение
echo "Настройка завершена. Приложение доступно по адресу $DOMAIN_NAME"
