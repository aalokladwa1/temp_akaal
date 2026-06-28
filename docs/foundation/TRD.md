\# AKAAL

\# TECHNICAL REQUIREMENTS DOCUMENT

VERSION: 1.0

STATUS: ACTIVE



\---



\# 1. PURPOSE



This document defines the complete technical requirements for building Akaal.



It specifies how every component shall behave, interact, validate, recover, and communicate.



This document is the engineering contract for all implementation decisions.



\---



\# 2. TECHNICAL OBJECTIVES



The platform shall:



Support deterministic execution — identical inputs always produce identical outputs.



Never modify source systems during discovery.



Support enterprise-scale migrations — 2M rows per minute throughput demonstrated.



Support automatic recovery from any failure point using checkpoints.



Support zero-trust validation — every stage validates before proceeding.



Support modular expansion — new databases added through adapters only.



Support cloud-native deployment.



Support horizontal scalability.



Support complete observability across every component.



Support immutable auditing of every action.



\---



\# 3. SYSTEM COMPONENTS



The platform shall consist of:



Manager Agent.



Scout Agent.



Validator Agent.



Live Intel Agent.



GB Agent.



Observability Supervisor Agent.



Standby Agents (for every critical agent).



Rulebook.



Risk Scorer.



Planner.



Advisor.



Decoder Engine.



Universal Adapter Layer.



Input Gateway.



Checkpoint Engine.



Recovery Engine.



CDC Engine.



Audit Engine.



Loop Governor Engine.



Message Bus.



Notification Engine.



Dashboard.



Every component shall operate independently while communicating through standardized interfaces.



\---



\# 4. CORE TECHNICAL PRINCIPLES



Every component shall satisfy:



Deterministic — same inputs, same outputs, always.



Stateless where practical — state lives in checkpoints, not agents.



Version controlled — every artifact is versioned.



Recoverable — every failure has a recovery path.



Observable — every action produces telemetry.



Testable — every component has a defined test contract.



Replaceable — no component creates hard coupling.



Loosely coupled — components communicate through contracts only.



Highly cohesive — each component owns one clear responsibility.



Vendor independent — no component is tied to a single database or cloud provider.



\---



\# 5. SUPPORTED MIGRATION CATEGORIES



The platform shall support:



Database migration — table, schema, index, constraint, relationship, permission migration.



Cloud migration — source on-premise to target cloud.



Storage migration — file and object storage.



Application migration — schema-coupled application data.



Hybrid migration — mixed on-premise and cloud.



Future migration categories shall require only adapter implementation without redesigning the orchestration engine.



\---



\# 6. INTELLIGENCE LAYER REQUIREMENTS



The pre-migration intelligence phase shall:



Run before any data movement.



Accept source schema as input (live connection or DDL file).



Produce a Blueprint containing all discovered objects with their source types.



Map every source type to a Universal Data Model concept through the Rulebook.



Analyze stored procedures, triggers, and packages through the Decoder Engine.



Score migration risk per object on a deterministic 0–10 scale.



Produce a CAST, TRANSFORM, or BLOCK decision per object through the Planner.



Generate a human-readable Migration Advisory Report through the Advisor.



Block migration if any object receives a BLOCK decision until human acknowledgment.



The intelligence phase shall never move data.



The intelligence phase shall never modify the source.



\---



\# 7. GATEWAY REQUIREMENTS



The Input Gateway shall:



Be the only authorized entry point into Akaal.



Validate every incoming request against a strict schema before passing to Manager.



Reject invalid requests immediately.



Log every request with a correlation ID.



Never pass malformed or unauthorized requests to workflow execution.



No agent shall receive user input directly.



\---



\# 8. MANAGER REQUIREMENTS



The Manager shall:



Orchestrate the complete workflow from project creation to archive.



Maintain the authoritative workflow state machine.



Assign tasks to agents.



Monitor agent health through Live Intel.



Create checkpoints at every stage transition.



Enforce the human approval gate before production migration.



Never contain vendor-specific migration logic.



Never modify data directly.



\---



\# 9. SCOUT REQUIREMENTS



The Scout shall:



Connect to source systems in read-only mode only.



Extract complete schema metadata including tables, columns, indexes, constraints, relationships, permissions, views, functions, triggers.



Generate Universal JSON from extracted metadata.



Generate checksums for all discovered objects.



Submit output to Validator before any downstream processing.



Support live database connections and DDL file parsing.



Never modify source data.



Never create, update, or delete source objects.



\---



\# 10. RULEBOOK REQUIREMENTS



The Rulebook shall:



Map every source database type to a Universal Data Model concept deterministically.



Use explicit mapping tables only — no heuristics, no ML, no guessing.



Fail hard if a type cannot be resolved — never return UNKNOWN.



Support precision, scale, length, and timezone extraction per type.



Be engine-agnostic — engines are metadata providers, not semantic authorities.



Produce UDM objects with: concept, family, precision (if applicable), scale (if applicable), length (if applicable), timezone (if applicable), status.



\---



\# 11. RISK SCORER REQUIREMENTS



The Risk Scorer shall:



Score migration risk on a deterministic 0–10 scale using fixed rule tables.



Use no heuristics, no ML, no inference.



Classify risk into: LOW (1–2), MEDIUM (3–4), HIGH (5–6), CRITICAL (7–10).



Produce risk flags for: HIGH\_PRECISION\_OVERFLOW\_RISK, HIGH\_SCALE\_PRECISION\_LOSS\_RISK, LARGE\_FIELD\_TRUNCATION\_RISK, TIMEZONE\_NORMALIZATION\_REQUIRED, spatial\_network\_mismatch.



Never modify the UDM input.



Never introduce new logic beyond the fixed rule tables.



\---



\# 12. PLANNER REQUIREMENTS



The Planner shall:



Consume validated UDM and Risk Scorer output.



Produce exactly one decision per object: CAST, TRANSFORM, or BLOCK.



CAST = safe direct migration, no transformation required.



TRANSFORM = conversion required, structural adaptation needed.



BLOCK = migration unsafe, data loss risk, human redesign required.



Never modify UDM.



Never recompute risk.



Never override Advisor output.



\---



\# 13. ADVISOR REQUIREMENTS



The Advisor shall:



Translate Planner decisions into human-readable explanations.



Produce: summary, decision explanation, risk interpretation, migration guidance, execution notes, confidence commentary.



Never modify UDM.



Never recompute risk.



Never override Planner decisions.



Never introduce new logic.



Never hallucinate system state.



\---



\# 14. VALIDATOR REQUIREMENTS



The Validator shall:



Execute validation at three stages: post-discovery, post-GB import, post-production migration.



Compare source against Universal JSON at discovery stage.



Compare Universal JSON against GB at staging stage.



Compare GB against production target at production stage.



Verify: schema, tables, columns, indexes, primary keys, foreign keys, views, functions, triggers, constraints, permissions, checksums, record counts, relationships.



Remain read-only at all times.



Produce a deterministic validation report with PASS or FAIL per check.



Block workflow progression on any FAIL result.



\---



\# 15. GB REQUIREMENTS



The GB (staging environment) shall:



Store validated Universal JSON before production migration.



Remain isolated from production at all times until human approval is granted.



Version every dataset — no mutation without version increment.



Freeze snapshots — no updates to validated data, only new versions.



Support human inspection of schema, data, and validation results.



Require all five conditions before promoting to production: Validation PASS, Human Approval TRUE, Checkpoint integrity VERIFIED, Audit logs COMPLETE, No active incidents.



\---



\# 16. CHECKPOINT ENGINE REQUIREMENTS



The Checkpoint Engine shall:



Create checkpoints at every workflow stage transition.



Store: workflow state, agent states, active tasks, validation status, GB state reference, CDC position, audit trail pointer, timestamp, checksum.



Generate checksums for all checkpoint data.



Preserve immutability — checkpoints cannot be modified after creation.



Support four checkpoint types: Automatic, Failover, Manual, Pre-Production.



Support five recovery modes: Full system, Partial agent, Workflow-level, GB-only, Validation-only.



Use cursor-based pagination for all table extraction — recovery resumes from last cursor without restarting.



\---



\# 17. CDC ENGINE REQUIREMENTS



The CDC Engine shall:



Read transaction logs directly (WAL/Binlog) — never query production tables for sync.



Apply changes to target within 1.5 seconds of source commit.



Support: INSERT, UPDATE, DELETE, and schema changes where supported.



Assign to every event: checksum, sequence number, timestamp, transaction identifier.



Validate: event order, duplicate events, missing events, corrupted events.



Trigger final validation when pending event queue reaches zero.



\---



\# 18. LIVE INTEL REQUIREMENTS



The Live Intel Agent shall:



Monitor all agent health continuously.



Predict failures before they occur using telemetry signals.



Repair infrastructure without workflow interruption where safe.



Promote standby agents automatically on primary failure.



Demote repaired primary to standby after recovery.



Operate independently of business workflows — monitoring is isolated.



Never modify business data.



Never override validation results.



\---



\# 19. LOOP GOVERNOR REQUIREMENTS



The Loop Governor shall:



Track attempt count, failure reason, state hash, last success state, last failure state, and timestamp for every workflow loop.



Enforce retry limits: Scout max 3 retries, Validator max 3 retries, Live Intel max 2 retries, GB max 2 retries.



Detect repeated state hashes: warning at 2 occurrences, stop at 3, force freeze at 4+.



Apply exponential backoff: attempt 1 no delay, attempt 2 small delay, attempt 3 higher delay, attempt 4 forbidden.



Escalate to Manager and Live Intel on loop stop.



Never execute tasks — only decide retry, stop, or escalate.



\---



\# 20. AUDIT ENGINE REQUIREMENTS



The Audit Engine shall:



Record every platform action with: Audit ID, Timestamp, Project ID, Migration ID, User ID, Agent ID, Action, Action Result, Severity, Correlation ID, Source Component, Target Component.



Store records in append-only, immutable storage.



Never allow modification or deletion of audit records after creation.



Support search, filtering, and reporting across audit history.



\---



\# 21. PRODUCTION EXECUTION REQUIREMENTS



All production migrations shall enforce:



Cursor-based pagination — extraction uses offsets, recovery resumes from cursor.



Idempotent writes — target inserts use ON CONFLICT DO UPDATE, no double-writes on recovery.



CDC latency SLA — changes applied to target within 1.5 seconds of source commit.



Partition pre-allocation — tables exceeding 50M rows get partitions pre-built before load.



Error classification — Transient (retry with exponential backoff), Data Quality (quarantine row and continue), Structural (halt migration and freeze).



Backpressure — Scout and GB capped at 30,000 rows per second, maximum 150,000 row buffer, maximum 300MB heap.



Incremental validation ledger — validation runs in 100,000 row blocks, SHA-256 per block, mismatched blocks quarantined and re-migrated individually.



\---



\# 22. SECURITY REQUIREMENTS



The platform shall enforce:



Zero-trust architecture — every request requires authentication, authorization, input validation, and audit logging.



TLS encryption for all data in transit.



AES-256 encryption for all data at rest.



Secrets never embedded in source code.



Role-based access control for every component.



Rate limiting on all API endpoints.



No unauthenticated access to any system layer.



\---



\# 23. PERFORMANCE REQUIREMENTS



Throughput: 2M rows per minute demonstrated in staging.



CDC latency: changes applied to target within 1.5 seconds.



Checkpoint creation: low-latency, parallel state capture.



Validation: 100,000 row blocks with SHA-256 per block.



Backpressure cap: 30,000 rows per second, 150,000 row max buffer.



Failover: sub-second for agent-level failover, few seconds for service-level.



\---



\# 24. TECHNOLOGY STACK



Backend: Python, FastAPI.



Frontend: React, TypeScript.



Operational Database: PostgreSQL.



Cache: Redis.



Queue: RabbitMQ.



Containerization: Docker.



Version Control: Git, GitHub.



Future Container Orchestration: Kubernetes.



\---



\# 25. ACCEPTANCE CRITERIA



Akaal shall be considered technically complete when:



Every component communicates through standardized interfaces only.



Universal JSON functions as the canonical internal data model.



GB operates as the validated staging environment.



Recovery restores workflow from verified checkpoints without repeating validated work.



Standby agents activate without workflow interruption.



Validation prevents inconsistent migrations at every stage.



Security protects every architectural layer.



Observability provides complete platform visibility.



Human approval gate cannot be bypassed by any agent.



Future adapters integrate without modification to the orchestration layer.



\---



\# TECHNICAL PRINCIPLE



Akaal shall be engineered as a deterministic enterprise migration platform.



Every technical decision shall prioritize correctness, reliability, validation, recovery, security, and long-term maintainability over implementation convenience or short-term optimization.

