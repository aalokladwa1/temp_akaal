\# AKAAL — SCOUT AGENT SPECIFICATION

VERSION: 1.0



\---



\# 1. PURPOSE



The Scout Agent is the data discovery and extraction engine of Akaal.



It reads source systems in read-only mode, extracts metadata, and converts it into a structured Blueprint for downstream intelligence processing.



The Scout never modifies any source system.



\---



\# 2. CORE RESPONSIBILITY



Source system discovery.



Schema extraction — tables, columns, indexes, constraints, views, functions, triggers, permissions, relationships.



DDL file parsing for offline schema analysis.



Dependency mapping.



Permission analysis.



Object relationship identification.



Universal JSON generation.



Checksum generation for all discovered objects.



Generating structured discovery reports.



\---



\# 3. TWO INPUT MODES



Mode 1 — Live Database Connection:



Connects via Universal Adapter Layer in read-only mode.



Reads database catalog directly.



Discovers live schema state.



Mode 2 — DDL File Parser:



Accepts a .sql file path.



Parses CREATE TABLE, indexes, constraints, foreign keys from DDL text.



Produces identical Blueprint output format as live mode.



Both modes produce the same Blueprint structure. Downstream components do not distinguish between modes.



\---



\# 4. INPUTS



Mode 1: Source database credentials (read-only), connection config, source type, migration ID, Manager task assignment.



Mode 2: File path to .sql schema file, source engine type (mysql, oracle, postgresql).



\---



\# 5. OUTPUTS



Blueprint (see BLUEPRINT\_CONTRACT.md for full schema).



Object dependency graph.



Metadata reports.



Checksum data per object.



Discovery logs.



\---



\# 6. BLUEPRINT STRUCTURE



```json

{

&#x20; "source": {

&#x20;   "engine": "oracle",

&#x20;   "version": ""

&#x20; },

&#x20; "objects": \[

&#x20;   {

&#x20;     "type": "table",

&#x20;     "name": "employees",

&#x20;     "attributes": \[

&#x20;       {

&#x20;         "name": "id",

&#x20;         "source\_type": "NUMBER(10,0)",

&#x20;         "nullable": false

&#x20;       }

&#x20;     ]

&#x20;   }

&#x20; ],

&#x20; "relationships": \[

&#x20;   {

&#x20;     "source\_object": "orders",

&#x20;     "target\_object": "employees",

&#x20;     "relationship\_type": "foreign\_key"

&#x20;   }

&#x20; ],

&#x20; "metadata": {

&#x20;   "object\_count": 1

&#x20; }

}

```



Scout shall never perform datatype normalization. source\_type is always the raw vendor type exactly as discovered.



\---



\# 7. READ-ONLY ENFORCEMENT



Scout MUST NEVER:



Modify source data.



Insert, update, or delete data.



Trigger transactions.



Execute write queries.



Bypass database permissions.



\---



\# 8. DDL PARSER RULES



The DDL parser shall:



Detect CREATE TABLE statements using pattern matching.



Extract table names, column definitions, data types, nullable flags.



Detect PRIMARY KEY, FOREIGN KEY, UNIQUE, INDEX, CONSTRAINT declarations.



Extract relationship edges from FOREIGN KEY REFERENCES.



Support MySQL and Oracle DDL syntax.



Support backtick, double-quote, and unquoted identifiers.



\---



\# 9. WORKFLOW BEHAVIOR



Receive task from Manager.



Establish read-only connection or load DDL file.



Validate access permissions (live mode only).



Scan source schema.



Extract metadata.



Map dependencies.



Generate Blueprint.



Compute checksums per object.



Submit Blueprint to Rulebook (intelligence pipeline) via Manager.



\---



\# 10. VALIDATION HANDOFF RULE



After generating Blueprint, Scout submits output only through Manager.



No direct communication with production systems.



No bypassing Manager control.



\---



\# 11. ERROR HANDLING



Connection failure → retry with exponential backoff (max 3 retries per Loop Governor).



Permission failure → report to Manager, halt discovery.



Schema inconsistency → flag to Validator.



Timeout → checkpoint restart from last cursor offset.



Critical failure → notify Live Intel.



\---



\# 12. PERFORMANCE REQUIREMENTS



Large-scale database scanning support.



Parallel schema extraction across independent schemas.



Incremental discovery with cursor-based offset tracking.



Streaming metadata processing.



Optimized memory usage — no full schema load into memory.



\---



\# 13. SECURITY CONSTRAINTS



Read-only access only.



Credential encryption — credentials never logged.



Secure connection handling.



Audit logging for all read operations.



\---



\# 14. STATE MANAGEMENT



Scout maintains temporary state during discovery:



Current schema snapshot.



Active connection session.



Discovery progress cursor.



Partial Blueprint build state.



All state is destroyed after successful Blueprint submission.



On failure, state is frozen and checkpointed for recovery.



\---



\# 15. FINAL ROLE DEFINITION



The Scout Agent is a deterministic discovery engine responsible for converting raw source systems into structured Blueprints without modifying any external data.

