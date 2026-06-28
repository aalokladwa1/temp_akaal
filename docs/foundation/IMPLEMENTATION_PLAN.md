\# AKAAL

\# IMPLEMENTATION CONTROL PROTOCOL

VERSION: 1.0



\---



\# 1. PURPOSE



This document defines the strict execution order and build discipline for implementing Akaal.



It ensures the system is built one component at a time, with full validation, without parallel incomplete agents, without skipping steps.



\---



\# 2. CORE PRINCIPLE (NON-NEGOTIABLE)



The system MUST follow:



Build → Validate → Stabilize → Integrate → Then proceed.



NOT:



Build everything together.



Parallel incomplete agents.



Skipping validation.



Batch implementation.



\---



\# 3. GOLDEN RULE



ONE COMPONENT = ONE COMPLETE CYCLE.



A cycle is complete ONLY when:



Component is implemented.



Component passes internal tests.



Component passes integration check with all previously built components.



Logs are verified.



State is stable.



Manager (or team lead) confirms readiness.



ONLY THEN does the next component start.



\---



\# 4. BUILD ORDER (STRICT SEQUENCE)



The system must be built in this exact order.



Round 1 — Foundation Infrastructure



1\. Message Bus

2\. Audit Engine

3\. Input Gateway

4\. Manager Agent (state machine + checkpoint coordination only)

5\. Checkpoint Engine



Round 2 — Discovery



6\. Universal Adapter Layer (base adapter + PostgreSQL adapter)

7\. Scout Agent (live connection mode)

8\. Scout DDL Parser (file mode)



Round 3 — Intelligence Pipeline



9\. Rulebook

10\. Decoder Engine

11\. Risk Scorer

12\. Planner

13\. Advisor



Round 4 — Validation and Staging



14\. Validator Agent

15\. GB Agent



Round 5 — Execution



16\. Loop Governor Engine

17\. Migration Executor

18\. Recovery Engine



Round 6 — Synchronization



19\. CDC Engine



Round 7 — Reliability



20\. Live Intel Agent

21\. Observability Supervisor Agent

22\. Standby Agents + Failover Controller



Round 8 — Remaining Adapters



23\. Oracle Adapter (extend to full BaseAdapter interface)

24\. MySQL Adapter (extend to full BaseAdapter interface)



\---



\# 5. COMPONENT BUILD RULES



For EACH component:



Step 1 — Create core logic.



Step 2 — Define inputs and outputs.



Step 3 — Implement execution rules per spec.



Step 4 — Add failure handling.



Step 5 — Add logging and audit integration.



Step 6 — Run unit tests.



Step 7 — Simulate workflow execution with previous components.



Step 8 — Confirm stability.



ONLY THEN mark component as COMPLETE.



\---



\# 6. NO PARALLELISM RULE



At no point shall:



Multiple components be in an incomplete state simultaneously.



A new component start before the current one is validated and integrated.



The system proceed with unresolved dependencies.



\---



\# 7. VALIDATION GATE (MANDATORY)



Before moving to the next component, the current component must pass:



Functional test — does it do what the spec says?



Failure simulation — does it handle failures correctly?



Recovery simulation — does it recover from its own failures?



Integration test with all previously built components.



Checkpoint compatibility test — can the system recover through this component?



If ANY test fails:



STOP BUILD.



FIX CURRENT COMPONENT.



REVALIDATE FROM START.



\---



\# 8. INTEGRATION RULE



After each component is built, it must be integrated into:



Manager control flow.



Checkpoint system.



Audit logging.



Validation system.



BEFORE the next component starts.



\---



\# 9. FAILURE RULE



If any component causes: crash, loop, mismatch, timeout, or validation failure:



Roll back to last stable checkpoint.



Fix component.



Re-run full validation.



ONLY THEN continue.



\---



\# 10. STATE RULE



At any time:



Only ONE active build component is allowed.



All others must be: Pending, Validated, or Locked.



\---



\# 11. PROGRESS PHILOSOPHY



Build small stable components.



Build trust through correctness.



Build reliability through incremental validation.



Then scale the system.



Not big-bang development.



\---



\# 12. FINAL EXECUTION COMMAND



Do not proceed until the current component is production-stable.



No assumptions. No partial completion. No skipping validation.

