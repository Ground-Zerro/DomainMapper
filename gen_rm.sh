#!/bin/bash

input=`ssh keenetic 'show ip route' | grep -i wireguard1 | grep -v '1.1.1.1' | grep -v '8.8.8.8' | grep -v '10.40.0'`

# Обработка каждой строки
echo "$input" | while read -r line; do
    # Извлечение IP-адреса и маски
    ip_route=$(echo "$line" | awk '{print $1}')
    
    # Формирование строки с "no ip route"
    echo "no ip route $ip_route 0.0.0.0"
done
