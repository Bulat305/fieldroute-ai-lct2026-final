# FieldRoute AI v0.5.7 — Render Deploy

## Что добавлено

- `render.yaml` — Blueprint для Render;
- `.python-version` — Python 3.12.6;
- `/health` — health check;
- production start command:
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`;
- `.gitignore`.

## Вариант 1 — через GitHub + Render

### 1. Создать репозиторий GitHub

Создайте новый пустой репозиторий, например:

`fieldroute-ai`

Не добавляйте README/.gitignore при создании, потому что они уже есть в проекте.

### 2. Загрузить проект в GitHub

Откройте PowerShell в корне проекта:

```powershell
git init
git add .
git commit -m "FieldRoute AI v0.5.7 deploy"
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/fieldroute-ai.git
git push -u origin main
```

Если Git не установлен:

```powershell
winget install --id Git.Git
```

После установки откройте новое окно PowerShell.

### 3. Render

1. Откройте Render Dashboard.
2. New → Web Service.
3. Подключите GitHub.
4. Выберите `fieldroute-ai`.
5. Render должен обнаружить `render.yaml`.
6. Если создаёте Web Service вручную:

Build Command:

```text
pip install -r requirements.txt
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Python:

```text
3.12.6
```

Health check:

```text
/health
```

### 4. После Deploy

Render выдаст ссылку вида:

`https://fieldroute-ai-xxxx.onrender.com`

Проверьте:

- `/`
- `/health`
- `/docs`

## Free plan

Free plan подходит для проверки и передачи ссылки жюри/команде, но сервис может уходить в sleep при отсутствии запросов. Первый запрос после простоя может запускаться заметно дольше.

Для самой защиты лучше либо открыть сервис заранее, либо перейти на платный compute без cold start.

## Ограничения текущего MVP

- история и сценарии хранятся в RAM и очищаются при рестарте;
- внешний OSRM может отвечать медленно;
- при недоступности OSRM используется `haversine-fallback`;
- persistent database пока не используется.
