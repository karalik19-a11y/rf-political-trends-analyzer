@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Обновление программы
echo.
echo  Обновление с GitHub...
echo  Не закрывайте окно.
echo.
where python >nul 2>&1
if errorlevel 1 (
  echo  Python не найден. Установите с python.org и поставьте галочку PATH.
  pause
  exit /b 1
)
python bootstrap.py --update
echo.
echo  Готово. Нажмите любую клавишу — откроется программа.
pause >nul
python bootstrap.py
