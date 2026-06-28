AKAAL — DECODER ENGINE SPECIFICATION



VERSION: 1.0





1\. PURPOSE



The Decoder Engine performs complex object analysis on source database objects that cannot be handled by simple type mapping.





2\. WHAT DECODER ANALYZES



Stored procedures.



Triggers.



Database packages (Oracle).



Functions.



Views with complex logic.



Custom data types.





3\. WHAT DECODER PRODUCES



Per analyzed object:



Syntax complexity score.



Vendor-specific feature dependencies (Oracle sequences, packages, etc.).



Risk signals for migration.



Recommendations: migrateable as-is, requires rewrite, not migratable.





4\. RISK SIGNALS DECODER GENERATES



Uses Oracle-specific syntax → requires rewrite.



References Oracle package → package must be decomposed.



Trigger uses vendor-specific function → compatibility risk.



Stored procedure uses dynamic SQL → high complexity.



Custom type with nested structure → structural migration risk.





5\. OUTPUT CONTRACT



json{

&#x20; "object\_name": "calculate\_bonus",

&#x20; "object\_type": "procedure",

&#x20; "complexity\_score": 7,

&#x20; "vendor\_dependencies": \["DBMS\_OUTPUT", "UTL\_FILE"],

&#x20; "risk\_signals": \["Oracle-specific package dependency"],

&#x20; "recommendation": "requires\_rewrite",

&#x20; "notes": "References Oracle-only DBMS\_OUTPUT package. Rewrite required for PostgreSQL compatibility."

}





6\. CONSTRAINTS



Decoder shall never modify source objects.



Decoder shall never execute source code.



Decoder operates on static analysis only — it reads, never runs.



Decoder output feeds into Risk Scorer as additional risk input.





7\. FINAL ROLE



The Decoder Engine is the static analysis layer that surfaces hidden migration complexity in stored procedures, triggers, and vendor-specific database objects.

