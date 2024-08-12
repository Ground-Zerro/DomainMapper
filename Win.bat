@echo off
setlocal enabledelayedexpansion
chcp 65001 > NUL

REM Проверяем, установлен ли Python 3
python --version 2>NUL | findstr /I "Python 3" >NUL
if ERRORLEVEL 1 (
    echo Python 3 не установлен.
    choice /C YN /M "Установить?"
    if ERRORLEVEL 2 (
        echo Без Python 3 ничего не получится...
        pause
        exit /b 1
    ) else (
        echo Загрузка дистрибутива...
        powershell -Command "if ($PSVersionTable.PSVersion.Major -ge 3) {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe' -OutFile 'python_installer.exe'} else {Start-BitsTransfer -Source 'https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe' -Destination 'python_installer.exe'}"
        
        REM Проверяем, был ли успешно скачан файл
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
        
        REM Нужно обновить системные PATH, но в этом сеансе не получится
        echo Вроде бы все прошло удачно, но нужно обновить окружение, запустите этот скрипт еще раз.
        pause
        exit
    )
) else (
    echo Похоже Python 3 имеется в системе.
)

REM Проверяем наличие необходимых библиотек
set "modules=requests dnspython ipaddress configparser httpx"

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

cls
REM Скачиваем main.py
echo Загрузка Domain Mapper...
powershell -Command "if ($PSVersionTable.PSVersion.Major -ge 3) {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/main.py' -OutFile 'main.py'} else {Start-BitsTransfer -Source 'https://raw.githubusercontent.com/Ground-Zerro/DomainMapper/main/main.py' -Destination 'main.py'}"

if not exist "main.py" (
    echo Ошибка загрузки Domain Mapper.
    pause
    exit /b 1
)

REM Запуск main.py в Python 3
echo Запускаем...
python main.py
if ERRORLEVEL 1 (
    echo Ошибка выполнения main.py.
    pause
    del /q /f main.py
    exit /b 1
)

echo Программа завершена.
endlocal
del /q /f main.py
exit
