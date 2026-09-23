from app.solver.common import engineer_can_do_job
from app.services.distance import vehicle_minutes

def _route_for(solution, engineer_id):
    return next((r for r in solution.routes if r.engineer_id == engineer_id), None)

def _assigned_engineer(solution, job_id):
    for route in solution.routes:
        if any(s.job_id == job_id for s in route.stops):
            return route.engineer_id
    return None

def explain_assignment(engineers, jobs, solution, matrix, job_id):
    jobs_by_id = {j.id: j for j in jobs}
    if job_id not in jobs_by_id:
        return {"error": "JOB_NOT_FOUND"}

    job = jobs_by_id[job_id]
    selected_id = _assigned_engineer(solution, job_id)
    V = len(engineers)
    node = V + jobs.index(job)
    candidates = []

    for i, e in enumerate(engineers):
        missing = []
        if job.required_skill not in e.skills:
            missing.append({
                "code": "MISSING_SKILL",
                "message": f"Нет навыка «{job.required_skill}»",
            })
        if job.required_vehicle_type and e.vehicle_type != job.required_vehicle_type:
            missing.append({
                "code": "WRONG_VEHICLE",
                "message": f"Требуется «{job.required_vehicle_type}», у инженера «{e.vehicle_type}»",
            })
        route = _route_for(solution, e.id)
        candidates.append({
            "engineer_id": e.id,
            "engineer_name": e.name,
            "selected": e.id == selected_id,
            "eligible_resources": not missing,
            "missing": missing,
            "vehicle_type": e.vehicle_type,
            "skills": e.skills,
            "direct_distance_km": round(matrix.distance(i, node), 2),
            "direct_travel_minutes": vehicle_minutes(matrix.time(i, node), e.vehicle_type),
            "route_jobs": 0 if route is None else len(route.stops),
            "route_distance_km": 0 if route is None else route.total_distance_km,
        })

    candidates.sort(key=lambda c: (
        0 if c["selected"] else 1,
        0 if c["eligible_resources"] else 1,
        c["direct_travel_minutes"],
    ))

    selected = next((c for c in candidates if c["selected"]), None)
    if selected:
        normative_text = ""
        if job.normative_name:
            normative_text = (
                f" Норматив «{job.normative_name}»: {job.base_normative_minutes} мин "
                f"({job.normative_road_minutes} дорога + {job.technical_minutes} технические работы "
                f"+ {job.documents_minutes} документы). "
                f"В расчёте дорога берётся по сети, но не меньше {job.normative_road_minutes} мин."
            )
        rationale = (
            f"Заявка требует навык «{job.required_skill}»"
            + (f" и транспорт «{job.required_vehicle_type}»" if job.required_vehicle_type else "")
            + f". Выбран {selected['engineer_name']}: обязательные ограничения выполнены."
            + normative_text
            + f" Маршрут сформирован глобальным оптимизатором с приоритетом: выполнить максимум заявок, "
            f"задействовать меньше исполнителей и затем уменьшить пробег."
        )
    else:
        rationale = "Заявка не назначена: допустимое включение в текущий план не найдено."

    return {
        "job": job.model_dump(),
        "selected_engineer": selected_id,
        "selected": selected,
        "rationale": rationale,
        "candidates": candidates,
        "matrix_source": solution.matrix_source,
    }

def unassigned_reason(engineers, job):
    skilled = [e for e in engineers if job.required_skill in e.skills]
    if not skilled:
        return "Нет исполнителя с требуемым навыком.", "NO_REQUIRED_SKILL"

    if job.required_vehicle_type:
        vehicle = [e for e in engineers if e.vehicle_type == job.required_vehicle_type]
        if not vehicle:
            return "Нет исполнителя с требуемым типом транспорта.", "NO_REQUIRED_VEHICLE"
        joint = [e for e in skilled if e.vehicle_type == job.required_vehicle_type]
        if not joint:
            return "Нет исполнителя, одновременно удовлетворяющего навыку и транспорту.", "NO_JOINT_RESOURCE"

    return "Подходящие по ресурсу исполнители есть, но работа не помещается во временное окно или смену.", "TIME_WINDOW_OR_SHIFT"

def build_problems(engineers, jobs, solution):
    assigned = {}
    for route in solution.routes:
        for stop in route.stops:
            assigned[stop.job_id] = (route.engineer_id, stop)

    items = []
    for job in jobs:
        if job.id not in assigned:
            msg, code = unassigned_reason(engineers, job)
            items.append({
                "job_id": job.id,
                "severity": "critical" if job.priority == 2 else "warning",
                "type": "UNASSIGNED",
                "code": code,
                "message": msg,
            })
        else:
            engineer_id, stop = assigned[job.id]
            if stop.sla_lateness_minutes > 0:
                items.append({
                    "job_id": job.id,
                    "severity": "warning",
                    "type": "SLA_KPI",
                    "code": "FINISH_AFTER_WINDOW",
                    "message": f"Начало внутри окна, но завершение на {stop.sla_lateness_minutes} мин позже конца окна.",
                    "engineer_id": engineer_id,
                })
    return items
