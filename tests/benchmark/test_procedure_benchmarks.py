"""
Akaal — Stored Procedure Migration Engine Performance Benchmarks
================================================================
Benchmarks compiler execution stages and reports timing statistics.
"""

import unittest
import time
import sys
import os
import platform
from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.service import ConversionRequest
from akaal.core.conversion.api.models import ConversionContext, DbVersion, ConversionPolicy
from akaal.core.conversion.internal.bootstrap import Bootstrap

class TestProcedureBenchmarks(unittest.TestCase):
    def setUp(self):
        self.service = Bootstrap.initialize_procedure_service()
        self.ctx = ConversionContext(
            source_vendor="oracle",
            source_version=DbVersion.parse("19c"),
            target_vendor="postgres",
            target_version=DbVersion.parse("15"),
            policy=ConversionPolicy()
        )
        self.source_ddl = """
        CREATE OR REPLACE PROCEDURE process_payments(
            p_batch_id IN NUMBER,
            p_status OUT VARCHAR2
        ) IS
            v_counter NUMBER := 0;
            v_total NUMBER(12,2) := 0;
        BEGIN
            FOR i IN 1..100 LOOP
                v_counter := v_counter + 1;
                v_total := v_total + 1.5;
            END LOOP;
            p_status := 'COMPLETED';
        END;
        """

    def test_performance_metrics(self):
        """Runs warm-up repetitions, measures timing, and logs p95/p99 performance statistics."""
        warm_ups = 10
        repetitions = 100
        
        # Warm up
        for _ in range(warm_ups):
            req = ConversionRequest(
                source_ddl=self.source_ddl,
                source_dialect=SystemType.ORACLE,
                target_dialect=SystemType.POSTGRESQL,
                context=self.ctx
            )
            _ = self.service.convert_procedure(req)

        # Benchmarking runs
        durations = []
        for _ in range(repetitions):
            req = ConversionRequest(
                source_ddl=self.source_ddl,
                source_dialect=SystemType.ORACLE,
                target_dialect=SystemType.POSTGRESQL,
                context=self.ctx
            )
            start = time.perf_counter()
            _ = self.service.convert_procedure(req)
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000.0)  # ms

        durations.sort()
        mean_dur = sum(durations) / len(durations)
        p95_dur = durations[int(len(durations) * 0.95)]
        p99_dur = durations[int(len(durations) * 0.99)]

        print("\n" + "=" * 50)
        print("  AKAAL PROCEDURE ENGINE BENCHMARK")
        print("=" * 50)
        print(f"  OS:              {platform.system()} {platform.release()}")
        print(f"  Python Version:  {sys.version.split()[0]}")
        print(f"  Warm-ups:        {warm_ups}")
        print(f"  Repetitions:     {repetitions}")
        print(f"  Mean Duration:   {mean_dur:.3f} ms")
        print(f"  p95 Duration:    {p95_dur:.3f} ms")
        print(f"  p99 Duration:    {p99_dur:.3f} ms")
        print("=" * 50)
