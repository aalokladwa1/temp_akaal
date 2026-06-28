AKAAL — PLANNER SPECIFICATION



VERSION: 1.0





1\. PURPOSE



The Planner produces exactly one migration decision per object based on validated UDM and Risk Scorer output.





2\. DECISIONS



CAST — Safe direct migration. No transformation required. Minimal risk.



TRANSFORM — Conversion required. Structural adaptation needed. Possible precision or schema adjustment.



BLOCK — Migration unsafe. High risk of data loss or incompatibility. Reject or redesign required.





3\. DECISION RULES



BLOCK if:



Risk level = CRITICAL.



Any irreversible loss flag present (irreversible\_loss, lossy\_conversion, precision\_loss, data\_truncation).



Spatial or network mismatch flag present.



TRANSFORM if:



Risk level = HIGH.



Precision or scale adjustment flags present.



Family mismatch flags present.



CAST if:



Risk level = LOW or MEDIUM.



No loss indicators.



No mismatch flags.





4\. INPUT CONTRACT



UDM object (from Validator V1).



Risk output (from Risk Scorer).





5\. OUTPUT CONTRACT



json{

&#x20; "decision": "CAST",

&#x20; "strategy": "direct",

&#x20; "confidence": 0.95,

&#x20; "reason": \["numeric family, low precision, no flags"],

&#x20; "risk\_snapshot": { ... }

}





6\. CONSTRAINTS



Planner shall never modify UDM.



Planner shall never recompute risk.



Planner shall never override Advisor output.



Planner operates exclusively on UDM — never on raw vendor types.

