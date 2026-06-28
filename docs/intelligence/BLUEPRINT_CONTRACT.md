AKAAL — BLUEPRINT CONTRACT



VERSION: 1.0

STATUS: FROZEN





1\. PURPOSE



The Blueprint is the canonical schema representation produced by the Scout and consumed by the Rulebook.



It represents discovered database metadata in a deterministic, database-agnostic structure.



The Blueprint contains only discovered schema information.



It never contains migration decisions, risk scores, planner output, or execution metadata.





2\. OWNERSHIP



Producer: Scout.



Primary Consumer: Rulebook.



Secondary Consumers: Decoder Engine, Risk Scorer (via enriched Blueprint), Manager.



The Blueprint is enriched by each component. No component rewrites information produced by earlier stages.





3\. DESIGN PRINCIPLES



The Blueprint must always remain:



Deterministic — identical inputs always produce identical Blueprints.



Serializable — fully JSON-serializable.



Database-agnostic — no vendor-specific data in the structure.



Versionable — every Blueprint carries a version identifier.



Immutable by convention — earlier stage data is never modified by later stages.





4\. BLUEPRINT STRUCTURE



json{

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

&#x20;       },

&#x20;       {

&#x20;         "name": "salary",

&#x20;         "source\_type": "NUMBER(12,2)",

&#x20;         "nullable": true

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





5\. OBJECT DEFINITION



Every object must contain:



type — Object type (table; future: view, index, sequence, trigger).



name — Object name exactly as discovered.



attributes — Collection of object attributes.





6\. ATTRIBUTE DEFINITION



Every attribute must contain:



name — Original attribute name.



source\_type — Original database datatype exactly as discovered. Never normalized.



nullable — Boolean nullable flag.



Scout must never perform datatype normalization. source\_type is always the raw vendor string.





7\. RULEBOOK ENRICHMENT



Rulebook enriches every attribute by attaching a UDM object.



Example enriched attribute:



json{

&#x20; "name": "salary",

&#x20; "source\_type": "NUMBER(12,2)",

&#x20; "nullable": true,

&#x20; "udm": {

&#x20;   "concept": "DECIMAL",

&#x20;   "family": "numeric",

&#x20;   "precision": 12,

&#x20;   "scale": 2,

&#x20;   "status": "mapped"

&#x20; }

}



Rulebook shall never modify: source, objects, object names, source\_type, nullable, relationships, metadata.



Its only responsibility is attaching the udm object to each attribute.





8\. BLUEPRINT INVARIANTS



Scout produces raw schema metadata only — never type mappings.



Rulebook enriches attributes with udm only — never modifies Scout fields.



Planner never modifies Scout metadata.



Components enrich the Blueprint instead of replacing it.



Original database metadata must always remain available.



Blueprint serialization must be deterministic.



Identical inputs must always produce identical Blueprints.





9\. FREEZE RULES



Allowed additions:



New fields added to objects or attributes (as optional).



New object types (view, index, etc.).



Optional attribute fields.



Not allowed:



Rename top-level keys.



Remove existing fields.



Break backward compatibility.



Status: FROZEN. Version: V1.

