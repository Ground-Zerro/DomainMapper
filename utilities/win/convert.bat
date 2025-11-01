@echo off
setlocal enabledelayedexpansion
chcp 65001 > NUL

REM Проверка Python 3
:CheckPython
python --version 2>NUL | findstr /I "Python 3" >NUL
if ERRORLEVEL 1 (
    echo Python 3 не установлен.
    choice /C YN /M "Установить?"
    if ERRORLEVEL 2 (
        echo Без Python 3 ничего не получится...
        pause
        exit /b 1
    ) else (
        call :InstallPython
    )
) else (
    echo Python 3 установлен.
)
goto :CheckModules

REM Инсталляция Python 3
:InstallPython
echo Загрузка дистрибутива...
powershell -Command "if ($PSVersionTable.PSVersion.Major -ge 3) {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe' -OutFile 'python_installer.exe'} else {Start-BitsTransfer -Source 'https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe' -Destination 'python_installer.exe'}"

REM Проверяем успешность загрузки
if not exist "python_installer.exe" (
    echo Ошибка загрузки установщика Python 3.
    pause
    exit /b 1
)

REM Установка Python 3
echo Установка...
echo PS - не забудьте ее разрешить в соседнем окне
python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
del /q /f python_installer.exe

REM Оповещение о перезапуске
echo.
echo Установка завершена, но требуется обновить окружение.
echo - закройте это окно и запустите скрипт снова.
pause
exit /b 0

REM Проверка и установка необходимых модулей Python
:CheckModules
set "modules=requests dnspython ipaddress configparser httpx colorama"
echo.
echo Проверка необходимых библиотек...

for %%m in (%modules%) do (
    pip show %%m >NUL 2>&1
    if ERRORLEVEL 1 (
        echo Установка библиотеки %%m...
        pip install %%m
        if ERRORLEVEL 1 (
            echo Не удалось установить библиотеку %%m. Проверьте pip.
            exit /b 1
        )
    )
)

goto :DownloadMain

REM Загрузка и запуск convert.py
:DownloadMain
echo Загрузка Domain Mapper Converter...
powershell -Command "if ($PSVersionTable.PSVersion.Major -ge 3) {Invoke-WebRequest -Uri 'https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/convert.py' -OutFile 'convert.py'} else {Start-BitsTransfer -Source 'https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/utilities/convert.py' -Destination 'convert.py'}"

if not exist "convert.py" (
    echo Ошибка загрузки Domain Mapper Converter.
    pause
    exit /b 1
)

if not exist "ip.txt" (
    echo.
    echo Файл ip.txt не найден.
    echo Создайте файл ip.txt в текущей директории и добавьте в него IP-адреса.
    echo.
    choice /C YN /M "Создать пустой файл ip.txt сейчас?"
    if ERRORLEVEL 2 (
        echo Завершение работы.
        del /q /f convert.py
        pause
        exit /b 1
    ) else (
        echo. > ip.txt
        echo Файл ip.txt создан. Добавьте в него IP-адреса и запустите скрипт снова.
        del /q /f convert.py
        pause
        exit /b 0
    )
)

cls
echo Запускаем...
python convert.py
if ERRORLEVEL 1 (
    echo Ошибка выполнения convert.py.
    pause
    del /q /f convert.py
    exit /b 1
)

echo Программа завершена.
del /q /f convert.py
endlocal
pause
exit /b 0
