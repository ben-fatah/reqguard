"""Security specialist rule pack: S1-S3 per requirement, S4 for the whole document."""
from __future__ import annotations

import re

from ..models import Finding, Requirement
from .common import find_terms, has_number, span_of

AGENT = "security"

_PROTECTION = re.compile(r"\b(hash|hashed|hashing|bcrypt|argon2|scrypt|salt|salted)\b", re.IGNORECASE)
_PERSONAL = ["national id", "id number", "phone number", "email address", "date of birth",
             "personal data", "medical record", "credit card", "bank account", "address"]
_PERSONAL_GUARD = re.compile(r"\b(encrypt|encrypted|encryption|mask|masked|access control|only|authori[sz]ed)\b",
                             re.IGNORECASE)
_STORE_VERB = re.compile(r"\b(store|stores|stored|storing|save|saves|saved|keep|kept|persist\w*|record|recorded|collect|collected)\b",
                         re.IGNORECASE)
_AUTH = re.compile(r"\b(log ?in|logs in|sign in|authenticat\w*|password)\b", re.IGNORECASE)
_USERS = re.compile(r"\b(users?|accounts?|students?|customers?|admin\w*|staff)\b", re.IGNORECASE)


def s1_password_storage(req: Requirement) -> list[Finding]:
    hits = find_terms(req.text, ["passwords", "password"])
    if not hits or not _STORE_VERB.search(req.text) or _PROTECTION.search(req.text):
        return []
    return [Finding(req.id, AGENT, "rule", "high",
                    "Passwords are stored but the requirement does not say how they are protected: require hashing with a unique salt.",
                    rule_id="S1", span=span_of(hits))]


def s2_session_without_limit(req: Requirement) -> list[Finding]:
    if has_number(req.text):
        return []
    hits = find_terms(req.text, ["session", "sessions", "timeout", "time out", "inactivity"])
    if not hits:
        return []
    return [Finding(req.id, AGENT, "rule", "medium",
                    "Session or timeout with no time limit: state the duration.",
                    rule_id="S2", span=span_of(hits))]


def s3_personal_data_unprotected(req: Requirement) -> list[Finding]:
    hits = find_terms(req.text, _PERSONAL)
    if not hits or not _STORE_VERB.search(req.text) or _PERSONAL_GUARD.search(req.text):
        return []
    return [Finding(req.id, AGENT, "rule", "medium",
                    "Personal data is stored with no protection or access rule: say who may see it and how it is protected.",
                    rule_id="S3", span=span_of(hits))]


RULES = [s1_password_storage, s2_session_without_limit, s3_personal_data_unprotected]


def s4_no_authentication(requirements: list[Requirement]) -> list[Finding]:
    """Document-level: a system with users but no login or authentication requirement."""
    if len(requirements) < 5:
        return []
    text = " ".join(r.text for r in requirements)
    if not _USERS.search(text) or _AUTH.search(text):
        return []
    return [Finding(None, AGENT, "rule", "high",
                    "The document mentions users but has no login or authentication requirement.",
                    rule_id="S4")]


def check(requirements: list[Requirement]) -> list[Finding]:
    found = [f for req in requirements for rule in RULES for f in rule(req)]
    return found + s4_no_authentication(requirements)
