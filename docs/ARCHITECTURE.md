# Архитектура FieldRoute AI

## Схема

```text
┌──────────────────────────────────────────────────────────┐
│ Browser UI                                               │
│ HTML / JavaScript / MapLibre GL JS                       │
│ KPI · карта · инженеры · проблемы · Demo Mode            │
└────────────────────────┬─────────────────────────────────┘
                         │ REST
                         ▼
┌──────────────────────────────────────────────────────────┐
│ FastAPI                                                  │
│ dataset · import · explain · problems · replan           │
└───────────────┬─────────────────────────────┬────────────┘
                │                             │
                ▼                             ▼
┌───────────────────────────────┐  ┌───────────────────────┐
│ Optimization                  │  │ Routing               │
│ Google OR-Tools               │  │ OSRM Table / Route    │
│ VRP / time windows / skills   │  │ road time / geometry  │
│ vehicle compatibility         │  └───────────┬───────────┘
└───────────────┬───────────────┘              │
                │                              ▼
                │                    Haversine / straight
                │                    fallback on failures
                ▼
┌──────────────────────────────────────────────────────────┐
│ Result                                                   │
│ routes · assignments · KPI · explanations · replanning   │
└──────────────────────────────────────────────────────────┘
```

## Frontend

Интерфейс работает в браузере и включает:

- выбор региона;
- KPI;
- интерактивную карту;
- список заявок;
- список бригад;
- выделение отдельного маршрута;
- плановую позицию бригады;
- окно стратегий;
- Explainability;
- Problems;
- Demo Mode;
- Import CSV/XLSX.

## Backend

FastAPI предоставляет HTTP API для:

- встроенного датасета;
- baseline / optimized comparison;
- explainability;
- проблем;
- геометрии маршрутов;
- срочного перепланирования;
- пользовательского импорта;
- health check.

## Optimization layer

OR-Tools решает расширенную routing-задачу с несколькими инженерами.

Главные обязательные ограничения:

- skill compatibility;
- vehicle compatibility;
- job time windows;
- engineer shifts.

Стоимость активации исполнителя используется для минимизации числа задействованных инженеров после максимизации числа назначенных заявок.

## Routing layer

OSRM используется в двух ролях:

1. **Table API** — дорожное время и расстояния для optimization matrix.
2. **Route API** — дорожная геометрия для отображения маршрутов.

При ошибке внешнего routing backend предусмотрен fallback.

## Deployment

Прототип может запускаться локально или как FastAPI web service.

Текущий публичный стенд развернут на Render:

```text
https://fieldroute-ai.onrender.com
```

Render free instance может иметь cold start после периода бездействия.
