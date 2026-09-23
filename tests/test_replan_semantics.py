from pathlib import Path

def test_replanner_uses_10_second_solver():
    text = (Path(__file__).resolve().parents[1] / "app" / "services" / "replanner.py").read_text(encoding="utf-8")
    assert "time_limit_seconds=10" in text
    assert "time_limit_seconds=2" not in text

def test_emergency_sla_is_based_on_start_not_finish():
    text = (Path(__file__).resolve().parents[1] / "app" / "services" / "replanner.py").read_text(encoding="utf-8")
    assert "emergency.sla_deadline - emergency_stop.start" in text
    assert "emergency.sla_deadline - emergency_stop.finish" not in text
