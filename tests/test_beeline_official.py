from app.services.beeline_data import load_region, region_catalog
from app.solver.common import engineer_can_do_job

def test_official_region_counts():
    expected = {"east": 66, "southeast": 83, "southcenter": 56}
    for region, count in expected.items():
        engineers, jobs, assumptions = load_region(region)
        assert len(jobs) == count
        assert 10 <= len(engineers) <= 15

def test_required_skills_are_official():
    engineers, jobs, _ = load_region("east")
    allowed = {
        "Локальные работы",
        "Работы на подключение и дозаказы",
        "Аварийные работы",
    }
    assert {j.required_skill for j in jobs}.issubset(allowed)

def test_transport_constraint():
    engineers, jobs, _ = load_region("east")
    job = next(j for j in jobs if j.required_vehicle_type)
    wrong = next(e for e in engineers if e.vehicle_type != job.required_vehicle_type)
    assert engineer_can_do_job(wrong, job) is False
