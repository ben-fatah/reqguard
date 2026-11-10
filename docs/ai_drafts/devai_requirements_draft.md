<!-- RAW DevAI output, unedited. Prompt 1. Captured 2026-10-21. -->
I’ll draft the ReqGuard requirements document directly. This is a requirements-authoring deliverable, so I’ll produce a single structured specifications document covering the persona, user stories, use cases, functional requirements, and non-functional requirements.

ReqGuard — Requirements Specification
System purpose: ReqGuard lets a software engineer upload a Software Requirements Specification (SRS) text file. AI agents automatically extract each requirement (with its ID), flag requirements that are ambiguous or untestable, suggest rewrites, and generate Given-When-Then acceptance tests. A human reviewer then accepts, edits, or rejects each AI finding before the results become part of the official, exportable specification.

Actors: Engineer (uploads and submits the SRS) and Reviewer (reviews and decides each finding). Both roles may be held by the same person; the system separates concerns so an independent review is possible.

1. Persona
Priya Sharma — Senior Systems Engineer, FinSight (mid-size fintech, 400 engineers)

Background: 9 years building payment and ledger systems. Writes and reviews many SRS documents for a platform team with strict regulatory (PCI, SOC 2) and release-quality obligations.
Pain points: Requirements arrive from product managers and business analysts in inconsistent formats — some crisp, many full of vague terms like "fast," "reasonable," or "user-friendly." These gaps surface late, as defects during QA or as change requests after release. Hand-reviewing every requirement line by line is slow, so ambiguous items slip through.
Goals: Turn large SRS documents into a set of clearly identified, testable requirements with acceptance criteria attached — without manually re-reading and re-writing everything. Wants an auditable trail of what the AI flagged and what she or her team decided, so the final spec is defensible in a compliance review.
Workflow: Uploads the SRS, trusts the AI's first pass to flag and rewrite, then wants a human gate before anything is treated as final. She is time-poor and skeptical of AI output, so she needs to accept, edit, or reject each item with a clear status rather than blindly trusting a "fix everything" button.
Frustrations with an absent tool: No automated way to detect untestable statements; acceptance-criteria generation is re-invented per team; decision history is lost or lives in chat threads.
2. User Stories
ID	Role	User Story
US-01	Engineer	As an engineer, I want to upload an SRS text file so that ReqGuard can parse it and begin extraction without manual data entry.
US-02	Engineer	As an engineer, I want the system to identify each requirement and give it a stable ID so I can track it through review.
US-03	Engineer	As an engineer, I want ReqGuard to flag requirements that are ambiguous or untestable so I can address them before code is written.
US-04	Engineer	As an engineer, I want the system to suggest a rewritten version of each flagged requirement so I have a concrete, compliant alternative to compare against.
US-05	Engineer	As an engineer, I want ReqGuard to generate Given-When-Then acceptance tests for each requirement so I have a starting point for validation.
US-06	Reviewer	As a reviewer, I want to accept, edit, or reject each AI finding so that only verified content makes it into the final specification.
3. Use Cases
Use Case 1: Review a Submitted SRS
Primary actor: Reviewer • Secondary actor: Engineer • Goal: Ensure every requirement in an uploaded SRS has been reviewed and given a per-item decision.
Preconditions: An SRS file has been uploaded and ReqGuard has completed extraction, flagging, rewrite, and test generation. The requirement items are in Review state.

Main flow:

Reviewer opens the ReqGuard review workspace for the submission.
System displays the list of extracted requirements, each with: original ID, original text, AI-generated rewrite (if flagged), AI-generated Given-When-Then tests, and AI flags.
System highlights findings needing a decision (ambiguous, untestable, or both).
Reviewer selects an item and reviews it.
Reviewer accepts, edits (updating text and/or tests), or rejects the item.
System updates the item's status: Accepted, Edited, or Rejected, and records who decided and when.
Reviewer moves to the next item; steps 4–6 repeat.
When all items have a decision, System marks the submission Completed and offers an export.
Alternate flows:

A1 — Bulk decision: Reviewer selects multiple items and applies the same decision (all accept / all reject) to save time.
A2 — No findings: If no item is flagged, the list still requires an accept decision per item before the submission completes.
Postconditions: Every requirement has a final decision; the audit trail is complete; the submission is exportable.

Use Case 2: Generate and Finalize Acceptance Tests
Primary actor: Reviewer • Goal: Produce a reviewed set of Given-When-Then acceptance tests for the accepted requirements.
Preconditions: At least one requirement exists and has been extracted (UC1, steps 1–3).

Main flow:

Reviewer opens an item's Acceptance Tests panel.
System displays the auto-generated Given-When-Then test(s), each parsed into Given / When / Then clauses.
Reviewer reviews each test for correctness against the (possibly edited) requirement.
Reviewer accepts a test as-is, edits any clause, or rejects it.
System re-renders the test from the edited clauses and updates its status.
Reviewer repeats for each test and each requirement.
System compiles all accepted tests into a single test suite and links each test to its source requirement ID for traceability.
Alternate flows:

A1 — Omit tests: Reviewer rejects all generated tests for an item and records a reason; the requirement is still reviewable.
A2 — Add a manual test: Reviewer adds a hand-written Given-When-Then test that the AI did not generate.
Postconditions: A linked, reviewed test suite exists with each test traceable to a source requirement.

4. Functional Requirements
ID	Requirement
FR-01	SRS upload. The system shall accept an SRS file upload from an engineer in plain-text or Markdown format (.txt, .md) and create a new submission.
FR-02	Requirement extraction. The system shall parse the uploaded document and extract each requirement as a discrete item, assigning each a stable, unique requirement ID.
FR-03	Ambiguity flagging. The system shall flag requirements that contain ambiguous or vague language (e.g., "fast," "reasonable," "user-friendly," "as soon as possible," or statements lacking a measurable threshold) and shall record the specific reason for the flag.
FR-04	Untestable flagging. The system shall flag requirements that cannot be verified by an observable test (e.g., unverifiable claims, missing acceptance criteria, or contradictory conditions) and shall record the specific reason for the flag.
FR-05	Suggested rewrite. For each flagged requirement, the system shall generate a suggested, concrete rewrite that removes the identified ambiguity and keeps the original intent.
FR-06	Acceptance-test generation. For each requirement, the system shall generate one or more Given-When-Then acceptance tests, each decomposed into explicit Given, When, and Then clauses.
FR-07	Review — accept. The system shall allow a reviewer to accept an AI finding or requirement as-is, recording the reviewer and timestamp.
FR-08	Review — edit. The system shall allow a reviewer to edit the text of a requirement, its suggested rewrite, or any clause of a generated test, and save the edited version as the operative content.
FR-09	Review — reject. The system shall allow a reviewer to reject an AI finding or requirement, requiring an optional but tracked reason for the rejection.
FR-10	Item status tracking. The system shall track and display a per-item status — Pending, Accepted, Edited, or Rejected — for every extracted requirement and generated test, and shall provide a filterable queue of items still awaiting a decision.
FR-11	Audit trail. The system shall record an immutable log of every decision (accept / edit / reject) with the actor, the timestamp, and the before/after content, so the review history is traceable.
FR-12	Export. The system shall export the finalized specification, including each requirement's ID, final text, review status, and accepted acceptance tests, in a portable format (e.g., Markdown and JSON) for use in downstream tools.
5. Non-Functional Requirements
ID	Requirement
NFR-01	Performance. The system shall process and flag a document of up to 500 requirements and complete extraction, flagging, rewrite, and test generation within 60 seconds, with streaming status so the user sees progress.
NFR-02	Usability & Accessibility. The review interface shall be operable by keyboard only and shall meet WCAG 2.2 AA for contrast, focus visibility, and labels; per-item decision controls must be reachable without reading-decisions-loading secondary steps.
NFR-03	Security & Access Control. The system shall enforce role-based access control distinguishing Engineer and Reviewer, require authentication for all submissions and reviews, encrypt files at rest and in transit, and ensure one actor cannot alter another's decision history.
NFR-04	Reliability. The system shall be available 99.9% during business hours; an in-progress review shall be recoverable without loss of decisions on interruption or retry.
NFR-05	Traceability & Auditability. The system shall maintain a complete, immutable audit trail linking every decision to the actor, timestamp, and the specific requirement/test IDs, retained for at least one year.
NFR-06	Interoperability & Data Portability. The system shall expose all final data (requirements, decisions, acceptance tests) via export in standards-based, machine-readable formats (Markdown and JSON), and shall support batch re-import so a previously exported specification can be re-edited.
Notes and Open Questions for the Team
Input format scope: FR-01 currently limits uploads to .txt/.md. Should docx, .pdf, or .rst be supported in v1? (Recommend .txt/.md first, PDF later.)
Flag criteria rigor: FR-03/FR-04 rely on AI judgment. Recommend defining a short lexicon of ambiguity terms and a minimum threshold for "measurable" to reduce false positives.
Test execution scope: The Given-When-Then tests are generated and reviewed here, but ReqGuard does not run them. Confirm whether the acceptance tests are to be exported to a test-runner format (e.g., Gherkin/Cucumber) — FR-12 could extend to that.
Independent reviewer: NFR-03 allows Engineer and Reviewer to be separate or the same person. Confirm whether the workflow requires a different user for review in any compliance scenario.
I’ve kept this as a self-contained draft you can drop into a spec doc or a requirements tool. A few things I made explicit that you may want to tighten: the upload formats (FR-01), the definition of "ambiguous/untestable" (FR-03/FR-04), and whether the auto-generated acceptance tests should also export as runnable Gherkin/Cucumber files (noted under FR-12).

Want me to (a) turn this into implementation-ready user stories with acceptance criteria, (b) generate a QA test plan from these requirements via the test-plan skill, or (c) hand it to Developer to scaffold the ReqGuard app? Tell me which, and I'll route it.


