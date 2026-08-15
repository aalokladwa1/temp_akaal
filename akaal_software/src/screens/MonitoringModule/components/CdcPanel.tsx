import React, { useState } from 'react';
import type { CdcMonitoringSnapshotDTO } from '../../../types/monitoring';
import { ipcService } from '../../../services/ipcService';
import styles from '../MonitoringModule.module.css';

interface CdcPanelProps {
  cdcSnapshot: CdcMonitoringSnapshotDTO | null;
  migrationId: string;
  onRefresh: () => void;
}

type CdcSubTab = 'overview' | 'pipeline' | 'workers' | 'ordering' | 'schema' | 'conflicts' | 'recovery' | 'history';

export const CdcPanel: React.FC<CdcPanelProps> = ({ cdcSnapshot, migrationId, onRefresh }) => {
  const [subTab, setSubTab] = useState<CdcSubTab>('overview');
  const [selectedConflictId, setSelectedConflictId] = useState<string | null>(null);
  const [manualWinner, setManualWinner] = useState<'SOURCE_A' | 'SOURCE_B'>('SOURCE_A');
  const [governanceReason, setGovernanceReason] = useState<string>('');
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  if (!cdcSnapshot) {
    return (
      <div className={styles.centerBox}>
        <div className={styles.spinner} />
        <div className={styles.emptyTitle}>Connecting to CDC Monitoring Engine...</div>
        <div className={styles.emptySub}>Fetching canonical CDC operational telemetry for {migrationId}</div>
      </div>
    );
  }

  const { health_strip, pipeline, overview, backlog_and_backpressure, workers_and_partitions, ordering_and_causality, schema_transitions, conflicts_and_topology, recovery_and_checkpoints, cutover_checklist, operational_events } = cdcSnapshot;
  const isHistorical = cdcSnapshot.monitoring_mode === 'HISTORICAL';

  const handlePauseCDC = async () => {
    setActionMsg(null);
    setActionError(null);
    try {
      if (cdcSnapshot.session_mode === 'BIDIRECTIONAL') {
        const topId = conflicts_and_topology.topology_id || `top-${migrationId}`;
        await ipcService.invokeEngineCapability('pause_cdc_bidirectional_topology', JSON.stringify({ topology_id: topId }));
      } else {
        await ipcService.invokeEngineCapability('pause_cdc_session', JSON.stringify({ cdc_session_id: cdcSnapshot.cdc_session_id }));
      }
      setActionMsg('CDC Session Paused successfully.');
      onRefresh();
    } catch (e: any) {
      setActionError(e?.message || String(e));
    }
  };

  const handleResumeCDC = async () => {
    setActionMsg(null);
    setActionError(null);
    try {
      if (cdcSnapshot.session_mode === 'BIDIRECTIONAL') {
        const topId = conflicts_and_topology.topology_id || `top-${migrationId}`;
        await ipcService.invokeEngineCapability('resume_cdc_bidirectional_topology', JSON.stringify({ topology_id: topId }));
      } else {
        await ipcService.invokeEngineCapability('resume_cdc_session', JSON.stringify({ cdc_session_id: cdcSnapshot.cdc_session_id }));
      }
      setActionMsg('CDC Session Resumed successfully.');
      onRefresh();
    } catch (e: any) {
      setActionError(e?.message || String(e));
    }
  };

  const handleResolveConflict = async (conflictId: string, policy: string) => {
    setActionMsg(null);
    setActionError(null);
    try {
      const topId = conflicts_and_topology.topology_id || `top-${migrationId}`;
      const payload: any = {
        topology_id: topId,
        conflict_id: conflictId,
        policy: policy,
        reason: governanceReason || 'Operator manual resolution via Monitoring UI',
      };
      if (policy === 'MANUAL_GOVERNANCE_REQUIRED') {
        payload.manual_winner = manualWinner;
      }
      const resStr = await ipcService.invokeEngineCapability('resolve_cdc_conflict', JSON.stringify(payload));
      const res = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
      if (res.status === 'RESOLVED') {
        setActionMsg(`Conflict '${conflictId}' resolved successfully via ${policy}.`);
        setSelectedConflictId(null);
        onRefresh();
      } else {
        setActionError(`Failed to resolve conflict: ${res.status}`);
      }
    } catch (e: any) {
      setActionError(e?.message || String(e));
    }
  };

  return (
    <div style={{ marginTop: 16 }}>
      {/* ── Action Banners ────────────────────────────────────────────── */}
      {isHistorical && (
        <div style={{ padding: '8px 16px', background: '#1e293b', border: '1px solid #334155', borderRadius: 8, marginBottom: 16, color: '#94a3b8', fontSize: 13 }}>
          🔒 <strong>HISTORICAL MODE</strong> — Viewing read-only CDC evidence for completed/historical session. Operational actions disabled.
        </div>
      )}
      {actionMsg && (
        <div style={{ padding: '8px 16px', background: '#064e3b', border: '1px solid #059669', borderRadius: 8, marginBottom: 16, color: '#34d399', fontSize: 13 }}>
          ✓ {actionMsg}
        </div>
      )}
      {actionError && (
        <div style={{ padding: '8px 16px', background: '#450a0a', border: '1px solid #dc2626', borderRadius: 8, marginBottom: 16, color: '#f87171', fontSize: 13 }}>
          ⚠️ {actionError}
        </div>
      )}

      {/* ── CDC Header Row ────────────────────────────────────────────── */}
      <div className={styles.bannerCard} style={{ marginBottom: 16 }}>
        <div className={styles.bannerMeta}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--dash-text-primary, #F9FAFB)' }}>
              CDC Monitoring — <span className={styles.mono}>{cdcSnapshot.migration_id}</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--dash-text-secondary, #9CA3AF)', marginTop: 4 }}>
              Source: <strong>{cdcSnapshot.source_engine}</strong> ({cdcSnapshot.source_database}) → Target: <strong>{cdcSnapshot.target_engine}</strong> ({cdcSnapshot.target_database}) | Session: <span className={styles.mono}>{cdcSnapshot.cdc_session_id}</span>
            </div>
          </div>
          <div className={styles.bannerBadges}>
            <span className={`${styles.badge} ${cdcSnapshot.session_mode === 'BIDIRECTIONAL' ? styles.badgeModeLive : styles.badgeModeHist}`}>
              {cdcSnapshot.session_mode}
            </span>
            <span className={`${styles.badge} ${cdcSnapshot.status === 'HEALTHY' ? styles.badgeRunning : cdcSnapshot.status === 'FAILED' ? styles.badgeFailed : styles.badgePaused}`}>
              {cdcSnapshot.status}
            </span>
          </div>
        </div>

        {!isHistorical && (
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button className={styles.primaryBtn} onClick={handlePauseCDC} disabled={cdcSnapshot.status === 'PAUSED'}>
              Pause CDC
            </button>
            <button className={styles.primaryBtn} onClick={handleResumeCDC} disabled={cdcSnapshot.status === 'HEALTHY'}>
              Resume CDC
            </button>
            <button className={styles.primaryBtn} style={{ background: '#374151' }} onClick={onRefresh}>
              Refresh Snapshot
            </button>
          </div>
        )}
      </div>

      {/* ── Top Operational Health Strip ──────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 16 }}>
        <div className={styles.card} style={{ padding: 12 }}>
          <div className={styles.statLbl}>CDC STATE</div>
          <div className={styles.statVal} style={{ fontSize: 16, color: health_strip.cdc_state === 'HEALTHY' ? '#10b981' : health_strip.cdc_state === 'FAILED' ? '#ef4444' : '#f59e0b' }}>
            {health_strip.cdc_state}
          </div>
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>Mode: {cdcSnapshot.session_mode}</div>
        </div>

        <div className={styles.card} style={{ padding: 12 }}>
          <div className={styles.statLbl}>SOURCE LAG</div>
          <div className={styles.statVal} style={{ fontSize: 16, color: health_strip.source_lag_sec > 5.0 ? '#f59e0b' : '#10b981' }}>
            {health_strip.source_lag_sec.toFixed(1)}s
          </div>
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{health_strip.source_lag_sec < 2.0 ? 'Real-time' : 'Catching up'}</div>
        </div>

        <div className={styles.card} style={{ padding: 12 }}>
          <div className={styles.statLbl}>BACKLOG</div>
          <div className={styles.statVal} style={{ fontSize: 16 }}>
            {health_strip.backlog_events.toLocaleString()}
          </div>
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{(health_strip.backlog_bytes / 1024).toFixed(0)} KB buffered</div>
        </div>

        <div className={styles.card} style={{ padding: 12 }}>
          <div className={styles.statLbl}>APPLY RATE</div>
          <div className={styles.statVal} style={{ fontSize: 16, color: '#3b82f6' }}>
            {health_strip.apply_rate_rows_per_sec > 0 ? `${(health_strip.apply_rate_rows_per_sec / 1000).toFixed(1)}k/s` : '0/s'}
          </div>
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{workers_and_partitions.active_workers || 4} active workers</div>
        </div>

        <div className={styles.card} style={{ padding: 12 }}>
          <div className={styles.statLbl}>CHECKPOINT</div>
          <div className={styles.statVal} style={{ fontSize: 14, fontFamily: 'monospace' }}>
            {health_strip.checkpoint_lsn}
          </div>
          <div style={{ fontSize: 11, color: '#10b981', marginTop: 2 }}>Contiguous Frontier</div>
        </div>

        <div className={styles.card} style={{ padding: 12 }}>
          <div className={styles.statLbl}>CONFLICTS</div>
          <div className={styles.statVal} style={{ fontSize: 16, color: health_strip.unresolved_conflicts_count > 0 ? '#ef4444' : '#10b981' }}>
            {health_strip.unresolved_conflicts_count}
          </div>
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{health_strip.quarantined_entities_count} quarantined</div>
        </div>
      </div>

      {/* ── Primary CDC Pipeline Visualization ────────────────────────── */}
      <div className={styles.card} style={{ padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
          CDC Pipeline Flow & Stage Status
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          {/* Stage 1: Capture */}
          <div style={{ flex: 1, padding: 10, background: '#1e293b', border: '1px solid #334155', borderRadius: 8, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>1. SOURCE CAPTURE</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#10b981', marginTop: 4 }}>{pipeline.source_capture.state}</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{pipeline.source_capture.rate_events_per_sec || 0} evt/s</div>
          </div>
          <div style={{ color: '#64748b', fontWeight: 700 }}>→</div>

          {/* Stage 2: Durable Buffer */}
          <div style={{ flex: 1, padding: 10, background: '#1e293b', border: '1px solid #334155', borderRadius: 8, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>2. DURABLE BUFFER</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: pipeline.durable_buffer.state === 'NORMAL' ? '#10b981' : '#f59e0b', marginTop: 4 }}>{pipeline.durable_buffer.state}</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{pipeline.durable_buffer.depth_events || 0} queued</div>
          </div>
          <div style={{ color: '#64748b', fontWeight: 700 }}>→</div>

          {/* Stage 3: Ordering DAG */}
          <div style={{ flex: 1, padding: 10, background: '#1e293b', border: '1px solid #334155', borderRadius: 8, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>3. ORDERING DAG</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: pipeline.ordering_dag.state === 'HEALTHY' ? '#10b981' : '#ef4444', marginTop: 4 }}>{pipeline.ordering_dag.state}</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{pipeline.ordering_dag.blocked_tx_count || 0} blocked</div>
          </div>
          <div style={{ color: '#64748b', fontWeight: 700 }}>→</div>

          {/* Stage 4: Partition Router */}
          <div style={{ flex: 1, padding: 10, background: '#1e293b', border: '1px solid #334155', borderRadius: 8, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>4. PARTITION ROUTER</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#10b981', marginTop: 4 }}>{pipeline.partition_router.state}</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{pipeline.partition_router.active_partitions || 1} partitions</div>
          </div>
          <div style={{ color: '#64748b', fontWeight: 700 }}>→</div>

          {/* Stage 5: Target Apply */}
          <div style={{ flex: 1, padding: 10, background: '#1e293b', border: '1px solid #334155', borderRadius: 8, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>5. TARGET APPLY</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: pipeline.target_apply.state === 'HEALTHY' ? '#10b981' : '#f59e0b', marginTop: 4 }}>{pipeline.target_apply.state}</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{pipeline.target_apply.apply_rate_rows_per_sec || 0} rows/s</div>
          </div>
        </div>
      </div>

      {/* ── Internal Sub-Tabs Navigation ───────────────────────────── */}
      <div className={styles.tabsRow} style={{ marginBottom: 16 }}>
        <button className={`${styles.tabBtn} ${subTab === 'overview' ? styles.tabBtnActive : ''}`} onClick={() => setSubTab('overview')}>Overview</button>
        <button className={`${styles.tabBtn} ${subTab === 'pipeline' ? styles.tabBtnActive : ''}`} onClick={() => setSubTab('pipeline')}>Pipeline & Throughput</button>
        <button className={`${styles.tabBtn} ${subTab === 'workers' ? styles.tabBtnActive : ''}`} onClick={() => setSubTab('workers')}>Workers & Partitions</button>
        <button className={`${styles.tabBtn} ${subTab === 'ordering' ? styles.tabBtnActive : ''}`} onClick={() => setSubTab('ordering')}>Ordering & Causality</button>
        <button className={`${styles.tabBtn} ${subTab === 'schema' ? styles.tabBtnActive : ''}`} onClick={() => setSubTab('schema')}>Schema Transitions</button>
        <button className={`${styles.tabBtn} ${subTab === 'conflicts' ? styles.tabBtnActive : ''}`} onClick={() => setSubTab('conflicts')}>Conflicts & Multi-Master</button>
        <button className={`${styles.tabBtn} ${subTab === 'recovery' ? styles.tabBtnActive : ''}`} onClick={() => setSubTab('recovery')}>Recovery & Checkpoints</button>
        <button className={`${styles.tabBtn} ${subTab === 'history' ? styles.tabBtnActive : ''}`} onClick={() => setSubTab('history')}>Timeline & History</button>
      </div>

      {/* ── SUB-TAB 1: Overview ──────────────────────────────────────── */}
      {subTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <div className={styles.card} style={{ padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
              Session & Position Telemetry
            </div>
            <table className={styles.table}>
              <tbody>
                <tr><td>CDC Session ID</td><td className={styles.mono}>{cdcSnapshot.cdc_session_id}</td></tr>
                <tr><td>Source LSN / SCN</td><td className={styles.mono}>{overview.current_source_lsn || '0/1A2B3C'}</td></tr>
                <tr><td>Applied Target LSN</td><td className={styles.mono}>{overview.target_applied_lsn || health_strip.checkpoint_lsn}</td></tr>
                <tr><td>Fencing Epoch</td><td className={styles.mono}>{overview.fencing_epoch || 1}</td></tr>
                <tr><td>Active Workers</td><td>{overview.active_workers || 4} / {overview.configured_workers || 4}</td></tr>
                <tr><td>Backlog Depth</td><td>{backlog_and_backpressure.queue_depth || 0} events ({backlog_and_backpressure.utilization_pct || 0}% capacity)</td></tr>
                <tr><td>Backpressure State</td><td style={{ color: backlog_and_backpressure.backpressure_state === 'NORMAL' ? '#10b981' : '#f59e0b' }}>{backlog_and_backpressure.backpressure_state || 'NORMAL'}</td></tr>
              </tbody>
            </table>
          </div>

          <div className={styles.card} style={{ padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
              Cutover Readiness Checklist
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
              <div style={{ color: cutover_checklist.backlog_drained ? '#10b981' : '#ef4444' }}>
                {cutover_checklist.backlog_drained ? '✓' : '✗'} Backlog Drained
              </div>
              <div style={{ color: cutover_checklist.ordering_dependencies_resolved ? '#10b981' : '#ef4444' }}>
                {cutover_checklist.ordering_dependencies_resolved ? '✓' : '✗'} Ordering Dependencies Resolved
              </div>
              <div style={{ color: cutover_checklist.schema_barriers_clear ? '#10b981' : '#ef4444' }}>
                {cutover_checklist.schema_barriers_clear ? '✓' : '✗'} Schema Barriers Clear
              </div>
              <div style={{ color: cutover_checklist.conflicts_resolved ? '#10b981' : '#ef4444' }}>
                {cutover_checklist.conflicts_resolved ? '✓' : '✗'} Multi-Master Conflicts Resolved
              </div>
              <div style={{ color: cutover_checklist.quarantines_clear ? '#10b981' : '#ef4444' }}>
                {cutover_checklist.quarantines_clear ? '✓' : '✗'} Entity Quarantines Released
              </div>
              <div style={{ borderTop: '1px solid #334155', paddingTop: 8, marginTop: 4, fontWeight: 700, color: cutover_checklist.cutover_ready ? '#10b981' : '#ef4444' }}>
                STATUS: {cutover_checklist.cutover_ready ? 'CUTOVER READY' : 'CUTOVER BLOCKED'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── SUB-TAB 2: Pipeline & Throughput ─────────────────────────── */}
      {subTab === 'pipeline' && (
        <div className={styles.card} style={{ padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
            Time-Series Operational Telemetry (Last 15 Minutes)
          </div>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Source Lag (sec)</th>
                <th>Capture Rate (evt/s)</th>
                <th>Apply Rate (evt/s)</th>
                <th>Backlog Events</th>
              </tr>
            </thead>
            <tbody>
              {(cdcSnapshot.telemetry_timeseries.lag_15m || []).map((pt: any, idx: number) => (
                <tr key={idx}>
                  <td className={styles.mono}>{pt.time}</td>
                  <td>{pt.val}s</td>
                  <td>{(cdcSnapshot.telemetry_timeseries.capture_rate_15m?.[idx]?.val || 0).toLocaleString()}</td>
                  <td>{(cdcSnapshot.telemetry_timeseries.apply_rate_15m?.[idx]?.val || 0).toLocaleString()}</td>
                  <td>{(cdcSnapshot.telemetry_timeseries.backlog_15m?.[idx]?.val || 0).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── SUB-TAB 3: Workers & Partitions ───────────────────────────── */}
      {subTab === 'workers' && (
        <div className={styles.card} style={{ padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
            Parallel Apply Workers & Shard Partitions (P3.6 Authority)
          </div>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Worker ID</th>
                <th>Partition</th>
                <th>Epoch</th>
                <th>Queue Depth</th>
                <th>Apply Rate</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(workers_and_partitions.worker_statuses || []).map((w: any) => (
                <tr key={w.worker_id}>
                  <td className={styles.mono}>{w.worker_id}</td>
                  <td>{w.partition_id}</td>
                  <td className={styles.mono}>{w.fencing_epoch}</td>
                  <td>{w.queue_depth}</td>
                  <td>{w.apply_rate} rows/s</td>
                  <td><span className={`${styles.badge} ${w.status === 'RUNNING' ? styles.badgeRunning : styles.badgePaused}`}>{w.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── SUB-TAB 4: Ordering & Causality ──────────────────────────── */}
      {subTab === 'ordering' && (
        <div className={styles.card} style={{ padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
            Transactional Causality DAG & Dependency Ordering (P3.7 Authority)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
            <div style={{ padding: 8, background: '#1e293b', borderRadius: 6 }}>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Ready Transactions</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#10b981' }}>{ordering_and_causality.ready_transaction_count || 0}</div>
            </div>
            <div style={{ padding: 8, background: '#1e293b', borderRadius: 6 }}>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Blocked Transactions</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: ordering_and_causality.blocked_transaction_count > 0 ? '#ef4444' : '#10b981' }}>{ordering_and_causality.blocked_transaction_count || 0}</div>
            </div>
            <div style={{ padding: 8, background: '#1e293b', borderRadius: 6 }}>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Causality DAG Nodes</div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{ordering_and_causality.causality_graph_nodes_count || 0}</div>
            </div>
            <div style={{ padding: 8, background: '#1e293b', borderRadius: 6 }}>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Ordering Health</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: ordering_and_causality.ordering_health === 'HEALTHY' ? '#10b981' : '#ef4444' }}>{ordering_and_causality.ordering_health || 'HEALTHY'}</div>
            </div>
          </div>

          {(ordering_and_causality.blocked_transactions || []).length > 0 && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#f87171', marginBottom: 8 }}>Blocked Transaction Drill-Down</div>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Transaction ID</th>
                    <th>Source Position</th>
                    <th>Block Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {ordering_and_causality.blocked_transactions.map((tx: any) => (
                    <tr key={tx.tx_id}>
                      <td className={styles.mono}>{tx.tx_id}</td>
                      <td className={styles.mono}>{tx.source_position}</td>
                      <td style={{ color: '#f87171' }}>{tx.block_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── SUB-TAB 5: Schema Transitions ───────────────────────────── */}
      {subTab === 'schema' && (
        <div className={styles.card} style={{ padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
            Live Schema Evolution Barriers (P3.5 Authority)
          </div>
          <div style={{ fontSize: 13, color: '#94a3b8' }}>
            Active Schema Barriers: <strong>{schema_transitions.active_barriers_count || 0}</strong> | Evolution State: <strong style={{ color: '#10b981' }}>{schema_transitions.schema_evolution_state || 'HEALTHY'}</strong>
          </div>
        </div>
      )}

      {/* ── SUB-TAB 6: Conflicts & Multi-Master ───────────────────────── */}
      {subTab === 'conflicts' && (
        <div className={styles.card} style={{ padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
            Bidirectional Topology & Multi-Master Conflict Management (P3.8 Authority)
          </div>

          {cdcSnapshot.session_mode === 'BIDIRECTIONAL' && (
            <div style={{ padding: 12, background: '#1e293b', border: '1px solid #334155', borderRadius: 8, marginBottom: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>BIDIRECTIONAL REPLICATION TOPOLOGY</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#38bdf8', marginTop: 4 }}>
                NODE A ({conflicts_and_topology.source_a_database_id}) &lt;=================&gt; NODE B ({conflicts_and_topology.source_b_database_id})
              </div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                Designated Primary: <strong>{conflicts_and_topology.designated_primary}</strong> | Echo Suppressed A→B: {conflicts_and_topology.echo_events_suppressed_a_to_b} | B→A: {conflicts_and_topology.echo_events_suppressed_b_to_a}
              </div>
            </div>
          )}

          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 8 }}>
            Detected Multi-Master Conflicts ({conflicts_and_topology.unresolved_conflicts_count || 0} Unresolved)
          </div>

          {(conflicts_and_topology.conflicts_list || []).length === 0 ? (
            <div style={{ fontSize: 13, color: '#10b981', padding: 12, background: '#064e3b', borderRadius: 6 }}>
              ✓ Zero multi-master conflicts detected. Topology operating safely.
            </div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Conflict ID</th>
                  <th>Type</th>
                  <th>Entity</th>
                  <th>State</th>
                  <th>Policy</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {conflicts_and_topology.conflicts_list.map((c: any) => (
                  <tr key={c.conflict_id}>
                    <td className={styles.mono}>{c.conflict_id}</td>
                    <td>{c.conflict_type}</td>
                    <td>{c.entity_table}:{c.entity_key}</td>
                    <td><span className={`${styles.badge} ${c.conflict_state === 'RESOLVED' ? styles.badgeCompleted : styles.badgeFailed}`}>{c.conflict_state}</span></td>
                    <td>{c.policy || 'UNRESOLVED'}</td>
                    <td>
                      {!isHistorical && c.conflict_state !== 'RESOLVED' && (
                        <button className={styles.primaryBtn} style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => setSelectedConflictId(c.conflict_id)}>
                          Inspect & Resolve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Conflict Inspection & Governance Modal */}
          {selectedConflictId && (
            <div style={{ marginTop: 16, padding: 16, background: '#0f172a', border: '1px solid #3b82f6', borderRadius: 8 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#60a5fa', marginBottom: 8 }}>
                Operator Conflict Governance Panel — <span className={styles.mono}>{selectedConflictId}</span>
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
                Select a canonical resolution policy to apply to conflict {selectedConflictId}:
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <button className={styles.primaryBtn} onClick={() => handleResolveConflict(selectedConflictId, 'SOURCE_A_WINS')}>
                  Source A Wins
                </button>
                <button className={styles.primaryBtn} onClick={() => handleResolveConflict(selectedConflictId, 'SOURCE_B_WINS')}>
                  Source B Wins
                </button>
                <button className={styles.primaryBtn} onClick={() => handleResolveConflict(selectedConflictId, 'DESIGNATED_PRIMARY_WINS')}>
                  Designated Primary Wins
                </button>
                <button className={styles.primaryBtn} onClick={() => handleResolveConflict(selectedConflictId, 'LATEST_VERSION_WINS')}>
                  Latest Version Wins
                </button>
              </div>

              <div style={{ borderTop: '1px solid #334155', paddingTop: 12, marginTop: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0', marginBottom: 6 }}>Explicit Manual Governance Winner:</div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <select value={manualWinner} onChange={(e) => setManualWinner(e.target.value as any)} className={styles.selectInput}>
                    <option value="SOURCE_A">Winner: Source A ({conflicts_and_topology.source_a_database_id})</option>
                    <option value="SOURCE_B">Winner: Source B ({conflicts_and_topology.source_b_database_id})</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Governance audit reason..."
                    value={governanceReason}
                    onChange={(e) => setGovernanceReason(e.target.value)}
                    style={{ flex: 1, padding: '6px 12px', background: '#1e293b', border: '1px solid #475569', borderRadius: 6, color: '#fff', fontSize: 12 }}
                  />
                  <button className={styles.primaryBtn} style={{ background: '#059669' }} onClick={() => handleResolveConflict(selectedConflictId, 'MANUAL_GOVERNANCE_REQUIRED')}>
                    Apply Manual Winner
                  </button>
                  <button className={styles.primaryBtn} style={{ background: '#475569' }} onClick={() => setSelectedConflictId(null)}>
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── SUB-TAB 7: Recovery & Checkpoints ─────────────────────────── */}
      {subTab === 'recovery' && (
        <div className={styles.card} style={{ padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
            Monotonic Recovery & Checkpoint Frontier (P1 & P3.6 Authority)
          </div>
          <table className={styles.table}>
            <tbody>
              <tr><td>Recovery State</td><td><span className={styles.badge} style={{ background: '#064e3b', color: '#34d399' }}>{recovery_and_checkpoints.recovery_state}</span></td></tr>
              <tr><td>Fencing Epoch Token</td><td className={styles.mono}>{recovery_and_checkpoints.fencing_epoch}</td></tr>
              <tr><td>Last Durable Checkpoint</td><td className={styles.mono}>{recovery_and_checkpoints.last_durable_checkpoint}</td></tr>
              <tr><td>Contiguous Frontier LSN</td><td className={styles.mono}>{recovery_and_checkpoints.contiguous_frontier_lsn}</td></tr>
              <tr><td>ACK Position</td><td className={styles.mono}>{recovery_and_checkpoints.ack_position}</td></tr>
              <tr><td>Reclamation Position</td><td className={styles.mono}>{recovery_and_checkpoints.reclamation_position}</td></tr>
            </tbody>
          </table>
        </div>
      )}

      {/* ── SUB-TAB 8: Operational Timeline & History ─────────────────── */}
      {subTab === 'history' && (
        <div className={styles.card} style={{ padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--dash-text-primary, #F9FAFB)', marginBottom: 12 }}>
            Operational Event Timeline
          </div>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Severity</th>
                <th>Category</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {(operational_events || []).map((evt: any, idx: number) => (
                <tr key={idx}>
                  <td className={styles.mono}>{evt.timestamp}</td>
                  <td><span className={`${styles.badge} ${evt.severity === 'CRITICAL' ? styles.badgeFailed : evt.severity === 'WARNING' ? styles.badgePaused : styles.badgeRunning}`}>{evt.severity}</span></td>
                  <td>{evt.category}</td>
                  <td>{evt.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
