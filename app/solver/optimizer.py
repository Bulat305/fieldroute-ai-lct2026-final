from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from app.models import Stop, Route, Solution
from app.services.distance import vehicle_minutes
from app.solver.common import engineer_can_do_job
from app.solver.metrics import calculate_metrics

DROP_PENALTY_NORMAL = 100_000_000
DROP_PENALTY_URGENT = 300_000_000

STRATEGIES = {
    "official": {
        "name": "Конкурсная",
        "fixed_vehicle_cost": 2_000_000,
        "distance_multiplier": 1,
        "sla_proxy_penalty": 0,
    },
    "balanced": {
        "name": "Сбалансированная",
        "fixed_vehicle_cost": 500_000,
        "distance_multiplier": 1,
        "sla_proxy_penalty": 8_000,
    },
    "sla_first": {
        "name": "Приоритет SLA",
        "fixed_vehicle_cost": 150_000,
        "distance_multiplier": 1,
        "sla_proxy_penalty": 40_000,
    },
    "distance_first": {
        "name": "Минимум пробега",
        "fixed_vehicle_cost": 0,
        "distance_multiplier": 1,
        "sla_proxy_penalty": 0,
    },
}

def solve_optimized(engineers, jobs, matrix, time_limit_seconds=2, strategy="official", coordinate_source="district-centroid-fallback"):
    profile = STRATEGIES.get(strategy, STRATEGIES["official"])
    V = len(engineers)
    N = V + len(jobs)
    starts = list(range(V))
    ends = list(range(V))

    manager = pywrapcp.RoutingIndexManager(N, V, starts, ends)
    routing = pywrapcp.RoutingModel(manager)

    def distance_cb(from_index, to_index):
        fn = manager.IndexToNode(from_index)
        tn = manager.IndexToNode(to_index)
        if tn < V:
            return 0
        return max(1, int(round(matrix.distance(fn, tn) * 1000 * profile["distance_multiplier"])))

    distance_idx = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(distance_idx)

    for v in range(V):
        routing.SetFixedCostOfVehicle(profile["fixed_vehicle_cost"], v)

    service_by_node = [0] * V + [j.service_minutes for j in jobs]
    transit_indices = []

    for engineer in engineers:
        def make_time_cb(vehicle_type):
            def time_cb(from_index, to_index):
                fn = manager.IndexToNode(from_index)
                tn = manager.IndexToNode(to_index)
                if tn < V:
                    travel = 0
                else:
                    target_job = jobs[tn - V]
                    actual_travel = vehicle_minutes(matrix.time(fn, tn), vehicle_type)
                    travel = max(actual_travel, target_job.normative_road_minutes)
                return int(travel + service_by_node[fn])
            return time_cb
        transit_indices.append(routing.RegisterTransitCallback(make_time_cb(engineer.vehicle_type)))

    routing.AddDimensionWithVehicleTransits(transit_indices, 12 * 60, 24 * 60, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")

    for v, e in enumerate(engineers):
        time_dim.CumulVar(routing.Start(v)).SetRange(e.shift_start, e.shift_start)
        time_dim.CumulVar(routing.End(v)).SetRange(e.shift_start, e.shift_end)

    for j_idx, job in enumerate(jobs):
        node = V + j_idx
        idx = manager.NodeToIndex(node)
        eligible = [v for v, e in enumerate(engineers) if engineer_can_do_job(e, job)]
        routing.AddDisjunction([idx], DROP_PENALTY_URGENT if job.priority == 2 else DROP_PENALTY_NORMAL)
        routing.VehicleVar(idx).SetValues(eligible + [-1] if eligible else [-1])
        time_dim.CumulVar(idx).SetRange(job.window_start, job.window_end)
        if profile["sla_proxy_penalty"] > 0:
            desirable_start = max(job.window_start, job.window_end - job.service_minutes)
            time_dim.SetCumulVarSoftUpperBound(idx, desirable_start, profile["sla_proxy_penalty"])

    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search.time_limit.seconds = max(1, int(time_limit_seconds))

    assignment = routing.SolveWithParameters(search)
    if assignment is None:
        from app.solver.baseline import solve_baseline
        return solve_baseline(engineers, jobs, matrix, coordinate_source=coordinate_source)

    assigned = set()
    routes = []
    for v, e in enumerate(engineers):
        index = routing.Start(v)
        stops = []
        total_distance = 0.0
        prev_node = v
        while not routing.IsEnd(index):
            next_index = assignment.Value(routing.NextVar(index))
            if routing.IsEnd(next_index):
                break
            node = manager.IndexToNode(next_index)
            if node >= V:
                job = jobs[node - V]
                assigned.add(job.id)
                start = assignment.Value(time_dim.CumulVar(next_index))
                arrival = start
                finish = start + job.service_minutes
                d = matrix.distance(prev_node, node)
                total_distance += d
                stops.append(Stop(
                    job_id=job.id,
                    arrival=arrival,
                    start=start,
                    finish=finish,
                    distance_km=round(d, 2),
                    sla_lateness_minutes=max(0, finish - job.sla_deadline),
                ))
                prev_node = node
            index = next_index
        routes.append(Route(engineer_id=e.id, stops=stops, total_distance_km=round(total_distance, 2)))

    unassigned = [j.id for j in jobs if j.id not in assigned]
    return Solution(
        routes=routes,
        unassigned=unassigned,
        metrics=calculate_metrics(routes, unassigned, len(jobs)),
        matrix_source=matrix.source,
        coordinate_source=coordinate_source,
    )
