from math import radians, sin, cos, asin, sqrt

AVERAGE_SPEED_KMH = 30.0

VEHICLE_TIME_FACTORS = {
    "Автомобиль": 1.0,
    "Пешеход": 4.5,
    "Велосипед": 2.2,
    "Общественный транспорт": 1.45,
}

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))

def fallback_travel_minutes(lat1, lon1, lat2, lon2):
    km = haversine_km(lat1, lon1, lat2, lon2)
    return max(1, round((km / AVERAGE_SPEED_KMH) * 60))

def vehicle_minutes(base_minutes, vehicle_type):
    return max(1, round(base_minutes * VEHICLE_TIME_FACTORS.get(vehicle_type, 1.0)))
