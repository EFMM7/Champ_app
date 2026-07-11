import numpy as np

from src.zoning import DEFAULT_THRESHOLDS, get_thresholds, annotate_zones


def test_get_thresholds_applies_overrides():
    thresholds = get_thresholds({"critical": 0.2, "warning": 0.4})
    assert thresholds["critical"] == 0.2
    assert thresholds["warning"] == 0.4


def test_annotate_zones_uses_override_thresholds():
    zones = [{"id": "A1", "mean_value": 0.15}]
    annotated = annotate_zones(zones, {"critical": 0.2, "warning": 0.4})
    assert annotated[0]["status"] == "critical"
