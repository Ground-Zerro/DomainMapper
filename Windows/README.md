## Domain Mapper


Батник для запуска Domain Mapper под windows. !!!ТЕСТ - может не работать!!!


**Описание:** Сам поставит Python и зависимости. Для тех кто не может этого сделать самостоятельно.


**Использование:**
- Скачать Win.bat и запустить его.

**Можете попробовать эти варианты:**

*PS: При загрузке меняется формат с 'CRLF' на 'LF' поэтому глючит. Как решить пока не знаю.*
- Запустить PowerShell и выполнить команду:
```
irm https://github.com/Ground-Zerro/DomainMapper/raw/main/Windows/Win.bat -OutFile "$env:TEMP\Win.bat"; cmd /c "$env:TEMP\Win.bat"
```
- Открыть командную строку Windows и выполнить команду:
```
powershell -Command "irm https://github.com/Ground-Zerro/DomainMapper/raw/main/Windows/Win.bat -OutFile $env:TEMP\Win.bat" && cmd /c "%TEMP%\Win.bat"
```
