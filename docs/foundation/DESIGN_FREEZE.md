\# AKAAL

\# DESIGN FREEZE V1

VERSION: 1.0

STATUS: APPROVED



\---



\# PURPOSE



This document defines the officially approved Akaal V1 architecture.



It prevents unnecessary redesigns, scope creep, and architecture drift during implementation.



This architecture is frozen until implementation evidence proves a change is required.



\---



\# 1. FROZEN CORE AGENTS



Approved agents for V1:



Manager Agent.



Scout Agent.



Validator Agent.



Live Intel Agent.



GB Agent.



Observability Supervisor Agent.



Standby Agents (mirrors of every critical agent).



Total: 7 agent types.



No additional agents are approved for V1.



\---



\# 2. FROZEN INTELLIGENCE COMPONENTS



Approved intelligence components for V1:



Rulebook.



Risk Scorer.



Planner.



Advisor.



Decoder Engine.



Total: 5 intelligence components.



No additional intelligence components are approved for V1.



\---



\# 3. FROZEN ENGINES



Approved engines for V1:



Checkpoint Engine.



CDC Engine.



Audit Engine.



Loop Governor Engine.



Recovery Engine.



Total: 5 engines.



\---



\# 4. FROZEN INFRASTRUCTURE



Approved infrastructure for V1:



Universal Adapter Layer (replaces Universal Key).



Input Gateway.



Message Bus.



Universal JSON Store.



GB (replaces Greenbox).



Notification Engine.



\---



\# 5. FROZEN ENGINEERING STRATEGIES



Approved strategies:



Dynamic Adapter Strategy — any-to-any migration through pluggable adapters.



Deterministic Type Mapping Strategy — explicit rules only, no guessing.



Isolated Schema Simulation Strategy — GB validates before production.



Log Sequence State Locking Strategy — checkpoint-based recovery.



Two Tier Telemetry Strategy — runtime signals and persistent logs.



Log Based CDC Strategy — reads WAL/Binlog directly.



Risk Intelligence Strategy — scores complexity before execution.



Cursor-Based Fault Resumption Strategy — recovery resumes from last cursor offset.



Idempotent Write Strategy — ON CONFLICT DO UPDATE for all target writes.



Total: 9 strategies. No additional strategies approved for V1.



\---



\# 6. FROZEN DATABASE SUPPORT



Source databases: Oracle, MySQL, PostgreSQL.



Target databases: PostgreSQL.



No other databases included in V1.



\---



\# 7. FROZEN MVP SCOPE



MVP Name: Migration Advisor + Execution Engine.



MVP Goal: Assess, plan, execute, validate, and recover any Oracle or MySQL to PostgreSQL migration.



Inputs: Oracle schemas, MySQL schemas, PostgreSQL schemas (live connection or DDL file).



Outputs: Migration Advisory Report, Migration Execution, Validation Report, Audit Trail.



\---



\# 8. FROZEN NAMING CONVENTION



The following Akaal names are final. No legacy names from either source system are used in code or docs.



Universal Key → Universal Adapter Layer.



Greenbox → GB.



Polaroid → Checkpoint Engine.



Backup Crew → Standby Agents.



The Mover → Migration Executor.



The Scout → Scout.



The Manager → Manager.



The Validator → Validator.



NexusForge (both) → Akaal.



\---



\# 9. EXPLICIT NON-GOALS FOR V1



Web UI.



SaaS multi-tenant platform.



Kubernetes deployment.



Billing and user management.



MongoDB, Cassandra, NoSQL targets.



Autonomous AI migrations without human approval.



Enterprise RBAC system.



\---



\# 10. CHANGE CONTROL POLICY



Before introducing any new component, answer:



Does it solve a real implementation problem found during build?



Can an existing component solve it?



Does it delay V1 delivery?



Can it wait for V2?



If the answer to question 4 is YES: Do Not Add It.



\---



\# 11. DESIGN FREEZE DECLARATION



The following are officially frozen for Akaal V1:



7 core agent types.



5 intelligence components.



5 engines.



9 engineering strategies.



Database support (Oracle, MySQL → PostgreSQL).



MVP scope and roadmap.



Naming convention.



Any modification requires implementation-driven justification and formal architectural review.



Status: APPROVED.

