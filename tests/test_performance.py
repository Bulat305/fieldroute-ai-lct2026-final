from app.services.generator import generate_demo
from app.services.matrix import build_matrix
from app.solver.optimizer import solve_optimized

def test_optimizer_runs_with_short_limit():
    engineers, jobs = generate_demo(seed=42, engineers_n=4, jobs_n=8)
    coords = [(e.lat, e.lon) for e in engineers] + [(j.lat, j.lon) for j in jobs]
    matrix = build_matrix(coords, use_osrm=False)
    solution = solve_optimized(
        engineers,
        jobs,
        matrix,
        time_limit_seconds=1,
        strategy="balanced",
    )
    assert solution.metrics.total_jobs == 8
    assert solution.matrix_source == "haversine-fallback"
