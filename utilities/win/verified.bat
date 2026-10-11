@echo off
setlocal
chcp 65001 > NUL
set "EXE_URL=https://github.com/Ground-Zerro/DomainMapper/raw/refs/heads/main/utilities/win/verified.exe"
set "EXE=%~dp0verified.exe"

echo Загрузка verified.exe ...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%EXE_URL%' -OutFile '%EXE%'"
if errorlevel 1 goto :download_failed

cd /d "%~dp0"
"%EXE%" %*
endlocal
exit /b 0

:download_failed
echo.
echo Не удалось загрузить verified.exe. Скачайте его вручную:
echo %EXE_URL%
endlocal
pause
exit /b 1
