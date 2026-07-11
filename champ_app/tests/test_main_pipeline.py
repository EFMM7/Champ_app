from src.main import run_pipeline
from src.demo_data import generate_synthetic_bands


def test_run_pipeline_accepts_explicit_thresholds():
    bands = generate_synthetic_bands(seed=7)
    result, _ = run_pipeline(bands, n_rows=4, n_cols=4, thresholds={"critical": 0.2, "warning": 0.4})

    assert result["thresholds_used"]["critical"] == 0.2
    assert result["thresholds_used"]["warning"] == 0.4
    assert "zones" in result
