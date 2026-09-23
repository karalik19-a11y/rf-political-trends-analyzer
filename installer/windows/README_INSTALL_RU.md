# Установка на Windows

## Быстрый способ

1. Скачайте этот репозиторий (кнопка **Code → Download ZIP**) или только папку `installer/windows`.
2. Распакуйте.
3. Запустите **`install.bat`** двойным кликом  
   (или правой кнопкой → «Запуск от имени пользователя»).

Установщик:
- проверит Python 3.9+
- скачает актуальный код с GitHub
- создаст виртуальное окружение
- установит все зависимости (включая CPU-версию torch)
- создаст ярлыки в меню «Пуск» и на рабочем столе
- зарегистрирует ежедневный сбор данных в Планировщике заданий Windows (06:00)

## Требования

- **Windows 10 / 11**
- **Python 3.9+** — скачать с [python.org](https://www.python.org/downloads/)  
  При установке отметьте **«Add python.exe to PATH»**.
- (Рекомендуется) **Git** — для более надёжного скачивания. Без Git будет использован ZIP.

## Параметры установки (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 `
    -InstallDir "D:\Apps\RFTrends" `
    -SkipDailyTask `
    -NoDesktopShortcut `
    -Force
```

| Параметр | Описание |
|----------|----------|
| `-InstallDir` | Папка установки (по умолчанию `%LOCALAPPDATA%\RFPoliticalTrends`) |
| `-SkipDailyTask` | Не создавать задание в Планировщике |
| `-NoDesktopShortcut` | Не создавать ярлык на рабочем столе |
| `-Force` | Перезаписать существующую установку без вопроса |

## После установки

| Действие | Как запустить |
|----------|---------------|
| Дашборд | Ярлык «RF Political Trends Dashboard» на рабочем столе или в меню Пуск |
| Разовый сбор | Пуск → RF Political Trends → Run Collector |
| Планировщик в консоли | Пуск → RF Political Trends → Start Scheduler |
| Экспорт CSV/JSON | Пуск → RF Political Trends → Export Data |
| Удаление | Запустить `uninstall.ps1` из папки установки |

## Удаление

```powershell
powershell -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\RFPoliticalTrends\uninstall.ps1"
```

Удаляются: папка приложения, ярлыки и задание Планировщика.

## Примечания

- Первый запуск collector/dashboard может скачать модель sentiment (~десятки МБ).
- Чтобы отключить sentiment: отредактируйте `app\config\sources.yaml` → `enable_sentiment: false`.
- Данные и экспорты хранятся в `%LOCALAPPDATA%\RFPoliticalTrends\app\data` и `...\exports`.
