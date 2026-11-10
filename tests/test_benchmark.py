"""NFR-02 on the labelled synthetic benchmark (rule engine only)."""
from pathlib import Path

from reqguard.bench import evaluate

LABELS = Path(__file__).resolve().parent.parent / "benchmark" / "srs_inventory_v1.labels.json"


def test_benchmark_meets_nfr02():
    result = evaluate(LABELS)
    assert result["requirements"] == 40
    assert result["precision"] >= 0.90 and result["recall"] >= 0.80
