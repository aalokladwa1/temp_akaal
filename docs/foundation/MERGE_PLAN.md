\# AKAAL — Merge Plan

\*\*Aalok's NexusForge + Friend's NexusForge V1 → Akaal\*\*



\---



\## Overview



Two systems. Same product vision. Complementary strengths.



\- \*\*Aalok's system\*\* = operational engine. Runs migrations at scale. Production-grade.

\- \*\*Friend's system\*\* = intelligence layer. Assesses, plans, advises before data moves.



Merged = a complete product neither has alone.



\---



\## Phase 0 — Rename and Repo Setup

\*\*Owner: Both | Time: 1 day\*\*



\- \[ ] Create new repo: `akaal`

\- \[ ] Copy Aalok's system as the base (it's the spine)

\- \[ ] Copy Friend's system components into designated folders

\- \[ ] Delete all references to "NexusForge" across both codebases, replace with "Akaal"

\- \[ ] Single `README.md` written fresh for Akaal



\*\*Why Aalok's system is the spine:\*\* it has the running orchestration engine, gateway, state machine, and live staging execution logs. Friend's components slot in as Phase 0 intelligence.



\---



\## Phase 1 — Terminology Alignment

\*\*Owner: Both | Time: 1 day\*\*



Resolve naming conflicts before touching any logic.



| Concept | Aalok Name | Friend Name | Akaal Name |

|---|---|---|---|

| Schema discovery agent | Scout Agent | The Scout | Scout |

| DB abstraction layer | Adapter Framework | Universal Key | Universal Adapter Layer |

| Type mapping engine | — | Rulebook | Rulebook |

| Staging environment | GB | Greenbox | GB |

| Checkpoint persistence | Checkpoint Engine | Polaroid | Checkpoint Engine |

| Recovery workers | Standby Agents | Backup Crew | Standby Agents |

| Live monitoring | Live Intel Agent | Live Intel | Live Intel |



\*\*Action:\*\* Do a global find-replace in Friend's code:

\- `Universal Key` → `UniversalAdapterLayer`

\- `Greenbox` → `GB`

\- `Polaroid` → `CheckpointEngine`

\- `Backup Crew` → `StandbyAgents`

\- `The Scout` → `Scout`

\- `The Mover` → `MigrationExecutor`

\- `The Manager` → `Manager`

\- `The Validator` → `Validator`



\---



\## Phase 2 — Plug In Friend's Intelligence Layer

\*\*Owner: Friend leads, Aalok reviews | Time: 2–3 days\*\*



Friend's pipeline (Scout → Rulebook → Decoder → Risk Scorer → Planner → Advisor) becomes Akaal's \*\*Pre-Migration Intelligence Phase\*\*.



\### Step 1: Move files

```

friend's system → akaal/

core/rulebook\\\_v1/       → akaal/core/rulebook/

core/risk\\\_scorer\\\_v1.py  → akaal/core/risk\\\_scorer/risk\\\_scorer.py

core/planner\\\_v1.py      → akaal/core/planner/planner.py

core/advisor\\\_v1.py      → akaal/core/advisor/advisor.py

core/scout.py           → akaal/agents/scout/schema\\\_scout.py  (alongside Aalok's scout)

core/executor.py        → akaal/core/executor/type\\\_executor.py

core/adapters/oracle.py → akaal/adapters/oracle\\\_adapter.py

core/adapters/mysql.py  → akaal/adapters/mysql\\\_adapter.py

lib/decoder\\\_engine/     → akaal/core/decoder/

```



\### Step 2: Wire into Manager workflow

Insert the intelligence phase before GB Import in Aalok's workflow state machine:



```

DISCOVERY\\\_COMPLETED

\&#x20;     ↓

\\\[NEW] INTELLIGENCE\\\_PHASE\\\_STARTED   ← insert here

\&#x20;     ↓

\\\[NEW] RULEBOOK\\\_MAPPING

\&#x20;     ↓

\\\[NEW] DECODER\\\_ANALYSIS

\&#x20;     ↓

\\\[NEW] RISK\\\_SCORING

\&#x20;     ↓

\\\[NEW] PLANNING

\&#x20;     ↓

\\\[NEW] ADVISORY\\\_GENERATED

\&#x20;     ↓

\\\[NEW] INTELLIGENCE\\\_PHASE\\\_COMPLETED

\&#x20;     ↓

GB\\\_LOADING                          ← continues as before

```



Add these states to `akaal/core/models/enums.py` WorkflowState enum.



\### Step 3: Update Manager to call intelligence pipeline

In Manager agent, after `DISCOVERY\\\_COMPLETED`:

```python

\\# Call intelligence pipeline

rulebook\\\_result = RulebookV1().resolve(universal\\\_json)

decoder\\\_result = DecoderEngine().analyze(universal\\\_json)

risk\\\_result = RiskScorerV1().score(universal\\\_json)

plan\\\_result = PlannerV1().plan(universal\\\_json, risk\\\_result)

advisory = AdvisorV1().generate(universal\\\_json, risk\\\_result, plan\\\_result)



\\# Store in checkpoint

checkpoint.save(intelligence\\\_phase={...})



\\# Block if any object is BLOCK decision

if any(obj\\\["decision"] == "BLOCK" for obj in plan\\\_result\\\["objects"]):

\&#x20;   trigger\\\_human\\\_alert(advisory)

\&#x20;   pause\\\_workflow()

```



\---



\## Phase 3 — Scout Merge

\*\*Owner: Both | Time: 1–2 days\*\*



Two scouts exist. Different strengths:

\- \*\*Aalok's Scout\*\* — connected to the full agent system, checkpoint-aware, async

\- \*\*Friend's Scout\*\* — better DDL parsing (regex-based, handles MySQL/Oracle schemas from files)



\*\*Merge strategy:\*\* Aalok's Scout is the primary. Friend's DDL parsing logic (`parse\\\_tables`, `\\\_extract\\\_balanced\\\_body`, etc.) moves into Aalok's Scout as a parsing module.



```

akaal/agents/scout/

├── scout\\\_agent.py          # Aalok's agent (primary)

├── ddl\\\_parser.py           # Friend's parsing logic (extracted)

└── schema\\\_models.py        # Shared schema object models

```



Scout Agent calls `DDLParser` when source is file-based, calls live adapter when source is a live DB connection.



\---



\## Phase 4 — Adapter Merge

\*\*Owner: Aalok | Time: 1 day\*\*



Aalok has full PostgreSQL adapter (mock + real). Friend has Oracle and MySQL (partial stubs).



```

akaal/adapters/

├── base\\\_adapter.py         # Aalok's BaseAdapter (keep as-is)

├── postgres\\\_adapter.py     # Aalok's (keep as-is — most complete)

├── oracle\\\_adapter.py       # Friend's → wrap in Aalok's BaseAdapter interface

└── mysql\\\_adapter.py        # Friend's → wrap in Aalok's BaseAdapter interface

```



Each adapter must implement: `connect()`, `close()`, `discover\\\_schema()`, `read\\\_batch()`, `write\\\_batch()`.



Friend's Oracle/MySQL adapters currently only do type mapping. Aalok needs to extend them to support live connection + `discover\\\_schema()`.



\---



\## Phase 5 — Test Suite Merge

\*\*Owner: Friend leads | Time: 1–2 days\*\*



Friend has a comprehensive test suite (rulebook, orchestrator, advisor, executor, planner, scout). Aalok has staging execution logs.



```

akaal/tests/

├── unit/

│   ├── test\\\_rulebook.py        # Friend's (keep)

│   ├── test\\\_advisor\\\_v1.py      # Friend's (keep)

│   ├── test\\\_risk\\\_scorer.py     # Friend's (keep)

│   ├── test\\\_planner\\\_v1.py      # Friend's (keep)

│   ├── test\\\_scout.py           # Friend's (keep)

│   └── test\\\_executor\\\_v1.py     # Friend's (keep)

├── integration/

│   ├── test\\\_orchestrator.py    # Friend's (adapt to Akaal Manager)

│   └── test\\\_v1\\\_pipeline.py     # Friend's (keep)

└── staging/

\&#x20;   └── run\\\_migration\\\_staging.py # Aalok's staging runner

```



\---



\## Phase 6 — Human Approval Gate Update

\*\*Owner: Aalok | Time: 1 day\*\*



Currently the human approval gate shows validation results and migration summary.



Update it to also show:

\- Risk Score + Risk Level (from Risk Scorer)

\- Planner decisions per object (CAST / TRANSFORM / BLOCK count)

\- Full Advisor report (guidance, warnings, safe alternatives)

\- Any BLOCK decisions as red flags requiring acknowledgment



\---



\## Phase 7 — Unified Docs

\*\*Owner: Both | Time: 1 day\*\*



\- \[ ] `ARCHITECTURE.md` — already done (see AKAAL\_ARCHITECTURE.md)

\- \[ ] `README.md` — product overview, setup, quickstart

\- \[ ] `AGENTS.md` — update with intelligence phase agents

\- \[ ] Per-agent spec files for Rulebook, Risk Scorer, Planner, Advisor



\---



\## Conflict Points to Resolve



| Conflict | Resolution |

|---|---|

| Both called "NexusForge" | Renamed to Akaal everywhere |

| Friend's `executor.py` is type-mapping executor; Aalok has migration executor | Friend's becomes `type\\\_executor.py`; Aalok's is `migration\\\_executor.py` |

| Friend's `orchestrator\\\_v1.py` is a mini pipeline runner; Aalok has full Manager | Friend's orchestrator becomes a utility used internally by the intelligence phase; Aalok's Manager stays as system controller |

| Friend's Scout does file-based DDL; Aalok's Scout does live DB | Both kept; DDL parsing extracted into shared module |

| Different checkpoint implementations | Aalok's Checkpoint Engine is primary (more complete); Friend's Polaroid concept is fully covered |



\---



\## What Not to Merge



| Item | Reason |

|---|---|

| Friend's `main.py` | Thin CLI wrapper — replace with Akaal's Gateway |

| Friend's `README.md` | Rewrite for Akaal |

| Aalok's `prd.md` / `trd.md` | Archive — superseded by AKAAL\_ARCHITECTURE.md |

| Friend's `docs/TOY\\\_BOX\\\_ANALOGY.md` | Good for pitch deck, not codebase |



\---



\## Execution Order Summary



| Phase | What | Who | Days |

|---|---|---|---|

| 0 | Repo setup + rename | Both | 1 |

| 1 | Terminology alignment | Both | 1 |

| 2 | Intelligence layer wired in | Friend leads | 2–3 |

| 3 | Scout merge | Both | 1–2 |

| 4 | Adapter merge | Aalok | 1 |

| 5 | Test suite merge | Friend leads | 1–2 |

| 6 | Human approval gate update | Aalok | 1 |

| 7 | Unified docs | Both | 1 |



\*\*Total: \~10 days clean execution.\*\*



\---



\## What You Can Show Your Dad After Phase 2



After Phase 2, Akaal can:

1\. Take a database schema (Oracle or MySQL)

2\. Assess migration complexity with a risk score

3\. Generate a deterministic migration plan (CAST / TRANSFORM / BLOCK per object)

4\. Produce an Advisor report explaining every decision in plain English

5\. Execute the full migration pipeline with checkpoint recovery

6\. Present a human approval gate with full risk context before any data moves



That's a complete demo. That's what you show him.



\---



\*Merge plan v1.0 — Akaal\*

