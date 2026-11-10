"""Rule packs, one per specialist agent. Deterministic: same input, same findings."""
from . import consistency, functional, non_functional, security

PACKS = {
    "functional": functional.check,
    "non_functional": non_functional.check,
    "security": security.check,
    "consistency": consistency.check,
}
