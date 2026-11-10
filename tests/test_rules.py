"""Rule packs: one positive and one negative case per rule (FR-04)."""
import pytest

from reqguard.models import Requirement
from reqguard.rules import consistency, functional, non_functional, security


def req(text, rid="REQ-01"):
    return Requirement(rid, text, 1)


def rule_ids(findings):
    return sorted(f.rule_id for f in findings)


@pytest.mark.parametrize("text,expected", [
    ("Reports should load quickly.", ["R1", "R2", "R5"]),
    ("Reports shall load within 3 seconds for 95% of requests.", []),
    ("The system shall be highly available.", ["R1", "R5"]),
    ("The system shall be available 99.5% of each month.", []),
    ("The system shall support many concurrent users.", ["R1", "R5"]),
    ("The login page shall be user-friendly.", ["R1"]),
])
def test_non_functional_rules(text, expected):
    assert rule_ids(non_functional.check([req(text)]) + functional.check([req(text)])) == expected


def test_r1_ignored_when_a_number_is_present():
    # 'fast' with a measurable target is acceptable (NFR-02 precision)
    assert non_functional.r1_vague_term(req("Search shall be fast: under 2 seconds.")) == []


def test_r1_reports_matched_word_and_span():
    [f] = non_functional.r1_vague_term(req("Search shall be fast."))
    assert '"fast"' in f.problem
    assert "Search shall be fast."[f.span[0]:f.span[1]] == "fast"
    assert f.severity == "medium" and f.source == "rule" and f.agent == "non_functional"


@pytest.mark.parametrize("text,rule,hit", [
    ("Users should be able to reset their password.", "R2", True),
    ("Users shall be able to reset their password.", "R2", False),
    ("The system shall support the roles admin, clerk, etc.", "R3", True),
    ("The system shall handle bulk imports, TBD.", "R3", True),
    ("Charts and/or tables shall be shown.", "R3", True),
    ("The system shall support the roles admin and clerk.", "R3", False),
    ("The system shall update the stock and shall notify the manager.", "R4", True),
    ("The system shall update the stock level.", "R4", False),
    ("All user input shall be validated.", "R6", True),
    ("Reversed movements shall be kept.", "R6", True),
    ("All user input shall be validated by the API gateway.", "R6", False),
    ("The system shall add a product.", "F1", True),
    ("The system shall add a product and reject a duplicate SKU.", "F1", False),
    ("The system shall display the product list.", "F1", False),
])
def test_functional_rules(text, rule, hit):
    assert (rule in rule_ids(functional.check([req(text)]))) is hit


@pytest.mark.parametrize("text,rule,hit", [
    ("Passwords shall be stored.", "S1", True),
    ("Passwords shall be stored hashed with bcrypt and a unique salt.", "S1", False),
    ("The system shall send a password-reset link.", "S1", False),   # mentions passwords, stores nothing
    ("A session shall expire after inactivity.", "S2", True),
    ("A session shall expire after 15 minutes of inactivity.", "S2", False),
    ("The system shall store each student's phone number.", "S3", True),
    ("The system shall store each student's phone number, visible only to authorised staff.", "S3", False),
])
def test_security_rules(text, rule, hit):
    assert (rule in rule_ids(security.check([req(text)]))) is hit


def test_s4_document_without_authentication():
    reqs = [req(f"The system shall show users report {i}.", f"REQ-0{i}") for i in range(1, 6)]
    [f] = security.s4_no_authentication(reqs)
    assert f.req_id is None and f.rule_id == "S4" and f.severity == "high"


def test_s4_not_raised_when_login_exists():
    reqs = [req(f"The system shall show users report {i}.", f"REQ-0{i}") for i in range(1, 5)]
    reqs.append(req("Users shall log in with an email address.", "REQ-05"))
    assert security.s4_no_authentication(reqs) == []


def test_s4_needs_at_least_five_requirements():
    reqs = [req(f"The system shall show users report {i}.", f"REQ-0{i}") for i in range(1, 5)]
    assert security.s4_no_authentication(reqs) == []


def test_c1_conflicting_session_durations():
    reqs = [req("The system shall log out a user after 20 minutes of inactivity.", "REQ-01"),
            req("A user session shall last 1 hour.", "REQ-02"),
            req("The system shall show a clock.", "REQ-03")]
    found = consistency.c1_conflicting_durations(reqs)
    assert {f.req_id for f in found} == {"REQ-01", "REQ-02"}
    assert found[0].related == ["REQ-02"] and found[1].related == ["REQ-01"]


def test_c1_same_duration_in_other_units_is_not_a_conflict():
    reqs = [req("A session shall end after 60 minutes of inactivity.", "REQ-01"),
            req("A user session shall last 1 hour.", "REQ-02")]
    assert consistency.c1_conflicting_durations(reqs) == []


def test_c2_near_duplicates():
    reqs = [req("The system shall export reports as CSV files.", "REQ-01"),
            req("The system shall export the reports as CSV files.", "REQ-02"),
            req("The system shall import products from CSV files.", "REQ-03")]
    [f] = consistency.c2_near_duplicates(reqs)
    assert f.req_id == "REQ-02" and f.related == ["REQ-01"]


def test_rules_are_deterministic():
    text = "Reports should load quickly and shall be highly available, etc."
    runs = [rule_ids(functional.check([req(text)]) + non_functional.check([req(text)])) for _ in range(5)]
    assert all(r == runs[0] for r in runs)
