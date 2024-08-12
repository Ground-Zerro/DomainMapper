## Domain Mapper


Батник для запуска Domain Mapper под windows. !!!ТЕСТ - может не работать!!!


**Описание:** Сам поставит Python и зависимости. Для тех кто не может этого сделать самостоятельно.


**Использование:**
- Запустить PowerShell и выполнить команду:
```
irm https://github.com/Ground-Zerro/DomainMapper/raw/main/Windows/Win.bat -OutFile "$env:TEMP\Win.bat"; cmd /c "$env:TEMP\Win.bat"
```
- Открыть командную строку Windows и выполнить команду:
```
powershell -Command "irm https://github.com/Ground-Zerro/DomainMapper/raw/main/Windows/Win.bat -OutFile $env:TEMP\Win.bat" && cmd /c "%TEMP%\Win.bat"
```
- Скачать Win.bat и запустить его.

##### При загрузке на github меняется формат с 'CRLF' в 'LF' поэтому глючит. Как решить пока не знаю.

