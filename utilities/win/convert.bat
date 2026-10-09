@echo off
setlocal
chcp 65001 > NUL
set "ARCHIVE=%TEMP%\DomainMapper.zip"
set "ROOT=%TEMP%\DomainMapper-main"

if not exist "ip.txt" (
    echo.
    echo Файл ip.txt не найден.
    echo Создайте файл ip.txt в текущей директории и добавьте в него IP-адреса.
    echo.
    choice /C YN /M "Создать пустой файл ip.txt сейчас?"
    if not errorlevel 2 (
        type NUL > ip.txt
        echo Файл ip.txt создан. Добавьте в него IP-адреса и запустите скрипт снова.
    )
    goto :finish
)

echo Загрузка Domain Mapper Converter...
if exist "%ROOT%" rmdir /s /q "%ROOT%"
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/Ground-Zerro/DomainMapper/archive/refs/heads/main.zip' -OutFile '%ARCHIVE%'; Expand-Archive -Path '%ARCHIVE%' -DestinationPath '%TEMP%' -Force"
del /q /f "%ARCHIVE%" 2>NUL
if not exist "%ROOT%\utilities\convert.py" (
    echo Ошибка загрузки Domain Mapper Converter.
    goto :finish
)

call "%ROOT%\utilities\win\setup.bat" httpx colorama
if errorlevel 1 goto :cleanup

cls
echo Запускаем...
set "PYTHONPATH=%ROOT%"
python -m utilities.convert
if errorlevel 1 echo Ошибка выполнения convert.py.
echo Программа завершена.

:cleanup
rmdir /s /q "%ROOT%"

:finish
endlocal
pause
