from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class Engineer(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    shift_start: int
    shift_end: int
    skills: List[str]
    vehicle_type: str
    region: str

class Job(BaseModel):
    id: str
    source_index: int
    region: str
    address: str
    district: str
    lat: float
    lon: float
    bk_type: str
    hd_type: str
    priority: int = Field(ge=1, le=2)  # 1 = обычная, 2 = срочная
    service_minutes: int
    normative_name: Optional[str] = None
    normative_road_minutes: int = 0
    technical_minutes: int = 0
    documents_minutes: int = 0
    base_normative_minutes: int = 0
    window_start: int
    window_end: int
    sla_deadline: int
    required_skill: str
    required_vehicle_type: Optional[str] = None

class Stop(BaseModel):
    job_id: str
    arrival: int
    start: int
    finish: int
    distance_km: float
    sla_lateness_minutes: int

class Route(BaseModel):
    engineer_id: str
    stops: List[Stop]
    total_distance_km: float

class Metrics(BaseModel):
    total_jobs: int
    assigned_jobs: int
    unassigned_jobs: int
    active_engineers: int
    total_distance_km: float
    distance_by_engineer: Dict[str, float]
    sla_compliance: float
    sla_violations: int

class Solution(BaseModel):
    routes: List[Route]
    unassigned: List[str]
    metrics: Metrics
    matrix_source: str = "unknown"
    coordinate_source: str = "unknown"
