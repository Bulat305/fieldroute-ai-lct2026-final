import random
from app.models import Engineer, Job

CENTER_LAT = 55.751244
CENTER_LON = 37.618423
SKILLS = ["GPON", "ETHERNET", "RADIO"]

def _point(rng, spread=0.11):
    return (
        CENTER_LAT + rng.uniform(-spread, spread),
        CENTER_LON + rng.uniform(-spread, spread),
    )

def generate_demo(seed=42, engineers_n=10, jobs_n=30):
    rng = random.Random(seed)
    engineers = []

    for i in range(engineers_n):
        lat, lon = _point(rng)
        primary = SKILLS[i % len(SKILLS)]
        skills = {primary: rng.randint(2, 3)}
        if rng.random() < 0.5:
            second = rng.choice([s for s in SKILLS if s != primary])
            skills[second] = rng.randint(1, 2)

        equipment = []
        if "GPON" in skills or rng.random() < 0.25:
            equipment.append("OTDR")
        if "ETHERNET" in skills or rng.random() < 0.25:
            equipment.append("LAPTOP")

        start = 8 * 60 + (60 if i in (2, 8) else 0)
        end = start + (9 * 60 if i in (1, 4, 9) else 10 * 60)

        engineers.append(Engineer(
            id=f"E{i+1:02d}",
            name=f"Инженер {i+1:02d}",
            lat=lat,
            lon=lon,
            shift_start=start,
            shift_end=end,
            skills=skills,
            equipment=equipment,
        ))

    priorities = [1] * 3 + [2] * 7 + [3] * 15 + [4] * 5
    rng.shuffle(priorities)
    jobs = []

    for i in range(jobs_n):
        lat, lon = _point(rng)
        skill = rng.choice(SKILLS)
        level = 3 if i in (4, 16) else rng.randint(1, 2)
        ws = 8 * 60 + rng.randint(0, 7) * 60
        we = min(19 * 60, ws + rng.choice([120, 180, 240]))
        service = rng.choice([30, 45, 60, 90])
        priority = priorities[i % len(priorities)]
        sla = min(we, ws + (60 if priority == 1 else 120 if priority == 2 else 240))
        equipment = ["OTDR"] if skill == "GPON" else ["LAPTOP"] if skill == "ETHERNET" else []

        jobs.append(Job(
            id=f"J{i+1:03d}",
            lat=lat,
            lon=lon,
            priority=priority,
            service_minutes=service,
            window_start=ws,
            window_end=we,
            sla_deadline=sla,
            required_skills={skill: level},
            required_equipment=equipment,
        ))
    return engineers, jobs
