import httpx
from app.services.distance import haversine_km, fallback_travel_minutes

OSRM_BASE = "https://router.project-osrm.org"

class TravelMatrix:
    def __init__(self, durations, distances, source):
        self.durations = durations
        self.distances = distances
        self.source = source

    def time(self, i, j):
        return int(round(self.durations[i][j]))

    def distance(self, i, j):
        return float(self.distances[i][j])

def _fallback(coords):
    n = len(coords)
    durations = [[0.0] * n for _ in range(n)]
    distances = [[0.0] * n for _ in range(n)]
    for i, (lat1, lon1) in enumerate(coords):
        for j, (lat2, lon2) in enumerate(coords):
            if i == j:
                continue
            distances[i][j] = haversine_km(lat1, lon1, lat2, lon2)
            durations[i][j] = fallback_travel_minutes(lat1, lon1, lat2, lon2)
    return TravelMatrix(durations, distances, "haversine-fallback")

def build_matrix(coords, use_osrm=True):
    if not use_osrm:
        return _fallback(coords)

    coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in coords)
    url = f"{OSRM_BASE}/table/v1/driving/{coord_str}"
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(url, params={"annotations": "duration,distance"})
            r.raise_for_status()
            data = r.json()
        if data.get("code") != "Ok":
            return _fallback(coords)
        durations = data.get("durations")
        distances = data.get("distances")
        if not durations or not distances:
            return _fallback(coords)
        durations = [[0 if x is None else x / 60.0 for x in row] for row in durations]
        distances = [[0 if x is None else x / 1000.0 for x in row] for row in distances]
        return TravelMatrix(durations, distances, "osrm-road-network")
    except Exception:
        return _fallback(coords)

def _route_request(client, coords):
    coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in coords)
    url = f"{OSRM_BASE}/route/v1/driving/{coord_str}"
    r = client.get(url, params={"overview": "full", "geometries": "geojson", "steps": "false"})
    r.raise_for_status()
    data = r.json()
    if data.get("code") == "Ok" and data.get("routes"):
        return data["routes"][0]["geometry"]["coordinates"]
    return None


def route_geometry(coords, with_source=False):
    if len(coords) < 2:
        geometry = [[coords[0][1], coords[0][0]]] if coords else []
        return {"coordinates": geometry, "source": "single-point"} if with_source else geometry

    # Fast path: normally one OSRM request per engineer route.
    try:
        with httpx.Client(timeout=8.0) as client:
            geometry = _route_request(client, coords)
            if geometry:
                result = {"coordinates": geometry, "source": "osrm-road-geometry"}
                return result if with_source else geometry
    except Exception:
        pass

    # If a long request is rejected, retry in chunks instead of one request per leg.
    full = []
    road_chunks = 0
    fallback_chunks = 0
    chunk_size = 12
    try:
        client = httpx.Client(timeout=8.0)
        for start in range(0, len(coords) - 1, chunk_size - 1):
            chunk = coords[start:start + chunk_size]
            if len(chunk) < 2:
                break
            part = None
            try:
                part = _route_request(client, chunk)
            except Exception:
                part = None
            if part:
                road_chunks += 1
            else:
                fallback_chunks += 1
                part = [[lon, lat] for lat, lon in chunk]
            full.extend(part[1:] if full else part)
        client.close()
    except Exception:
        full = [[lon, lat] for lat, lon in coords]
        fallback_chunks = 1

    if fallback_chunks == 0:
        source = "osrm-road-geometry"
    elif road_chunks == 0:
        source = "straight-line-fallback"
    else:
        source = f"mixed: {road_chunks} road / {fallback_chunks} fallback"
    result = {"coordinates": full, "source": source}
    return result if with_source else full
