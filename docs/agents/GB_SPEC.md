AKAAL — GB AGENT SPECIFICATION



VERSION: 1.0





1\. PURPOSE



The GB (Global Buffer) Agent is the controlled staging and human-verification layer of Akaal.



It is the final intermediate system between validated structured data and production systems.



GB is not production. GB is not raw source. It is a controlled, versioned, human-verifiable staging environment.





2\. CORE RESPONSIBILITY



Storing validated Universal JSON.



Maintaining staging consistency.



Supporting human verification.



Holding pre-production datasets.



Managing the approval gate interface.



Version-controlled staging of migrations.



Ensuring safe promotion to production.





3\. INPUTS



Validated Universal JSON from Validator.



Checkpoint state from Checkpoint Engine.



Migration metadata from Manager.



Validation reports.



CDC sync updates.



Human review feedback.





4\. OUTPUTS



Staged dataset snapshots.



Human-readable verification views.



Pre-production validation state.



Approval readiness status.



Diff reports (GB vs production).



Final promotion package.





5\. STAGING RULES



No direct mutation of validated data.



Every change creates a new version.



All datasets are immutable after staging.



Every dataset has a checksum.



Every dataset has a version ID.





6\. VERSION CONTROL MODEL



Every GB dataset includes:



GB ID. Version ID. Migration ID. Checkpoint Reference. Validation Reference. Timestamp. Checksum. Approval State.



Version history is fully preserved and immutable.





7\. HUMAN VERIFICATION LAYER



GB is the only layer where humans directly inspect:



Schema structure. Data correctness. Relationships. Validation results. Migration readiness.



Humans may: Approve, Reject, Request Re-Validation, Request Re-Discovery.





8\. PROMOTION TO PRODUCTION RULE



Data can ONLY move to production when ALL five conditions are true:



Validation = PASS.



Human Approval = TRUE.



Checkpoint Integrity = VERIFIED.



Audit Logs = COMPLETE.



No active incidents exist.



If any condition is false, promotion is blocked.





9\. DIFF ENGINE



GB maintains comparison system showing:



Schema differences. Data differences. Constraint differences. Relationship differences. Version differences.



Any mismatch blocks production promotion.





10\. FAILURE HANDLING



If GB detects inconsistency: freeze migration, notify Manager, trigger Validator re-run, trigger Scout re-extraction if required, notify Live Intel.



If GB fails: checkpoint rollback triggered, system enters safe mode, Manager halts migration flow, Live Intel analyzes failure, backup GB instance activated.





11\. FINAL ROLE DEFINITION



The GB Agent is a deterministic, version-controlled staging and human approval system that ensures no data reaches production without strict validation, traceability, and explicit human consent.





