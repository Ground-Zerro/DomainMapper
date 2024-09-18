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
  <summary>Поддерживаемые сервисы (нажать чтоб открыть)</summary>

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
- Разрешение доменных имен популярных сервисов в IP-адреса.
- Агрегация маршрутов до /16 (255.255.0.0), /24 (255.255.255.0).
- Фильтрация IP-адресов Cloudflare (опционально).
- Восемь вариантов сохранения результата.


**Особенности:**
- Можно выбрать системный или публичный DNS сервер, либо их комбинацию.
- Разрешение каждого доменного имени происходит используя каждый из указанных пользователем DNS серверов и не останавливается при первом же успешном получении его IP-адреса.
- Автоматическое исключение дублирующихся IP, а также "заглушек" в виде IP-адресов самих DNS-серверов, редиректа на `0.0.0.0` и `localhost`.
- Конфигурационный файл позволяет настроить работу скрипта в "молчаливом" режиме - без промтов к пользователю.
- В конфигурационном файле можно указать выполнение команды в консоли для запуска другого скрипта или программы при завершении его работы.


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
  <summary>Локальный режим работы (нажать чтоб открыть)</summary>

В этом режиме списки DNS серверов и сервисов будут загружены из локальных файлов в папке со скриптом, а не из сети.

Включить загрузку списка сервисов из локального файла `platformdb` - указать `localplatform = yes` в config.ini.
- Формат файла `platformdb`: Название сервиса двоеточие путь к локальному файлу.
Пример:
```
Torrent Truckers: platforms/dns-ttruckers.lst
Search engines: dns-search-engines.txt
Twitch: platforms/service/dns-twitch.txt
```

Включить загрузку списка DNS серверов из локального файла `dnsdb` - указать `localplatform = yes` в config.ini.
- Формат файла `dnsdb`: Название DNS сервера двоеточие IP-адрес пробел IP-адрес.
Пример:
```
CleanBrowsing: 185.228.168.9 185.228.169.9
Alternate DNS: 76.76.19.19 76.223.122.150
AdGuard DNS: 94.140.14.14 94.140.15.15
```

Обратите внимание, что при использовании этого режима названия сервисов и нумерация DNS серверов в config.ini должны соответствовать указанными вами в platformdb и dnsdb файлах.
-

- Формат файла с доменными именами: один домен на одну строку.
Пример:
```
ab.chatgpt.com
api.openai.com
arena.openai.com
```
Указание URL вместо доменного имени (например `ab.chatgpt.com/login` вместо `ab.chatgpt.com` и т.п.) приведет к ошибке.
</details>


<details>
  <summary>Запуск скрипта с файлом конфигурации отличным от config.ini (нажать чтоб открыть)</summary>

- Можно передавать путь к конфигурационному файлу при запуске скрипта с помощью опции `-c` (или `--config`). Если параметр не указан, по умолчанию будет использоваться файл `config.ini`.

Пример использования: `main.py -с myconfig.ini` или `python main.py -с config2.ini` или `main.py -с srv5.ini` и т.п.
</details>


<details>
  <summary>Личный (локальный) список с доменными именами (нажать чтоб открыть)</summary>

- Создать файл "custom-dns-list.txt", записать в него доменные имена и положить рядом со скриптом.  Список будет подхвачен при запуске и отображен в меню как "Custom DNS list".

- Пример файла "custom-dns-list.txt":
```
ab.chatgpt.com
api.openai.com
arena.openai.com
```
Указание URL вместо доменного имени (например `ab.chatgpt.com/login` вместо `ab.chatgpt.com` и т.п.) приведет к ошибке.
</details>


<details>
  <summary>Для пользователей Windows, не знающих "как", но кому "очень нужно" (нажать чтоб открыть)</summary>

- Загляните в директорию "Windows" репозитория.
</details>


##### Протестировано в Ubuntu 20.04, macOS Sonoma и Windows 10/11
