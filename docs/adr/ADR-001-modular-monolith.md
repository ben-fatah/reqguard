# ADR-001: Modular monolith instead of distributed queue workers

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Abderrahmane Benfatah, Omar Ramadhan
- **Related requirements:** NFR-01, NFR-04, NFR-07, NFR-08, FR-10
- **Trade-off matrix rows:** TM-1, TM-5, TM-6, TM-7

## Context and problem

ReqGuard runs a three-agent pipeline that takes up to two minutes per document, then waits for human review. We must choose the runtime structure. The forces are: one deployment target and at most two students to operate it (brief scope ceilings); agents and rules that must be unit- and mutation-testable (M2); the coupling rule that Analysis never writes storage (NFR-08); and long-running runs whose progress must be visible (FR-10).

## Considered options

- **Option A — Modular monolith:** one FastAPI process, in-process orchestrator in a background task, SQLite, one Docker container.
- **Option B — Distributed workers:** Streamlit UI, FastAPI API, Redis queue, RQ workers, PostgreSQL — five containers.

## Decision

Chose **Option A** because it scores 49/54 against 36/54 in the trade-off matrix, passes the coupling check with 0 violations where B fails with 7 (`07_coupling_report.md`), and needs one container instead of five.

## Consequences

- **Positive:** a single authorisation boundary (TM-5); the orchestrator is the only writer of run data, so the task record stays consistent; tests run without Redis or PostgreSQL.
- **Accepted downside:** runs execute in one process. A process crash loses the in-flight stage, so the run must be restarted from that stage (it is marked *Failed – retryable*). There is no horizontal scaling: concurrent runs share one process and one SQLite writer, which is fine for the 2–10 concurrent users we target but not for hundreds. Tracked as risk RK-06.
- **Rejected:** Option B, because its fan-out multiplies tokens 4.8× and breaks NFR-06, its workers write tables directly (7 coupling violations), and it adds an unauthenticated-by-default Redis and four more containers to secure and operate. Its real advantages — parallel latency and job-level fault isolation (TM-1, TM-6) — matter only at a volume we do not have.

## Y-statement

In the context of a two-person course project running a long agent pipeline, facing a one-deployment-target limit and the need for mutation-testable agents, we decided on a modular monolith with an in-process orchestrator to achieve low coupling, a single security boundary and low operational burden, accepting that a crash loses the in-flight stage and that there is no horizontal scaling.
