# RF Political Trends Analyzer

Открытая система сбора и анализа **публичной** политической информации и тенденций по Российской Федерации.

**Важно:** Система работает только с открытыми источниками (RSS официальных агентств и публичных новостных сайтов). Не предназначена для несанкционированного сбора данных, мониторинга частных лиц или нарушения законодательства. Используйте ответственно, соблюдайте robots.txt, rate limits и условия использования источников.

## Возможности (v1.2)

- Автоматический сбор новостей из RSS-лент (TASS, RIA, Interfax, Известия, РГ, Коммерсантъ и др.)
- Хранение в SQLite
- **Русский NLP**: извлечение ключевых слов + sentiment-анализ (модель `cointegrated/rubert-tiny-sentiment-balanced`)
- **Планировщик** ежедневного сбора (APScheduler + Windows Task Scheduler)
- **Экспорт** в CSV и JSON
- Streamlit-дашборд с графиками, трендами, sentiment и поиском по темам
- **Windows Installer** — автоматическая установка, ярлыки, ежедневное задание

## Установка на Windows (рекомендуется)

1. Установите [Python 3.9+](https://www.python.org/downloads/) (обязательно отметьте **Add to PATH**).
2. Скачайте репозиторий (Code → Download ZIP) или клонируйте.
3. Перейдите в папку `installer\windows` и запустите **`install.bat`**.

Подробности: [installer/windows/README_INSTALL_RU.md](installer/windows/README_INSTALL_RU.md)

Установщик скачает код, создаст venv, установит зависимости, сделает ярлыки и зарегистрирует ежедневный сбор в Планировщике заданий Windows.

## Ручная установка (Linux / macOS / Windows)

```bash
git clone https://github.com/karalik19-a11y/rf-political-trends-analyzer.git
cd rf-political-trends-analyzer
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Разовый сбор данных
python -m src.collector

# Запуск дашборда
streamlit run src/dashboard.py

# Ежедневный сбор (по умолчанию в 06:00 UTC)
python -m src.scheduler
# или с другим временем:
python -m src.scheduler --hour 3 --minute 30

# Экспорт
python -m src.export --format both
```

> При первом запуске sentiment-модели transformers скачает веса (~десятки МБ). Можно отключить в `config/sources.yaml` → `enable_sentiment: false`.

## Структура

```
config/
  sources.yaml          # RSS-источники + настройки NLP
src/
  collector.py          # Сбор из RSS + NLP
  nlp_utils.py          # Ключевые слова + sentiment (transformers)
  database.py           # SQLite
  analyzer.py           # Тренды и агрегаты
  dashboard.py          # Streamlit UI
  scheduler.py          # Ежедневный запуск
  export.py             # CSV / JSON
installer/
  windows/              # Установщик для Windows
exports/                # Папка экспортов (создаётся автоматически)
data/                   # SQLite (в .gitignore)
```

## Источники (по умолчанию)

- TASS
- RIA Novosti
- Interfax
- Izvestia
- Rossiyskaya Gazeta
- Kommersant

Добавляйте только легальные публичные ленты в `config/sources.yaml`.

## Этические и правовые замечания

- Собирайте только публично доступные данные.
- Соблюдайте robots.txt и условия использования сайтов.
- Не используйте для доксинга, преследования или незаконной деятельности.
- Для коммерческого или масштабного использования проверяйте лицензии источников.
- Система не хранит персональные данные частных лиц.

## Требования

- Python 3.9+
- Для sentiment: torch + transformers (можно отключить)
- Windows 10/11 для автоматического установщика

## Лицензия

MIT. Используйте на свой страх и риск.
