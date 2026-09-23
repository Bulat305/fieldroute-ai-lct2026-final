from copy import deepcopy
from app.models import Job
from app.services.matrix import build_matrix
from app.solver.optimizer import solve_optimized

def assignment_map(solution):
    out = {}
    order = {}
    for route in solution.routes:
        order[route.engineer_id] = [s.job_id for s in route.stops]
        for stop in route.stops:
            out[stop.job_id] = route.engineer_id
    return out, order

def replan(engineers, jobs, old_solution, current_time=15*60, use_osrm=True, strategy="official"):
    old_map, old_order = assignment_map(old_solution)
    jobs_by_id = {j.id: j for j in jobs}
    routes_by_engineer = {r.engineer_id: r for r in old_solution.routes}

    locked = set()
    updated = []

    for e in engineers:
        ne = deepcopy(e)
        available = max(current_time, e.shift_start)
        last_lat, last_lon = e.lat, e.lon
        route = routes_by_engineer.get(e.id)

        if route:
            for stop in route.stops:
                job = jobs_by_id[stop.job_id]
                if stop.finish <= current_time:
                    locked.add(job.id)
                    last_lat, last_lon = job.lat, job.lon
                    available = max(available, stop.finish)
                elif stop.start <= current_time < stop.finish:
                    locked.add(job.id)
                    last_lat, last_lon = job.lat, job.lon
                    available = stop.finish
                    break

        ne.lat, ne.lon = last_lat, last_lon
        ne.shift_start = min(max(available, ne.shift_start), ne.shift_end)
        updated.append(ne)

    remaining = [j for j in jobs if j.id not in locked and j.window_end >= current_time]

    # Новая срочная заявка — демонстрационное событие из ТЗ.
    center_lat = sum(j.lat for j in jobs) / len(jobs)
    center_lon = sum(j.lon for j in jobs) / len(jobs)
    emergency = Job(
        id="EMERGENCY-001",
        source_index=10**9,
        region=jobs[0].region if jobs else "",
        address="Срочная заявка, добавленная в течение дня",
        district="",
        lat=center_lat + 0.008,
        lon=center_lon - 0.006,
        bk_type="Глобальная проблема",
        hd_type="Авария",
        priority=2,
        service_minutes=80,
        normative_name="Аварий на ТКД",
        normative_road_minutes=20,
        technical_minutes=80,
        documents_minutes=0,
        base_normative_minutes=100,
        window_start=current_time,
        window_end=min(current_time + 120, 22 * 60),
        sla_deadline=min(current_time + 90, 22 * 60),
        required_skill="Аварийные работы",
        required_vehicle_type="Автомобиль",
    )
    remaining.append(emergency)

    coords = [(e.lat, e.lon) for e in updated] + [(j.lat, j.lon) for j in remaining]
    matrix = build_matrix(coords, use_osrm=use_osrm)
    new_solution = solve_optimized(
        updated,
        remaining,
        matrix,
        time_limit_seconds=10,
        strategy=strategy,
        coordinate_source="district-centroid-fallback",
    )

    new_map, new_order = assignment_map(new_solution)
    future_old = {
        jid: eng for jid, eng in old_map.items()
        if jid not in locked and jid in {j.id for j in remaining}
    }

    changed_assignments = []
    for jid, old_eng in future_old.items():
        new_eng = new_map.get(jid)
        if new_eng != old_eng:
            changed_assignments.append({
                "job_id": jid,
                "before": old_eng,
                "after": new_eng or "не назначена",
            })

    order_changes = []
    for engineer_id in set(old_order) | set(new_order):
        before = [x for x in old_order.get(engineer_id, []) if x not in locked]
        after = [x for x in new_order.get(engineer_id, []) if x != "EMERGENCY-001"]
        if before != after:
            order_changes.append({
                "engineer_id": engineer_id,
                "before": before,
                "after": after,
            })

    denom = max(1, len(future_old))
    stability = 1 - len(changed_assignments) / denom

    emergency_engineer = new_map.get(emergency.id)
    emergency_stop = None
    if emergency_engineer:
        route = next(r for r in new_solution.routes if r.engineer_id == emergency_engineer)
        emergency_stop = next((s for s in route.stops if s.job_id == emergency.id), None)

    regular_remaining_ids = {j.id for j in remaining if j.id != emergency.id}
    assigned_regular_after = sum(1 for jid in regular_remaining_ids if jid in new_map)
    emergency_assigned = emergency.id in new_map

    return {
        "current_time": current_time,
        "locked_jobs": sorted(locked),
        "locked_jobs_count": len(locked),
        "regular_remaining_jobs_count": len(regular_remaining_ids),
        "replanning_jobs_count": len(remaining),
        "assigned_regular_after_replan": assigned_regular_after,
        "unassigned_regular_after_replan": len(regular_remaining_ids) - assigned_regular_after,
        "previous_future_assigned_count": len(future_old),
        "emergency_job": emergency.model_dump(),
        "selected_engineer": emergency_engineer,
        "emergency_assigned": emergency_assigned,
        "emergency_eta_minutes": None if emergency_stop is None else max(0, emergency_stop.start - current_time),
        # Для аварийной заявки SLA интерпретируется как дедлайн реакции:
        # инженер должен прибыть / начать работу до sla_deadline.
        "emergency_sla_margin_minutes": None if emergency_stop is None else emergency.sla_deadline - emergency_stop.start,
        "emergency_completion_minutes": None if emergency_stop is None else max(0, emergency_stop.finish - current_time),
        "changed_assignments": changed_assignments,
        "order_changes": order_changes,
        "plan_stability": round(stability, 4),
        "solution": new_solution.model_dump(),
        "updated_engineers": [e.model_dump() for e in updated],
        "replanning_jobs": [j.model_dump() for j in remaining],
    }
