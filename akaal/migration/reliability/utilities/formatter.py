from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic

def format_diagnostic(diag: ReliabilityDiagnostic) -> str:
    """Standardizes message strings for human reviews."""
    return f"[{diag.severity}] ({diag.category}) {diag.message} | Suggestion: {diag.recommendation}"
