\# AKAAL — MANAGER AGENT SPECIFICATION

VERSION: 1.0



\---



\# 1. PURPOSE



The Manager Agent is the central orchestration controller of Akaal.



It owns the workflow. It assigns tasks. It enforces every gate. It never executes business logic itself.



\---



\# 2. CORE RESPONSIBILITY



The Manager is responsible for:



Creating and managing migration projects.



Driving the workflow state machine from IDLE to MIGRATION\_COMPLETED.



Assigning tasks to Scout, Validator, GB, Live Intel, and Migration Executor.



Monitoring agent health through Live Intel.



Creating checkpoints at every stage transition.



Enforcing the human approval gate before production migration.



Coordinating recovery on failure.



Generating audit records for every workflow transition.



\---



\# 3. INPUTS



Source type, target type, authentication config, migration strategy — from Input Gateway.



Agent status reports — from Scout, Validator, GB, Live Intel.



Human approval decisions — from Dashboard.



Checkpoint restoration signals — from Checkpoint Engine.



Live Intel alerts — from Live Intel Agent.



\---



\# 4. OUTPUTS



Task assignments to agents.



Workflow state updates.



Checkpoint creation requests.



Human approval notifications.



Incident records.



Audit records for every transition.



Migration report on completion.



\---



\# 5. WORKFLOW STATE MACHINE



The Manager enforces this exact sequence. No state may be skipped.



```

IDLE

↓

PROJECT\_CREATED

↓

DISCOVERY\_STARTED

↓

DISCOVERY\_COMPLETED

↓

INTELLIGENCE\_PHASE\_STARTED

↓

RULEBOOK\_MAPPING

↓

DECODER\_ANALYSIS

↓

RISK\_SCORING

↓

PLANNING

↓

ADVISORY\_GENERATED

↓

INTELLIGENCE\_PHASE\_COMPLETED

↓

DISCOVERY\_VALIDATED

↓

GB\_LOADING

↓

GB\_LOADED

↓

GB\_VALIDATION

↓

GB\_VALIDATED

↓

HUMAN\_APPROVAL\_PENDING

↓

HUMAN\_APPROVED

↓

PRODUCTION\_MIGRATION

↓

PRODUCTION\_VALIDATION

↓

CDC\_SYNCHRONIZATION

↓

MIGRATION\_COMPLETED

↓

ARCHIVED

```



Failure states: FAILED, RECOVERY\_STARTED, CHECKPOINT\_RESTORE, RETRYING, ESCALATED, CANCELLED, PAUSED.



\---



\# 6. HUMAN APPROVAL GATE ENFORCEMENT



Manager shall:



Block all progression at HUMAN\_APPROVAL\_PENDING until explicit approval is received.



Display full migration summary, risk assessment, Advisor report, schema differences, estimated time, recovery plan, and rollback plan.



Accept: Approve, Reject, Pause, Request Investigation, Cancel.



Record approval decision in audit trail before proceeding.



Never accept approval from an agent — only from authenticated human operator.



\---



\# 7. TASK ASSIGNMENT RULES



Every task assignment shall include:



Task ID. Agent ID. Execution Timeout. Priority. Correlation ID.



No agent shall communicate directly with another agent for workflow decisions.



All workflow control returns through Manager.



Exception: Live Intel may independently monitor and repair infrastructure.



\---



\# 8. FAILURE HANDLING



On any agent failure:



Manager receives alert from Live Intel.



Manager pauses workflow.



Manager verifies latest checkpoint.



Manager activates standby agent.



Manager coordinates recovery.



Manager resumes workflow after Validator verification.



\---



\# 9. MANAGER MODULES



Workflow Scheduler.



Execution Planner.



State Machine Controller.



Checkpoint Controller.



Recovery Coordinator.



Human Approval Controller.



Queue Manager.



Progress Tracker.



Incident Coordinator.



Audit Coordinator.



\---



\# 10. CONSTRAINTS



Manager shall never contain vendor-specific migration logic.



Manager shall never modify data directly.



Manager shall never bypass the human approval gate.



Manager shall never skip checkpoint creation at stage transitions.

