## Domain Mapper для Windows

`DomainMapper.exe` — готовая программа для Windows. Устанавливать Python и библиотеки не нужно.


**Требования:** Windows 10 или новее, 64-битная версия, доступ в интернет.


**Использование:**
1. Скачайте [DomainMapper.exe](https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/Windows/DomainMapper.exe) и положите его в отдельную папку.
2. Запустите двойным щелчком и ответьте на вопросы.
3. Результат (`domain-ip-resolve.txt` или его части `domain-ip-resolve_p1.txt`, `domain-ip-resolve_p2.txt` и т.д.) появится в той же папке.

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

**Старые команды с `Win.bat`** продолжают работать: теперь `Win.bat` сообщает, что программа доступна как `DomainMapper.exe`, скачивает её в папку `Загрузки` и запускает. Python для этого не нужен.


**Настройка:**
- Файлы `config.ini` и `custom-dns-list.txt` положите в папку с `DomainMapper.exe`. Описание параметров — в [основном README](https://github.com/Ground-Zerro/DomainMapper#domain-mapper). Файлы можно сохранять в UTF-8 или в стандартной кодировке Windows (ANSI).
- Другой файл конфигурации указывается из командной строки: `DomainMapper.exe -c myconfig.ini`.
- Для локального режима (`localplatform = yes`, `localdns = yes`) положите рядом с `DomainMapper.exe` файлы `platformdb`, `dnsdb` и папку `platforms` из репозитория.
- Если в `config.ini` задан параметр `run`, после выполнения команды окно закрывается без ожидания нажатия Enter.


**Предупреждения Windows:** программа не подписана цифровой подписью, поэтому SmartScreen может показать окно «Windows защитила ваш компьютер» — нажмите «Подробнее» → «Выполнить в любом случае». Некоторые антивирусы ошибочно реагируют на программы, собранные PyInstaller. Если не доверяете готовому файлу, запустите Domain Mapper из исходников (см. основной README) или соберите exe сами.


**Сборка exe из исходников** (в Windows, из корневой папки репозитория, нужен Python 3.10+):
```
python -m pip install pyinstaller -r requirements.txt
python -m PyInstaller --onefile --console --clean --noconfirm --name DomainMapper --distpath Windows --workpath build --specpath build main.py
```
