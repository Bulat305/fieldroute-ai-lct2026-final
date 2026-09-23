from app.models import Engineer, Job
from app.solver.common import engineer_can_do_job
from app.services.distance import haversine_km

def test_skill_level_blocks_assignment():
    e=Engineer(id="E1",name="A",lat=55.75,lon=37.61,shift_start=480,shift_end=1080,skills={"GPON":2},equipment=["OTDR"])
    j=Job(id="J1",lat=55.76,lon=37.62,priority=1,service_minutes=30,window_start=480,window_end=600,sla_deadline=600,required_skills={"GPON":3},required_equipment=["OTDR"])
    assert engineer_can_do_job(e,j) is False

def test_equipment_blocks_assignment():
    e=Engineer(id="E1",name="A",lat=55.75,lon=37.61,shift_start=480,shift_end=1080,skills={"GPON":3},equipment=[])
    j=Job(id="J1",lat=55.76,lon=37.62,priority=1,service_minutes=30,window_start=480,window_end=600,sla_deadline=600,required_skills={"GPON":2},required_equipment=["OTDR"])
    assert engineer_can_do_job(e,j) is False

def test_distance_positive():
    assert haversine_km(55.75,37.61,55.76,37.62)>0
