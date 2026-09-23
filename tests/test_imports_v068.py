from pathlib import Path
from app.services.custom_import import parse_engineers, parse_jobs

BASE = Path(__file__).resolve().parents[1]


def test_templates_import():
    ep = BASE / 'app/static/templates/engineers_v06.csv'
    jp = BASE / 'app/static/templates/jobs_v06.csv'
    assert len(parse_engineers(ep.read_bytes(), ep.name)) >= 2
    assert len(parse_jobs(jp.read_bytes(), jp.name)) >= 2


def test_organizer_jobs_import_without_lat_lon():
    p = BASE / 'app/data/beeline/Восток Синтетические данные.csv'
    jobs = parse_jobs(p.read_bytes(), p.name)
    assert len(jobs) == 66
    assert all(j.lat and j.lon for j in jobs)


def test_control_file_can_form_engineer_roster():
    p = BASE / 'app/data/beeline/Восток Контрольное распределение..csv'
    engineers = parse_engineers(p.read_bytes(), p.name)
    assert 10 <= len(engineers) <= 15
    assert all(e.skills and e.vehicle_type for e in engineers)
