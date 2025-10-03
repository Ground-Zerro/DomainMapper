# Запуск вспомогательных утилит под Win:
- [convert - конвертер маршрутов](#convert)

**Описание:** Поставит Python и зависимости, запустит выбранную утилиту.

## convert

**Использование:**
- Открыть командную строку Windows и выполнить команду:
```
powershell -Command "irm https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/utilities/win/convert.bat -OutFile $env:TEMP\convert.bat" && cmd /c "%TEMP%\convert.bat"
```
или  
- Запустить PowerShell и выполнить команду:
```
irm https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/refs/heads/main/utilities/win/convert.bat -OutFile "$env:TEMP\convert.bat"; cmd /c "$env:TEMP\convert.bat"
```

**Можете:**
- Скачать convert.bat и запустить его.
