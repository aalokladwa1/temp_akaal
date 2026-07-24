"""ResiliencePolicyEngine re-export."""
from akaal.resilience_eng.policy.declarations import DeclarativePolicyEngine, PolicyDeclaration

class ResiliencePolicyEngine(DeclarativePolicyEngine):
    """Facade policy engine for Platform 5."""
    pass

__all__ = ["ResiliencePolicyEngine", "DeclarativePolicyEngine", "PolicyDeclaration"]
