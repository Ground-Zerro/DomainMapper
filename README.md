## Domain Mapper
<details>
  <summary>Что нового (нажать, чтобы открыть)</summary>

- Большое обновление:
  - Код переработан: общий пакет `domainmapper`, меньше потребление памяти, одинаковые домены из разных сервисов проверяются один раз.
  - Новый механизм ограничения запросов: общий лимит на все DNS-серверы (`total_rate_limit`), лимит на каждый сервер с автоматическим снижением частоты при таймаутах (`rate_limit`), повтор запросов, на которые сервер не ответил. Сбоев практически нет, а при выборе одного-двух серверов сканирование стало быстрее.
  - В отчёте домены без A-записи отделены от настоящих сбоев.
  - Новый прогресс-бар: обновляется непрерывно, показывает скорость, число сбоев и точную оценку оставшегося времени, подстраивается под ширину окна.
  - Обновлён список DNS-серверов. Добавлены сервисы Linkedin, Disney+, Eufy, Petlibro, TMDB.
  - Для Windows — готовая программа `DomainMapper.exe` вместо Win.bat. Файлы настроек читаются и в UTF-8, и в кодировке Windows.
  - Docker-образ собирается на базе `python:3.12-slim`, результаты сохраняются в отдельную папку.
  - Утилита `split` удалена: большие файлы делит на части сам Domain Mapper.
- Реворк работы с DNS серверами. Прогрессбар. Разделение файла на части для некоторых форматов. Обновлена утилита Convert.
- Keenetic BAT формат сохранения. Небольшие изменения в интерфейсе. Некоторые доработки/улучшения.
- Добавлены некоторые [онлайн кинотеатры](https://github.com/Ground-Zerro/DomainMapper/blob/main/platforms/dns-onlinetheater.txt). Запрос @Andrey_schumacher
- Добавлены списки от [ITDog](https://t.me/itdoginfo/36).
- Добавлен сервис xBox. Запрос @Deni5c
- Запуск в докере. [Запрос @andrejs82git](https://github.com/Ground-Zerro/DomainMapper/issues/21), [Реализация @MrEagle123](https://github.com/Ground-Zerro/DomainMapper/issues/21#issuecomment-2509565392)
- Опция в config.ini: не добавлять comment="%SERVICE_NAME%" при сохранении IP-адресов в mikrotik формате. [Запрос @ITNetSystem](https://github.com/Ground-Zerro/DomainMapper/issues/45)
- Изменена кодировка файла результатов на UTF-8 без BOM. [Запрос @Savanture](https://github.com/Ground-Zerro/DomainMapper/issues/54)
- [Конвертер маршрутов](https://github.com/Ground-Zerro/DomainMapper/tree/main/utilities) как отдельная утилита. [Запрос @Andrey999r](https://github.com/Ground-Zerro/DomainMapper/discussions/43)
- Добавлен сервис Jetbrains. [Запрос @SocketSomeone](https://github.com/Ground-Zerro/DomainMapper/issues/40)
- Добавлен сервис Discord. [Запрос @AHuMex](https://github.com/Ground-Zerro/DomainMapper/issues/38)
- [Комбинированный режим объединения IP-адресов в подсеть.](https://github.com/Ground-Zerro/DomainMapper/issues/36)
- Возможность загрузки списков сервисов и DNS-серверов из локального файла. [Запрос @Noksa](https://github.com/Ground-Zerro/DomainMapper/issues/26)
- Вспомогательные [утилиты](https://github.com/Ground-Zerro/DomainMapper/tree/main/utilities) для поиска субдоменов.
- Добавлен сервис Twitch. [Запрос @shevernitskiy](https://github.com/Ground-Zerro/DomainMapper/issues/31)
- Добавлен Yandex DNS сервер. [Запрос @Noksa](https://github.com/Ground-Zerro/DomainMapper/issues/26)
- Опция в config.ini: отключить отображение сведений о загруженной конфигурации.
- Передача имени конфигурационного файла ключом в терминале/командной строке. [Запрос @Noksa](https://github.com/Ground-Zerro/DomainMapper/issues/25)
- Добавлен сервис Github Copilot. [Запрос @aspirisen](https://github.com/Ground-Zerro/DomainMapper/issues/23)
- Keenetic CLI формат сохранения. [Запрос @vchikalkin](https://github.com/Ground-Zerro/DomainMapper/pull/20)
- Wireguard формат сохранения. [Запрос @sanikroot](https://github.com/Ground-Zerro/DomainMapper/issues/18)
- Агрегация маршрутов до /24, /16. [Запрос @sergeeximius](https://github.com/Ground-Zerro/DomainMapper/issues/8)
- OVPN формат сохранения. [Запрос @SonyLo](https://github.com/Ground-Zerro/DomainMapper/pull/13)
- Mikrotik формат сохранения. [Запрос @Shaman2010](https://github.com/Ground-Zerro/DomainMapper/pull/9)

</details>

**Описание:** Инструмент на языке Python, предназначенный для разрешения DNS имен популярных веб-сервисов в IP-адреса и сохранения их в виде готовых маршрутов или списков для роутеров, VPN и операционных систем.


<details>
  <summary>Поддерживаемые сервисы (нажать, чтобы открыть)</summary>

Названия указаны так, как они отображаются в меню. В `config.ini` их можно писать в любом регистре.

- [Antifilter community edition](https://community.antifilter.download/)
- [ITDog Inside](https://github.com/itdoginfo/allow-domains)
- [ITDog Outside](https://github.com/itdoginfo/allow-domains)
- Youtube
- Anthropic
- Linkedin
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
- Torrent Trackers
- Search engines
- [Github Copilot](https://github.com/features/copilot)
- Twitch
- Discord
- Jetbrains
- Xbox
- Telegram
- [WhatsApp](https://github.com/HybridNetworks/whatsapp-cidr)
- Online movie theaters
- Windsurf
- Roblox
- Zscaler
- Disney+
- Eufy
- Petlibro
- TMDB
- Custom DNS list — личный список (см. раздел «Личный список доменов»)

</details>


<details>
  <summary>Используемые DNS-серверы (нажать, чтобы открыть)</summary>

Номер — это значение для параметра `dnsserver` в `config.ini`.

| № | Сервер | Адреса |
|---|--------|--------|
| 0 | Все перечисленные ниже | — |
| 1 | Системный DNS | из настроек ОС |
| 2 | Google Public DNS | 8.8.8.8, 8.8.4.4 |
| 3 | Quad9 | 9.9.9.9, 149.112.112.112 |
| 4 | Cloudflare DNS | 1.1.1.1, 1.0.0.1 |
| 5 | OpenDNS | 208.67.222.222, 208.67.220.220 |
| 6 | AdGuard DNS (без фильтрации) | 94.140.14.140, 94.140.14.141 |
| 7 | Control D (без фильтрации) | 76.76.2.0, 76.76.10.0 |
| 8 | CleanBrowsing (Security) | 185.228.168.9, 185.228.169.9 |
| 9 | UltraDNS Public | 64.6.64.6, 64.6.65.6 |
| 10 | NextDNS | 45.90.28.0, 45.90.30.0 |
| 11 | Yandex DNS | 77.88.8.8, 77.88.8.1 |

Список загружается из файла [`dnsdb`](dnsdb) этого репозитория (или с диска в локальном режиме).
</details>


**Функции:**
- Преобразование доменных имен популярных сервисов в IP-адреса.
- Агрегация маршрутов в /16 (255.255.0.0) и /24 (255.255.255.0) подсети. Комбинированный режим /24 + /32.
- Фильтрация IP-адресов Cloudflare (опционально).
- Множество форматов сохранения результата.
- Разделение больших файлов на части для формата Keenetic BAT.


**Ключевые особенности:**
- Возможность выбора системного, публичного DNS-сервера или их комбинации.
- Каждое доменное имя разрешается через каждый из выбранных DNS-серверов, поэтому собираются все IP-адреса, которые отдают разные серверы, а не только первый успешный ответ.
- Автоматическое исключение дубликатов IP-адресов, а также "заглушек": `0.0.0.0`, `127.0.0.1` и IP-адресов самих DNS-серверов.
- Бережная нагрузка на сеть: общий лимит запросов ко всем DNS-серверам, лимит на каждый сервер с автоматическим снижением частоты при таймаутах и повторный запрос доменов, на которые сервер не ответил.
- В отчёте отдельно показаны домены без A-записи (это нормальный ответ DNS) и настоящие сбои.
- Работа в "тихом" режиме без взаимодействия с пользователем — все ответы можно задать в конфигурационном файле.
- Запуск команды или программы по завершении работы.


## Использование

Требуется Python 3.10 или новее. Для Windows есть готовая программа без установки Python — см. раздел «Для пользователей Windows».

1. Скачайте репозиторий и перейдите в его папку:

   ```bash
   git clone https://github.com/Ground-Zerro/DomainMapper.git
   cd DomainMapper
   ```

2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. При необходимости создайте `config.ini` на основе [`config.ini.example`](config.ini.example):

   ```bash
   cp config.ini.example config.ini
   ```

4. Запустите скрипт:

   ```bash
   python main.py
   ```

Без `config.ini` скрипт по очереди спросит:
1. сервисы — номера через пробел, `0` — все;
2. DNS-серверы — номера через пробел, `0` — все;
3. исключать ли IP-адреса Cloudflare;
4. нужно ли объединять IP-адреса в подсети;
5. формат сохранения и, если формат этого требует, шлюз, интерфейс или имя списка.

Результат сохраняется в файл `domain-ip-resolve.txt` в текущей папке.


<details>
  <summary>Параметры config.ini (нажать, чтобы открыть)</summary>

Все параметры находятся в секции `[DomainMapper]`. Пустое значение означает, что скрипт спросит его у пользователя.
Для параметров вида да/нет принимаются значения `yes`, `y`, `on` и `no`, `n`, `off`.

| Параметр | Значения | Описание |
|----------|----------|----------|
| `service` | названия через запятую, `all`, `custom` | Сервисы для проверки. `all` — все сервисы, `custom` — личный список. Регистр не важен. |
| `dnsserver` | номера через пробел | DNS-серверы из раздела «Используемые DNS-серверы», `0` — все, `1` — системный. |
| `rate_limit` | число, по умолчанию `100` | Максимум запросов в секунду к одному DNS-серверу. При таймаутах частота к серверу снижается автоматически и затем восстанавливается. |
| `total_rate_limit` | число, по умолчанию `200` | Максимум запросов в секунду ко всем DNS-серверам вместе. Уменьшите, если сбоев много (слабый роутер, мобильный интернет); увеличивать обычно бесполезно — при перегрузке сети сканирование только замедляется. |
| `cloudflare` | `yes` / `no` | Исключить IP-адреса Cloudflare из результата. |
| `subnet` | `16`, `24`, `mix`, `no` | Агрегация IP-адресов, см. раздел «Агрегация IP-адресов». |
| `filetype` | см. раздел «Форматы сохранения» | Формат сохранения результата. |
| `gateway` | IP или имя интерфейса | Шлюз для форматов `win` и `unix`. |
| `keenetic` | IP и/или имя интерфейса через пробел | Шлюз для формата `keenetic cli`. |
| `listname` | строка | Имя address-list для формата `mikrotik`. |
| `mk_comment` | `on` / `off` | Добавлять `comment="..."` с названиями сервисов в формате `mikrotik`. |
| `filename` | имя файла, по умолчанию `domain-ip-resolve.txt` | Файл для сохранения результата. |
| `localplatform` | `yes` / `no` | Локальный режим для списков сервисов. |
| `localdns` | `yes` / `no` | Локальный режим для списка DNS-серверов. |
| `cfginfo` | `yes` / `no` | Показывать загруженную конфигурацию при запуске. |
| `run` | команда | Выполнить команду или запустить программу после завершения. |

Если значение `subnet` или `filetype` не распознано, скрипт сообщит об этом и спросит его у пользователя.
Если файл не найден, в нём нет секции `[DomainMapper]` или числовой параметр указан неверно, используются настройки по умолчанию.

Пример для работы без вопросов:
```ini
[DomainMapper]
service = youtube, telegram, custom
dnsserver = 1 2 4
cloudflare = yes
subnet = mix
filetype = mikrotik
listname = vpn-routes
mk_comment = off
rate_limit = 100
total_rate_limit = 200
cfginfo = no
```
</details>


<details>
  <summary>Ход проверки и отчёт (нажать, чтобы открыть)</summary>

Во время проверки отображается строка прогресса:
```
[█████████░░░░░░░░░░░░░░░░░░░]  22.8% | 1255/5500 | сбоев:    0 |   199 запр/с | прошло 00:06 | осталось ~00:23
```
- `1255/5500` — выполнено DNS-запросов из общего числа (число доменов × число выбранных DNS-серверов);
- `сбоев` — запросы, на которые DNS-сервер так и не ответил после повтора;
- `запр/с` — текущая скорость за последние секунды;
- `осталось` — оценка по самому медленному из выбранных серверов.

После проверки выводится отчёт:
- **Разрешено уникальных IP-адресов** — сколько адресов попадёт в результат.
- **Домен не существует или нет A-записи** — нормальный ответ DNS, а не ошибка: в списках сервисов встречаются устаревшие имена и имена только с IPv6/CNAME.
- **Сбоев: DNS-сервер не ответил / отказал в ответе** — запросы, которые не удалось выполнить и после повторной попытки. Если их много, уменьшите `total_rate_limit` в `config.ini`.
- **Исключено IP-адресов 'заглушек' / Cloudflare** — адреса, отброшенные фильтрами.

Как ограничиваются запросы:
- не больше `total_rate_limit` запросов в секунду ко всем серверам вместе (по умолчанию 200) — это защищает роутер и канал от перегрузки;
- не больше `rate_limit` запросов в секунду к одному серверу (по умолчанию 100); если сервер начинает не отвечать, частота к нему автоматически снижается, а затем восстанавливается;
- каждый запрос ждёт ответа до 2 секунд на попытку и до 6 секунд всего; не ответившие домены запрашиваются повторно в конце проверки.
</details>


<details>
  <summary>Форматы сохранения (нажать, чтобы открыть)</summary>

| `filetype` | Пример строки |
|------------|---------------|
| `ip` | `1.2.3.4` |
| `win` | `route add 1.2.3.4 mask 255.255.255.255 GATEWAY` |
| `unix` | `ip route 1.2.3.4/32 GATEWAY` |
| `keenetic bat` | `route add 1.2.3.4 mask 255.255.255.255 0.0.0.0` |
| `keenetic cli` | `ip route 1.2.3.4/32 GATEWAY auto !Youtube,Telegram` |
| `cidr` | `1.2.3.4/32` |
| `mikrotik` | `/ip/firewall/address-list add list=LIST_NAME comment="Youtube,Telegram" address=1.2.3.4/32` |
| `ovpn` | `push "route 1.2.3.4 255.255.255.255"` |
| `wireguard` | `1.2.3.4/32, 5.6.7.8/32, ...` (одной строкой) |

- Маска и префикс берутся из выбранной агрегации, например `1.2.3.0/24` или `mask 255.255.255.0`.
- В формате `keenetic bat` файл делится на части по 999 строк, если строк больше: `domain-ip-resolve_p1.txt`, `domain-ip-resolve_p2.txt` и т.д.
- В форматах `keenetic cli` и `mikrotik` в комментарий записываются названия выбранных сервисов.
</details>


<details>
  <summary>Агрегация IP-адресов (нажать, чтобы открыть)</summary>

| `subnet` | Результат |
|----------|-----------|
| `16` | Все адреса сокращаются до подсетей /16 (255.255.0.0). |
| `24` | Все адреса сокращаются до подсетей /24 (255.255.255.0). |
| `mix` | Если в одной подсети /24 найдено два адреса или больше, сохраняется подсеть /24, иначе — отдельный адрес /32. |
| `no` | Адреса сохраняются как есть (/32). |
</details>


<details>
  <summary>Локальный режим (нажать, чтобы открыть)</summary>

По умолчанию списки сервисов, доменов и DNS-серверов загружаются из этого репозитория на GitHub. В локальном режиме они читаются из файлов в папке со скриптом — так можно использовать свои списки.

**Список сервисов** — `localplatform = yes`. Используется файл `platformdb`, а также сами списки доменов.
- Формат `platformdb`: название сервиса и путь к файлу со списком доменов через двоеточие и пробел.
- Относительные пути отсчитываются от папки со скриптом. В локальном режиме файл читается с диска, в обычном — загружается из репозитория на GitHub по тому же пути.
- Полный адрес http(s) всегда загружается из сети.

Пример:
```
Torrent Trackers: platforms/dns-ttrackers.txt
Twitch: platforms/service/dns-twitch.txt
WhatsApp: https://raw.githubusercontent.com/HybridNetworks/whatsapp-cidr/main/WhatsApp/whatsapp_domainlist.txt
```

**Список DNS-серверов** — `localdns = yes`. Используется файл `dnsdb`.
- Формат: название DNS-сервера и один или несколько IP-адресов через пробел.

Пример:
```
SkyDNS: 77.88.8.8
AdGuard DNS: 94.140.14.140 94.140.14.141
```

Если локальный файл `platformdb` или `dnsdb` не найден, он загружается из сети.

Названия сервисов и номера DNS-серверов в `config.ini` должны соответствовать файлам `platformdb` и `dnsdb`. Номер 1 всегда занимает системный DNS, поэтому первый сервер из `dnsdb` получает номер 2.

**Формат списка доменов:** по одному домену на строку, пустые строки и строки, начинающиеся с `#`, пропускаются.
```
ab.chatgpt.com
api.openai.com
arena.openai.com
```
Указывать нужно доменное имя, а не URL: `ab.chatgpt.com/login` не будет разрешено.
</details>


<details>
  <summary>Личный список доменов (нажать, чтобы открыть)</summary>

- Создайте файл `custom-dns-list.txt` в текущей папке (из которой запускается скрипт) и запишите в него доменные имена по одному на строку (формат описан в разделе «Локальный режим»).
- Список автоматически появится в меню последним пунктом под названием "Custom DNS list". В `config.ini` его можно выбрать значением `custom`.

Пример файла `custom-dns-list.txt`:
```
ab.chatgpt.com
api.openai.com
arena.openai.com
```
</details>


<details>
  <summary>Запуск с другим файлом конфигурации (нажать, чтобы открыть)</summary>

Путь к конфигурационному файлу задаётся опцией `-c` (или `--config`). Без неё используется `config.ini` из текущей папки.

```bash
python main.py -c myconfig.ini
python main.py --config /etc/domainmapper/srv5.ini
```
</details>


<details>
  <summary>Запуск в Docker (нажать, чтобы открыть)</summary>

```
curl -L -s "https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/dm-docker.sh" > /tmp/dm-docker.sh && chmod +x /tmp/dm-docker.sh && sh /tmp/dm-docker.sh
```

Скрипт:
- при необходимости устанавливает Docker и git (для Debian/Ubuntu, требуются права root);
- клонирует или обновляет репозиторий в папку `DomainMapper` текущей директории;
- собирает образ из [`Dockerfile`](Dockerfile) на базе `python:3.12-slim` и запускает контейнер;
- после завершения удаляет сам себя.

Результаты сохраняются в папку `domainmapper-output` в текущей директории. В эту же папку можно положить `config.ini` и `custom-dns-list.txt` до запуска.

Запуск уже собранного образа вручную:
```bash
docker run --rm -it -v "$(pwd)/domainmapper-output:/data" domainmapper
```
</details>


<details>
  <summary>Для пользователей Windows (нажать, чтобы открыть)</summary>

Готовая программа [DomainMapper.exe](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/Windows/DomainMapper.exe) — Python устанавливать не нужно.

**Запуск одной командой** (программа скачивается в папку `Загрузки` и сразу запускается; результаты и `config.ini` — в той же папке):
- в PowerShell:
```
$ProgressPreference='SilentlyContinue'; irm https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/Windows/DomainMapper.exe -OutFile "$HOME\Downloads\DomainMapper.exe"; cd "$HOME\Downloads"; .\DomainMapper.exe
```
- в командной строке (cmd):
```
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; irm https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/Windows/DomainMapper.exe -OutFile '%USERPROFILE%\Downloads\DomainMapper.exe'" && cd /d "%USERPROFILE%\Downloads" && DomainMapper.exe
```
Повторный запуск той же командой скачивает актуальную версию программы.

Подробности в директории [Windows](https://github.com/Ground-Zerro/DomainMapper/tree/main/Windows) репозитория.
</details>


<details>
  <summary>Вспомогательные утилиты (нажать, чтобы открыть)</summary>

В директории [utilities](https://github.com/Ground-Zerro/DomainMapper/tree/main/utilities):
- `convert` — конвертер готового списка IP-адресов в маршруты (те же форматы и агрегация, что и в Domain Mapper);
- `extract_apex_domains` — извлечение доменов первого уровня из списков сервисов;
- `subdomain` — поиск субдоменов через rapiddns.io;
- `verified` — проверка активности доменов.
</details>


# ☕ Поддержка

Если проект оказался Вам полезен — можно поблагодарить автора:

- [Поддержать на Boosty](https://boosty.to/ground_zerro)
