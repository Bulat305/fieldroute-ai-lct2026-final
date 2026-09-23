from app.services.beeline_data import load_region

EXPECTED = {
    "Подключение": (20, 60, 10, 90, 70),
    "Глобальная проблема": (20, 80, 0, 100, 80),
    "Дозаказ": (20, 10, 10, 40, 20),
    "Локальная заявка": (20, 30, 0, 50, 30),
}

def test_organizer_normatives_are_applied():
    _, jobs, _ = load_region("east")
    for bk_type, expected in EXPECTED.items():
        sample = next(j for j in jobs if j.bk_type == bk_type)
        road, tech, docs, base, service = expected
        assert sample.normative_road_minutes == road
        assert sample.technical_minutes == tech
        assert sample.documents_minutes == docs
        assert sample.base_normative_minutes == base
        assert sample.service_minutes == service
        assert base == road + tech + docs
