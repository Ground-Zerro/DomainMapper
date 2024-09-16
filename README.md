## Domain Mapper


**Описание:** Инструмент на языке Python, предназначенный для разрешения DNS имен популярных веб-сервисов в IP-адреса.

Имеется поддержка следующих сервисов:
- [Antifilter - community edition](https://community.antifilter.download/)
- Youtube
- Facebook
- Openai
- Tik-Tok
- Instagram
- Twitter
- Netflix
- Bing
- Adobe
- Apple
- Google
- Torrent Truckers
- Search engines
- [Github сopilot](https://github.com/features/copilot)
- Twitch
- Личный список


**Функции:**
- Скрипт использует списки доменных имен популярных сервисов и разрешает их в IP-адреса.
- Итоговый список содержит только уникальные IP-адреса исключая дубликаты, также фильтруются IP-адреса самих DNS-серверов, заглушки в виде редиректа на localhost и (по желанию) IP-адреса Cloudflare.
- Выбор между системным DNS сервером, популярными публичными, либо их комбинации.
- Разрешение DNS имени происходит используя каждый из указанных пользователем DNS серверов и не останавливается при первом же успешном получении его IP-адреса.
- Пользователь может создать свой список с DNS именами, необходимыми лично ему.
- Агрегация маршрутов до /16 (255.255.0.0), /24 (255.255.255.0).


**Автоматизация:**
Конфигурационный файл позволяет настроить работу скрипта в "молчаливом" режиме - без промтов к пользователю.
Так же в конфигурационном файле можно добавить выполнение кастомной команды в консоли для запуска другого скрипта или программы при завершении его работы.


**Зависимости:** Для работы Domain Mapper необходимо наличие следующих библиотек Python:
- configparser, ipaddress, dnspython, httpx, colorama.

*Не забудьте установить их перед запуском:*
```
pip3 install -r requirements.txt
```


**Использование:**
- Запустить с помощью Python. Для работы необходим только "main.py" и (по желанию) файл "config.ini".

**Работа с личным списком DNS:**
- Создать файл "custom-dns-list.txt", записать в него DNS имена (одна строчка - одно имя) и положить рядом со скриптом.  Список будет подхвачен при запуске и отображен в меню как "Custom DNS list".

**Использование скрипта с кастомным конфигурационным файлом**
- Можно передавать путь к конфигурационному файлу при запуске скрипта с помощью опции `-c` (или `--config`). Если параметр не указан, по умолчанию будет использоваться файл config.ini.

Пример использования: `main.py -с myconfig.ini` или `python main.py -с config2.ini` или `main.py -с srv5.ini` и т.п.

**Кто не знает "как", но кому "очень нужно":**
- Загляните в директорию "Windows" репозитория.


<details>
  <summary>Что нового</summary>

- Вспомагательные [утилиты](https://github.com/Ground-Zerro/DomainMapper/tree/main/utilities) для поиска субдоменов.
- Добавлен сервис Twitch. [Запрос @shevernitskiy](https://github.com/Ground-Zerro/DomainMapper/issues/31)
- Добавлен Yandex DNS сервер. [Запрос @Noksa](https://github.com/Ground-Zerro/DomainMapper/issues/26)
- Опция в config.ini: Отключить отображение сведений о загруженой конфигурации.
- Кастомное имя конфигурационного файла. [Запрос @Noksa](https://github.com/Ground-Zerro/DomainMapper/issues/25)
- Добавлен сервис Github Copilot. [Запрос @aspirisen](https://github.com/Ground-Zerro/DomainMapper/issues/23)
- Keenetic CLI формат сохранения. [Запрос @vchikalkin](https://github.com/Ground-Zerro/DomainMapper/pull/20)
- Wireguard формат сохранения. [Запрос @sanikroot](https://github.com/Ground-Zerro/DomainMapper/issues/18)
- Агрегация маршрутов до /24, /16. [Запрос @sergeeximius](https://github.com/Ground-Zerro/DomainMapper/issues/8)
- OVPN формат сохранения. [Запрос @SonyLo](https://github.com/Ground-Zerro/DomainMapper/pull/13)
- Wireguard формат сохранения.[Запрос @Shaman2010](https://github.com/Ground-Zerro/DomainMapper/pull/9)

</details>



##### Протестировано в Ubuntu 20.04, macOS Sonoma и Windows 10/11
