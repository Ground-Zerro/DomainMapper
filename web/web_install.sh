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
        useradd -m -s /bin/bash "$USERNAME"
        echo "Пользователь $USERNAME успешно создан."
    else
        echo "Скрипт завершён, так как пользователь не существует."
        exit 1
    fi
fi

# Обновление системы и установка зависимостей
echo "Обновляем систему и устанавливаем зависимости..."
apt update && apt upgrade -y
apt install python3 python3-pip python3-venv gunicorn nginx certbot python3-certbot-nginx -y

# Создание директории приложения
echo "Создаем директорию приложения..."
mkdir -p $APP_DIR

# Настройка прав доступа
echo "Настроим права доступа для директории приложения..."
chown -R $USERNAME:$USERNAME $APP_DIR
chmod -R 755 $APP_DIR

# Перемещение в директорию приложения
cd $APP_DIR

# Создание виртуального окружения
echo "Создаем виртуальное окружение..."
su - $USERNAME -c "python3 -m venv $APP_DIR/venv"

# Загрузка файла requirements.txt
echo "Загружаем файл requirements.txt..."
curl -o $APP_DIR/requirements.txt https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/requirements.txt

# Установка зависимостей из requirements.txt и добавление необходимых библиотек
echo "Устанавливаем зависимости Python..."
su - $USERNAME -c "source $APP_DIR/venv/bin/activate && pip install -r $APP_DIR/requirements.txt fastapi uvicorn pydantic gunicorn"

# Загрузка файлов приложения
echo "Загружаем файлы приложения..."
curl -o "$APP_DIR/index.html" -L "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/web/index.html"
curl -o "$APP_DIR/app.py" -L "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/web/app.py"
curl -o "$APP_DIR/main.py" -L "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/main.py"

chown "$USERNAME":"$USERNAME" "$APP_DIR/main.py"

# Создание системного сервиса
echo "Создаем системный сервис..."
tee $SERVICE_FILE > /dev/null <<EOF
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
EOF

# Активация и запуск сервиса
echo "Активируем и запускаем сервис..."
systemctl daemon-reload
systemctl start dns_resolver
systemctl enable dns_resolver

# Настройка Nginx
echo "Настраиваем Nginx..."
rm -f /etc/nginx/sites-enabled/default  # Удаляем стандартный конфиг

tee $NGINX_CONF > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    root $APP_DIR;
    index index.html;

    # Статические файлы
    location / {
        try_files \$uri /index.html;
    }

    # Прокси для FastAPI
    location /run {
        proxy_pass http://127.0.0.1:5000;  # Прокси на сервер FastAPI, если он работает на localhost и порту 5000
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    error_page 404 /index.html;
}
EOF

# Создаем символическую ссылку для конфигурации
ln -sf $NGINX_CONF /etc/nginx/sites-enabled/

# Проверяем конфигурацию Nginx
nginx -t

# Перезапускаем Nginx
systemctl restart nginx

# Настройка прав доступа к директории приложения
echo "Настраиваем права доступа..."
chmod -R 777 $APP_DIR

echo "Права доступа к директории приложения настроены."

# Открытие портов для Nginx
echo "Открываем порты для Nginx..."
ufw allow 'Nginx Full'
ufw reload

echo "Конфигурация Nginx завершена."

# Настройка HTTPS с помощью Certbot
echo "Настроим HTTPS с помощью Certbot..."
certbot --nginx -n --agree-tos --email $EMAIL_ADR -d $DOMAIN_NAME

# Завершение
echo "Настройка завершена. Приложение доступно по адресу $DOMAIN_NAME"
