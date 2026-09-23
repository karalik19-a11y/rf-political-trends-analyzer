# RF Political Trends Analyzer

Сбор и анализ **публичных** политических новостей по РФ из **независимых** источников (не госСМИ).

Источники по умолчанию: **Meduza, Mediazona, The Moscow Times, BBC Russian, DW Russian, Novaya Gazeta Europe, Radio Svoboda**.

## Windows — установка

1. Python 3.9+ с [python.org](https://www.python.org/downloads/) (**Add to PATH**).
2. Скачайте ZIP репозитория → папка `installer\windows` → **`install.bat`**.
3. Ярлык на рабочем столе **RF Political Trends Dashboard**.

Переустановка поверх: `install.ps1 -Force`

Если RSS недоступны из РФ — включите VPN, затем **Run Collector** или кнопку «Собрать новости» в сайдбаре.

## В приложении

- **Собрать новости сейчас**
- **Проверить обновления** / **Скачать и установить** (без удаления, `data/` сохраняется)
- Экспорт CSV/JSON

## Ручной запуск

```bash
pip install feedparser requests pyyaml pandas streamlit plotly sqlalchemy python-dateutil nltk scikit-learn beautifulsoup4 lxml apscheduler
python run_collector.py
python run_dashboard.py
```

## Важно

Только публичные RSS. Не для слежки. Соблюдайте закон и этику.

MIT
