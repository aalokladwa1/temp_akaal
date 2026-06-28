AKAAL — RISK SCORER SPECIFICATION



VERSION: 1.0





1\. PURPOSE



The Risk Scorer annotates every UDM object with a deterministic risk score before migration planning.





2\. RULES



No heuristics.



No ML.



No inference.



ONLY deterministic rule tables.



MUST NOT modify UDM.



ONLY annotate risk.





3\. FAMILY RISK TABLE (FIXED)



FamilyBase Scorenumeric1boolean1string2identifier2temporal3structured4binary4network4spatial5





4\. ADDITIONAL SCORING RULES



Precision > 18 → +2 score, flag: HIGH\_PRECISION\_OVERFLOW\_RISK.



Scale > 6 → +2 score, flag: HIGH\_SCALE\_PRECISION\_LOSS\_RISK.



Length > 1024 → +2 score, flag: LARGE\_FIELD\_TRUNCATION\_RISK.



Timezone = true → +1 score, flag: TIMEZONE\_NORMALIZATION\_REQUIRED.



Family = spatial or network → +2 score, flag: spatial\_network\_mismatch.





5\. RISK CLASSIFICATION



ScoreLevel1–2LOW3–4MEDIUM5–6HIGH7–10CRITICAL





6\. OUTPUT CONTRACT



json{

&#x20; "udm": { ... },

&#x20; "risk": {

&#x20;   "score": 4,

&#x20;   "level": "MEDIUM",

&#x20;   "flags": \["TIMEZONE\_NORMALIZATION\_REQUIRED"]

&#x20; }

}





