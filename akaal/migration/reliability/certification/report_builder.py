from typing import List
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic

class CertificationReportBuilder:
    """Computes final compliance metrics and letters grades."""
    def compute_grade(self, diagnostics: List[ReliabilityDiagnostic]) -> str:
        errors = sum(1 for d in diagnostics if d.severity == "ERROR")
        warnings = sum(1 for d in diagnostics if d.severity == "WARNING")
        
        if errors > 0:
            return "F"
        elif warnings > 2:
            return "C"
        elif warnings > 0:
            return "B"
        return "A"
