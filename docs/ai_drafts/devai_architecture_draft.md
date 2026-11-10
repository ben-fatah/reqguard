<!-- RAW DevAI output, unedited. Prompt 2. Captured 2026-10-21. -->
I'll route this architecture-design task to the Planner specialist, since it's a design deliverable on its own (not code to implement). I'll give it the full ReqGuard context and the specific outputs you asked for.


Worked
·
1 step
The Planner agent isn't available in this workspace, so rather than guess among the specialist options (and risk an uncertain hop), I'll produce the architecture directly. Here it is.

ReqGuard — Architecture Proposal (Python)
1. Technology Stack & Rationale
Layer	Choice	Why
API / Backend	FastAPI (Python 3.11+), Pydantic v2, SQLAlchemy 2.0, Alembic	Async-native for the long-running AI pipeline; Pydantic gives us typed contracts for the agent hand-off; auto OpenAPI for the frontend.
Web App	React/Vite SPA	Rich, keyboard-operable review UI (WCAG 2.2 AA), best fit for list + per-item decision workflows.
Database	PostgreSQL (+ JSONB)	ACID for decisions/audit; row-level locking for per-item review; JSONB for flexible AI metadata.
Queue / Cache	Redis + Celery	Celery runs the AI pipeline off the request path; Redis is the broker and the pub/sub channel for streaming progress (NFR-01).
Object Storage	S3-compatible (MinIO locally, AWS S3 in prod)	Raw SRS files; uploads may be large and are byte-addressed by hash for dedup.
AI Layer	LiteLLM (provider abstraction) + structured JSON output	Swappable models (GPT/Claude/self-hosted); prompt templates kept separate; failures/retries are centralized.
Auth	JWT + FastAPI role dependency	Implements NFR-03 RBAC (engineer vs reviewer) at the API boundary.
Retrieval (optional, v2)	pgvector on Postgres	Requirement similarity / duplicate-requirement detection; not required for v1.
2. Component Breakdown
Each named component below is a deployable unit with one responsibility.

API Layer
Web App — the browser SPA; upload screen for the Engineer, review/decision screen for the Reviewer.
API Gateway (FastAPI) — all endpoints: upload, list requirements, review decisions, export. Enforces auth + RBAC. Streams pipeline progress via SSE/WebSocket on a Redis channel.
Auth / RBAC service — issues JWT, maps engineer/reviewer roles to endpoint permissions.
Ingestion
Ingestion Service — accepts the .txt/.md upload, computes a SHA-256 for dedup, stores the blob in object storage, records a submission, and enqueues the extraction job.
AI Pipeline (Celery worker pool)
AI Orchestrator — a state machine that sequences the agent stages, fans-out per-requirement work, handles retries/backoff, collects per-item failures, and merges results back into the database. This is the "hand-off coordinator."
Requirement Extractor Agent — parses the document, segments it into discrete requirements, and assigns stable IDs.
Ambiguity / Untestable Flagging Agent — classifies each requirement as ambiguous and/or untestable and emits a human-readable reason.
Rewrite Agent — for flagged items, generates a concrete replacement preserving intent.
Acceptance-Test Agent — generates Given/When/Then tests split into explicit Given/When/Then clauses.
Review & Output
Review / Decision Service — accepts, edits, or rejects each finding; updates item status and enforces the decision queue.
Audit Service — writes the immutable append-only trail.
Exporter — produces Markdown and JSON output (NFR-06) and supports re-import for re-editing.
3. How the AI Agents Hand Off Work
Shared intermediate representation. Every stage reads and writes the same typed contract — a Pydantic model that is persisted:

Python
class RequirementItem(BaseModel):
    id: UUID
    submission_id: UUID
    ordinal: int
    original_text: str
    flags: list[Finding]          # ambiguous / untestable, each with a reason
    rewrite_text: str | None
    tests: list[AcceptanceTest]   # each is Given / When / Then clauses
    status: Literal["pending", "ready", "error"]
Pipeline stages (1 → 2 → 3 → 4):

Extract — Orchestrator runs the Extractor once per document.
Flag — the Orchestrator fans out to the Flagging Agent in parallel, one task per requirement. Each returns flags/reasons.
Rewrite — Orchestrator routes only flagged requirements to the Rewrite Agent (skips clean items — no wasted LLM calls).
Test generation — one task per requirement, run in parallel; it consumes the (possibly rewritten) requirement text so tests target the operative version.
Parallelism & partial-failure isolation. Flagging and test generation are embarrassingly parallel per requirement, so a 500-item doc becomes 500 independent small tasks (NFR-01). Each task's result is merged atomically per item. If one requirement's agent call fails, that item is marked error with a captured reason, and everything else completes — the document is not blocked.

Data contract hand-off. Each stage takes the current RequirementItem, enriches it, and the Orchestrator persists the merged result. Stages communicate only through these persisted items + a Redis progress channel, never by passing raw prompts between agents directly.

Human review feeds back. When a Reviewer edits a requirement or rewrite, the Orchestrator can re-run only that item's Flag → Rewrite (optional) → Test-generation stages, so downstream artifacts stay consistent with the operative text.

Fallback & retry. The AI layer is wrapped with exponential backoff + retry, a provider failover (primary → fallback model), and a "degraded but honest" policy: if an agent can't produce structured output, the item is left in pending with a flag rather than emitting a fabricated result.

4. Data Storage Model
Where things live
Data	Store	Notes
Uploaded SRS files	Object store (S3)	keyed by sha256(file); raw + parsed copies.
Extraction + status + decisions	PostgreSQL	the source of truth for all review state.
AI findings / rewrites / tests	PostgreSQL (JSONB columns)	linked to their requirement item.
Immutable audit trail	PostgreSQL (append-only tables)	no UPDATE/DELETE; enforced by DB permissions + triggers.
Pipeline progress / pub-sub	Redis	transient only; streaming to the UI.
Optional vector index	pgvector (v2)	similarity / dedup.
Recommended schema outline
SQL
users(id, email, role, created_at)                 -- role: engineer | reviewer

submissions(id, uploader_user_id, filename, object_key, file_sha256,
            pipeline_status, created_at, updated_at)

requirements(id, submission_id, ordinal, req_id, original_text,
             flags_meta JSONB, status, updated_at)

flag_findings(id, requirement_id, flag_type, reason,        -- flag_type: ambiguous | untestable
              review_status, final_decision, decided_by, decided_at)

rewrites(id, requirement_id, suggested_text, review_status, decided_by, decided_at)

acceptance_tests(id, requirement_id, given, when, then, source,  -- source: ai | manual
                 review_status, decided_by, decided_at)

review_decisions(id, target_type, target_id, action, actor_id,   -- action: accept|edit|reject
                 change_payload JSONB, created_at)               -- append-only

audit_log(id, actor_id, action, entity_type, entity_id,
          before JSONB, after JSONB, created_at)                 -- append-only
Immutability enforcement: audit_log and review_decisions are insert-only. The DB role used by the app has no UPDATE/DELETE grant on them; a BEFORE UPDATE OR DELETE trigger aborts any attempt. Every decision stores the full before/after payload so history is reconstructable (NFR-05, retained ≥1 year).

5. C4 Container Diagram (Mermaid)
Mermaid
flowchart LR
    subgraph User[User]
        E[Engineer]
        R[Reviewer]
    end

    subgraph Frontend[Container: Web App]
        UI[React SPA<br/>Upload + Review UI]
    end

    subgraph Backend[Container: API Backend - FastAPI]
        API[API Gateway<br/>Auth + RBAC + Endpoints]
        ING[Ingestion Service<br/>parse, hash, store]
        REV[Review/Decision Service]
        AUD[Audit Service]
        EXP[Exporter]
    end

    subgraph Pipeline[Container: AI Pipeline - Celery Workers]
        ORCH[AI Orchestrator<br/>state machine + fan-out]
        EXT[Extractor Agent]
        FLAG[Flagging Agent<br/>ambiguity / untestable]
        RW[Rewrite Agent]
        GWT[Acceptance-Test Agent]
    end

    subgraph Data[Container: Data Stores]
        PG[(PostgreSQL<br/>reqs, decisions, audit)]
        OBJ[(Object Store (S3)
            raw SRS files)]
        RED[(Redis<br/>queue + progress pub/sub)]
    end

    LLM[External LLM Provider<br/>(LiteLLM abstraction)]

    E -- "upload .txt/.md" --> UI
    R -- "accept / edit / reject" --> UI

    UI -- "HTTPS (REST + SSE)" --> API
    API -- "authorize & store blob" --> ING
    ING -- "write blob + submission" --> OBJ
    ING -- "enqueue extraction job" --> RED
    RED -- "dispatch tasks" --> ORCH

    ORCH -- "stage 1" --> EXT
    ORCH -- "stage 2 (fan-out/req)" --> FLAG
    ORCH -- "stage 3 (flagged only)" --> RW
    ORCH -- "stage 4 (fan-out/req)" --> GWT

    FLAG -- "LLM call" --> LLM
    RW -- "LLM call" --> LLM
    GWT -- "LLM call" --> LLM

    ORCH -- "persist enriched items" --> PG
    FLAG -- "write findings" --> PG
    GWT -- "write tests" --> PG
    RED -- "progress channel -> API (SSE)" --> API

    API -- "decision" --> REV
    REV -- "append-only decision" --> AUD
    AUD -- "append audit_log" --> PG
    API -- "export" --> EXP
    EXP -- "read reqs + tests" --> PG
6. Key Design Decisions (summary)
Pipeline is decoupled from the request path. Upload only enqueues; the worker pool does the heavy AI work and streams status back — this keeps the API responsive and lets us scale workers independently (NFR-01, NFR-04).
One persisted RequirementItem contract across all agents — makes hand-offs unambiguous, enables selective re-runs after a review edit, and gives a clean partial-failure story.
Per-requirement fan-out, not per-document — the 500-item / 60s target is met by parallelizing the independent flagging and test-generation stages.
Immutable audit via DB permissions + triggers — not application logic — so even a buggy code path can't mutate history (NFR-05).
AI is a swappable provider behind LiteLLM with retries and failover — the architecture doesn't lock in one vendor, and structured JSON output keeps agent results machine-parseable.
This is a design artifact, ready to hand to Developer if you want it implemented. Two things worth confirming before that: (a) whether you want a React SPA or a server-rendered/replaceable frontend, and (b) whether pgvector similarity/dedup is in scope for v1 or deferred. Want me to route this to Developer to scaffold the FastAPI + Celery backend, and optionally run a proof-of-concept of the agent pipeline?




