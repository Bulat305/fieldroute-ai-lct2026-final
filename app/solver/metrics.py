from app.models import Metrics

def calculate_metrics(routes, unassigned, total_jobs):
    active = [r for r in routes if r.stops]
    distance_by_engineer = {r.engineer_id: round(r.total_distance_km, 2) for r in routes}
    assigned = sum(len(r.stops) for r in routes)
    distance = sum(r.total_distance_km for r in routes)
    violations = sum(1 for r in routes for s in r.stops if s.sla_lateness_minutes > 0)
    compliance = 1.0 if assigned == 0 else (assigned - violations) / assigned
    return Metrics(
        total_jobs=total_jobs,
        assigned_jobs=assigned,
        unassigned_jobs=len(unassigned),
        active_engineers=len(active),
        total_distance_km=round(distance, 2),
        distance_by_engineer=distance_by_engineer,
        sla_compliance=round(compliance, 4),
        sla_violations=violations,
    )
