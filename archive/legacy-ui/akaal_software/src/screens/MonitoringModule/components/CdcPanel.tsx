import React, { useState } from 'react';
import type { CdcMonitoringSnapshotDTO } from '../../../types/monitoring';
import { ipcService } from '../../../services/ipcService';
import { Lock, Check, X, CheckCircle2, AlertTriangle, ArrowRight, ArrowLeftRight, RefreshCw, Pause, Play } from 'lucide-react';
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
      {/* ── Action Notifications ───────────────────────────────────────── */}
      {isHistorical && (
        <div style={{ padding: '10px 16px', background: 'var(--dash-input-bg)', border: '1px solid var(--dash-border)', borderRadius: 10, marginBottom: 16, fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Lock size={15} />
          <span><strong>HISTORICAL MODE</strong> — Viewing read-only CDC evidence for completed/historical session. Operational actions disabled.</span>
        </div>
      )}
      {actionMsg && (
        <div style={{ padding: '10px 16px', background: 'var(--dash-notif-success-bg, rgba(16,185,129,0.1))', border: '1px solid var(--dash-notif-success-border, rgba(16,185,129,0.3))', borderRadius: 10, marginBottom: 16, color: 'var(--dash-tag-running-text, #10B981)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircle2 size={15} />
          <span>{actionMsg}</span>
        </div>
      )}
      {actionError && (
        <div style={{ padding: '10px 16px', background: 'var(--dash-notif-error-bg, rgba(239,68,68,0.1))', border: '1px solid var(--dash-notif-error-border, rgba(239,68,68,0.3))', borderRadius: 10, marginBottom: 16, color: 'var(--dash-tag-failed-text, #EF4444)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertTriangle size={15} />
          <span>{actionError}</span>
        </div>
      )}

      {/* ── CDC Header Row ────────────────────────────────────────────── */}
      <div className={styles.cdcHeaderCard}>
        <div className={styles.bannerMeta}>
          <div>
            <div className={styles.cdcHeaderTitle}>
              CDC Monitoring — <span className={styles.mono}>{cdcSnapshot.migration_id}</span>
            </div>
            <div className={styles.cdcHeaderSub}>
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
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button className={styles.primaryBtn} onClick={handlePauseCDC} disabled={cdcSnapshot.status === 'PAUSED'}>
              <Pause size={14} /> Pause CDC
            </button>
            <button className={styles.primaryBtn} onClick={handleResumeCDC} disabled={cdcSnapshot.status === 'HEALTHY'}>
              <Play size={14} /> Resume CDC
            </button>
            <button className={styles.primaryBtn} style={{ background: 'var(--dash-input-bg, #374151)', color: 'var(--dash-text-primary, #fff)', boxShadow: 'none' }} onClick={onRefresh}>
              <RefreshCw size={14} /> Refresh Snapshot
            </button>
          </div>
        )}
      </div>

      {/* ── Top Operational Health Strip ──────────────────────────────── */}
      <div className={styles.cdcHealthStripGrid}>
        <div className={styles.cdcHealthCard}>
          <div className={styles.cdcHealthLabel}>CDC STATE</div>
          <div className={`${styles.cdcHealthValue} ${health_strip.cdc_state === 'HEALTHY' ? styles.successText : health_strip.cdc_state === 'FAILED' ? styles.errorText : styles.warningText}`}>
            {health_strip.cdc_state}
          </div>
          <div className={styles.cdcHealthSub}>Mode: {cdcSnapshot.session_mode}</div>
        </div>

        <div className={styles.cdcHealthCard}>
          <div className={styles.cdcHealthLabel}>SOURCE LAG</div>
          <div className={`${styles.cdcHealthValue} ${health_strip.source_lag_sec > 5.0 ? styles.warningText : styles.successText}`}>
            {health_strip.source_lag_sec.toFixed(1)}s
          </div>
          <div className={styles.cdcHealthSub}>{health_strip.source_lag_sec < 2.0 ? 'Real-time' : 'Catching up'}</div>
        </div>

        <div className={styles.cdcHealthCard}>
          <div className={styles.cdcHealthLabel}>BACKLOG</div>
          <div className={styles.cdcHealthValue}>
            {health_strip.backlog_events.toLocaleString()}
          </div>
          <div className={styles.cdcHealthSub}>{(health_strip.backlog_bytes / 1024).toFixed(0)} KB buffered</div>
        </div>

        <div className={styles.cdcHealthCard}>
          <div className={styles.cdcHealthLabel}>APPLY RATE</div>
          <div className={`${styles.cdcHealthValue} ${styles.accentText}`}>
            {health_strip.apply_rate_rows_per_sec > 0 ? `${(health_strip.apply_rate_rows_per_sec / 1000).toFixed(1)}k/s` : '0/s'}
          </div>
          <div className={styles.cdcHealthSub}>{workers_and_partitions.active_workers || 4} active workers</div>
        </div>

        <div className={styles.cdcHealthCard}>
          <div className={styles.cdcHealthLabel}>CHECKPOINT</div>
          <div className={`${styles.cdcHealthValue} ${styles.mono}`} style={{ fontSize: 14 }}>
            {health_strip.checkpoint_lsn}
          </div>
          <div className={`${styles.cdcHealthSub} ${styles.successText}`}>Contiguous Frontier</div>
        </div>

        <div className={styles.cdcHealthCard}>
          <div className={styles.cdcHealthLabel}>CONFLICTS</div>
          <div className={`${styles.cdcHealthValue} ${health_strip.unresolved_conflicts_count > 0 ? styles.errorText : styles.successText}`}>
            {health_strip.unresolved_conflicts_count}
          </div>
          <div className={styles.cdcHealthSub}>{health_strip.quarantined_entities_count} quarantined</div>
        </div>
      </div>

      {/* ── Primary CDC Pipeline Visualization ────────────────────────── */}
      <div className={styles.pipelineFlowBox}>
        <div className={styles.pipelineFlowTitle}>
          CDC Pipeline Flow & Stage Status
        </div>
        <div className={styles.pipelineFlowRow}>
          {/* Stage 1: Capture */}
          <div className={styles.pipelineStageCard}>
            <div className={styles.pipelineStageNum}>1. SOURCE CAPTURE</div>
            <div className={`${styles.pipelineStageState} ${styles.successText}`}>{pipeline.source_capture.state}</div>
            <div className={styles.pipelineStageSub}>{pipeline.source_capture.rate_events_per_sec || 0} evt/s</div>
          </div>
          <ArrowRight size={16} className={styles.pipelineArrow} />

          {/* Stage 2: Durable Buffer */}
          <div className={styles.pipelineStageCard}>
            <div className={styles.pipelineStageNum}>2. DURABLE BUFFER</div>
            <div className={`${styles.pipelineStageState} ${pipeline.durable_buffer.state === 'NORMAL' ? styles.successText : styles.warningText}`}>{pipeline.durable_buffer.state}</div>
            <div className={styles.pipelineStageSub}>{pipeline.durable_buffer.depth_events || 0} queued</div>
          </div>
          <ArrowRight size={16} className={styles.pipelineArrow} />

          {/* Stage 3: Ordering DAG */}
          <div className={styles.pipelineStageCard}>
            <div className={styles.pipelineStageNum}>3. ORDERING DAG</div>
            <div className={`${styles.pipelineStageState} ${pipeline.ordering_dag.state === 'HEALTHY' ? styles.successText : styles.errorText}`}>{pipeline.ordering_dag.state}</div>
            <div className={styles.pipelineStageSub}>{pipeline.ordering_dag.blocked_tx_count || 0} blocked</div>
          </div>
          <ArrowRight size={16} className={styles.pipelineArrow} />

          {/* Stage 4: Partition Router */}
          <div className={styles.pipelineStageCard}>
            <div className={styles.pipelineStageNum}>4. PARTITION ROUTER</div>
            <div className={`${styles.pipelineStageState} ${styles.successText}`}>{pipeline.partition_router.state}</div>
            <div className={styles.pipelineStageSub}>{pipeline.partition_router.active_partitions || 1} partitions</div>
          </div>
          <ArrowRight size={16} className={styles.pipelineArrow} />

          {/* Stage 5: Target Apply */}
          <div className={styles.pipelineStageCard}>
            <div className={styles.pipelineStageNum}>5. TARGET APPLY</div>
            <div className={`${styles.pipelineStageState} ${pipeline.target_apply.state === 'HEALTHY' ? styles.successText : styles.warningText}`}>{pipeline.target_apply.state}</div>
            <div className={styles.pipelineStageSub}>{pipeline.target_apply.apply_rate_rows_per_sec || 0} rows/s</div>
          </div>
        </div>
      </div>

      {/* ── Internal Sub-Tabs Navigation ───────────────────────────── */}
      <div className={styles.tabsRow} style={{ marginBottom: 20 }}>
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
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
          <div className={styles.card}>
            <div className={styles.pipelineFlowTitle}>
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
                <tr><td>Backpressure State</td><td className={backlog_and_backpressure.backpressure_state === 'NORMAL' ? styles.successText : styles.warningText}>{backlog_and_backpressure.backpressure_state || 'NORMAL'}</td></tr>
              </tbody>
            </table>
          </div>

          <div className={styles.card}>
            <div className={styles.pipelineFlowTitle}>
              Cutover Readiness Checklist
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13 }}>
              <div className={`${cutover_checklist.backlog_drained ? styles.successText : styles.errorText}`} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {cutover_checklist.backlog_drained ? <Check size={14} /> : <X size={14} />} Backlog Drained
              </div>
              <div className={`${cutover_checklist.ordering_dependencies_resolved ? styles.successText : styles.errorText}`} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {cutover_checklist.ordering_dependencies_resolved ? <Check size={14} /> : <X size={14} />} Ordering Dependencies Resolved
              </div>
              <div className={`${cutover_checklist.schema_barriers_clear ? styles.successText : styles.errorText}`} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {cutover_checklist.schema_barriers_clear ? <Check size={14} /> : <X size={14} />} Schema Barriers Clear
              </div>
              <div className={`${cutover_checklist.conflicts_resolved ? styles.successText : styles.errorText}`} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {cutover_checklist.conflicts_resolved ? <Check size={14} /> : <X size={14} />} Multi-Master Conflicts Resolved
              </div>
              <div className={`${cutover_checklist.quarantines_clear ? styles.successText : styles.errorText}`} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {cutover_checklist.quarantines_clear ? <Check size={14} /> : <X size={14} />} Entity Quarantines Released
              </div>
              <div style={{ borderTop: '1px solid var(--dash-border)', paddingTop: 10, marginTop: 6, fontWeight: 700 }} className={cutover_checklist.cutover_ready ? styles.successText : styles.errorText}>
                STATUS: {cutover_checklist.cutover_ready ? 'CUTOVER READY' : 'CUTOVER BLOCKED'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── SUB-TAB 2: Pipeline & Throughput ─────────────────────────── */}
      {subTab === 'pipeline' && (
        <div className={styles.card}>
          <div className={styles.pipelineFlowTitle}>
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
        <div className={styles.card}>
          <div className={styles.pipelineFlowTitle}>
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
        <div className={styles.card}>
          <div className={styles.pipelineFlowTitle}>
            Transactional Causality DAG & Dependency Ordering (P3.7 Authority)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 20 }}>
            <div className={styles.pipelineStageCard}>
              <div className={styles.pipelineStageNum}>Ready Transactions</div>
              <div className={`${styles.pipelineStageState} ${styles.successText}`}>{ordering_and_causality.ready_transaction_count || 0}</div>
            </div>
            <div className={styles.pipelineStageCard}>
              <div className={styles.pipelineStageNum}>Blocked Transactions</div>
              <div className={`${styles.pipelineStageState} ${ordering_and_causality.blocked_transaction_count > 0 ? styles.errorText : styles.successText}`}>{ordering_and_causality.blocked_transaction_count || 0}</div>
            </div>
            <div className={styles.pipelineStageCard}>
              <div className={styles.pipelineStageNum}>Causality DAG Nodes</div>
              <div className={styles.pipelineStageState}>{ordering_and_causality.causality_graph_nodes_count || 0}</div>
            </div>
            <div className={styles.pipelineStageCard}>
              <div className={styles.pipelineStageNum}>Ordering Health</div>
              <div className={`${styles.pipelineStageState} ${ordering_and_causality.ordering_health === 'HEALTHY' ? styles.successText : styles.errorText}`}>{ordering_and_causality.ordering_health || 'HEALTHY'}</div>
            </div>
          </div>

          {(ordering_and_causality.blocked_transactions || []).length > 0 && (
            <div>
              <div className={`${styles.pipelineFlowTitle} ${styles.errorText}`} style={{ fontSize: 13, marginBottom: 10 }}>Blocked Transaction Drill-Down</div>
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
                      <td className={styles.errorText}>{tx.block_reason}</td>
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
        <div className={styles.card}>
          <div className={styles.pipelineFlowTitle}>
            Live Schema Evolution Barriers (P3.5 Authority)
          </div>
          <div style={{ fontSize: 13, color: 'var(--dash-text-secondary)' }}>
            Active Schema Barriers: <strong>{schema_transitions.active_barriers_count || 0}</strong> | Evolution State: <strong className={styles.successText}>{schema_transitions.schema_evolution_state || 'HEALTHY'}</strong>
          </div>
        </div>
      )}

      {/* ── SUB-TAB 6: Conflicts & Multi-Master ───────────────────────── */}
      {subTab === 'conflicts' && (
        <div className={styles.card}>
          <div className={styles.pipelineFlowTitle}>
            Bidirectional Topology & Multi-Master Conflict Management (P3.8 Authority)
          </div>

          {cdcSnapshot.session_mode === 'BIDIRECTIONAL' && (
            <div className={styles.topologyBox}>
              <div className={styles.topologyTitle}>BIDIRECTIONAL REPLICATION TOPOLOGY</div>
              <div className={styles.topologyNodes} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <span>NODE A ({conflicts_and_topology.source_a_database_id})</span>
                <ArrowLeftRight size={18} />
                <span>NODE B ({conflicts_and_topology.source_b_database_id})</span>
              </div>
              <div className={styles.topologySub}>
                Designated Primary: <strong>{conflicts_and_topology.designated_primary}</strong> | Echo Suppressed A→B: {conflicts_and_topology.echo_events_suppressed_a_to_b} | B→A: {conflicts_and_topology.echo_events_suppressed_b_to_a}
              </div>
            </div>
          )}

          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--dash-text-primary)', marginBottom: 12 }}>
            Detected Multi-Master Conflicts ({conflicts_and_topology.unresolved_conflicts_count || 0} Unresolved)
          </div>

          {(conflicts_and_topology.conflicts_list || []).length === 0 ? (
            <div className={styles.successText} style={{ fontSize: 13, padding: 14, background: 'var(--dash-notif-success-bg)', border: '1px solid var(--dash-notif-success-border)', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle2 size={16} />
              <span>Zero multi-master conflicts detected. Topology operating safely.</span>
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
                        <button className={styles.primaryBtn} style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => setSelectedConflictId(c.conflict_id)}>
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
            <div className={styles.governanceBox}>
              <div className={`${styles.pipelineFlowTitle} ${styles.accentText}`} style={{ marginBottom: 8 }}>
                Operator Conflict Governance Panel — <span className={styles.mono}>{selectedConflictId}</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginBottom: 14 }}>
                Select a canonical resolution policy to apply to conflict {selectedConflictId}:
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
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

              <div style={{ borderTop: '1px solid var(--dash-border)', paddingTop: 14 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--dash-text-primary)', marginBottom: 8 }}>Explicit Manual Governance Winner:</div>
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
                    style={{ flex: 1, padding: '8px 14px', background: 'var(--dash-input-bg)', border: '1px solid var(--dash-border)', borderRadius: 8, color: 'var(--dash-text-primary)', fontSize: 12 }}
                  />
                  <button className={styles.primaryBtn} style={{ background: '#059669' }} onClick={() => handleResolveConflict(selectedConflictId, 'MANUAL_GOVERNANCE_REQUIRED')}>
                    Apply Manual Winner
                  </button>
                  <button className={styles.primaryBtn} style={{ background: 'var(--dash-input-bg)', color: 'var(--dash-text-primary)', boxShadow: 'none' }} onClick={() => setSelectedConflictId(null)}>
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
        <div className={styles.card}>
          <div className={styles.pipelineFlowTitle}>
            Monotonic Recovery & Checkpoint Frontier (P1 & P3.6 Authority)
          </div>
          <table className={styles.table}>
            <tbody>
              <tr><td>Recovery State</td><td><span className={`${styles.badge} ${styles.badgeRunning}`}>{recovery_and_checkpoints.recovery_state}</span></td></tr>
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
        <div className={styles.card}>
          <div className={styles.pipelineFlowTitle}>
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
