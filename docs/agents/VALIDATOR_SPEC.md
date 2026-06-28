AKAAL — VALIDATOR AGENT SPECIFICATION



VERSION: 1.0





1\. PURPOSE



The Validator Agent is the integrity verification engine of Akaal.



It runs at three stages of the workflow. It never modifies data. It never fixes errors. It only verifies and reports.





2\. VALIDATION STAGES



Stage 1 — Discovery Validation:



Compares source database against generated Universal JSON.



Verifies Scout captured the source correctly.



Stage 2 — GB Validation:



Compares Universal JSON against GB staging environment.



Verifies GB import was complete and correct.



Stage 3 — Production Validation:



Compares GB against production target.



Verifies every migrated row, schema, and relationship arrived correctly.





3\. WHAT VALIDATOR CHECKS (ALL STAGES)



Schemas.



Tables.



Columns.



Indexes.



Primary Keys.



Foreign Keys.



Views.



Functions.



Triggers.



Constraints.



Permissions.



Checksums.



Metadata.



Record counts (Stage 3 only).



Relationship integrity (Stage 3 only).





4\. VALIDATION LEDGER (STAGE 3)



Stage 3 validation runs in 100,000 row blocks.



Every block receives a SHA-256 checksum.



Block verification status and checksum are recorded in the incremental validation ledger.



Mismatched blocks are isolated, quarantined, and re-migrated individually.



The ledger is immutable and append-only.





5\. OUTPUTS



Validation Report per stage containing:



Validation ID.



Validator Version.



Validation Time.



Validation Scope.



Compared Objects.



Failed Objects.



Passed Objects.



Checksum Results.



Relationship Results.



Constraint Results.



Permission Results.



Execution Duration.



PASS or FAIL overall result.





6\. DECISION RULES



PASS → Manager proceeds to next stage.



FAIL → Manager creates incident, recovery begins, Scout may be required to regenerate Universal JSON.



Repeated failures (3+) → Live Intel investigation, human notification.





7\. CONSTRAINTS



Validator shall remain read-only at all times.



Validation shall always be deterministic.



Validation records shall remain immutable after creation.



Every validation shall reference the associated Migration ID and Checkpoint ID.





8\. PERFORMANCE REQUIREMENTS



Parallel validation of independent schemas.



Streaming comparison for large datasets.



Incremental ledger updates — no full reload required.





9\. FINAL ROLE DEFINITION



The Validator Agent is the deterministic integrity verification system that ensures no inconsistent data reaches the next workflow stage.

