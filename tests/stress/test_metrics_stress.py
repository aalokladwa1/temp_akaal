# -*- coding: utf-8 -*-
import unittest
import threading
import time
import random
from akaal.metrics.registry import MetricsRegistry

class TestMetricsStress(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.registry = MetricsRegistry()
        self.stop_signal = threading.Event()

    def tearDown(self):
        self.stop_signal.set()

    def run_worker(self):
        """Worker thread performing rapid updates on multiple metric types under the same keys."""
        # Mix of shared and worker-specific labels
        labels_shared = {"env": "prod", "task": "gb_migration"}
        counter = self.registry.counter("stress.counter", labels_shared)
        gauge = self.registry.gauge("stress.gauge", labels_shared)
        histogram = self.registry.histogram("stress.histogram", labels_shared)
        
        while not self.stop_signal.is_set():
            # Update metrics
            counter.increment(1)
            gauge.set(random.random())
            histogram.record(random.randint(1, 100))
            
            # Rate metrics
            self.registry.rate("stress.rate", labels_shared).observe(
                count=random.randint(100, 1000),
                elapsed_seconds=max(0.1, random.random())
            )
            
            # Timer context manager
            with self.registry.timer("stress.timer", labels_shared):
                pass
            
            # Dynamic lookup checks (forces concurrent key discovery/get_or_create checks)
            self.registry.counter("stress.dynamic", {"id": str(random.randint(1, 10))}).increment()

    def run_snapshotter(self):
        """Background thread continuously requesting snapshots."""
        while not self.stop_signal.is_set():
            snap = self.registry.snapshot()
            self.assertIsNotNone(snap)
            self.assertTrue(len(snap.data) >= 0)
            time.sleep(0.01)

    def execute_concurrency_stress(self, thread_count: int, duration_seconds: float = 1.0):
        """Spawns thread_count workers + 1 snapshotter and runs for duration_seconds."""
        self.stop_signal.clear()
        
        workers = []
        for _ in range(thread_count):
            t = threading.Thread(target=self.run_worker)
            t.daemon = True
            workers.append(t)
            
        snapshot_thread = threading.Thread(target=self.run_snapshotter)
        snapshot_thread.daemon = True
        
        # Start threads
        for w in workers:
            w.start()
        snapshot_thread.start()
        
        # Run for specified duration
        time.sleep(duration_seconds)
        
        # Signal shutdown and join
        self.stop_signal.set()
        for w in workers:
            w.join(timeout=2.0)
        snapshot_thread.join(timeout=2.0)
        
        # Verify basic post-stress consistency
        snap = self.registry.snapshot()
        self.assertIsNotNone(snap)

    # 1. 10 workers concurrency stress test
    def test_stress_concurrency_10_workers(self):
        self.execute_concurrency_stress(thread_count=10, duration_seconds=1.0)

    # 2. 25 workers concurrency stress test
    def test_stress_concurrency_25_workers(self):
        self.execute_concurrency_stress(thread_count=25, duration_seconds=1.0)

    # 3. 50 workers concurrency stress test
    def test_stress_concurrency_50_workers(self):
        self.execute_concurrency_stress(thread_count=50, duration_seconds=1.0)

    # 4. 100 workers concurrency stress test
    def test_stress_concurrency_100_workers(self):
        self.execute_concurrency_stress(thread_count=100, duration_seconds=1.0)


if __name__ == "__main__":
    unittest.main()
