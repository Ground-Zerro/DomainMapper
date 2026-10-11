@echo off
setlocal
chcp 65001 > NUL
set "EXE_URL=https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/convert.exe"
set "EXE=%~dp0convert.exe"

echo Загрузка convert.exe ...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%EXE_URL%' -OutFile '%EXE%'"
if errorlevel 1 goto :download_failed

cd /d "%~dp0"
"%EXE%" %*
endlocal
exit /b 0

:download_failed
echo.
echo Не удалось загрузить convert.exe. Скачайте его вручную:
echo %EXE_URL%
endlocal
pause
exit /b 1
