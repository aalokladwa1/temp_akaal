"""akaalEngine.intelligence.remediation
========================================
P7C.18 -- Governed Recovery & Remediation Intelligence. Produces typed
ActionProposal objects (akaalEngine.intelligence.mediation.proposal) for
already-existing canonical commands only -- never fabricates support for an
action the canonical runtime does not actually have. Mediation, authorization,
approval, and execution all remain the job of the EXISTING Group-1
ActionMediationGateway / canonical command handlers -- this module never
executes anything itself.
"""
