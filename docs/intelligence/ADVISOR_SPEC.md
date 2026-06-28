AKAAL — ADVISOR SPECIFICATION



VERSION: 1.0





1\. PURPOSE



The Advisor is the final intelligence layer before execution.



It transforms internal migration decisions into human-readable explanations, migration recommendations, risk interpretations, and execution guidance.





2\. POSITION IN PIPELINE



Rulebook → Risk Scorer → Planner → Advisor → Human Review Gate.





3\. CORE RESPONSIBILITY



Explain Planner decisions.



Interpret risk signals.



Generate migration guidance.



Provide warnings and safe alternatives.



Translate system output into human understanding.





4\. INPUT CONTRACT



UDM object (validated).



Risk output from Risk Scorer.



Planner output (Migration Plan Object).





5\. OUTPUT CONTRACT — MIGRATION ADVISORY OBJECT (MAO)



json{

&#x20; "summary": "Safe direct migration. No transformation required.",

&#x20; "decision\_explanation": "The source type INTEGER maps directly to PostgreSQL INTEGER with no precision loss.",

&#x20; "risk\_interpretation": "Low risk. No flags detected.",

&#x20; "migration\_guidance": {

&#x20;   "recommended\_action": "Proceed with direct CAST migration.",

&#x20;   "safe\_alternative": null,

&#x20;   "warnings": \[]

&#x20; },

&#x20; "execution\_notes": \[],

&#x20; "confidence\_commentary": "High confidence. Planner confidence 0.95, risk level LOW, stable decision."

}





6\. DECISION INTERPRETATION RULES



CAST → safe direct migration, no transformation required, minimal risk.



TRANSFORM → conversion required, structural adaptation needed, possible precision or schema adjustment.



BLOCK → migration unsafe, high risk of data loss or incompatibility, reject or redesign required.





7\. RISK INTERPRETATION RULES



Advisor MUST translate:



risk.level → human explanation.



risk.score → severity context.



risk.flags → actionable warnings in plain English.



NO new risk logic is allowed.





8\. GUIDANCE MODEL



Every MAO must include:



Recommended Action — clear next step based on Planner decision.



Safe Alternative — fallback approach when TRANSFORM or BLOCK occurs.



Warnings — human-readable risk insights derived from risk flags.





9\. CONSTRAINTS



Advisor shall never modify UDM.



Advisor shall never recompute risk.



Advisor shall never override Planner decisions.



Advisor shall never introduce new logic.



Advisor shall never hallucinate system state.



Output must be deterministic — identical inputs produce identical output.







