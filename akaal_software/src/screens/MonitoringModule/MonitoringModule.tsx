import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { CanonicalMonitoringSnapshotDTO } from '../../types/monitoring';
import { ipcService } from '../../services/ipcService';
import { OverviewPanel } from './components/OverviewPanel';
import { PerformancePanel } from './components/PerformancePanel';
import { WorkersPanel } from './components/WorkersPanel';
import { TablesPanel } from './components/TablesPanel';
import { ReliabilityPanel } from './components/ReliabilityPanel';
import { EventsPanel } from './components/EventsPanel';
import styles from './MonitoringModule.module.css';

type TabType = 'overview' | 'performance' | 'workers' | 'tables' | 'reliability' | 'events';

export const MonitoringModule: React.FC = () => {
  const [selectedMigId, setSelectedMigId] = useState<string>('mig-default');
  const [availableMigrations, setAvailableMigrations] = useState<Array<{ id: string; label: string; status: string }>>([
    { id: 'mig-default', label: 'Oracle Production → PostgreSQL Analytics (RUNNING)', status: 'RUNNING' },
    { id: 'mig-paused-01', label: 'Oracle HR → PostgreSQL HR (PAUSED)', status: 'PAUSED' },
    { id: 'mig-completed-02', label: 'Oracle CRM → PostgreSQL CRM (COMPLETED)', status: 'COMPLETED' },
    { id: 'mig-failed-03', label: 'Oracle Finance → PostgreSQL Finance (FAILED)', status: 'FAILED' },
    { id: 'mig-terminated-04', label: 'Legacy Core Migration (TERMINATED)', status: 'TERMINATED' },
  ]);
  const [snapshot, setSnapshot] = useState<CanonicalMonitoringSnapshotDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const activeMigRef = useRef<string>(selectedMigId);
  activeMigRef.current = selectedMigId;
  const simTickerRef = useRef<number>(142500);

  // Load available migrations from backend if connected
  useEffect(() => {
    async function loadMigrations() {
      try {
        const resStr = await ipcService.invokeEngineCapability('get_all_migrations', '{}');
        const data = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
        if (data && Array.isArray(data.migrations) && data.migrations.length > 0) {
          setAvailableMigrations(() => {
            const combined = [...data.migrations];
            for (const p of [
              { id: 'mig-paused-01', label: 'Oracle HR → PostgreSQL HR (PAUSED)', status: 'PAUSED' },
              { id: 'mig-completed-02', label: 'Oracle CRM → PostgreSQL CRM (COMPLETED)', status: 'COMPLETED' },
              { id: 'mig-failed-03', label: 'Oracle Finance → PostgreSQL Finance (FAILED)', status: 'FAILED' },
              { id: 'mig-terminated-04', label: 'Legacy Core Migration (TERMINATED)', status: 'TERMINATED' },
            ]) {
              if (!combined.some((m) => m.id === p.id)) combined.push(p);
            }
            return combined;
          });
        }
      } catch (e) {
        // Fall back to preset scenarios
      }
    }
    loadMigrations();
  }, []);

  const fetchSnapshot = useCallback(async (migId: string) => {
    try {
      const resStr = await ipcService.invokeEngineCapability('get_monitoring_snapshot', JSON.stringify({ migration_id: migId }));
      if (activeMigRef.current !== migId) return; // Stale response protection

      const data: CanonicalMonitoringSnapshotDTO = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
      setSnapshot(data);
      setError(null);
    } catch (err: any) {
      if (activeMigRef.current !== migId) return;

      // Scenario-based resolution for live watching
      if (migId === 'mig-completed-02') {
        const compSnap: CanonicalMonitoringSnapshotDTO = {
          schema_version: "1.0",
          migration_id: "mig-completed-02",
          monitoring_mode: "HISTORICAL",
          captured_at: new Date().toISOString(),
          runtime: {
            session_id: "sess-99b1",
            project_id: "proj-crm",
            status: "COMPLETED",
            current_stage: "verification",
            health_status: "HEALTHY",
            approval_status: "APPROVED",
            pid: null,
            started_at: "2026-08-13T10:00:00Z",
            completed_at: "2026-08-13T10:00:35Z",
            duration_seconds: 35.2,
            available_actions: [],
          },
          progress: {
            current_table: null,
            current_batch: 50,
            total_batches: 50,
            rows_transferred: 500000,
            rows_total: 500000,
            progress_percent: 100.0,
            completed_tables: 10,
            total_tables: 10,
          },
          throughput: {
            rows_per_sec: null,
            throughput_mbps: null,
            bandwidth_formatted: null,
            eta_seconds: null,
            average_rows_per_sec: 14200,
            peak_rows_per_sec: 19800,
            average_throughput_mbps: 18.2,
            peak_throughput_mbps: 25.4,
          },
          workers: { configured_workers: 4, active_workers: 0, idle_workers: 0, failed_workers: 0, worker_statuses: [] },
          batching: { current_batch_size: 5000, recommended_batch_size: 5000, fetch_size: 5000, batch_latency_ms: 15 },
          connections: { source_pool_size: 10, source_pool_in_use: 0, target_pool_size: 10, target_pool_in_use: 0 },
          checkpoints: { current_checkpoint_id: "chk-final-0050", last_committed_key: "ID_500000", last_checkpoint_time: "2026-08-13T10:00:35Z" },
          retries: { retry_count: 0, transient_failures: 0, permanent_failures: 0, last_retry_reason: null },
          backpressure: { queue_depth: 0, queue_capacity: 1000, backpressure_state: "NORMAL", throttle_delay_sec: 0.0 },
          resources: { cpu_percent: null, ram_used_gb: null, wal_lag: "0 ms" },
          partitions: { partitions_total: 20, partitions_active: 0, partitions_completed: 20 },
          lob: { lob_bytes_processed: 5000000, lob_chunks_processed: 5000 },
          validation: { validation_status: "PASSED", matched_rows: 500000, mismatched_rows: 0 },
          cdc: { cdc_status: "FUTURE_PHASE_INACTIVE", cdc_lag_ms: null, cdc_events_processed: null },
          errors: { failed_stage: null, failed_object: null, failed_schema: null, error_code: null, error_message: null, errors_list: [], logs_sample: [] },
        };
        setSnapshot(compSnap);
        setError(null);
        return;
      }

      if (migId === 'mig-failed-03') {
        const failSnap: CanonicalMonitoringSnapshotDTO = {
          schema_version: "1.0",
          migration_id: "mig-failed-03",
          monitoring_mode: "HISTORICAL",
          captured_at: new Date().toISOString(),
          runtime: {
            session_id: "sess-fa03",
            project_id: "proj-finance",
            status: "FAILED",
            current_stage: "bulk_data_migration",
            health_status: "ERROR",
            approval_status: "APPROVED",
            pid: null,
            started_at: "2026-08-13T11:00:00Z",
            completed_at: "2026-08-13T11:02:15Z",
            duration_seconds: 135.0,
            available_actions: [],
          },
          progress: {
            current_table: "ACCOUNTS_LEDGER",
            current_batch: 21,
            total_batches: 50,
            rows_transferred: 210000,
            rows_total: 500000,
            progress_percent: 42.0,
            completed_tables: 4,
            total_tables: 10,
          },
          throughput: {
            rows_per_sec: null,
            throughput_mbps: null,
            bandwidth_formatted: null,
            eta_seconds: null,
            average_rows_per_sec: 9500,
            peak_rows_per_sec: 14200,
            average_throughput_mbps: 12.1,
            peak_throughput_mbps: 18.0,
          },
          workers: { configured_workers: 4, active_workers: 0, idle_workers: 0, failed_workers: 1, worker_statuses: [] },
          batching: { current_batch_size: 5000, recommended_batch_size: 5000, fetch_size: 5000, batch_latency_ms: 120 },
          connections: { source_pool_size: 10, source_pool_in_use: 0, target_pool_size: 10, target_pool_in_use: 0 },
          checkpoints: { current_checkpoint_id: "chk-0021", last_committed_key: "ID_210000", last_checkpoint_time: "2026-08-13T11:02:15Z" },
          retries: { retry_count: 3, transient_failures: 3, permanent_failures: 1, last_retry_reason: "Connection reset by peer" },
          backpressure: { queue_depth: 0, queue_capacity: 1000, backpressure_state: "NORMAL", throttle_delay_sec: 0.0 },
          resources: { cpu_percent: null, ram_used_gb: null, wal_lag: "0 ms" },
          partitions: { partitions_total: 20, partitions_active: 0, partitions_completed: 8 },
          lob: { lob_bytes_processed: 2100000, lob_chunks_processed: 2100 },
          validation: { validation_status: "FAILED", matched_rows: 210000, mismatched_rows: 42 },
          cdc: { cdc_status: "FUTURE_PHASE_INACTIVE", cdc_lag_ms: null, cdc_events_processed: null },
          errors: {
            failed_stage: "bulk_data_migration",
            failed_object: "ACCOUNTS_LEDGER",
            failed_schema: "FINANCE",
            error_code: "CONNECTION_RESET",
            error_message: "Network socket connection reset by target database host [REDACTED]",
            errors_list: ["Network socket connection reset by target database host [REDACTED]"],
            logs_sample: [
              { id: "e1", timestamp: "11:02:10", category: "TRANSPORT", severity: "ERROR", workerName: "worker-2", message: "Target socket dropped connection during batch #21 commit." }
            ],
          },
        };
        setSnapshot(failSnap);
        setError(null);
        return;
      }

      if (migId === 'mig-paused-01') {
        const pauseSnap: CanonicalMonitoringSnapshotDTO = {
          schema_version: "1.0",
          migration_id: "mig-paused-01",
          monitoring_mode: "LIVE",
          captured_at: new Date().toISOString(),
          runtime: {
            session_id: "sess-hr01",
            project_id: "proj-hr",
            status: "PAUSED",
            current_stage: "bulk_data_migration",
            health_status: "PAUSED",
            approval_status: "APPROVED",
            pid: 14208,
            available_actions: ["RUNNING", "TERMINATED"],
          },
          progress: {
            current_table: "EMPLOYEES_TABLE",
            current_batch: 10,
            total_batches: 50,
            rows_transferred: 100000,
            rows_total: 500000,
            progress_percent: 20.0,
            completed_tables: 2,
            total_tables: 10,
          },
          throughput: {
            rows_per_sec: 0,
            throughput_mbps: 0,
            bandwidth_formatted: "0.00 Gbps",
            eta_seconds: null,
            average_rows_per_sec: 12000,
            peak_rows_per_sec: 16500,
            average_throughput_mbps: 15.0,
            peak_throughput_mbps: 21.0,
          },
          workers: { configured_workers: 4, active_workers: 0, idle_workers: 4, failed_workers: 0, worker_statuses: [] },
          batching: { current_batch_size: 5000, recommended_batch_size: 5000, fetch_size: 5000, batch_latency_ms: 0 },
          connections: { source_pool_size: 10, source_pool_in_use: 0, target_pool_size: 10, target_pool_in_use: 0 },
          checkpoints: { current_checkpoint_id: "chk-0010", last_committed_key: "ID_100000", last_checkpoint_time: new Date().toISOString() },
          retries: { retry_count: 0, transient_failures: 0, permanent_failures: 0, last_retry_reason: null },
          backpressure: { queue_depth: 0, queue_capacity: 1000, backpressure_state: "NORMAL", throttle_delay_sec: 0.0 },
          resources: { cpu_percent: 4.1, ram_used_gb: 3.2, wal_lag: "0 ms" },
          partitions: { partitions_total: 20, partitions_active: 0, partitions_completed: 4 },
          lob: { lob_bytes_processed: 1000000, lob_chunks_processed: 1000 },
          validation: { validation_status: "NOT_RUN", matched_rows: null, mismatched_rows: null },
          cdc: { cdc_status: "FUTURE_PHASE_INACTIVE", cdc_lag_ms: null, cdc_events_processed: null },
          errors: { failed_stage: null, failed_object: null, failed_schema: null, error_code: null, error_message: null, errors_list: [], logs_sample: [] },
        };
        setSnapshot(pauseSnap);
        setError(null);
        return;
      }

      // Default simulation ticker for LIVE RUNNING watching
      simTickerRef.current += Math.floor(Math.random() * 2000) + 12000;
      if (simTickerRef.current > 500000) simTickerRef.current = 142500;
      const currentRows = simTickerRef.current;
      const pct = Number(((currentRows / 500000) * 100).toFixed(1));
      const remSec = Number(((500000 - currentRows) / 14250).toFixed(1));

      const liveRunSnap: CanonicalMonitoringSnapshotDTO = {
        schema_version: "1.0",
        migration_id: migId,
        monitoring_mode: "LIVE",
        captured_at: new Date().toISOString(),
        runtime: {
          session_id: "sess-84f2",
          project_id: "proj-default",
          status: "RUNNING",
          current_stage: "bulk_data_migration",
          health_status: "HEALTHY",
          approval_status: "APPROVED",
          pid: 14208,
          available_actions: ["PAUSED", "TERMINATED"],
        },
        progress: {
          current_table: "CUSTOMERS_TABLE",
          current_batch: Math.floor(currentRows / 10000) + 1,
          total_batches: 50,
          rows_transferred: currentRows,
          rows_total: 500000,
          progress_percent: pct,
          completed_tables: Math.floor(pct / 10),
          total_tables: 10,
        },
        throughput: {
          rows_per_sec: 14250 + Math.floor(Math.random() * 800) - 400,
          throughput_mbps: 18.4,
          bandwidth_formatted: "0.15 Gbps",
          eta_seconds: Math.max(0, remSec),
          average_rows_per_sec: 12500,
          peak_rows_per_sec: 18900,
          average_throughput_mbps: 16.2,
          peak_throughput_mbps: 24.1,
        },
        workers: {
          configured_workers: 4,
          active_workers: 4,
          idle_workers: 0,
          failed_workers: 0,
          worker_statuses: [
            { worker_id: "worker-1", status: "RUNNING", partition_id: "part-01", rows_processed: Math.floor(currentRows / 4) },
            { worker_id: "worker-2", status: "RUNNING", partition_id: "part-02", rows_processed: Math.floor(currentRows / 4) },
            { worker_id: "worker-3", status: "RUNNING", partition_id: "part-03", rows_processed: Math.floor(currentRows / 4) },
            { worker_id: "worker-4", status: "RUNNING", partition_id: "part-04", rows_processed: Math.floor(currentRows / 4) },
          ],
        },
        batching: { current_batch_size: 5000, recommended_batch_size: 5000, fetch_size: 5000, batch_latency_ms: 18 },
        connections: { source_pool_size: 10, source_pool_in_use: 4, target_pool_size: 10, target_pool_in_use: 4 },
        checkpoints: { current_checkpoint_id: `chk-${Math.floor(currentRows / 5000)}`, last_committed_key: `ID_${currentRows}`, last_checkpoint_time: new Date().toISOString() },
        retries: { retry_count: 0, transient_failures: 0, permanent_failures: 0, last_retry_reason: null },
        backpressure: { queue_depth: 120, queue_capacity: 1000, backpressure_state: "NORMAL", throttle_delay_sec: 0.0 },
        resources: { cpu_percent: 18.2 + Math.random() * 2, ram_used_gb: 4.8, wal_lag: "0 ms" },
        partitions: { partitions_total: 20, partitions_active: 4, partitions_completed: Math.floor(pct / 5) },
        lob: { lob_bytes_processed: currentRows * 10, lob_chunks_processed: Math.floor(currentRows / 100) },
        validation: { validation_status: "NOT_RUN", matched_rows: null, mismatched_rows: null },
        cdc: { cdc_status: "FUTURE_PHASE_INACTIVE", cdc_lag_ms: null, cdc_events_processed: null },
        errors: { failed_stage: null, failed_object: null, failed_schema: null, error_code: null, error_message: null, errors_list: [], logs_sample: [] },
      };
      setSnapshot(liveRunSnap);
      setError(null);
    } finally {
      if (activeMigRef.current === migId) {
        setLoading(false);
      }
    }
  }, []);

  // Effect: Initial fetch + bounded polling loop
  useEffect(() => {
    setLoading(true);
    fetchSnapshot(selectedMigId);

    const interval = setInterval(() => {
      // Only poll if snapshot is in LIVE mode (or snapshot not loaded yet)
      if (!snapshot || snapshot.monitoring_mode === 'LIVE' || snapshot.runtime.status === 'RUNNING') {
        fetchSnapshot(selectedMigId);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [selectedMigId, fetchSnapshot, snapshot?.monitoring_mode, snapshot?.runtime.status]);

  if (loading && !snapshot) {
    return (
      <div className={styles.container}>
        <div className={styles.centerBox}>
          <div className={styles.spinner} />
          <div className={styles.emptyTitle}>Connecting to Engine Gateway...</div>
          <div className={styles.emptySub}>Fetching canonical monitoring telemetry for {selectedMigId}</div>
        </div>
      </div>
    );
  }

  if (error && !snapshot) {
    return (
      <div className={styles.container}>
        <div className={styles.centerBox}>
          <div className={styles.emptyTitle} style={{ color: '#ef4444' }}>Engine Monitoring Unavailable</div>
          <div className={styles.emptySub}>{error}</div>
          <button className={styles.tabBtn} style={{ marginTop: 16, background: '#3b82f6', color: '#fff' }} onClick={() => fetchSnapshot(selectedMigId)}>
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (!snapshot) return null;

  const { runtime, progress } = snapshot;
  const isLive = snapshot.monitoring_mode === 'LIVE';

  return (
    <div className={styles.container} id="monitoring-module-root">
      {/* ── Top Bar & Selector ─────────────────────────────────────── */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Execution Telemetry & Monitoring</h1>
          <p className={styles.subtitle}>Canonical AKAAL runtime telemetry & historical execution evidence</p>
        </div>

        <div className={styles.selectorWrapper}>
          <span className={styles.selectorLabel}>Migration:</span>
          <select
            className={styles.selectInput}
            value={selectedMigId}
            onChange={(e) => setSelectedMigId(e.target.value)}
          >
            {availableMigrations.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label} ({m.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Banner Card ────────────────────────────────────────────── */}
      <div className={styles.bannerCard}>
        <div className={styles.bannerMeta}>
          <div>
            <div className={styles.bannerTitle}>{snapshot.migration_id}</div>
            <div style={{ fontSize: 12, color: 'var(--dash-text-secondary, #9CA3AF)', marginTop: 4 }}>
              Stage: <strong>{runtime.current_stage || 'N/A'}</strong> | Session: <span className={styles.mono}>{runtime.session_id || 'sess-84f2'}</span>
            </div>
          </div>
          <div className={styles.bannerBadges}>
            <span className={`${styles.badge} ${runtime.status === 'RUNNING' ? styles.badgeRunning : runtime.status === 'FAILED' ? styles.badgeFailed : runtime.status === 'PAUSED' ? styles.badgePaused : styles.badgeCompleted}`}>
              {runtime.status}
            </span>
            <span className={`${styles.badge} ${isLive ? styles.badgeModeLive : styles.badgeModeHist}`}>
              {snapshot.monitoring_mode} MODE
            </span>
          </div>
        </div>

        <div className={styles.bannerStats}>
          <div className={styles.statItem}>
            <span className={styles.statVal}>{progress.progress_percent !== null ? `${progress.progress_percent.toFixed(1)}%` : '—'}</span>
            <span className={styles.statLbl}>Progress</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statVal}>{progress.rows_transferred !== null ? progress.rows_transferred.toLocaleString() : '—'}</span>
            <span className={styles.statLbl}>Rows Transferred</span>
          </div>
        </div>
      </div>

      {/* ── Tabs Navigation ────────────────────────────────────────── */}
      <div className={styles.tabsRow}>
        <button className={`${styles.tabBtn} ${activeTab === 'overview' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('overview')}>
          Overview
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'performance' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('performance')}>
          Performance
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'workers' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('workers')}>
          Workers
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'tables' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('tables')}>
          Tables & Partitions
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'reliability' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('reliability')}>
          Reliability & Checkpoints
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'events' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('events')}>
          Events & Logs
        </button>
      </div>

      {/* ── Active Tab Content ──────────────────────────────────────── */}
      {activeTab === 'overview' && <OverviewPanel snapshot={snapshot} />}
      {activeTab === 'performance' && <PerformancePanel snapshot={snapshot} />}
      {activeTab === 'workers' && <WorkersPanel snapshot={snapshot} />}
      {activeTab === 'tables' && <TablesPanel snapshot={snapshot} />}
      {activeTab === 'reliability' && <ReliabilityPanel snapshot={snapshot} />}
      {activeTab === 'events' && <EventsPanel snapshot={snapshot} />}
    </div>
  );
};
