@echo off
setlocal
chcp 65001 > NUL
set "EXE_URL=https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/Windows/DomainMapper.exe"
set "REPOSITORY_URL=https://github.com/Ground-Zerro/DomainMapper/tree/main/Windows"
set "TARGET=%USERPROFILE%\Downloads"
set "EXE=%TARGET%\DomainMapper.exe"

echo ================================================================
echo  Domain Mapper теперь распространяется как готовая программа
echo  DomainMapper.exe - устанавливать Python больше не нужно.
echo.
echo  Скачать программу можно из репозитория:
echo  %REPOSITORY_URL%
echo  и запускать двойным щелчком.
echo ================================================================
echo.

if not exist "%TARGET%" mkdir "%TARGET%"
echo Загрузка DomainMapper.exe в папку %TARGET% ...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%EXE_URL%' -OutFile '%EXE%'"
if errorlevel 1 goto :download_failed

echo Программа сохранена: %EXE%
echo Результаты и config.ini - в той же папке.
echo.
cd /d "%TARGET%"
"%EXE%"
endlocal
exit /b 0

:download_failed
echo.
echo Не удалось загрузить DomainMapper.exe. Скачайте его вручную:
echo %REPOSITORY_URL%
endlocal
pause
exit /b 1
