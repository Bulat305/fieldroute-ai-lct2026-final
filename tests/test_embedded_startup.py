from pathlib import Path

from app.services.beeline_data import load_region

EXPECTED = {
    "east": 66,
    "southeast": 83,
    "southcenter": 56,
}

def test_embedded_files_exist_with_ascii_safe_names():
    base = Path(__file__).resolve().parents[1] / "app" / "data" / "beeline"
    for name in (
        "east_synthetic.csv",
        "east_control.csv",
        "southeast_synthetic.csv",
        "southeast_control.csv",
        "southcenter_synthetic.csv",
        "southcenter_control.csv",
    ):
        assert (base / name).exists(), name

def test_all_embedded_regions_load_without_import():
    for region, expected_jobs in EXPECTED.items():
        engineers, jobs, assumptions = load_region(region)
        assert len(jobs) == expected_jobs
        assert len(engineers) > 0
        assert assumptions["source"]
