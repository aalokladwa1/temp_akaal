"""
Akaal Coverage Tracer — Execution Collector
==========================================
Collects line execution data by tracing Python bytecode execution during test runs.
Supports multi-threaded execution collection and path normalization.
"""

import os
import sys
import trace
from typing import Dict, Set


class CoverageCollector:
    """Execution line collector tracking executed statement line numbers."""

    def __init__(self, target_directory: str) -> None:
        self.target_directory = os.path.abspath(target_directory)
        self.executed_lines: Dict[str, Set[int]] = {}

    def run_target(self, target_function, *args, **kwargs) -> Dict[str, Set[int]]:
        """Run target function or command under bytecode line tracer."""
        tracer = trace.Trace(count=1, trace=0)
        
        # Execute target function under tracer
        tracer.runctx("target_function(*args, **kwargs)", globals(), locals())
        results = tracer.results()

        executed: Dict[str, Set[int]] = {}
        for (filename, lineno), count in results.counts.items():
            if count > 0:
                abs_path = os.path.abspath(filename)
                if abs_path.startswith(self.target_directory):
                    if abs_path not in executed:
                        executed[abs_path] = set()
                    executed[abs_path].add(lineno)

        self.executed_lines = executed
        return executed
