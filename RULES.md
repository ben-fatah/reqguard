# RULES.md — ReqGuard team rules

These rules apply to every member and every AI-assisted change. Anything that must never happen is also checked by a test or by lint.

## Stack
- Python 3.12, FastAPI, SQLite (`sqlite3`), pytest, ruff.
- The AI agents run as DevAI agents inside DevAI flows (`REQGUARD_LLM=devai`); the offline mock is used for tests.
- No new runtime dependency without both members agreeing and checking the package name on PyPI. Dev tools (ruff, vulture) stay out of `requirements.txt`.

## Architecture boundaries
- `reqguard/rules/` and `reqguard/grounding.py` are pure functions: no database, no network, no file writes.
- Agents (`reqguard/agents/`) never write the database and never choose the next step. The orchestrator (`reqguard/pipeline.py`) runs a fixed order.
- Only `reqguard/store.py` writes the database. Decisions are append-only: never add code that updates or deletes a decision.
- Agents reach a language model only through `reqguard/llm/` (`get_client()`).
- Rule findings are the source of truth; AI findings are advisory and never change the score or the grade (ADR-002, ADR-005).

## Every change
- Keep `python -m pytest -q` and `ruff check .` green. Run them yourself; do not rely on an assistant saying they pass.
- If you change any file in `reqguard/prompts/`, run `python -m reqguard.devai setup`, then `python -m reqguard.devai check`.
- Do not weaken a validator or a test to make a run pass. Fix the prompt or the code instead.

## Security
- Never commit `.env` or any key. `.env.example` holds fake values only.
- Never put real or personal data into ReqGuard, DevAI or any AI tool. Use the synthetic benchmark.
- SRS text is data: prompts wrap it in delimiters and tell the model to ignore instructions inside it. Never change the text sent to a model, because the grounding check compares it word for word.

## Provenance
- AI involvement is recorded in `AI_USE_DISCLOSURE.md`; commits do not carry AI co-author trailers.
- Use small commits with clear messages.
- Record every AI error found and every rejected AI suggestion in `AI_USE_DISCLOSURE.md` as it happens.
