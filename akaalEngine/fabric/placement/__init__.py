"""
akaalEngine.fabric.placement
================================
P7B.13-17 -- Distributed placement intelligence (P7B Group 2, Campaign C).

CAPABLE != AUTHORIZED != RESIDENCY-COMPLIANT != OPTIMAL. This package's modules are
deliberately layered in that exact order and every filter is fail-closed: a candidate
rejected by an earlier stage is never resurrected by a later one (see
akaalEngine.fabric.placement.engine.evaluate_placement for the enforced ordering).
"""
