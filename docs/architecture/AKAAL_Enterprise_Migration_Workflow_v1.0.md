# AKAAL ENTERPRISE MIGRATION WORKFLOW

## 1. Canonical Workflow Principle

AKAAL MUST NOT model migration as one fixed WF-001 → WF-020 sequence.

Instead:

```
OPERATOR INTENT
      ↓
9-Step Creation Flow
      ↓
Canonical Migration Model
      ↓
Plan Compiler
      ↓
Immutable ExecutionPlan + Dynamic Execution DAG
      ↓
Canonical Runtime
      ↓
Mode-Specific Execution Workflow
      ↓
Completion / Continuous Operation
```

AKAAL therefore has:

- one common migration creation/configuration experience;
- one canonical migration model;
- one canonical plan-compilation model;
- one canonical runtime/orchestration framework;
- multiple legitimate execution workflows selected according to operator intent and connector capabilities.

The implementation MUST NOT force every migration through stages that do not apply to the selected execution mode.

For example:

- Bulk-only migration must not pretend CDC exists.
- CDC-only operation must not secretly execute a bulk migration.
- Schema-only operation must not execute data transport.
- Validation-only operation must not perform migration writes unless an explicitly governed repair operation is separately approved.
- Monitoring is cross-cutting and must not be modeled as a sequential migration stage.

---

## 2. Common AKAAL Creation Workflow

Every AKAAL migration/operation begins with the common 9-step creation workflow.

### Step 1 — Migration Definition

The operator defines:

- migration identity/name/description;
- project/workspace;
- owner;
- environment;
- business context;
- strategy;
- priority;
- planning mode;
- execution mode;
- migration window;
- optional template;
- optional clone/source configuration.

Execution mode is a first-class planning decision.

### Step 2 — Source Instance

Establish the source instance/account/endpoint rather than prematurely selecting an individual database.

The operator may:

- select a saved connection profile;
- create a new profile;
- configure network route;
- configure authentication;
- configure connector-specific properties;
- test connectivity;
- retrieve connector capabilities;
- verify source authority.

Actual databases/catalogs/schemas/namespaces are discovered afterward.

### Step 3 — Target Instance

Establish the target instance/account/endpoint.

AKAAL verifies:

- connectivity;
- authentication;
- target write authority;
- connector capabilities;
- source↔target compatibility;
- applicable migration mechanisms.

### Step 4 — Discovery & Advanced Scope

AKAAL discovers the actual source topology and metadata.

The operator can navigate structures such as:

```
Instance
  → Database/Catalog
    → Schema/Namespace
      → Object Group
        → Object
```

Applicable functionality includes:

- Quick discovery;
- Standard discovery;
- Deep discovery;
- Compliance discovery;
- database/catalog selection;
- schema/namespace selection;
- table/object selection;
- include/exclude rules;
- wildcard/pattern selection;
- column projection;
- row predicates;
- partition/range selection;
- sampling;
- dependency analysis;
- FK/dependency warnings;
- selection preview;
- estimated selected volume.

### Step 5 — Mapping & Data Controls Studio

Configure the logical treatment of selected data.

Applicable capabilities include:

- source→target routing;
- schema mapping;
- object/table mapping;
- column mapping;
- renaming;
- 1:1 routing;
- many:1 routing;
- controlled 1:many routing;
- controlled many:many routing;
- datatype-aware mapping;
- transformations;
- cleansing;
- masking;
- redaction;
- pseudonymization;
- tokenization;
- deduplication;
- data-quality rules;
- target-collision policies;
- conflict policies;
- custom SQL;
- governed hooks.

The UI MUST be capability-driven.

Controls irrelevant to the selected execution mode or connector combination should not be presented as though they apply.

### Step 6 — Enterprise Configuration Center

Configure the runtime characteristics applicable to the selected execution mode.

Step 6 operates in two canonical operator modes: **Standard Mode** and **Advanced Mode**.

#### Configuration Modes Overview

```
STANDARD MODE:
  Enterprise-grade operational configuration of the migration at a high level,
  allowing AKAAL to safely calculate and derive appropriate lower-level runtime settings.

ADVANCED MODE:
  AKAAL's complete expert configuration surface, exposing EVERY legitimate dynamic/configurable
  control of the migration supported by the selected execution mode, connectors, runtime,
  authorities, and policies.
```

Standard Mode is a top-tier enterprise migration configuration experience and MUST NOT be treated as a beginner or basic mode. It allows operators to configure major behaviors—such as execution mode, strategy, concurrency profile, performance profile, resource limits, bandwidth policy, bulk/CDC behavior, validation strategy/levels, checkpoint/recovery policies, failure/retry behavior, quarantine, LOB strategy, cutover/failback strategies, notification behavior, scheduling, major connector options, and approval barriers—while AKAAL dynamically derives safe lower-level execution parameters based on source/target capabilities, topology, metadata, volume, object characteristics, available compute/memory, network, CDC mechanics, validation requirements, migration window, risk, and organizational policy. The resulting synthesized configuration remains visible and reviewable before execution.

Advanced Mode exposes the complete expert configuration surface of the compiled migration. It is capability-driven and generated dynamically from:
$$\text{Execution Mode} + \text{Source/Target Connector Capability Manifests} + \text{Topology} + \text{Selected Scope} + \text{Mapping/Data Controls} + \text{Runtime Capabilities} + \text{Workflow DAG} + \text{Policies}$$

Controls that do not apply to the selected setup MUST NOT be shown as though valid. Advanced Mode exposes dynamic controls across all legitimate operational domains.

#### Advanced Mode Control Domains

- **A. Connection / Session:** Connection-pool min/max sizing, acquisition/idle timeouts, connection lifetime, reconnect/keepalive behavior, source/target session initialization SQL, transaction/session isolation options, connector-specific session properties, network/socket read/write timeouts, retry policies, authentication refresh behavior, route/tunnel/bastion behavior.
- **B. Discovery / Metadata:** Discovery depth, discovery concurrency, metadata batching, refresh policies, cache behavior, object inspection depth, dependency traversal depth, statistics collection, sampling behavior, compatibility inspection behavior.
- **C. Work Partitioning:** Table/object partitioning strategy, partition keys (PK, range, hash, connector-native), partition count and sizing, skew handling, large-object/table thresholds, hot-partition handling, partition reassignment, dynamic repartitioning.
- **D. Workers / Parallelism:** Global worker count, per-source/target/object worker limits, reader/transformation/writer/validation/CDC capture/apply/reconciliation worker pools, worker queue sizing, worker lifecycle, affinity, parallelism ceilings/floors, adaptive parallelism scale-up/down thresholds.
- **E. Batching:** Initial/min/max batch size, row-based and byte-based batch limits, adaptive batching interval, latency targets, throughput targets, memory/target pressure reaction, batch flush behavior, partial-batch handling.
- **F. Memory / Buffering / Queues:** Memory envelope, per-worker memory caps, queue capacities, high/low watermarks, buffer sizes, spill-to-disk thresholds, temporary-storage limits, buffer retention, queue persistence, queue backpressure, producer/consumer throttling.
- **G. Bandwidth / Throttling:** Global, source, target, and migration-specific bandwidth limits, worker-level throttling, time-window throttling, burst allowance, adaptive throttling, network-pressure response, rate-limiting policy.
- **H. Bulk Transport:** Bulk read/write strategy, fetch size, write batch size, commit frequency, transaction boundaries, target loading mechanism, staging behavior, direct-path/native interfaces, insert/upsert strategy, existing-target collision behavior, ordering constraints, target constraint/index handling, preparation and finalization, transport compression.
- **I. LOB / Large Value Handling:** Inline vs streamed handling, LOB chunk size, stream buffer size, parallel LOB streams, memory/spill thresholds, retry boundary, checkpoint granularity, integrity verification, large-value timeout, connector-specific LOB mechanisms.
- **J. Checkpointing:** Checkpoint frequency (row-based, byte-based, time-based intervals), partition/object/transaction checkpointing, checkpoint durability, flush behavior, retention, restart granularity, checkpoint compaction.
- **K. Retry / Failure Policy:** Retry count, initial/max retry delay, backoff algorithm, jitter, retryable vs non-retryable error classification, per-object/partition/worker/source/target failure policies, timeout policy, fail-fast thresholds, continue-with-warning policy, quarantine policy, escalation behavior.
- **L. Recovery:** Worker recovery, process/daemon restart recovery, checkpoint recovery, partition reassignment, transaction replay, recovery concurrency, retry limits, recovery validation, recovery fencing, escalation, automatic vs operator-governed recovery.
- **M. CDC Capture:** Capture mechanism, starting position, snapshot/change boundary, polling/capture frequency, capture batch size, capture buffer, source log position tracking, native CDC options, transaction capture, DDL/schema event capture, heartbeats, capture checkpoint interval, retry policy, source-retention awareness.
- **N. CDC Buffer / Backlog:** Persistent buffer capacity, backlog warning/critical thresholds, spill behavior, retention, reclamation, ACK frontier, checkpoint frontier, catch-up behavior, catch-up parallelism, backlog pressure response.
- **O. CDC Apply:** Apply batch size, apply workers, transaction-aware apply, ordering strategy, causality handling, partition routing, parallel apply, commit behavior, idempotency behavior, deduplication/replay behavior, apply throttling, target-pressure handling.
- **P. Bidirectional / Multi-Master CDC:** Topology, primary/peer roles, provenance, echo suppression, conflict-detection/routing/resolution policy, quarantine, governed release, pause/resume, split-brain protection, fencing behavior.
- **Q. Incremental Query / Polling (M4):** Incremental key, watermark strategy, initial watermark, polling interval, bounded query window, overlap window, lookback behavior, query batch size, ordering, late-arriving data behavior, watermark commit behavior (never advance watermark before corresponding target work safely commits), source predicate behavior, retry behavior, schedule.
- **R. State-Based Synchronization (M5):** Comparison boundary, comparison partitioning, state fingerprint/checksum/Merkle strategy, comparison depth, mismatch thresholds, delta-generation policy, reconciliation policy, repair eligibility, repair batching, revalidation policy.
- **S. Validation:** Validation level, validation timing, validation concurrency, count validation, checksum validation, Merkle validation, row-level validation, column-level validation, sample vs full validation, partition validation, mismatch thresholds, mismatch localization, continuous vs post-migration validation, validation-only behavior, failure thresholds.
- **T. Reconciliation / Repair:** Reconciliation depth, repair eligibility, automatic vs governed repair, repair scope, repair batch size, repair concurrency, fencing, idempotency, repair thresholds, revalidation requirements, evidence requirements.
- **U. Schema Execution:** Schema action policy, create/alter behavior, dependency ordering, constraint handling, FK handling, index handling, sequence handling, identity handling, partition handling, view handling, procedure/function/trigger handling, unsupported-object behavior, DDL transaction behavior, schema rollback options.
- **V. Mapping / Transformation / Privacy / Quality Execution:** Operational runtime controls for rules defined in Step 5: rule/dependency ordering, transformation failure behavior, malformed-value behavior, lookup behavior, privacy-policy execution, tokenization behavior, deterministic masking, deduplication survivor policy, target-collision behavior, reject/quarantine handling, quality thresholds.
- **W. Custom SQL / Hook Execution:** Hook stage, ordering, dependency, transaction behavior, timeout, retry, failure policy, approval requirement, rollback behavior, session scope, parameter behavior.
- **X. Cutover:** Readiness thresholds, acceptable CDC lag/backlog, validation requirements, quiescence behavior, final boundary behavior, final drain, final validation, timeout, cutover fencing, commit/abort policies, cutover approval barriers.
- **Y. Failback:** Failback eligibility, divergence thresholds, reverse synchronization requirements, validation requirements, fencing, primary-role authority, split-brain prevention, approval requirements, failback execution behavior.
- **Z. Observability / Telemetry:** Telemetry sampling, metric granularity, history retention, event verbosity, progress update frequency, diagnostic detail, tracing controls, correlation behavior, alert/notification thresholds. (Cross-cutting observer only).
- **AA. Scheduling / Runtime Windows:** Start time, maintenance windows, blackout windows, allowed execution windows, pause windows, throttled windows, recurring incremental/validation schedules, deadline and overrun behavior.
- **AB. Approval Barriers:** Expert control over approval-barrier placement at EVERY semantically valid, safely resumable execution boundary (position, approver roles, approvers/groups, quorum, maker-checker/four-eyes, expiry, timeout, escalation, rejection behavior, evidence requirements, protected action, applicable conditions).
- **AC. Connector-Specific Dynamic Controls:** Native bulk/CDC mechanisms, consistency controls, transaction controls, fetch/write controls, source positions, partition mechanisms, compression, staging, native tuning, API limits, warehouse-specific behavior, object-store behavior, connector-native retry semantics, surfaced dynamically via connector capability manifests.

#### Scoped Override Hierarchy

Advanced Mode exposes scoped overrides at progressively narrower levels:

```
Organization Default
        ↓
Environment Default
        ↓
Migration Configuration
        ↓
Execution-Mode Configuration
        ↓
DAG Stage / Node Configuration
        ↓
Object / Table Configuration
        ↓
Partition / Worker Configuration
        ↓
Connector-Specific Configuration
```

Overrides are governed by explicit, deterministic precedence rules.

#### Static vs Dynamic Controls & Metadata Contract

Advanced Mode exposes 100% of legitimate product/migration controls, NOT internal code implementation variables (e.g. internal class names, private flags, debug hacks, magic constants, test-only switches). All dynamic controls declare metadata describing control identity, owner authority, type, valid range/values, default, recommended value, current effective value, scope, inheritance behavior, execution modes, connector applicability, mutability, restart/recompilation/approval invalidation impacts, security sensitivity, permissions, and operational risk.

#### Plan Compilation & Mode Switching

Both Standard and Advanced Mode compile into the exact same canonical `ExecutionPlan` model (there is no separate `StandardExecutionPlan` vs `AdvancedExecutionPlan`). 
Switching from Standard → Advanced reveals the detailed resolved configuration generated by AKAAL for explicit customization. Switching from Advanced → Standard requires an explicit decision (retain, reset, or cancel) so expert overrides are never silently destroyed. Advanced Mode cannot bypass underlying correctness, durability, consistency, security, governance, or connector invariants.

Approval barriers may also be configured at valid workflow boundaries from this step.

---

### Step 7 — Dynamic Migration Plan

AKAAL compiles the decisions from Steps 1–6 into the Stage-1 logical migration plan.

The plan presents:

- topology;
- selected scope;
- mappings;
- transformations;
- privacy policies;
- quality policies;
- runtime configuration (Standard or Advanced);
- compatibility analysis;
- schema actions;
- dependencies;
- risk;
- estimated work;
- warnings;
- blockers;
- plan version;
- plan diff;
- dynamic execution DAG.

Step 7 exposes the direct operational effect of configuration on the compiled execution DAG. Operators can inspect node-level configuration, inheritance paths, explicit overrides, connector settings, resource allocations, concurrency, batching, checkpoint boundaries, validation boundaries, retry/recovery policies, and approval barriers.

Where permitted, DAG and node-specific configuration edits can be made directly from Step 7. All such modifications MUST flow back through the canonical configuration model and cause the plan to be recompiled. The visual DAG UI must NOT become an independent configuration store.

AKAAL MUST support compile/dry-run behavior without performing target data writes.

The operator may inspect the generated execution DAG and configure permitted approval barriers at valid execution boundaries. Approval-barrier changes are themselves part of the plan and governance model.

---

### Step 8 — Governance & Readiness

AKAAL performs final execution-readiness evaluation.

Applicable checks include:

- preflight;
- source readiness;
- target readiness;
- compatibility blockers;
- permissions;
- capacity;
- storage;
- network;
- runtime configuration;
- security requirements;
- policy requirements;
- approval requirements;
- risk;
- waivers where permitted;
- execution-mode compatibility.

Approvals MUST bind to the exact plan version and fingerprint being authorized. Material modification of the approved plan invalidates the affected approval.

---

### Step 9 — Review, Schedule & Initialize

The operator performs the final review.

Review includes:

- source;
- target;
- execution mode;
- selected scope;
- mappings;
- policies;
- runtime configuration;
- execution DAG;
- approval barriers;
- readiness;
- risks;
- approvals;
- schedule.

The operator chooses:

```
Run Now
```

or:

```
Schedule Migration
```

AKAAL then compiles/freezes the immutable `ExecutionPlan`.

Scheduled execution MUST reference this immutable snapshot rather than whichever draft happens to be newest at execution time. The immutable `ExecutionPlan` becomes the authoritative input to runtime initialization.

---

## 3. Canonical Execution Modes

AKAAL defines eight first-class execution modes.

### M1 — Bulk Migration

Purpose: One-time movement of existing data.

Canonical runtime flow:

```
ExecutionPlan
     ↓
Runtime Initialization
     ↓
Acquire / Verify Connections
     ↓
Execution Preconditions
     ↓
Target Preparation
     ↓
Schema Execution
     ↓
Pre-Transport Hooks
     ↓
Partition / Work Planning
     ↓
┌───────────────────────────────┐
│       PARALLEL BULK LOAD      │
│                               │
│ Read → Controls → Write       │
│          │                    │
│   checkpoint/progress         │
└───────────────────────────────┘
     ↓
Post-Transport Hooks
     ↓
Validation
     ↓
Reconciliation
     ↓
Finalize Target
     ↓
Certification / Evidence
     ↓
COMPLETE
```

Monitoring, telemetry, audit, checkpointing and recovery operate alongside the execution workflow. They are not separate sequential migration stages.

---

### M2 — Bulk + CDC

Purpose: Perform an initial bulk load followed by continuous synchronization and controlled low/near-zero-downtime cutover.

CDC MUST NOT simply begin after bulk migration has completed if doing so would create an unprotected change window. AKAAL must establish an appropriate consistent source/change boundary.

Canonical runtime flow:

```
ExecutionPlan
      ↓
Runtime Initialization
      ↓
Connection / Capability Verification
      ↓
Execution Preconditions
      ↓
Target Preparation
      ↓
Schema Execution
      ↓
Establish Consistent Source Boundary
      │
      ├───────────────────┐
      ↓                   ↓
Initialize CDC        Snapshot/Bulk
Capture Boundary      Read Boundary
      │                   │
      ↓                   ↓
Capture Changes        Bulk Transport
      │                   │
      │               Validation
      │                   │
      └─────────┬─────────┘
                ↓
            CDC Catch-Up
                ↓
       Continuous Synchronization
                ↓
         Continuous Validation
                ↓
          Cutover Readiness
                ↓
          Approval Barrier
                ↓
         Source Quiescence
                ↓
       Capture Final Boundary
                ↓
            Final Drain
                ↓
         Final Validation
                ↓
          Atomic Cutover
                ↓
             Hypercare
                │
          ┌─────┴─────┐
          ↓           ↓
       SUCCESS      FAILBACK
          │           │
          └─────┬─────┘
                ↓
       Certification/Evidence
```

CDC capture and bulk execution may therefore overlap according to the consistency strategy required by the source connector and execution plan.

---

### M3 — CDC / Continuous Replication

Purpose: Start synchronization from an established CDC position without requiring an AKAAL bulk load.

The runtime MUST NOT silently execute bulk migration as part of CDC-only mode.

Canonical runtime flow:

```
ExecutionPlan
      ↓
Runtime Initialization
      ↓
CDC Capability Verification
      ↓
Determine Starting Position
      ↓
Validate Source/Target Baseline
      ↓
Initialize Durable CDC Session
      ↓
Capture
      ↓
Persistent Buffer
      ↓
Ordering / Causality
      ↓
Partition / Parallel Apply
      ↓
Conflict / Schema Evolution Handling
      ↓
Checkpoint + ACK
      ↓
Continuous Validation
      ↓
Continuous Synchronization
```

The workflow may remain operational indefinitely. Cutover is optional depending on whether the operation represents temporary migration synchronization or permanent replication.

---

### M4 — Incremental Query/Polling

Purpose: Provide incremental synchronization where native log-based CDC is unavailable, unsuitable or intentionally not selected.

Conceptually:

```sql
SELECT ...
FROM source
WHERE incremental_key > :last_watermark
  AND incremental_key <= :current_boundary
```

Canonical runtime flow:

```
Initialize
   ↓
Verify Incremental Key
   ↓
Establish Initial Watermark
   ↓
Poll Source
   ↓
Bound Query Window
   ↓
Read Changed Rows
   ↓
Apply Data Controls
   ↓
Apply Target Mutations
   ↓
Validate
   ↓
Durably Commit Watermark
   ↓
Wait / Schedule
   ↓
Poll Again
```

Critical correctness invariant:
```
AKAAL MUST NEVER advance the durable watermark until the
corresponding target work has safely committed.
```
Otherwise a crash could produce silent data loss.

Possible strategies include timestamp, increasing identifier, composite watermark, version column, change-version marker, or connector-specific incremental cursor.

---

### M5 — State-Based Synchronization

Purpose: Synchronize systems by comparing authoritative state rather than consuming a native change stream.

This differs from incremental polling. Incremental polling asks: *"What changed since position X?"* State-based synchronization asks: *"How does the source state differ from the target/reference state now?"*

Canonical runtime flow:

```
Establish Comparison Boundary
          ↓
Partition Comparison Space
          ↓
Source State ───────── Target State
       │                   │
       └─────────┬─────────┘
                 ↓
          State Comparison
                 │
         ┌───────┼───────┐
         ↓       ↓       ↓
       Equal   Changed  Missing
                 │
                 ↓
          Generate Delta Set
                 ↓
      Governed Reconciliation
                 ↓
             Validation
                 ↓
          Commit New State
```

This mode SHOULD reuse canonical validation and reconciliation authorities rather than introducing another competing comparison engine.

---

### M6 — Schema Only

Purpose: Translate/deploy schema and database objects without transporting data rows.

Canonical runtime flow:

```
ExecutionPlan
      ↓
Connection Verification
      ↓
Source Schema Discovery
      ↓
Canonical Schema
      ↓
Compatibility Analysis
      ↓
Schema Translation
      ↓
Dependency Ordering
      ↓
DDL Execution
      ↓
Object Verification
      ↓
Schema Reconciliation
      ↓
Evidence
      ↓
COMPLETE
```

Bulk transport and CDC are not invoked. The runtime MUST NOT fabricate concepts such as "0 rows migrated" to simulate participation of irrelevant engines.

---

### M7 — Data Only

Purpose: Transport data into an existing or separately prepared target structure.

Canonical runtime flow:

```
ExecutionPlan
      ↓
Verify Source
      ↓
Verify Target
      ↓
Validate Target Structure Compatibility
      ↓
Partition Work
      ↓
Read
      ↓
Mapping / Transformation / Privacy / Quality
      ↓
Write
      ↓
Checkpoint
      ↓
Validation
      ↓
Reconciliation
      ↓
Evidence
```

Schema execution is not invoked unless explicitly required by a separately authorized operation.

---

### M8 — Validation / Reconciliation Only

Purpose: Validate and reconcile existing source/target systems without requiring AKAAL to perform the original migration.

Canonical runtime flow:

```
Source                    Target
   │                         │
   └───────────┬─────────────┘
               ↓
      Boundary Establishment
               ↓
      Structural Validation
               ↓
        Count Validation
               ↓
     Checksum / Merkle Validation
               ↓
        Deep Row Validation
               ↓
       Column-Level Analysis
               ↓
       Mismatch Localization
               ↓
      Reconciliation Analysis
               ↓
        ┌──────┴──────┐
        ↓             ↓
     REPORT       Repair Eligible
                      │
                      ↓
               Approval/Governance
                      │
                      ↓
               Controlled Repair
                      │
                      ↓
                  Revalidate
                      ↓
            Certification/Evidence
```

AKAAL may therefore be used as an independent validation/certification platform even when the original migration was performed by another product or process. Validation-only mode MUST remain non-mutating unless an explicit controlled repair operation is separately authorized.

---

## 4. Dynamic Approval Barriers

AKAAL MUST NOT model governance as only three permanently hardcoded approval gates. Approval is a first-class graph primitive.

Conceptually:

```
Execution DAG
     ↓
   Node
     ↓
◆ ApprovalBarrier
     ↓
   Node
```

An `ApprovalBarrier` contains:
- identity;
- execution position/boundary;
- required roles;
- required approvers;
- quorum;
- maker-checker/four-eyes requirement;
- conditions;
- expiry;
- rejection policy;
- timeout/escalation;
- exact plan version;
- plan fingerprint;
- evidence requirements;
- authorization record.

AKAAL provides recommended approval boundaries (before schema modification, before first target write, before bulk transport, before CDC activation, before reconciliation repair, before source quiescence, before cutover, before failback, before destructive cleanup). Operators can configure additional approval barriers at valid execution boundaries in Step 6 (Enterprise Configuration Center) and Step 7 (Dynamic Migration Plan).

The plan compiler validates that an approval barrier is placed at a semantically valid and safely resumable boundary. Approvals bind to the immutable plan identity/fingerprint; changing approval placement or protected execution behavior invalidates previous approval.

---

## 5. Workflow Composition Model

AKAAL MUST NOT implement these execution modes as one giant hardcoded conditional (`if mode == "bulk": ...`). Instead, AKAAL's workflow framework is composed from reusable canonical execution capabilities/authorities:

- Connection, Discovery, Assessment, Risk
- Schema, Selection, Mapping, Transformation, Privacy, Data Quality
- Planning, Governance, Hooks
- Bulk Transport, Change Acquisition, CDC, Incremental Synchronization, State Comparison
- Validation, Reconciliation, Checkpoint, State, Recovery
- Cutover, Failback
- Monitoring, Telemetry, Reporting, Certification, Evidence
- Connector Infrastructure

Execution modes compose these reusable authorities into mode-specific DAGs:

```
BULK:            Schema → Bulk → Validate
BULK + CDC:      Boundary → (CDC Capture || Bulk → Validate) → Catch-Up → Sync → Cutover
CDC ONLY:        CDC → Validate → Sync
INCREMENTAL:     Poll → Delta → Apply → Validate → Commit Watermark → Repeat
VALIDATION:      Compare → Reconcile → Evidence
```

Different execution DAGs MUST NOT create duplicate schema, transport, CDC, validation, checkpoint, recovery, monitoring, reporting or governance engines merely because the workflow differs.

---

## 6. Cross-Cutting Runtime Authorities

Some responsibilities are not sequential workflow stages. They operate continuously across execution:

### Monitoring & Telemetry

Observes every active execution mode (state, worker status, throughput, rows/bytes, partitions, batch behavior, lag, CDC backlog, checkpoints, retries, failures, recovery, validation status, resource usage, connector health, queue pressure, approval wait states, cutover readiness, runtime history). Consumes authoritative runtime state; MUST NOT become a second execution authority.

### Checkpoint & Durable State

Operates across applicable runtime nodes to provide durable progress, restart reconstruction, idempotency boundaries, worker recovery, CDC positions, incremental watermarks, plan identity, runtime identity, approval waiting states, and recovery state.

### Recovery

Invoked according to failure semantics of execution nodes. It is a node-level resilience capability, not a fake sequential "self-healing stage".

### Audit & Evidence

Produces durable evidence/audit records according to organizational compliance policies.

### Governance

Evaluates protected operations dynamically throughout execution rather than only once at startup.

---

## 7. Canonical High-Level AKAAL Model

```
                    OPERATOR INTENT
                          │
                          ▼
                  9-Step Creation Flow
                          │
                          ▼
               Canonical Migration Model
                          │
                          ▼
                    PLAN COMPILER
                          │
                          ▼
                ExecutionPlan + DAG
                          │
         ┌────────────────┼────────────────┐
         │                │                │
      Bulk DAG        Bulk+CDC DAG      CDC DAG
         │                │                │
         ├──── Incremental DAG ────────────┤
         │                │                │
      Schema DAG       Data DAG       Validation DAG
         │                │                │
         └────────────────┼────────────────┘
                          ▼
                  CANONICAL RUNTIME
                          │
                          ▼
              Completion / Continuous Run
```

State-based synchronization is another DAG compiled by the same framework and canonical authorities.

---

## 8. Architectural Consequence

This workflow specification becomes the basis for upcoming AKAAL architecture reconciliation. The repository MUST NOT be reorganized merely according to its current folder structure. Instead, subsequent forensic work will:

1. derive required root responsibilities/authorities from this workflow;
2. define contracts between those authorities;
3. inspect existing AKAAL/NexusForge implementations responsibility-by-responsibility;
4. classify candidate implementations using evidence;
5. KEEP, RECTIFY, MERGE, REPLACE, REMOVE or BUILD as appropriate;
6. make selected production authorities real and dynamic;
7. rebuild production wiring around those authorities;
8. establish one canonical production execution path;
9. reconnect UI → Tauri → IPC to that path;
10. verify P0–P5 capabilities against the resulting canonical runtime.

This document itself DOES NOT claim that the current repository already satisfies this architecture.

---

## 9. Future-Roadmap Adaptability

The workflow framework must remain extensible for future AKAAL phases (P5 remaining capabilities, P6 enterprise operations/fleet management, P7 security/compliance, P7A connector/plugin ecosystem, P7B cloud/hybrid/data-fabric, P7C AI-native migration intelligence, P7D unified enterprise experience, P8 scale/resilience certification, P9 packaging/deployment, P10 final enterprise acceptance).

Future capabilities must extend plan inputs, reusable authorities, execution node types, policies, capability contracts, connector capabilities, runtime services, monitoring, governance, and workflow compilation rather than replacing the migration architecture.

---

## 10. Frozen Principles

The following principles are frozen by this workflow specification:

1. AKAAL has one workflow framework, not one universal linear migration sequence.
2. Operator intent and connector capability determine the compiled execution workflow.
3. The 9-step creation workflow is the common planning/configuration entry path.
4. Step 6 is Enterprise Configuration Center.
5. Step 7 is Dynamic Migration Plan.
6. `ExecutionPlan` is immutable once frozen for execution.
7. Scheduled execution references the frozen `ExecutionPlan`.
8. Runtime execution is represented as a DAG/graph.
9. Bulk, Bulk+CDC, CDC-only, Incremental Query/Polling, State-Based Synchronization, Schema-only, Data-only and Validation/Reconciliation-only are first-class execution modes.
10. Irrelevant engines are not invoked merely to preserve a fixed sequence.
11. Monitoring and telemetry are cross-cutting runtime authorities, not sequential workflow stages.
12. Checkpoint/state/recovery are cross-cutting runtime concerns.
13. Approval is a configurable graph primitive rather than only three hardcoded gates.
14. Approval barriers may be configured from both Enterprise Configuration Center and Dynamic Migration Plan.
15. Approvals bind to exact plan versions/fingerprints.
16. Material plan changes invalidate affected approvals.
17. Bulk+CDC must protect changes occurring during the initial-load window through a valid consistency/change-boundary strategy.
18. CDC-only must not secretly perform bulk migration.
19. Incremental watermarks must not advance before corresponding target work safely commits.
20. Validation-only must remain non-mutating unless a separately governed repair is explicitly authorized.
21. State-based synchronization must reuse canonical comparison/reconciliation authorities rather than creating duplicate engines.
22. Different workflow modes reuse canonical authorities instead of creating duplicate transport/schema/CDC/validation/recovery/etc. implementations.
23. The workflow framework must remain extensible for the future AKAAL roadmap.
24. Existing code is NOT automatically considered correct merely because it matches a name in this document.
25. Future repository reconciliation must determine implementation truth from code evidence.
26. AKAAL configuration has two canonical operator modes: Standard Mode and Advanced Mode.
27. Standard Mode is an enterprise-grade configuration experience, not a beginner/basic mode.
28. Standard Mode exposes major operational decisions while allowing AKAAL to safely derive lower-level runtime settings.
29. Advanced Mode exposes every legitimate configurable/dynamic part of the selected migration that is supported by the active execution mode, connectors, runtime authorities and policies.
30. Advanced Mode is capability-driven and must not be implemented as one universal static settings form.
31. Advanced Mode may expose scoped overrides down to DAG/node, object/table, partition/worker and connector-specific levels where semantically safe.
32. Configuration inheritance and override precedence must be explicit and deterministic.
33. Advanced Mode exposes legitimate product controls, not arbitrary internal implementation variables.
34. Connector-specific advanced controls are discovered through canonical connector capability/configuration contracts.
35. Standard and Advanced Mode compile into the same canonical configuration and immutable `ExecutionPlan`.
36. The canonical runtime does not maintain separate Standard and Advanced execution engines.
37. Standard → Advanced switching reveals the detailed resolved configuration generated by AKAAL.
38. Advanced → Standard switching must never silently destroy expert overrides.
39. Advanced Mode cannot override correctness, durability, consistency, security, governance or connector invariants.
40. Every effective execution-relevant dynamic configuration required for deterministic execution/recovery must be captured in the frozen `ExecutionPlan` or an explicitly referenced immutable configuration authority.
41. Material configuration changes must trigger plan recompilation and invalidate affected approvals.
42. Step 7 must make the relationship between configuration and execution-DAG behavior inspectable.
43. DAG-level configuration edits must flow through the canonical configuration authority; the DAG UI must not become an independent configuration store.
