from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from app.models import Engineer, Job

BASE = Path(__file__).resolve().parents[1] / "data" / "beeline"

SKILL_LOCAL = "Локальные работы"
SKILL_CONNECT = "Работы на подключение и дозаказы"
SKILL_EMERGENCY = "Аварийные работы"
ALL_SKILLS = [SKILL_LOCAL, SKILL_CONNECT, SKILL_EMERGENCY]

VEHICLES = ["Автомобиль", "Пешеход", "Велосипед", "Общественный транспорт"]

REGIONS = {
    "east": {
        "name": "Восток",
        "synthetic": "east_synthetic.csv",
        "control": "east_control.csv",
        "office": (55.7008, 37.7658),
        "source_label": "Восток Синтетические данные.csv",
        "control_label": "Восток Контрольное распределение..csv",
    },
    "southeast": {
        "name": "Юго-восток",
        "synthetic": "southeast_synthetic.csv",
        "control": "southeast_control.csv",
        "office": (55.5945, 37.6670),
        "source_label": "Юго-восток Синтетические данные.csv",
        "control_label": "Юго-восток Контрольное распределение.csv",
    },
    "southcenter": {
        "name": "Югоцентр",
        "synthetic": "southcenter_synthetic.csv",
        "control": "southcenter_control.csv",
        "office": (55.6650, 37.6070),
        "source_label": "Югоцентр Синтетические данные.csv",
        "control_label": "Югоцентр Контрольное распределение..csv",
    },
}

DISTRICT_CENTERS = {
    "Таганский": (55.7404, 37.6536),
    "Текстильщики": (55.7088, 37.7314),
    "Кузьминки": (55.7056, 37.7654),
    "Рязанский": (55.7163, 37.7910),
    "Нижегородский": (55.7306, 37.7147),
    "Выхино": (55.7150, 37.8180),
    "Лефортово": (55.7586, 37.7050),
    "Басманный": (55.7670, 37.6680),
    "Южнопортовый": (55.7099, 37.6800),
    "Домодедово": (55.4372, 37.7680),
    "Орехово Борисово Южное": (55.6085, 37.7325),
    "Зябликово": (55.6127, 37.7461),
    "Москворечье - Сабурово": (55.6412, 37.6700),
    "Бирюлево Восточное": (55.5918, 37.6663),
    "Царицыно": (55.6210, 37.6677),
    "Орехово Борисово Северное": (55.6213, 37.7085),
    "Братеево": (55.6350, 37.7650),
    "Бирюлево Западное": (55.5873, 37.6437),
    "Кашира": (54.8534, 38.1905),
    "Ступино": (54.9008, 38.0708),
    "Даниловский": (55.7091, 37.6260),
    "GPON Даниловский": (55.7091, 37.6260),
    "Академический": (55.6877, 37.5732),
    "Котловка": (55.6767, 37.6090),
    "Зюзино": (55.6570, 37.5794),
    "Нагатинский Затон": (55.6795, 37.6786),
    "Хамовники": (55.7339, 37.5747),
    "Нагатино - Садовники": (55.6718, 37.6477),
    "Замоскворечье": (55.7356, 37.6352),
    "Нагорный": (55.6650, 37.6100),
    "Донской": (55.7046, 37.6002),
    "Гагаринский": (55.6910, 37.5560),
}

OFFICIAL_NORMATIVES = {'Подключение': {'name': 'Подключение клиентов Базовая', 'road_minutes': 20, 'technical_minutes': 60, 'documents_minutes': 10, 'base_normative_minutes': 90}, 'Глобальная проблема': {'name': 'Аварий на ТКД', 'road_minutes': 20, 'technical_minutes': 80, 'documents_minutes': 0, 'base_normative_minutes': 100}, 'Дозаказ': {'name': 'Дозаказ оборудования', 'road_minutes': 20, 'technical_minutes': 10, 'documents_minutes': 10, 'base_normative_minutes': 40}, 'Локальная заявка': {'name': 'Локальная заявка/ремонт у клиента', 'road_minutes': 20, 'technical_minutes': 30, 'documents_minutes': 0, 'base_normative_minutes': 50}}

def _normative_for(bk_type: str):
    return OFFICIAL_NORMATIVES.get(
        bk_type,
        {
            "name": "Норматив не определён",
            "road_minutes": 20,
            "technical_minutes": 30,
            "documents_minutes": 0,
            "base_normative_minutes": 50,
        },
    )

def _read_cp1251(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Встроенный файл датасета не найден: {path.name}. "
            f"Переустановите полную сборку FieldRoute AI."
        )
    return path.read_bytes().decode("cp1251")

def _minutes(value: str) -> int:
    dt = datetime.strptime(value.strip(), "%d.%m.%Y %H:%M")
    return dt.hour * 60 + dt.minute

def _point_from_district(district: str, address: str, office: Tuple[float, float]):
    center = DISTRICT_CENTERS.get(district, office)
    digest = hashlib.sha1(address.encode("utf-8")).digest()
    a = int.from_bytes(digest[:2], "big") / 65535.0 - 0.5
    b = int.from_bytes(digest[2:4], "big") / 65535.0 - 0.5
    spread = 0.018 if district not in ("Кашира", "Ступино", "Домодедово") else 0.035
    return center[0] + a * spread, center[1] + b * spread

def _required_skill(bk_type: str) -> str:
    if bk_type == "Локальная заявка":
        return SKILL_LOCAL
    if bk_type in ("Подключение", "Дозаказ"):
        return SKILL_CONNECT
    return SKILL_EMERGENCY

def _priority(hd_type: str) -> int:
    return 2 if hd_type.strip() == "Авария" else 1

def _generated_required_vehicle(job_id: str):
    # В исходном архиве отдельного поля транспорта нет.
    # Для проверки обязательного resource constraint добавляем
    # прозрачное детерминированное demo-допущение примерно для 15% заявок.
    n = int(hashlib.sha1(job_id.encode()).hexdigest()[:8], 16)
    if n % 17 == 0:
        return "Автомобиль"
    if n % 29 == 0:
        return "Общественный транспорт"
    if n % 37 == 0:
        return "Велосипед"
    if n % 43 == 0:
        return "Пешеход"
    return None

def _extract_rows(region_key: str):
    cfg = REGIONS[region_key]
    text = _read_cp1251(BASE / cfg["synthetic"])
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = []
    for r in reader:
        job_id = (r.get("Заявка") or "").strip()
        if job_id.isdigit():
            rows.append(r)
    return rows

def _brigades(region_key: str):
    cfg = REGIONS[region_key]
    text = _read_cp1251(BASE / cfg["control"])
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    names = []
    seen = set()
    for r in reader:
        name = (r.get("Бригада") or "").strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names

def _engineer_attributes(i: int):
    vehicle_pattern = [
        "Автомобиль", "Автомобиль", "Пешеход",
        "Велосипед", "Общественный транспорт"
    ]
    skills_pattern = [
        ALL_SKILLS,
        [SKILL_LOCAL, SKILL_CONNECT],
        [SKILL_CONNECT, SKILL_EMERGENCY],
        [SKILL_LOCAL, SKILL_EMERGENCY],
        ALL_SKILLS,
    ]
    return list(skills_pattern[i % len(skills_pattern)]), vehicle_pattern[i % len(vehicle_pattern)]

def load_region(region_key: str):
    if region_key not in REGIONS:
        region_key = "east"

    cfg = REGIONS[region_key]
    office = cfg["office"]
    rows = _extract_rows(region_key)
    brigade_names = _brigades(region_key)

    engineers: List[Engineer] = []
    for i, name in enumerate(brigade_names):
        skills, vehicle = _engineer_attributes(i)
        engineers.append(Engineer(
            id=f"E{i+1:02d}",
            name=name,
            lat=office[0],
            lon=office[1],
            shift_start=9 * 60,
            shift_end=23 * 60,
            skills=skills,
            vehicle_type=vehicle,
            region=cfg["name"],
        ))

    jobs: List[Job] = []
    for idx, r in enumerate(rows):
        job_id = (r.get("Заявка") or "").strip()
        district = (r.get("Район") or "").strip()
        address = (r.get("Адрес") or "").strip()
        bk = (r.get("Тип заявки BK") or "").strip()
        hd = (r.get("Тип заявки HD") or "").strip()
        ws = _minutes(r["Начало"])
        we = _minutes(r["Окончание"])
        lat, lon = _point_from_district(district, address, office)
        norm = _normative_for(bk)
        service_minutes = norm["technical_minutes"] + norm["documents_minutes"]
        jobs.append(Job(
            id=job_id,
            source_index=idx,
            region=cfg["name"],
            address=address,
            district=district,
            lat=lat,
            lon=lon,
            bk_type=bk,
            hd_type=hd,
            priority=_priority(hd),
            service_minutes=service_minutes,
            normative_name=norm["name"],
            normative_road_minutes=norm["road_minutes"],
            technical_minutes=norm["technical_minutes"],
            documents_minutes=norm["documents_minutes"],
            base_normative_minutes=norm["base_normative_minutes"],
            window_start=ws,
            window_end=we,
            sla_deadline=we,
            required_skill=_required_skill(bk),
            required_vehicle_type=_generated_required_vehicle(job_id),
        ))

    assumptions = {
        "source": cfg.get("source_label", cfg["synthetic"]),
        "control_source": cfg.get("control_label", cfg["control"]),
        "jobs": len(jobs),
        "engineers": len(engineers),
        "coordinate_source": "district-centroid-fallback",
        "engineer_source": "brigade names from control file; skills/shift/vehicle generated by documented demo rules",
        "duration_source": "официальные нормативы из Нормативы.xlsx; service = технические работы + документы; дорожное плечо не меньше 20 мин и заменяется фактическим OSRM, если оно больше",
        "transport_source": "source archive has no required transport field; deterministic demo requirements added to a subset",
        "priority_source": "Тип заявки HD=Авария -> Срочная; others -> Обычная",
        "shift_assumption": "09:00-23:00 for generated engineers",
        "normatives_source": "Нормативы.xlsx",
        "normatives": list(OFFICIAL_NORMATIVES.values()),
    }
    return engineers, jobs, assumptions

def region_catalog():
    return [
        {"id": key, "name": cfg["name"], "jobs": len(_extract_rows(key)), "engineers": len(_brigades(key))}
        for key, cfg in REGIONS.items()
    ]
