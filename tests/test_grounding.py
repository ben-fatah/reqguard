"""Grounding check (FR-03, ADR-004) and classifier."""
from reqguard.grounding import classify, filter_grounded, line_of, normalise

SOURCE = """# Title

1. The system shall export reports as CSV files.
2. Search shall be fast.
3. The system shall keep movement
   records for at least 3 years.
"""


def test_invented_requirement_is_dropped():
    kept, dropped = filter_grounded([{"text": "The system shall send SMS alerts."}], SOURCE)
    assert kept == [] and dropped == [{"text": "The system shall send SMS alerts.", "reason": "not found in source"}]


def test_paraphrased_requirement_is_dropped():
    kept, _ = filter_grounded([{"text": "Reports shall be exported as CSV."}], SOURCE)
    assert kept == []


def test_exact_requirement_kept_with_fresh_id_and_real_line():
    kept, _ = filter_grounded([{"text": "Search shall be fast.", "line": 99, "id": "REQ-77"}], SOURCE)
    assert [(r.id, r.line) for r in kept] == [("REQ-01", 4)]


def test_whitespace_and_line_breaks_are_normalised():
    kept, _ = filter_grounded([{"text": "The system shall keep movement records for at least 3 years."}], SOURCE)
    assert kept and kept[0].line == 5


def test_smart_quotes_are_normalised():
    assert normalise("the “Admin” role’s  page") == 'the "Admin" role\'s page'


def test_duplicate_extraction_dropped():
    kept, dropped = filter_grounded([{"text": "Search shall be fast."}, {"text": "Search shall be fast."}], SOURCE)
    assert len(kept) == 1 and dropped[0]["reason"] == "duplicate extraction"


def test_empty_text_not_found():
    assert line_of("   ", SOURCE) is None


def test_classifier():
    assert classify("Search shall return results within 2 seconds.") == "non_functional"
    assert classify("The system shall be highly available.") == "non_functional"
    assert classify("The system shall export reports as CSV files.") == "functional"
