import time
from abc import ABC, abstractmethod
from typing import List, Any
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic

class BaseReliabilityEngine(ABC):
    """
    Common base engine class handling execution timing, hook lifecycles,
    metrics recording, error isolation, and diagnostics gathering.
    """
    def __init__(self, name: str) -> None:
        self.name = name

    def execute_engine(self, context: ReliabilityContext, before_hook: Any, after_hook: Any) -> Any:
        """Runs the lifecycle sequence for the engine with standard error handling."""
        start_time = time.perf_counter()
        before_hook(context)
        
        engine_diagnostics: List[ReliabilityDiagnostic] = []
        try:
            report = self._run(context, engine_diagnostics)
        except Exception as e:
            # Capture error details cleanly
            from akaal.migration.reliability.utilities.diagnostics import create_error
            err_diag = create_error(
                message=f"Engine '{self.name}' execution crash: {str(e)}",
                category=self.name.upper(),
                recommendation="Inspect execution snapshot variables and input schemas."
            )
            context.diagnostics.append(err_diag)
            raise e
            
        # Merge local diagnostics
        for diag in engine_diagnostics:
            context.diagnostics.append(diag)
            
        after_hook(context, report)
        return report

    @abstractmethod
    def _run(self, context: ReliabilityContext, diagnostics: List[ReliabilityDiagnostic]) -> Any:
        """Internals executed by the subclasses."""
        pass
