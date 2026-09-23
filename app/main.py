from pathlib import Path
from threading import RLock

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.models import Solution
from app.services.beeline_data import load_region, region_catalog
from app.services.matrix import build_matrix, route_geometry
from app.services.explainer import explain_assignment, build_problems
from app.services.replanner import replan
from app.services.custom_import import parse_engineers, parse_jobs
from app.solver.baseline import solve_baseline
from app.solver.optimizer import solve_optimized, STRATEGIES

app = FastAPI(title="FieldRoute AI", version="0.6.9")
BASE = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

CACHE = {}
LOCK = RLock()
CUSTOM_ENGINEERS = None
CUSTOM_JOBS = None
GEOMETRY_CACHE = {}

def get_data(region):
    if region == "custom":
        if CUSTOM_ENGINEERS is None or CUSTOM_JOBS is None:
            raise HTTPException(400, "Для пользовательского набора импортируйте инженеров и заявки.")
        assumptions = {
            "source": "user-import",
            "control_source": "not-applicable",
            "jobs": len(CUSTOM_JOBS),
            "engineers": len(CUSTOM_ENGINEERS),
            "coordinate_source": "uploaded-lat-lon",
            "engineer_source": "uploaded",
            "duration_source": "uploaded",
            "transport_source": "uploaded",
            "priority_source": "uploaded",
            "shift_assumption": "uploaded",
        }
        return CUSTOM_ENGINEERS, CUSTOM_JOBS, assumptions

    key = ("data", region)
    with LOCK:
        if key in CACHE:
            return CACHE[key]
    value = load_region(region)
    with LOCK:
        CACHE[key] = value
    return value

def get_matrix(region, road=True):
    key = ("matrix", region, bool(road))
    with LOCK:
        if key in CACHE:
            return CACHE[key]
    engineers, jobs, assumptions = get_data(region)
    coords = [(e.lat, e.lon) for e in engineers] + [(j.lat, j.lon) for j in jobs]
    value = build_matrix(coords, use_osrm=road)
    with LOCK:
        CACHE[key] = value
    return value

def get_compare(region="east", road=True, seconds=10, strategy="official"):
    if strategy not in STRATEGIES:
        strategy = "official"
    key = ("compare", region, bool(road), int(seconds), strategy)
    with LOCK:
        if key in CACHE:
            return CACHE[key]

    engineers, jobs, assumptions = get_data(region)
    matrix = get_matrix(region, road=road)
    coordinate_source = assumptions["coordinate_source"]

    baseline = solve_baseline(engineers, jobs, matrix, coordinate_source=coordinate_source)
    optimized = solve_optimized(
        engineers, jobs, matrix,
        time_limit_seconds=seconds,
        strategy=strategy,
        coordinate_source=coordinate_source,
    )

    b = baseline.metrics
    o = optimized.metrics
    payload = {
        "strategy": strategy,
        "strategy_name": STRATEGIES[strategy]["name"],
        "baseline": baseline.model_dump(),
        "optimized": optimized.model_dump(),
        "improvement": {
            "active_engineers_delta": b.active_engineers - o.active_engineers,
            "active_engineers_pct": None if b.active_engineers == 0 else round((b.active_engineers-o.active_engineers)/b.active_engineers*100, 2),
            "distance_pct": None if b.total_distance_km == 0 else round((b.total_distance_km-o.total_distance_km)/b.total_distance_km*100, 2),
            "assigned_delta": o.assigned_jobs - b.assigned_jobs,
            "sla_points": round((o.sla_compliance-b.sla_compliance)*100, 2),
        },
        "assumptions": assumptions,
    }
    with LOCK:
        CACHE[key] = payload
    return payload

@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status": "ok", "service": "FieldRoute AI", "version": "0.6.9"}


@app.get("/api/embedded-data-status")
def embedded_data_status():
    status = []
    for region in ("east", "southeast", "southcenter"):
        engineers, jobs, assumptions = get_data(region)
        status.append({
            "region": region,
            "jobs": len(jobs),
            "engineers": len(engineers),
            "source": assumptions.get("source"),
            "ready": True,
        })
    return {
        "ready": True,
        "default_region": "east",
        "regions": status,
    }

@app.get("/api/regions")
def regions():
    return {"items": region_catalog()}

@app.get("/api/strategies")
def strategies():
    return {
        "default": "official",
        "items": [{"id": key, "name": value["name"]} for key, value in STRATEGIES.items()],
    }

@app.get("/api/normatives")
def normatives():
    return {
        "source": "Нормативы.xlsx",
        "rule": "travel = max(road network time, норматив дороги); service = технические работы + документы",
        "items": {'Подключение': {'name': 'Подключение клиентов Базовая', 'road_minutes': 20, 'technical_minutes': 60, 'documents_minutes': 10, 'base_normative_minutes': 90}, 'Глобальная проблема': {'name': 'Аварий на ТКД', 'road_minutes': 20, 'technical_minutes': 80, 'documents_minutes': 0, 'base_normative_minutes': 100}, 'Дозаказ': {'name': 'Дозаказ оборудования', 'road_minutes': 20, 'technical_minutes': 10, 'documents_minutes': 10, 'base_normative_minutes': 40}, 'Локальная заявка': {'name': 'Локальная заявка/ремонт у клиента', 'road_minutes': 20, 'technical_minutes': 30, 'documents_minutes': 0, 'base_normative_minutes': 50}},
    }

@app.get("/api/dataset")
def dataset(region: str = "east"):
    engineers, jobs, assumptions = get_data(region)
    return {
        "region": region,
        "engineers": [e.model_dump() for e in engineers],
        "jobs": [j.model_dump() for j in jobs],
        "assumptions": assumptions,
    }

@app.get("/api/compare")
def compare(region: str = "east", road: bool = True, seconds: int = 10, strategy: str = "official"):
    return get_compare(region=region, road=road, seconds=max(1, min(seconds, 10)), strategy=strategy)

@app.get("/api/problems")
def problems(region: str = "east", road: bool = True, strategy: str = "official"):
    engineers, jobs, _ = get_data(region)
    matrix = get_matrix(region, road)
    payload = get_compare(region, road, 10, strategy)
    solution = Solution.model_validate(payload["optimized"])
    items = build_problems(engineers, jobs, solution)
    return {"items": items, "count": len(items)}

@app.get("/api/explain/{job_id}")
def explain(job_id: str, region: str = "east", road: bool = True, strategy: str = "official"):
    engineers, jobs, _ = get_data(region)
    matrix = get_matrix(region, road)
    payload = get_compare(region, road, 10, strategy)
    solution = Solution.model_validate(payload["optimized"])
    result = explain_assignment(engineers, jobs, solution, matrix, job_id)
    if result.get("error"):
        raise HTTPException(404, "Заявка не найдена")
    return result

@app.post("/api/import/engineers")
async def import_engineers(file: UploadFile = File(...)):
    global CUSTOM_ENGINEERS
    raw = await file.read()
    try:
        CUSTOM_ENGINEERS = parse_engineers(raw, file.filename or "engineers.csv")
    except Exception as exc:
        raise HTTPException(400, f"Ошибка импорта инженеров: {exc}")
    with LOCK:
        CACHE.clear()
        GEOMETRY_CACHE.clear()
    return {"ok": True, "count": len(CUSTOM_ENGINEERS), "custom_ready": CUSTOM_JOBS is not None, "message": "Инженеры импортированы"}

@app.post("/api/import/jobs")
async def import_jobs(file: UploadFile = File(...)):
    global CUSTOM_JOBS
    raw = await file.read()
    try:
        CUSTOM_JOBS = parse_jobs(raw, file.filename or "jobs.csv")
    except Exception as exc:
        raise HTTPException(400, f"Ошибка импорта заявок: {exc}")
    with LOCK:
        CACHE.clear()
        GEOMETRY_CACHE.clear()
    return {"ok": True, "count": len(CUSTOM_JOBS), "custom_ready": CUSTOM_ENGINEERS is not None, "message": "Заявки импортированы"}

@app.post("/api/route-geometry")
def geometry(payload: dict):
    coords = payload.get("coords", [])
    parsed = [(float(x["lat"]), float(x["lon"])) for x in coords]
    key = tuple((round(lat, 6), round(lon, 6)) for lat, lon in parsed)
    with LOCK:
        cached = GEOMETRY_CACHE.get(key)
    if cached is not None:
        return {**cached, "cache_hit": True}
    result = route_geometry(parsed, with_source=True)
    with LOCK:
        GEOMETRY_CACHE[key] = result
    return {**result, "cache_hit": False}

@app.post("/api/replan")
def emergency_replan(region: str = "east", road: bool = True, strategy: str = "official"):
    engineers, jobs, _ = get_data(region)
    matrix = get_matrix(region, road)
    payload = get_compare(region, road, 10, strategy)
    current = Solution.model_validate(payload["optimized"])
    # replanning core retains official hard constraints; selected strategy is used for current plan.
    return replan(engineers, jobs, current, current_time=15*60, use_osrm=road, strategy=strategy)
