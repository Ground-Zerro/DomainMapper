# Вспомогательные утилиты для Windows
- [convert - конвертер маршрутов](#convert)
- [extract_apex_domains - извлечение доменов первого уровня](#extract_apex_domains)
- [subdomain - поиск субдоменов](#subdomain)
- [verified - проверка активности доменов](#verified)

Каждая утилита — готовая программа (`.exe`), устанавливать Python и библиотеки не нужно. Исходники и подробное описание — в [README утилит](../README.md).

**Требования:** Windows 10 или новее, 64-битная версия, доступ в интернет.

**Два способа запуска:**
- скачать `.exe` и запустить двойным щелчком;
- скачать `.bat` и запустить его: он каждый раз загружает актуальную версию `.exe` в свою папку и запускает её.

Рабочие файлы (`ip.txt`, `result.txt` и т.д.) читаются из папки, в которой лежит программа или `.bat`, и результаты сохраняются туда же.

**Предупреждения Windows:** программы не подписаны цифровой подписью, поэтому SmartScreen может показать окно «Windows защитила ваш компьютер» — нажмите «Подробнее» → «Выполнить в любом случае».

## convert

Скачайте [convert.exe](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/convert.exe) или [convert.bat](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/convert.bat).

1. Создайте рядом с программой файл `ip.txt` и добавьте в него IP-адреса или любой текст, содержащий IP-адреса.
2. Запустите программу и ответьте на вопросы.
3. Результат будет записан в `ip.txt` (для формата Keenetic BAT — в файлы `ip_p1.txt`, `ip_p2.txt` и т.д.).

## extract_apex_domains

Работает со списками из папки `platforms` репозитория, поэтому нужен скачанный (клонированный) репозиторий.

Скачайте [extract_apex_domains.exe](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/extract_apex_domains.exe) или [extract_apex_domains.bat](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/extract_apex_domains.bat).

1. Запустите `extract_apex_domains.bat` из папки `utilities\win` репозитория: он загрузит `extract_apex_domains.exe` и запустит его в корне репозитория.
2. Результаты будут сохранены в папке `platforms_apex` в корне репозитория.

`extract_apex_domains.exe` можно запускать и напрямую — из папки, в которой есть папка `platforms`.

## subdomain

Скачайте [subdomain.exe](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/subdomain.exe) или [subdomain.bat](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/subdomain.bat).

1. Запустите программу и введите домен, например `example.com`. Домен можно передать и из командной строки: `subdomain.exe example.com`.
2. Найденные субдомены будут сохранены в файл `result.txt`.

Для крупных доменов поиск может занять несколько минут из-за ограничений бесплатных источников. `Ctrl+C` прерывает поиск и сохраняет всё найденное к этому моменту.

## verified

Скачайте [verified.exe](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/verified.exe) или [verified.bat](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/verified.bat).

1. Положите рядом с программой файл `result.txt` со списком доменов (по одному на строку), например результат `subdomain`.
2. Запустите программу.
3. Активные домены будут сохранены в файл `verified_domains.txt`.

## Сборка из исходников

В Windows, из корневой папки репозитория, нужен Python 3.10+:
```
python -m pip install pyinstaller -r requirements.txt
for %u in (convert extract_apex_domains subdomain verified) do python -m PyInstaller --onefile --console --clean --noconfirm --paths . --name %u --distpath utilities\win --workpath build --specpath build utilities\%u.py
```
