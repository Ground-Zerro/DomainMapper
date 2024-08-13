## Domain Mapper


Батник для запуска Domain Mapper под windows.


**Описание:** Сам поставит Python и зависимости. Для тех кто не может этого сделать самостоятельно.


**Использование:**
- Скачать Win.bat и запустить его.

**Можете попробовать эти варианты:**
- Запустить PowerShell и выполнить команду:
```
irm https://github.com/Ground-Zerro/DomainMapper/raw/main/Windows/Win.bat -OutFile "$env:TEMP\Win.bat"; cmd /c "$env:TEMP\Win.bat"
```
- Открыть командную строку Windows и выполнить команду:
```
powershell -Command "irm https://github.com/Ground-Zerro/DomainMapper/raw/main/Windows/Win.bat -OutFile $env:TEMP\Win.bat" && cmd /c "%TEMP%\Win.bat"
```
