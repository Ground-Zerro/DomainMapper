## Domain Mapper
<details>
  <summary>Что нового (нажать чтоб открыть)</summary>

- Режим работы с личными (локальными) `platformdb` и `dnsdb`. [Запрос @Noksa](https://github.com/Ground-Zerro/DomainMapper/issues/26) 
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
- Mikrotik формат сохранения. [Запрос @Shaman2010](https://github.com/Ground-Zerro/DomainMapper/pull/9)

</details>

**Описание:** Инструмент на языке Python, предназначенный для разрешения DNS имен популярных веб-сервисов в IP-адреса.


<details>
  <summary>Поддерживаемые сервисы (нажать чтобы открыть)</summary>

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

</details>


**Функции:**
- Преобразование доменных имен популярных сервисов в IP-адреса.
- Агрегация маршрутов до сетей /16 (255.255.0.0), /24 (255.255.255.0).
- Фильтрация IP-адресов Cloudflare (опционально).
- Восемь вариантов сохранения результатов.


**Ключевые особенности**
- Возможность выбора системного, публичного DNS-сервера или их комбинации.
- При разрешении доменного имени используется каждый из указанных DNS-серверов, при этом процесс продолжается до получения всех возможных IP-адресов, а не останавливается на первом успешном ответе.
- Автоматическое исключение дубликатов IP-адресов, а также "заглушек" (например, IP самих DNS-серверов, редиректов на `0.0.0.0` и `localhost`).
- Поддержка работы в "тихом" режиме без взаимодействия с пользователем, настройка через конфигурационный файл.
- В конфигурационном файле можно указать команду для автоматического запуска другого скрипта или программы по завершении работы.


###  Использование:

1. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```
2. Отредактируйте `config.ini` под свои задачи (опционально)

4. Запустите скрипт:

   ```bash
   python main.py
   ```


<details>
  <summary>Локальный режим работы (нажать чтобы открыть)</summary>

В этом режиме списки DNS-серверов и сервисов загружаются из локальных файлов в папке со скриптом, а не из сети.

Для включения загрузки списка сервисов из локального файла `platformdb`, укажите `localplatform = yes` в config.ini.
- Формат файла `platformdb`: название сервиса и путь к локальному файлу через двоеточие.
Пример:
```
Torrent Truckers: platforms/dns-ttruckers.lst
Search engines: dns-search-engines.txt
Twitch: platforms/service/dns-twitch.txt
```

Для включения загрузки списка DNS-серверов из локального файла `dnsdb`, укажите `localdns = yes` в config.ini.
- Формат файла `dnsdb`: название DNS-сервера и его IP-адреса через двоеточие и пробел.
Пример:
```
CleanBrowsing: 185.228.168.9 185.228.169.9
Alternate DNS: 76.76.19.19 76.223.122.150
AdGuard DNS: 94.140.14.14 94.140.15.15
```

Важно: названия сервисов и нумерация DNS-серверов в config.ini должны соответствовать тем, что указаны в файлах `platformdb` и `dnsdb`.

- Формат файла с доменными именами: по одному домену на строку.
Пример:
```
ab.chatgpt.com
api.openai.com
arena.openai.com
```
Указание URL вместо доменного имени (например, `ab.chatgpt.com/login` вместо `ab.chatgpt.com`) приведет к ошибке.
</details>


<details>
  <summary>Запуск скрипта с файлом конфигурации, отличным от `config.ini` (нажать чтобы открыть)</summary>

- Указать путь к другому конфигурационному файлу при запуске скрипта можно с помощью опции `-c` (или `--config`). Если параметр не указан, по умолчанию будет использоваться файл `config.ini`.

Пример использования: `main.py -c myconfig.ini`, `python main.py -c config2.ini` или `main.py -c srv5.ini` и т.д.
</details>


<details>
  <summary>Личный (локальный) список с доменными именами (нажать чтобы открыть)</summary>

- Создайте файл `custom-dns-list.txt`, запишите в него доменные имена и разместите его рядом со скриптом. Список будет автоматически подхвачен при запуске и появится в меню как "Custom DNS list".

- Пример файла `custom-dns-list.txt`:
```
ab.chatgpt.com
api.openai.com
arena.openai.com
```
Указание URL вместо доменного имени (например, `ab.chatgpt.com/login` вместо `ab.chatgpt.com`) приведет к ошибке.
</details>


<details>
  <summary>Для пользователей Windows, не знающих "как", но кому "очень нужно" (нажать чтобы открыть)</summary>

- Загляните в директорию [Windows](https://github.com/Ground-Zerro/DomainMapper/tree/main/Windows) репозитория.
</details>


##### Протестировано в Ubuntu 20.04, macOS Sonoma и Windows 10/11
