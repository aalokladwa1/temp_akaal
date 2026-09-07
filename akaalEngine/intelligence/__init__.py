"""akaalEngine.intelligence
=========================
P7C.1 -- Intelligence Kernel, Artifact Identity & Contracts.

Single canonical entrypoint and façade package for AKAAL's AI-native intelligence
layer, following the same "Authority façade" convention already established by
Authority #7 (akaalEngine.telemetry), Authority #11 (akaalEngine.validation), and
Authority #12 (akaalEngine.evidence).

Permanent architectural law (see project progress.md P7C authorization):
Intelligence THINKS, ANALYZES, EXPLAINS, PREDICTS, OPTIMIZES and PROPOSES.
Existing AKAAL authorities DECIDE what is valid, authorized, and what executes.
This package never grants its own authorization, never writes Evidence/Validation
truth, and never mutates canonical migration state directly.
"""

from akaalEngine.intelligence.api import IntelligenceKernel

__all__ = ["IntelligenceKernel"]
