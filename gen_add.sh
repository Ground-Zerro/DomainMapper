#!/bin/bash

# Путь к файлу с IP-адресами и масками
input_file="domain-ip-resolve.txt"

# Проверка существования файла
if [[ ! -f $input_file ]]; then
    echo "Файл $input_file не найден!"
    exit 1
fi

# Чтение строк из файла и их обработка
while read -r line; do
    # Пропуск пустых строк
    [[ -z "$line" ]] && continue

    # Формирование строки с "no ip route"
    echo "ip route $line 0.0.0.0 Wireguard1 auto"
done < "$input_file"
