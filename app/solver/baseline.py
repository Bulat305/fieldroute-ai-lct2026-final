from app.models import Stop, Route, Solution
from app.services.distance import vehicle_minutes
from app.solver.common import engineer_can_do_job
from app.solver.metrics import calculate_metrics

def solve_baseline(engineers, jobs, matrix, coordinate_source="district-centroid-fallback"):
    """
    Официальный baseline из ТЗ:
    - заявки идут во входном порядке;
    - выбирается первый по порядку инженер, который удовлетворяет hard constraints;
    - порядок посещения равен порядку назначения;
    - глобальной оптимизации нет.
    """
    V = len(engineers)
    job_node = {j.id: V + i for i, j in enumerate(jobs)}
    state = {
        e.id: {
            "time": e.shift_start,
            "node": i,
            "stops": [],
            "distance": 0.0,
        }
        for i, e in enumerate(engineers)
    }
    unassigned = []

    for job in sorted(jobs, key=lambda j: j.source_index):
        chosen = None
        target = job_node[job.id]

        for e in engineers:
            if not engineer_can_do_job(e, job):
                continue
            st = state[e.id]
            travel = max(vehicle_minutes(matrix.time(st["node"], target), e.vehicle_type), job.normative_road_minutes)
            arrival = st["time"] + travel
            start = max(arrival, job.window_start)
            finish = start + job.service_minutes

            # ТЗ: начало работы внутри временного окна,
            # вся работа должна целиком помещаться в смену.
            if start > job.window_end:
                continue
            if finish > e.shift_end:
                continue

            chosen = (e, travel, arrival, start, finish, target)
            break

        if chosen is None:
            unassigned.append(job.id)
            continue

        e, travel, arrival, start, finish, target = chosen
        st = state[e.id]
        d = matrix.distance(st["node"], target)
        st["distance"] += d
        st["stops"].append(Stop(
            job_id=job.id,
            arrival=arrival,
            start=start,
            finish=finish,
            distance_km=round(d, 2),
            sla_lateness_minutes=max(0, finish - job.sla_deadline),
        ))
        st["time"] = finish
        st["node"] = target

    routes = [
        Route(
            engineer_id=e.id,
            stops=state[e.id]["stops"],
            total_distance_km=round(state[e.id]["distance"], 2),
        )
        for e in engineers
    ]
    return Solution(
        routes=routes,
        unassigned=unassigned,
        metrics=calculate_metrics(routes, unassigned, len(jobs)),
        matrix_source=matrix.source,
        coordinate_source=coordinate_source,
    )
