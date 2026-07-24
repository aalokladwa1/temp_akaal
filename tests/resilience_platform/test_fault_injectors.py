"""Tests: Resilience Platform — Fault Injectors (Capabilities 1-10)."""

import pytest
from akaal.resilience_eng.injection.chaos_engine import (
    ChaosTestingEngine, RecoverySimulationEngine, NetworkFaultInjector,
    DatabaseFailureInjector, WorkerFailureInjector, StorageFaultSimulator,
    CPUMemoryStressSimulator, LatencyInjector, DependencyFailureSimulator,
)


class TestFaultInjectors:
    def test_chaos_testing_engine(self):
        eng = ChaosTestingEngine()
        res = eng.inject_chaos("database_primary")
        assert res["status"] == "CHAOS_INJECTED"
        assert res["target"] == "database_primary"

    def test_recovery_simulation_engine(self):
        eng = RecoverySimulationEngine()
        res = eng.simulate_recovery("database_primary")
        assert res["status"] == "RECOVERY_SIMULATED"

    def test_network_fault_injector(self):
        inj = NetworkFaultInjector()
        res = inj.inject_packet_loss(15.0)
        assert res["status"] == "NETWORK_FAULT_INJECTED"
        assert res["packet_loss_pct"] == 15.0

    def test_database_failure_injector(self):
        inj = DatabaseFailureInjector()
        res = inj.inject_connection_failure("main_db")
        assert res["status"] == "DB_FAILURE_INJECTED"
        assert res["database"] == "main_db"

    def test_worker_failure_injector(self):
        inj = WorkerFailureInjector()
        res = inj.simulate_worker_crash("worker_01")
        assert res["status"] == "WORKER_CRASHED"

    def test_storage_fault_simulator(self):
        sim = StorageFaultSimulator()
        res = sim.simulate_storage_latency(300.0)
        assert res["status"] == "STORAGE_FAULT_SIMULATED"
        assert res["latency_ms"] == 300.0

    def test_cpu_memory_stress_simulator(self):
        sim = CPUMemoryStressSimulator()
        res = sim.apply_stress(70.0, 2048.0)
        assert res["status"] == "STRESS_APPLIED"
        assert res["cpu_pct"] == 70.0

    def test_latency_injector(self):
        inj = LatencyInjector()
        res = inj.inject_latency(100.0)
        assert res["status"] == "LATENCY_INJECTED"
        assert res["delay_ms"] == 100.0

    def test_dependency_failure_simulator(self):
        sim = DependencyFailureSimulator()
        res = sim.simulate_dependency_outage("auth_service")
        assert res["status"] == "DEPENDENCY_OUTAGE_SIMULATED"
        assert res["dependency"] == "auth_service"
