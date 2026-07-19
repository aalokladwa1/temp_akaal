"""
AKAAL Enterprise Intelligence Subsystem (Phase 9 Platform 2)
============================================================
The strategic decision synthesis and enterprise intelligence platform layer of AKAAL.
Transforms MigrationAdvisoryModel into canonical, immutable, versioned, and checksummed
EnterpriseIntelligenceModel documents.
"""

from akaal.intelligence.api.enterprise_intelligence_platform import EnterpriseIntelligencePlatform
from akaal.intelligence.engine.enterprise_intelligence_engine import EnterpriseIntelligenceEngine

__all__ = [
    "EnterpriseIntelligencePlatform",
    "EnterpriseIntelligenceEngine",
]
__version__ = "1.0.0"
