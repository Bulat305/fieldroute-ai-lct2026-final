# FieldRoute AI — Render Deployment

## Production deployment

Рабочий web-прототип FieldRoute AI:

https://fieldroute-ai-lct2026-final.onrender.com/

Версия: `v0.6.9 stable`

## Render configuration

Проект подготовлен для развертывания как Render Web Service.

### Runtime

```text
Python 3.12.6
```

### Build command

```text
pip install -r requirements.txt
```

### Start command

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Health check

```text
/health
```

## Файлы конфигурации

- `render.yaml` — конфигурация Render;
- `.python-version` — версия Python;
- `requirements.txt` — зависимости проекта;
- `start.sh` — production start script;
- `.gitignore` — исключения для Git.

## Основные endpoints

- `/` — web-интерфейс FieldRoute AI;
- `/health` — проверка состояния сервиса;
- `/docs` — Swagger / OpenAPI документация FastAPI.

## Стек развернутого решения

- **Backend:** FastAPI;
- **Optimization:** Google OR-Tools;
- **Routing:** OSRM;
- **Map:** MapLibre GL JS / OpenStreetMap;
- **Deployment:** Render.

Основной и аварийный solver используют лимит поиска 10 секунд.

## Работа с маршрутизацией

Для расчета дорожного времени и геометрии маршрутов используется внешний OSRM.

При недоступности routing-сервиса предусмотрен fallback-режим на основе географического расстояния.

## Особенности runtime

Конкурсный MVP не использует persistent production database.

Состояние пользовательского импорта и часть временных данных хранятся в памяти процесса и очищаются при рестарте сервиса.

Внешний OSRM может иметь переменное время ответа.

## Статус

Render используется как публичный стенд конкурсного прототипа FieldRoute AI для ЛЦТ 2026.
