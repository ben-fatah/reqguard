"""Rule packs, one per specialist agent. Deterministic: same input, same findings."""
from . import consistency, functional, non_functional, security

PACKS = {
    "functional": functional.check,
    "non_functional": non_functional.check,
    "security": security.check,
    "consistency": consistency.check,
}

RULE_CATALOGUE = {
    "R1": ("non_functional", "Vague quality word without a number"),
    "R2": ("functional", "Weak modal (should, may, might, could)"),
    "R3": ("functional", "Open-ended wording (etc, TBD, and/or)"),
    "R4": ("functional", "Two shall/must clauses in one requirement"),
    "R5": ("non_functional", "Performance or availability without a measurable value"),
    "R6": ("functional", "Passive obligation with no actor"),
    "F1": ("functional", "Action with no failure path"),
    "S1": ("security", "Password storage without hashing"),
    "S2": ("security", "Session or timeout without a duration"),
    "S3": ("security", "Personal data stored without protection"),
    "S4": ("security", "Users but no authentication requirement (document)"),
    "C1": ("consistency", "Conflicting time limits on the same topic"),
    "C2": ("consistency", "Near-duplicate requirements"),
}
