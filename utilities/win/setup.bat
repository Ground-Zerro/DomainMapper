@echo off
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"

python --version 2>NUL | findstr /B /C:"Python 3" >NUL
if not errorlevel 1 goto :modules

echo Python 3 не установлен.
choice /C YN /M "Установить?"
if errorlevel 2 (
    echo Без Python 3 ничего не получится...
    exit /b 1
)

echo Загрузка дистрибутива...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"
if not exist "%PYTHON_INSTALLER%" (
    echo Ошибка загрузки установщика Python 3.
    exit /b 1
)

echo Установка...
echo PS - не забудьте ее разрешить в соседнем окне
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1
del /q /f "%PYTHON_INSTALLER%"
echo.
echo Установка завершена, но требуется обновить окружение.
echo - закройте это окно и запустите скрипт снова.
exit /b 2

:modules
echo.
echo Проверка необходимых библиотек...
python -m pip install --disable-pip-version-check --quiet %*
if errorlevel 1 (
    echo Не удалось установить библиотеки. Проверьте pip.
    exit /b 1
)
exit /b 0
