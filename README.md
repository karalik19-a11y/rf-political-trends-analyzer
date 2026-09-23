# RF Regional Political Analytics

Региональная аналитика (субъект / город): медиа, карта, выборы из CSV.

## Самый простой запуск (Windows)

1. Установите [Python 3.9+](https://www.python.org/downloads/) с галочкой **Add to PATH**.
2. Скачайте ZIP репозитория и распакуйте.
3. Дважды нажмите **`START.bat`**.

Всё остальное (venv, библиотеки, браузер) сделает сам `bootstrap.py`.

```text
START.bat                  — запуск
START.bat  →  внутри можно: python bootstrap.py --update
```

Или в командной строке из папки проекта:

```bash
python bootstrap.py              # запуск
python bootstrap.py --update     # обновить код с GitHub, затем запуск
python bootstrap.py --collect    # сначала сбор новостей, потом UI
```

## Обновление вместе с репозиторием

**Вариант 1 — в приложении**  
Сайдбар → «Проверить обновление на GitHub» → «Скачать и установить» → закрыть окно → снова `START.bat`.

**Вариант 2 — одной командой**

```bash
python bootstrap.py --update
```

Обновляются файлы кода с ветки `main`. Папки **`data/`** (новости, выборы) и **`venv/`** не удаляются.

**Вариант 3 — git**

```bash
git pull
python bootstrap.py
```

## Что внутри

| | |
|---|---|
| A | Справочник регионов и городов |
| B | Выборы из `data/elections/*.csv` |
| C | Независимые RSS → регион/город + карта |

Нет сбора взглядов людей «по улицам».

MIT
