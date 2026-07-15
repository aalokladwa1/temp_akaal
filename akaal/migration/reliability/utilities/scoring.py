from typing import List
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.models.risk import RiskAssessment, RiskLevel

def calculate_risk_assessment(diagnostics: List[ReliabilityDiagnostic], initial_confidence: float = 1.0) -> RiskAssessment:
    """Aggregates diagnostic levels to formulate a structured RiskAssessment."""
    errors = sum(1 for d in diagnostics if d.severity == "ERROR")
    warnings = sum(1 for d in diagnostics if d.severity == "WARNING")
    
    # Calculate confidence mapping
    confidence = max(0.0, initial_confidence - (errors * 0.25) - (warnings * 0.05))
    risk_score = min(10.0, (errors * 3.5) + (warnings * 1.2))
    
    if errors > 0 or risk_score >= 8.0:
        level = RiskLevel.CRITICAL
    elif risk_score >= 5.0:
        level = RiskLevel.HIGH
    elif risk_score >= 2.5:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
        
    explanation = f"Assessment matches {errors} critical errors and {warnings} warning events."
    recommendations = tuple(set(d.recommendation for d in diagnostics if d.recommendation))
    
    return RiskAssessment(
        confidence_score=confidence,
        risk_score=risk_score,
        risk_level=level,
        explanation=explanation,
        recommendations=recommendations
    )
