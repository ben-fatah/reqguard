# ReqGuard

A multi-agent requirements review crew. Give it an SRS (or just a project idea) and eight agents review it: Python rules check first, AI specialists add advice and rewrites, and a human reviewer accepts, edits or rejects every finding before acceptance tests are written and a report is exported.

**Team:** Abderrahmane Benfatah (444106928), Omar Ramadhan (444106902) · SWE 485, King Saud University · Python 3.12+

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn reqguard.api:app --reload
```

Open http://127.0.0.1:8000. It runs with the **offline mock model** by default, so no key is needed.

1. As **Engineer**, paste the example SRS (or upload a `.txt`/`.md`, or type an idea) and press **Run review**.
2. Switch to **Reviewer** (top right). Accept, edit or reject each finding. A rejection needs a reason of 10–500 characters.
3. Press **Generate tests**, approve or reject each Given–When–Then test.
4. Press **Export report** (blocked until every finding is decided).

Command line, without the web app:

```bash
python -m reqguard review benchmark/srs_inventory_v1.md
python -m reqguard idea "A mobile app for students to book study rooms"
python -m reqguard.bench          # rule precision / recall on the labelled benchmark
python -m pytest -q               # 112 tests
```

## Run with DevAI

With DevAI, all eight agents run as **DevAI agents inside DevAI flows** on your machine. The Python orchestrator still runs the fixed order, the rules, the grounding check, the store, the API and the UI. Only the language-model calls go to DevAI.

1. Open **DevAI Desktop**. It serves the flow API on port 7583 and the host on port 7588.
2. Copy `.env.example` to `.env` (never commit `.env`). It already contains `REQGUARD_LLM=devai`. `.env` is read automatically by the CLI and the web app.
3. Deploy the agents and flows once, and again after every change to `reqguard/prompts/*.md`:

```bash
python -m reqguard.devai setup    # create/update the 8 agents and 8 flows, then verify them
python -m reqguard.devai check    # does each agent/flow exist, and does it match prompts/*.md?
python -m reqguard.devai ping     # run the extractor flow on one line: reply + duration
python -m reqguard review benchmark/srs_inventory_v1.md
uvicorn reqguard.api:app --reload # the web app now uses DevAI too
```

`REQGUARD_LOG=INFO python -m reqguard review ...` logs when each agent call starts and ends.

**What `setup` creates.** It only touches ids that start with `reqguard-`, so your other DevAI agents and flows are left alone.

| DevAI object | Content |
|---|---|
| Agent `reqguard-<name>` (×8) | Instructions = `prompts/<name>.md` + `prompts/_shared.md` + "Do not use any tools. Answer only from the message." Tools: `read_file`, `list_directory`, `todo_read`. That is the smallest set DevAI allows, because an empty tool list gives an agent DevAI's full default set. Temperature 0. |
| Flow `reqguard-<name>` (×8) | Webhook trigger → agent node (prompt `{{trigger.payload.message}}`) → text output. Working directory: the empty folder `~/.devai/playground/reqguard-sandbox`, so the read/list tools see nothing. |

**One agent call:** `POST /webhook/reqguard-<name>` with `{"message": "<the agent's input>"}`, then `GET /api/flows/reqguard-<name>/runs/<runId>` every second until the run ends. The reply is the agent step's `output`; it goes through the same JSON validation and retry as before.

- A failed run is retried once.
- A timeout (`REQGUARD_DEVAI_TIMEOUT`, default 180 s) cancels the run.
- If DevAI is closed, the error is "DevAI is not running: open DevAI Desktop".

The four specialists run in parallel in DevAI. A 40-requirement review takes about 40–70 s.

**Which model?** The model is a global DevAI setting (Settings in DevAI Desktop). ReqGuard reads `modelId` from `GET http://127.0.0.1:7588/` once per run and stores it in the run usage. The UI, the report and the CLI show it as "Model: …".

| Variable | Default | Meaning |
|---|---|---|
| `REQGUARD_LLM` | `mock` | `devai`, `mock` or `openai` |
| `REQGUARD_DEVAI_URL` | `http://127.0.0.1:7583` | DevAI flow API (use 127.0.0.1: on Windows `localhost` adds about 2 s per new connection) |
| `REQGUARD_DEVAI_HOST_URL` | `http://127.0.0.1:7588` | DevAI host, read for the model id |
| `REQGUARD_DEVAI_TIMEOUT` | `180` | Seconds to wait for one agent run |

## Use another OpenAI-compatible model

Instead of DevAI, any OpenAI-compatible chat API works, for example DeepSeek. Set these in `.env`:

```
REQGUARD_LLM=openai
REQGUARD_LLM_BASE_URL=https://api.deepseek.com
REQGUARD_LLM_API_KEY=<your key>
REQGUARD_LLM_MODEL=deepseek-chat
```

Any provider that speaks the OpenAI `/chat/completions` format works (OpenAI, DeepSeek, Ollama). If the provider rejects JSON mode, set `REQGUARD_LLM_JSON_MODE=0`.

## How it works

```
idea ──> Idea-to-SRS ─┐
SRS ──────────────────┴─> Extractor ─> grounding check (Python) ─┬─> Functional      ┐
                                                                 ├─> Non-functional  │ parallel: rules first,
                                                                 ├─> Security        │ then AI advice
                                                                 └─> Consistency     ┘
                                                     ─> Judge (merge, rank, score) ─> Reviewer decides ─> Test-writer ─> Report
```

| Agent | Job | Deterministic guard (Python) |
|---|---|---|
| Idea-to-SRS | Drafts an SRS from a short idea | Output must be a list of requirement texts |
| Extractor | Splits the document into requirements | Grounding check: anything not found word for word in the source is dropped |
| Functional | Actor, trigger, failure path, wording | Rules R2, R3, R4, R6, F1 |
| Non-functional | Measurable quality targets | Rules R1, R5 |
| Security | Passwords, sessions, personal data, authentication | Rules S1, S2, S3, S4 (document-level) |
| Consistency | Conflicts and duplicates between requirements | Rules C1, C2 |
| Judge | Summary for the reviewer | Merge, de-duplicate, rank and score are plain Python. The score counts rule findings only (ADR-005); AI advisory findings are shown and counted separately. Grade gate: any high-severity rule finding caps the grade at "Needs work", 5 or more give "High risk" |
| Test-writer | Given–When–Then acceptance tests | Every test must have given/when/then and a real requirement ID |

Every agent is the same model with its own instructions (`reqguard/prompts/*.md`), a JSON output that is validated, and one retry. Agents never touch the database: only `store.py` writes it. If an AI call fails, the rule findings are kept and the run shows a warning.

| Rule | Detects |
|---|---|
| R1 | Vague quality word with no number (fast, user-friendly, highly…) |
| R2 | Weak modal: should, may, might, could |
| R3 | Open-ended wording: etc, TBD, and/or |
| R4 | Two shall/must clauses in one requirement |
| R5 | Performance or availability with no measurable value |
| R6 | Passive "shall be validated" with no actor |
| F1 | Action (add, create, upload…) with no failure path |
| S1 | Passwords stored with no hashing stated |
| S2 | Session or timeout with no duration |
| S3 | Personal data stored with no protection or access rule |
| S4 | Document has users but no login/authentication requirement |
| C1 | Conflicting time limits on the same topic (e.g. 20 min vs 1 hour session) |
| C2 | Near-duplicate requirements |

## Project layout

```
reqguard/
  rules/        rule packs, one per specialist (pure functions)
  grounding.py  verbatim grounding check + functional/non-functional classifier
  llm/          DevAI flow client, OpenAI-compatible client, offline mock
  agents/       the eight agents
  prompts/      each agent's instructions (also deployed to DevAI by devai.py)
  devai.py      setup / check / ping for the DevAI agents and flows
  env.py        tiny .env loader
  pipeline.py   orchestrator (fixed order, specialists in parallel)
  store.py      SQLite; decisions are append-only
  api.py        FastAPI endpoints with Engineer/Reviewer roles
  report.py     Markdown export
  bench.py      precision/recall on the labelled benchmark
  web/          single-page interface
tests/          112 pytest tests
benchmark/      synthetic SRS with planted defects + labels
docs/           M1 documents (charter, requirements, ADRs, risks, cost model)
```

## Known limitations

- Roles are chosen in the interface (X-Role header). There is no password login; this is a course demo.
- The mock model only adds template rewrites to problems the rules found. It never adds new AI findings, so the "AI advisory" count stays at 0 until a real model is configured.
- English requirements only. PDF and DOCX are not supported.
- Rules flag possible problems by word lists; the reviewer decides. Expect some false positives.
- The benchmark was written by the team, so its precision and recall are optimistic; an independent benchmark is still needed.
- One process with SQLite: fine for a class demo, not for many concurrent users.
- Text containing {{...}} may be altered by DevAI's template engine.
- DevAI cannot run an agent with no tools, so each ReqGuard agent can still read and list files. Its flow runs in an empty sandbox folder, so there is nothing to read (risk RK-12).
- Under DevAI, temperature is ignored and the model is a global DevAI setting, so AI findings vary between runs. The score does not, because it counts rule findings only (ADR-005, risk RK-13).
- The score ignores problems that only the AI found. Read the "AI advisory" count next to the score.
