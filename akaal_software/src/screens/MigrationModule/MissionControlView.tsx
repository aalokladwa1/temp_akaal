import { useState, useEffect, useMemo, type FC } from 'react';
import {
  Table,
  Zap,
  Cpu,
  CheckCircle2,
  ChevronDown,
  ArrowLeft,
  X,
  Activity,
  Play,
  Pause,
  Square,
  Bookmark,
  RotateCcw,
  ShieldAlert,
  Download,
  PlayCircle,
  ShieldCheck,
  Terminal,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Wifi,
  WifiOff,
} from 'lucide-react';
import type { MigrationPipeline, EngineStageId } from '../../types/migration';
import { ENGINE_STAGE_METADATA } from '../../services/migrationService';
import { notificationService } from '../../services/notificationService';

export type ConfirmActionType =
  | 'pause'
  | 'resume'
  | 'stop_batch'
  | 'terminate'
  | 'restart'
  | 'recover'
  | 'checkpoint'
  | 'rollback'
  | 'retry'
  | 'maintenance'
  | 'run_again'
  | 'clone'
  | 'mission_replay'
  | 'export_replay'
  | 'download_cert';

export interface MissionControlViewProps {
  migration: MigrationPipeline;
  onBack: () => void;
  onOpenWizard?: () => void;
}

export type MigrationRunStatus = 'running' | 'paused' | 'failed' | 'completed';
export type RuntimeConnectionState = 'CONNECTED' | 'LOADING' | 'RECONNECTING' | 'ERROR' | 'OFFLINE';

const fmtRows = (n: number | null | undefined): string => {
  if (n == null || n < 0) return '—';
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return `${n}`;
};

export const MissionControlView: FC<MissionControlViewProps> = ({
  migration,
  onBack,
  onOpenWizard: _onOpenWizard,
}) => {
  // Runtime Connection & Health State
  const [connectionState, setConnectionState] = useState<RuntimeConnectionState>('CONNECTED');
  const [snapshotAgeMs, setSnapshotAgeMs] = useState(120);

  // Migration Live Run State (Bound for DTO presentation)
  const [runStatus, setRunStatus] = useState<MigrationRunStatus>('running');
  const [activeStage, setActiveStage] = useState<EngineStageId>('data_migration');
  const [showPlanDrawer, setShowPlanDrawer] = useState(false);
  const [showOperationsMenu, setShowOperationsMenu] = useState(false);

  // Operational Confirmation Modal State
  const [confirmAction, setConfirmAction] = useState<ConfirmActionType | null>(null);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState('chkpt-04a8f910-lsn');
  const [exportFormat, setExportFormat] = useState<'HTML' | 'MP4' | 'PDF'>('HTML');

  // Live Telemetry Bindings
  const [rowsProcessed] = useState<number | null>(780_450_000);
  const totalRows = 1_240_500_000;
  const progressPercent = rowsProcessed != null ? Math.min(100, Math.round((rowsProcessed / totalRows) * 100)) : 0;

  // Mission Replay™ Mode State
  const [isReplayMode, setIsReplayMode] = useState(false);
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [replayTimeSec, setReplayTimeSec] = useState(0);
  const [replaySpeed, setReplaySpeed] = useState<1 | 2 | 5 | 10>(1);

  // Upgrade 9: Rich Structured Activity Log Stream (Newest First)
  const [activityFeed] = useState([
    {
      id: 'act-6',
      timestamp: '14:32:05',
      workerName: 'Worker #2',
      database: 'HRDB',
      schema: 'SYSTEM',
      object: 'AUDIT_TRAIL',
      severity: 'SUCCESS',
      category: 'VALIDATION',
      message: 'Column checksum reconciliation passed for 124 catalog objects',
    },
    {
      id: 'act-5',
      timestamp: '14:31:40',
      workerName: 'Worker #4',
      database: 'HRDB',
      schema: 'HR',
      object: 'CUSTOMER_RECORDS',
      severity: 'INFO',
      category: 'TRANSPORT',
      message: 'CUSTOMER_RECORDS table chunk completed (500M rows in 12m 40s)',
    },
    {
      id: 'act-4',
      timestamp: '14:25:10',
      workerName: 'Worker #1',
      database: 'FINANCEDB',
      schema: 'FIN',
      object: 'GL_BALANCES',
      severity: 'INFO',
      category: 'TRANSPORT',
      message: 'Parallel Worker #4 initiated partition stream chunk #18',
    },
    {
      id: 'act-3',
      timestamp: '14:20:00',
      workerName: 'Supervisor',
      database: 'SALESDB',
      schema: 'SALES',
      object: 'ALL_OBJECTS',
      severity: 'CHECKPOINT',
      category: 'CHECKPOINT',
      message: 'Durable WAL Checkpoint sealed at LSN 0/4A8F910 (RPO: 0s)',
    },
    {
      id: 'act-2',
      timestamp: '14:18:20',
      workerName: 'Governance',
      database: 'SYSTEM',
      schema: 'GATE',
      object: 'GATE_2',
      severity: 'SUCCESS',
      category: 'CERTIFICATE',
      message: 'Four-Eyes Executive Approval granted by Governance Security Gate',
    },
    {
      id: 'act-1',
      timestamp: '14:15:00',
      workerName: 'ScoutAgent',
      database: 'HRDB',
      schema: 'HR',
      object: 'CATALOG',
      severity: 'INFO',
      category: 'DDL',
      message: 'Discovery catalog fenced: 3 Databases, 4 Schemas, 124 Objects cataloged',
    },
  ]);

  // Snapshot Age Simulator
  useEffect(() => {
    const interval = setInterval(() => {
      setSnapshotAgeMs((prev) => (prev > 1500 ? 120 : prev + 120));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Action Execution Handler called ONLY after operator confirms inside dialog
  const executeConfirmedAction = (action: ConfirmActionType) => {
    setConfirmAction(null);
    switch (action) {
      case 'pause':
        setRunStatus('paused');
        notificationService.push('Migration Paused', 'warning', 'Transport workers held gracefully. Checkpoint recorded.');
        break;
      case 'resume':
        setRunStatus('running');
        notificationService.push('Migration Resumed', 'success', 'Resumed 8 parallel stream workers at ~154.8 MB/s.');
        break;
      case 'stop_batch':
        setRunStatus('paused');
        notificationService.push('Stop After Current Batch', 'info', 'Current batch will finish and commit cleanly.');
        break;
      case 'terminate':
        setRunStatus('failed');
        notificationService.push('Migration Terminated', 'error', 'Runtime process terminated immediately.');
        break;
      case 'restart':
        setRunStatus('running');
        setActiveStage('data_migration');
        notificationService.push('Runtime Restarted', 'info', 'Recycled process and restored from checkpoint LSN.');
        break;
      case 'recover':
        setRunStatus('running');
        notificationService.push('Runtime Recovered', 'info', 'WAL replayed and process locks reset.');
        break;
      case 'checkpoint':
        notificationService.push('Checkpoint Created', 'success', 'Manual recovery checkpoint sealed (RPO: 0s).');
        break;
      case 'rollback':
        setRunStatus('paused');
        notificationService.push('Rollback Executed', 'warning', `Rolled back target database to checkpoint ${selectedCheckpoint}.`);
        break;
      case 'retry':
        setRunStatus('running');
        setActiveStage('data_migration');
        notificationService.push('Retrying Failed Step', 'info', 'Re-executing current stage under supervisor.');
        break;
      case 'maintenance':
        notificationService.push('Maintenance Mode Enabled', 'warning', 'Runtime isolated. New operation requests held.');
        break;
      case 'run_again':
        setRunStatus('running');
        notificationService.push('New Execution Run Created', 'success', 'Instantiated fresh pipeline run for workspace.');
        break;
      case 'clone':
        notificationService.push('Migration Cloned', 'success', 'Cloned configuration into new pipeline template.');
        break;
      case 'mission_replay':
        setIsReplayMode(true);
        setReplayTimeSec(0);
        setReplayPlaying(true);
        notificationService.push('Mission Replay™ Active', 'info', 'Replaying recorded engine events & telemetry stream.');
        break;
      case 'export_replay':
        notificationService.push('Replay Manifest Exported', 'success', `Exported Mission Replay as ${exportFormat} file.`);
        break;
      case 'download_cert':
        notificationService.push('Trust Certificate Downloaded', 'success', 'Downloaded SHA-256 cryptographic proof document.');
        break;
    }
  };

  const handleExitReplay = () => {
    setIsReplayMode(false);
    setReplayPlaying(false);
  };

  // Stage metadata
  const stageMeta = ENGINE_STAGE_METADATA[activeStage] || ENGINE_STAGE_METADATA['data_migration'];

  // Dynamic Execution Plan Nodes Presentation Binding
  const dynamicExecutionPlanNodes = useMemo(() => {
    return [
      { stage: 1, name: 'Discovery & Catalog Fencing', category: 'Catalog', details: `Source Engine: ${migration.sourceEngine} -> Target: ${migration.targetEngine}` },
      { stage: 2, name: 'DAG Topological Dependency Sorting', category: 'Planner', details: '3 Databases, 4 Schemas, 124 Objects cataloged' },
      { stage: 3, name: 'Target Schema Structure Deployment', category: 'DDL', details: `Deploy DDL definitions to target ${migration.targetEngine}` },
      { stage: 4, name: 'Sequence Generator Sync Node', category: 'DDL', details: 'Initialize 6 database sequences' },
      { stage: 5, name: 'Parallel Stream Data Transport', category: 'Data Transport', details: '68 Tables (8 Workers, 10,000 Batch Size)' },
      { stage: 6, name: 'Target View DDL Creation', category: 'DDL', details: 'Deploy 18 SQL view definitions' },
      { stage: 7, name: 'PL/SQL Transpilation & Deployment', category: 'Transpiler', details: 'Transpile 24 PL/SQL routines to PL/pgSQL' },
      { stage: 8, name: 'Trigger Definition Deployment', category: 'DDL', details: 'Attach 12 database triggers' },
      { stage: 9, name: 'CDC Continuous Replication Setup', category: 'Replication', details: 'Setup WAL Log Reader & streaming sync' },
      { stage: 10, name: 'Reconciliation & Validation Node', category: 'Validation', details: 'Level: CHECKSUM (100% sampling rate)' },
      { stage: 11, name: 'SHA-256 Digital Trust Seal', category: 'Certification', details: 'Generate cryptographic migration certificate' },
    ];
  }, [migration]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', minHeight: 0, background: 'var(--dash-bg)', overflow: 'hidden' }}>
      
      {/* ── PART 5 & 6: RUNTIME STATUS & DESKTOP-ENGINE CONNECTION HEALTH RIBBON ─ */}
      <div style={{ padding: '4px 24px', background: connectionState === 'RECONNECTING' ? 'rgba(245,158,11,0.18)' : 'var(--dash-surface)', borderBottom: '1px solid var(--dash-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, fontWeight: 700, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: connectionState === 'CONNECTED' ? '#10B981' : connectionState === 'RECONNECTING' ? '#F59E0B' : '#EF4444' }}>
            {connectionState === 'CONNECTED' ? <Wifi size={12} /> : <WifiOff size={12} />}
            <span>ENGINE: {connectionState === 'CONNECTED' ? 'CONNECTED' : connectionState === 'RECONNECTING' ? 'RECONNECTING TO AKAAL ENGINE...' : 'OFFLINE'}</span>
          </div>

          <div style={{ width: 1, height: 10, background: 'var(--dash-border)' }} />

          <span style={{ color: 'var(--dash-text-secondary)' }}>IPC: <span style={{ color: '#10B981' }}>HEALTHY (0.4ms)</span></span>
          <span style={{ color: 'var(--dash-text-secondary)' }}>Snapshot Age: <span style={{ color: 'var(--dash-text-primary)' }}>{snapshotAgeMs}ms</span></span>
          <span style={{ color: 'var(--dash-text-secondary)' }}>Event Stream: <span style={{ color: '#10B981' }}>RECEIVING</span></span>
          <span style={{ color: 'var(--dash-text-secondary)' }}>Supervisor: <span style={{ color: '#10B981' }}>HEALTHY (PID 89412)</span></span>
        </div>

        {/* Development Connection State Toggle for Verification */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ color: 'var(--dash-text-tertiary)', fontSize: 9 }}>Simulate Health:</span>
          <button type="button" onClick={() => setConnectionState(connectionState === 'CONNECTED' ? 'LOADING' : connectionState === 'LOADING' ? 'RECONNECTING' : 'CONNECTED')}
            style={{ padding: '1px 6px', borderRadius: 3, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: 'var(--dash-text-secondary)', fontSize: 9, cursor: 'pointer' }}>
            Toggle State ({connectionState})
          </button>
        </div>
      </div>

      {/* ── MISSION REPLAY™ HEADER BANNER (Shows only in Replay Mode) ─────── */}
      {isReplayMode && (
        <div style={{ padding: '8px 24px', background: 'rgba(37,99,235,0.15)', borderBottom: '1px solid var(--dash-accent)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <PlayCircle size={18} color="var(--dash-accent)" />
            <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--dash-text-primary)', letterSpacing: '0.04em' }}>
              MISSION REPLAY™ MODE — HISTORICAL EVENT STREAM RECORDING
            </span>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 12, background: 'var(--dash-accent)', color: '#FFF', fontWeight: 700 }}>
              REPLAY ACTIVE
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--dash-surface)', padding: '3px 8px', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
              <button type="button" onClick={() => setReplayTimeSec(0)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-primary)', cursor: 'pointer', padding: 4 }} title="Restart Replay">
                <RotateCcw size={14} />
              </button>
              <button type="button" onClick={() => setReplayPlaying(!replayPlaying)} style={{ background: 'none', border: 'none', color: 'var(--dash-accent)', cursor: 'pointer', padding: 4 }} title={replayPlaying ? 'Pause' : 'Play'}>
                {replayPlaying ? <Pause size={14} /> : <Play size={14} />}
              </button>
              <span style={{ fontSize: 11, fontFamily: 'var(--akaal-font-mono, monospace)', color: 'var(--dash-text-primary)', fontWeight: 700, padding: '0 6px' }}>
                {replayTimeSec}s / 180s
              </span>
              {( [1, 2, 5, 10] as const).map((spd) => (
                <button key={spd} type="button" onClick={() => setReplaySpeed(spd)}
                  style={{ padding: '2px 6px', borderRadius: 4, border: 'none', background: replaySpeed === spd ? 'var(--dash-accent)' : 'transparent', color: replaySpeed === spd ? '#FFF' : 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}>
                  {spd}x
                </button>
              ))}
            </div>

            <button type="button" onClick={handleExitReplay} style={{ padding: '4px 12px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>
              Exit Replay Mode
            </button>
          </div>
        </div>
      )}

      {/* ── HEADER BAR ─────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-surface)', flexShrink: 0, gap: 16, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, overflow: 'hidden' }}>
          <button type="button" onClick={onBack} style={{ background: 'none', border: '1px solid var(--dash-border)', padding: '6px 12px', borderRadius: 6, color: 'var(--dash-text-secondary)', fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            <ArrowLeft size={14} /> Back
          </button>
          <div style={{ width: 1, height: 20, background: 'var(--dash-border)' }} />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)', whiteSpace: 'nowrap' }}>
                {migration.name}
              </h2>
              <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: runStatus === 'running' ? 'rgba(16,185,129,0.15)' : runStatus === 'paused' ? 'rgba(245,158,11,0.15)' : runStatus === 'failed' ? 'rgba(239,68,68,0.15)' : 'rgba(37,99,235,0.15)', color: runStatus === 'running' ? '#10B981' : runStatus === 'paused' ? '#F59E0B' : runStatus === 'failed' ? '#EF4444' : '#3B82F6', fontWeight: 700, textTransform: 'uppercase' }}>
                ● {runStatus}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 12 }}>
              <span>{migration.sourceEngine} ──► {migration.targetEngine}</span>
              <span>• ETA: 14 Mins</span>
              <span>• ID: MIG-2026-0806-001</span>
              <span>• Owner: {migration.owner}</span>
            </div>
          </div>
        </div>

        <button type="button" onClick={() => setShowPlanDrawer(true)}
          style={{ padding: '8px 16px', borderRadius: 8, background: 'rgba(37,99,235,0.12)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <Zap size={15} /> View Plan
        </button>
      </div>

      {/* ── ENTERPRISE OPERATIONS TOOLBAR (State-Aware Controls) ─────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 24px', background: 'var(--dash-bg)', borderBottom: '1px solid var(--dash-border)', flexShrink: 0, gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginRight: 6 }}>
            Operations Console:
          </span>

          {/* RUNNING STATE CONTROLS */}
          {runStatus === 'running' && (
            <>
              <button type="button" onClick={() => setConfirmAction('pause')} style={{ padding: '6px 14px', borderRadius: 6, background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)', color: '#F59E0B', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Pause size={13} /> Pause Migration
              </button>
              <button type="button" onClick={() => setConfirmAction('stop_batch')} style={{ padding: '6px 14px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Square size={13} /> Stop After Current Batch
              </button>
              <button type="button" onClick={() => setConfirmAction('checkpoint')} style={{ padding: '6px 14px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Bookmark size={13} /> Create Manual Checkpoint
              </button>
            </>
          )}

          {/* PAUSED STATE CONTROLS */}
          {runStatus === 'paused' && (
            <>
              <button type="button" onClick={() => setConfirmAction('resume')} style={{ padding: '6px 14px', borderRadius: 6, background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', color: '#10B981', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Play size={13} /> Resume Migration
              </button>
              <button type="button" onClick={() => setConfirmAction('terminate')} style={{ padding: '6px 14px', borderRadius: 6, background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', color: '#EF4444', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <XCircle size={13} /> Terminate Migration
              </button>
              <button type="button" onClick={() => setConfirmAction('rollback')} style={{ padding: '6px 14px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <RotateCcw size={13} /> Rollback To Checkpoint
              </button>
            </>
          )}

          {/* FAILED STATE CONTROLS */}
          {runStatus === 'failed' && (
            <>
              <button type="button" onClick={() => setConfirmAction('retry')} style={{ padding: '6px 14px', borderRadius: 6, background: 'rgba(37,99,235,0.15)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <RotateCcw size={13} /> Retry Failed Step
              </button>
              <button type="button" onClick={() => setConfirmAction('recover')} style={{ padding: '6px 14px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <ShieldAlert size={13} /> Recover Runtime
              </button>
              <button type="button" onClick={() => setConfirmAction('export_replay')} style={{ padding: '6px 14px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Download size={13} /> Export Diagnostics
              </button>
            </>
          )}

          {/* COMPLETED STATE CONTROLS (Mission Replay™ & Exports) */}
          {runStatus === 'completed' && (
            <>
              <button type="button" onClick={() => setConfirmAction('mission_replay')} style={{ padding: '6px 14px', borderRadius: 6, background: 'rgba(37,99,235,0.15)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', fontSize: 11, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <PlayCircle size={14} color="#3B82F6" /> Mission Replay™
              </button>
              <button type="button" onClick={() => setConfirmAction('export_replay')} style={{ padding: '6px 14px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Download size={13} /> Export Replay
              </button>
              <button type="button" onClick={() => setConfirmAction('download_cert')} style={{ padding: '6px 14px', borderRadius: 6, background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', color: '#10B981', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <ShieldCheck size={13} /> Download Trust Certificate
              </button>
              <button type="button" onClick={() => setConfirmAction('run_again')} style={{ padding: '6px 14px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <RefreshCw size={13} /> Run Again
              </button>
            </>
          )}

          {/* Operations Dropdown Menu */}
          <div style={{ position: 'relative' }}>
            <button type="button" onClick={() => setShowOperationsMenu(!showOperationsMenu)}
              style={{ padding: '6px 12px', borderRadius: 6, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
              Operations <ChevronDown size={13} />
            </button>
            {showOperationsMenu && (
              <div onClick={() => setShowOperationsMenu(false)} style={{ position: 'absolute', top: '100%', left: 0, marginTop: 4, width: 220, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.3)', zIndex: 99, padding: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <button type="button" onClick={() => setConfirmAction('terminate')} style={{ padding: '8px 12px', textAlign: 'left', background: 'none', border: 'none', color: '#EF4444', fontSize: 11, fontWeight: 600, cursor: 'pointer', borderRadius: 4 }}>Terminate Runtime</button>
                <button type="button" onClick={() => setConfirmAction('restart')} style={{ padding: '8px 12px', textAlign: 'left', background: 'none', border: 'none', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', borderRadius: 4 }}>Restart Migration Runtime</button>
                <button type="button" onClick={() => setConfirmAction('recover')} style={{ padding: '8px 12px', textAlign: 'left', background: 'none', border: 'none', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', borderRadius: 4 }}>Recover Migration Runtime</button>
                <button type="button" onClick={() => setConfirmAction('rollback')} style={{ padding: '8px 12px', textAlign: 'left', background: 'none', border: 'none', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', borderRadius: 4 }}>Rollback To Checkpoint</button>
                <button type="button" onClick={() => setConfirmAction('maintenance')} style={{ padding: '8px 12px', textAlign: 'left', background: 'none', border: 'none', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', borderRadius: 4 }}>Enable Maintenance Mode</button>
                <button type="button" onClick={() => setConfirmAction('clone')} style={{ padding: '8px 12px', textAlign: 'left', background: 'none', border: 'none', color: 'var(--dash-text-primary)', fontSize: 11, fontWeight: 600, cursor: 'pointer', borderRadius: 4 }}>Clone Migration</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── MAIN CONTENT WORKSPACE ────────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', padding: 20, gap: 16, width: '100%' }}>

        {/* LEFT COLUMN: CURRENT EXECUTION STAGE (Observer Mode) ─────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0, overflowY: 'auto' }}>

          {/* PART 2 & PART 4: ENTERPRISE SKELETON LOADING STATE WHEN HYDRATING */}
          {connectionState === 'LOADING' ? (
            <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--dash-bg)', animation: 'pulse 1.5s infinite' }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ width: 140, height: 12, background: 'var(--dash-bg)', borderRadius: 4, animation: 'pulse 1.5s infinite' }} />
                  <div style={{ width: 220, height: 18, background: 'var(--dash-bg)', borderRadius: 4, animation: 'pulse 1.5s infinite' }} />
                </div>
              </div>
              <div style={{ padding: 16, background: 'var(--dash-bg)', borderRadius: 8, textAlign: 'center', fontSize: 13, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>
                <RefreshCw size={18} className="spin" style={{ marginBottom: 6, display: 'block', margin: '0 auto 6px auto', color: '#3B82F6' }} />
                Waiting for Runtime Snapshot from AKAAL Engine...
              </div>
            </div>
          ) : (
            /* PART 7 & 8: UPGRADED CURRENT STAGE CARD WITH ANIMATIONS */
            <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 20, display: 'flex', flexDirection: 'column', gap: 16, transition: 'all 200ms ease-out' }}>
              
              {/* Stage Header (Read-Only Observer Mode) */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dash-border)', paddingBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: 'rgba(37,99,235,0.15)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 12px rgba(37,99,235,0.25)' }}>
                    <Activity size={20} />
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Current Execution Stage</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                      {stageMeta.label}
                    </div>
                  </div>
                </div>

                {/* Read-Only Observer Badge */}
                <span style={{ fontSize: 11, padding: '4px 12px', borderRadius: 20, background: 'rgba(16,185,129,0.12)', color: '#10B981', fontWeight: 700, border: '1px solid rgba(16,185,129,0.3)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981', boxShadow: '0 0 6px #10B981' }} /> ENGINE ACTIVE STAGE (READ-ONLY)
                </span>
              </div>

              {/* Stage Specific Telemetry Grid */}
              {activeStage === 'data_migration' ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
                  <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Active Workers</div>
                    <div style={{ fontSize: 16, fontWeight: 800, marginTop: 4, color: '#3B82F6' }}>8 Pool Workers</div>
                  </div>
                  <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Streaming Speed</div>
                    <div style={{ fontSize: 16, fontWeight: 800, marginTop: 4, color: '#10B981' }}>154.8 MB/s</div>
                  </div>
                  <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>Rows/sec Rate</div>
                    <div style={{ fontSize: 16, fontWeight: 800, marginTop: 4, color: '#8B5CF6' }}>48,500/s</div>
                  </div>
                  <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>WAN Bandwidth</div>
                    <div style={{ fontSize: 16, fontWeight: 800, marginTop: 4, color: '#F59E0B' }}>1.2 Gbps</div>
                  </div>
                  <div style={{ padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>WAL Ring Buffer</div>
                    <div style={{ fontSize: 16, fontWeight: 800, marginTop: 4, color: '#10B981' }}>100% OK</div>
                  </div>
                </div>
              ) : (
                <div style={{ padding: 12, background: 'var(--dash-bg)', borderRadius: 8, fontSize: 12, color: 'var(--dash-text-secondary)' }}>
                  Stage: {stageMeta.description}
                </div>
              )}
            </div>
          )}

          {/* ── LIVE OBJECT STREAM PROGRESS CARD ────────────────────────────── */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Table size={16} color="#10B981" />
                <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--dash-text-primary)' }}>Live Object Stream Progress</span>
              </div>
              <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--dash-accent)', fontVariantNumeric: 'tabular-nums' }}>
                {progressPercent}% Complete ({fmtRows(rowsProcessed)} / {fmtRows(totalRows)} Rows)
              </span>
            </div>

            {/* Smooth Progress Bar */}
            <div style={{ width: '100%', height: 10, borderRadius: 6, background: 'var(--dash-bg)', overflow: 'hidden', border: '1px solid var(--dash-border)' }}>
              <div style={{ width: `${progressPercent}%`, height: '100%', background: 'linear-gradient(90deg, #3B82F6 0%, #10B981 100%)', transition: 'width 250ms ease-in-out', borderRadius: 6 }} />
            </div>

            {/* Active Object Telemetry Matrix */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, fontSize: 11, marginTop: 4 }}>
              <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Current Target Object</div>
                <div style={{ fontWeight: 700, color: 'var(--dash-text-primary)', marginTop: 2, fontFamily: 'var(--akaal-font-mono, monospace)' }}>CUSTOMER_RECORDS</div>
              </div>
              <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Indexes Built</div>
                <div style={{ fontWeight: 700, color: '#10B981', marginTop: 2 }}>4 of 5 Indexes</div>
              </div>
              <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Constraints Verified</div>
                <div style={{ fontWeight: 700, color: '#10B981', marginTop: 2 }}>2 PK / 4 FK Verified</div>
              </div>
              <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Upstream Lock Status</div>
                <div style={{ fontWeight: 700, color: '#3B82F6', marginTop: 2 }}>0 Lock Conflicts</div>
              </div>
            </div>
          </div>

          {/* PART 9: UPGRADED LIVE ACTIVITY FEED (Structured Readability) ───── */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 18, display: 'flex', flexDirection: 'column', gap: 12, flex: 1, minHeight: 220 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dash-border)', paddingBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Terminal size={15} color="#3B82F6" />
                <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--dash-text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Live Human-Readable Activity Stream</span>
              </div>
              <span style={{ fontSize: 10, color: '#10B981', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981' }} /> LIVE EVENT BUS
              </span>
            </div>

            {/* PART 3: PROPER EMPTY STATE IF NO EVENTS */}
            {activityFeed.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--dash-text-secondary)', fontSize: 12 }}>
                Waiting for runtime events from EnterpriseEventBus...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', maxHeight: 260, paddingRight: 4 }}>
                {activityFeed.map((item) => {
                  const iconColor = item.severity === 'SUCCESS' ? '#10B981' : item.severity === 'WARNING' ? '#F59E0B' : item.severity === 'ERROR' ? '#EF4444' : '#3B82F6';
                  return (
                    <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', fontSize: 11, transition: 'all 150ms ease' }}>
                      <span style={{ fontFamily: 'var(--akaal-font-mono, monospace)', fontSize: 10, color: 'var(--dash-text-secondary)', flexShrink: 0 }}>[{item.timestamp}]</span>
                      <span style={{ padding: '1px 6px', borderRadius: 4, background: `${iconColor}18`, color: iconColor, fontWeight: 800, fontSize: 9, textTransform: 'uppercase', flexShrink: 0 }}>
                        {item.category}
                      </span>
                      <span style={{ color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 600, flexShrink: 0 }}>
                        {item.workerName} · {item.database}.{item.schema}.{item.object}:
                      </span>
                      <span style={{ color: 'var(--dash-text-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.message}
                      </span>
                      <CheckCircle2 size={12} color={iconColor} />
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

        {/* PART 10: COMPACT RUNTIME OVERVIEW PANEL (High Density) ───────────── */}
        <div style={{ width: 310, display: 'flex', flexDirection: 'column', gap: 14, flexShrink: 0 }}>
          
          {/* PART 11: MISSION REPLAY™ COLLAPSED SUMMARY CARD */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 800, color: 'var(--dash-text-primary)' }}>
                <PlayCircle size={14} color="#3B82F6" /> Mission Replay™
              </div>
              <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, background: 'rgba(37,99,235,0.12)', color: '#3B82F6', fontWeight: 800 }}>
                {runStatus === 'completed' ? 'AVAILABLE' : 'STANDBY'}
              </span>
            </div>
            <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', lineHeight: 1.4 }}>
              {runStatus === 'completed'
                ? 'Replay recorded historical events & telemetry timeline (180s duration, 10 events).'
                : 'Replay becomes available after migration completion.'}
            </div>
            {runStatus === 'completed' && (
              <button type="button" onClick={() => setConfirmAction('mission_replay')} style={{ padding: '6px 12px', borderRadius: 6, background: 'rgba(37,99,235,0.15)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', fontSize: 11, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, width: '100%' }}>
                <Play size={12} /> Open Mission Replay™
              </button>
            )}
          </div>

          {/* Compact Runtime Metrics Overview Card */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6, borderBottom: '1px solid var(--dash-border)', paddingBottom: 8 }}>
              <Cpu size={14} color="#3B82F6" /> Compact Runtime Overview
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>Parallel Worker Threads</span>
                <strong style={{ color: 'var(--dash-text-primary)' }}>8 Active Pool</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>CPU Usage</span>
                <strong style={{ color: '#10B981' }}>42% (4 Cores)</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>RAM Memory Quota</span>
                <strong style={{ color: '#3B82F6' }}>2.4 GB / 4.0 GB</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>Streaming Speed</span>
                <strong style={{ color: '#10B981' }}>154.8 MB/s</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>Rows/sec Throughput</span>
                <strong style={{ color: '#8B5CF6' }}>48,500 rows/s</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>WAN Network Bandwidth</span>
                <strong style={{ color: '#F59E0B' }}>1.2 Gbps</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>WAL Buffer Lag</span>
                <strong style={{ color: '#10B981' }}>0.1 seconds (RPO 0)</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>Active Connections</span>
                <strong style={{ color: 'var(--dash-text-primary)' }}>16 Open Socket Links</strong>
              </div>
            </div>
          </div>

          {/* Engine Health Governance Card */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={14} color="#10B981" /> Engine Supervisor Status
            </div>

            <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', lineHeight: 1.4 }}>
              MigrationRuntimeDaemon running on PID 89412 with active RuntimeSupervisorTree monitoring process locks.
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 2, paddingTop: 6, borderTop: '1px solid var(--dash-border)', fontSize: 10 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Supervisor Health:</span>
              <span style={{ color: '#10B981', fontWeight: 700 }}>● HEALTHY (0 Failures)</span>
            </div>
          </div>

        </div>

      </div>

      {/* ── DYNAMIC EXECUTION PLAN DRAWER ─────────────────────────────────── */}
      {showPlanDrawer && (
        <div onClick={() => setShowPlanDrawer(false)}
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', zIndex: 9999, display: 'flex', justifyContent: 'flex-end' }}>
          <div onClick={(e) => e.stopPropagation()}
            style={{ width: 520, height: '100%', background: 'var(--dash-surface)', borderLeft: '1px solid var(--dash-border)', padding: 24, display: 'flex', flexDirection: 'column', gap: 18, overflowY: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dash-border)', paddingBottom: 14 }}>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)' }}>Dynamic Migration Execution Plan</h3>
                <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>Generated for current migration pipeline</div>
              </div>
              <button onClick={() => setShowPlanDrawer(false)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', cursor: 'pointer', padding: 4 }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Generated DAG Execution Stages ({dynamicExecutionPlanNodes.length} Pipeline Stages)
            </div>

            {/* PART 3: PROPER EMPTY STATE IF NO PLAN */}
            {dynamicExecutionPlanNodes.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--dash-text-secondary)', fontSize: 12 }}>
                No execution plan generated yet. Generate a migration plan to visualize the workflow.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {dynamicExecutionPlanNodes.map((item, idx) => {
                  const currentStageIdx = 4;
                  const isCompleted = idx < currentStageIdx;
                  const isCurrent = idx === currentStageIdx;
                  const isFailed = runStatus === 'failed' && isCurrent;
                  const isPaused = runStatus === 'paused' && isCurrent;

                  const bg = isFailed
                    ? 'rgba(239,68,68,0.12)'
                    : isPaused
                    ? 'rgba(245,158,11,0.12)'
                    : isCompleted
                    ? 'rgba(16,185,129,0.12)'
                    : isCurrent
                    ? 'rgba(37,99,235,0.15)'
                    : 'var(--dash-bg)';

                  const color = isFailed
                    ? '#EF4444'
                    : isPaused
                    ? '#F59E0B'
                    : isCompleted
                    ? '#10B981'
                    : isCurrent
                    ? '#3B82F6'
                    : 'var(--dash-text-secondary)';

                  const badgeText = isFailed ? 'FAILED' : isPaused ? 'PAUSED' : isCompleted ? 'VERIFIED' : isCurrent ? 'EXECUTING' : 'PENDING';
                  const badgeIcon = isFailed ? '✕' : isPaused ? '⏸' : isCompleted ? '✓' : isCurrent ? '▶' : item.stage;

                  return (
                    <div key={item.stage} style={{ display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between', padding: 10, background: bg, borderRadius: 8, border: `1px solid ${color}33`, transition: 'all 150ms ease' }}>
                      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ width: 22, height: 22, borderRadius: '50%', background: color, color: '#FFF', fontSize: 10, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          {badgeIcon}
                        </span>
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{item.name}</div>
                          <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{item.details}</div>
                        </div>
                      </div>
                      <span style={{ fontSize: 9, fontWeight: 800, padding: '2px 7px', borderRadius: 4, background: `${color}22`, color: color, textTransform: 'uppercase' }}>
                        {badgeText}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            <div style={{ borderTop: '1px solid var(--dash-border)', paddingTop: 14, display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
              <div style={{ fontWeight: 700, color: 'var(--dash-text-primary)' }}>Runtime Engine Architecture</div>
              <div>• <strong>Daemon:</strong> MigrationRuntimeDaemon (Isolated Process)</div>
              <div>• <strong>Supervisor:</strong> RuntimeSupervisorTree (Auto-Healing)</div>
              <div>• <strong>WAL Buffer:</strong> DurableWALRingBuffer (10k Records, CRC32)</div>
              <div>• <strong>Mailbox:</strong> DurableCommandMailbox (SQLite Epoch Fencing)</div>
            </div>
          </div>
        </div>
      )}

      {/* ── ENTERPRISE OPERATIONAL SAFETY CONFIRMATION DIALOG ──────────────────── */}
      {confirmAction && (
        <div
          onClick={() => setConfirmAction(null)}
          style={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.75)',
            backdropFilter: 'blur(4px)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 560,
              maxWidth: '90vw',
              background: 'var(--dash-surface)',
              border: confirmAction === 'terminate' || confirmAction === 'rollback' ? '1px solid #EF4444' : '1px solid var(--dash-border)',
              borderRadius: 14,
              boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              transition: 'all 200ms ease-out',
            }}
          >
            {/* Modal Header */}
            <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--dash-border)', background: 'var(--dash-bg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 10,
                  background: confirmAction === 'terminate' || confirmAction === 'rollback' ? 'rgba(239,68,68,0.15)' : confirmAction === 'pause' || confirmAction === 'maintenance' ? 'rgba(245,158,11,0.15)' : 'rgba(37,99,235,0.15)',
                  border: confirmAction === 'terminate' || confirmAction === 'rollback' ? '1px solid rgba(239,68,68,0.3)' : confirmAction === 'pause' || confirmAction === 'maintenance' ? '1px solid rgba(245,158,11,0.3)' : '1px solid rgba(37,99,235,0.3)',
                  color: confirmAction === 'terminate' || confirmAction === 'rollback' ? '#EF4444' : confirmAction === 'pause' || confirmAction === 'maintenance' ? '#F59E0B' : '#3B82F6',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  {confirmAction === 'terminate' || confirmAction === 'rollback' ? <AlertTriangle size={20} /> : confirmAction === 'pause' ? <Pause size={18} /> : confirmAction === 'resume' ? <Play size={18} /> : <Zap size={18} />}
                </div>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)' }}>
                    {confirmAction === 'pause' && 'Pause Migration'}
                    {confirmAction === 'resume' && 'Resume Migration'}
                    {confirmAction === 'stop_batch' && 'Stop Migration Gracefully'}
                    {confirmAction === 'terminate' && 'Terminate Migration'}
                    {confirmAction === 'restart' && 'Restart Migration Runtime'}
                    {confirmAction === 'recover' && 'Recover Migration Runtime'}
                    {confirmAction === 'checkpoint' && 'Create Checkpoint'}
                    {confirmAction === 'rollback' && 'Rollback Migration'}
                    {confirmAction === 'retry' && 'Retry Failed Step'}
                    {confirmAction === 'maintenance' && 'Enable Maintenance Mode'}
                    {confirmAction === 'run_again' && 'Run Migration Again'}
                    {confirmAction === 'clone' && 'Clone Migration'}
                    {confirmAction === 'mission_replay' && 'Open Mission Replay™'}
                    {confirmAction === 'export_replay' && 'Export Mission Replay'}
                    {confirmAction === 'download_cert' && 'Download Trust Certificate'}
                  </h3>
                  <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>
                    AKAAL Enterprise Operational Safety Control Layer
                  </div>
                </div>
              </div>
              <button type="button" onClick={() => setConfirmAction(null)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: 22, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <p style={{ fontSize: 13, color: 'var(--dash-text-primary)', margin: 0, lineHeight: 1.5 }}>
                {confirmAction === 'pause' && 'This will pause the migration after the current safe execution point. Current progress, checkpoints, and runtime state will be preserved.'}
                {confirmAction === 'resume' && 'The migration will resume from the latest checkpoint and continue execution.'}
                {confirmAction === 'stop_batch' && 'The engine will finish the current batch, commit any completed work, and stop safely. No in-flight data will be lost.'}
                {confirmAction === 'terminate' && 'This action immediately terminates the migration runtime. Uncommitted work may be discarded. Recovery may require restarting from the latest checkpoint. This action should only be used during emergencies.'}
                {confirmAction === 'restart' && 'The runtime process will be restarted. Recovery Coordinator will restore execution using the latest checkpoint.'}
                {confirmAction === 'recover' && 'Recovery Coordinator will replay the WAL and restore the runtime from the latest recoverable checkpoint.'}
                {confirmAction === 'checkpoint' && 'A manual recovery checkpoint will be created. This checkpoint can later be used for rollback or recovery.'}
                {confirmAction === 'rollback' && 'Select the checkpoint to restore. Displaying available cryptographic LSN checkpoint snapshots below.'}
                {confirmAction === 'retry' && 'Retry only the failed workflow step. Previously completed stages remain untouched.'}
                {confirmAction === 'maintenance' && 'The runtime will enter maintenance mode. New operations will be blocked until maintenance mode is disabled.'}
                {confirmAction === 'run_again' && 'A new migration execution will be created using the same migration configuration. The previous migration remains unchanged.'}
                {confirmAction === 'clone' && 'A new migration configuration will be created using the current migration as its template.'}
                {confirmAction === 'mission_replay' && 'Mission Replay will load the recorded runtime events and telemetry for this completed migration. This does not execute the migration again.'}
                {confirmAction === 'export_replay' && 'Choose the export format for offline timeline report generation.'}
                {confirmAction === 'download_cert' && 'The SHA-256 Trust Certificate and migration verification report will be downloaded.'}
              </p>

              {/* Special Controls for Rollback Checkpoint Selection */}
              {confirmAction === 'rollback' && (
                <div style={{ border: '1px solid var(--dash-border)', borderRadius: 8, padding: 12, background: 'var(--dash-bg)', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Select Checkpoint to Restore</div>
                  {[
                    { id: 'chkpt-04a8f910-lsn', time: '2026-08-06 14:20:00', rows: '650,000,000', stage: 'Data Transport' },
                    { id: 'chkpt-01b2c3d4-ddl', time: '2026-08-06 14:18:20', rows: '0', stage: 'Schema DDL' },
                  ].map((chk) => (
                    <label key={chk.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 8, borderRadius: 6, background: selectedCheckpoint === chk.id ? 'rgba(37,99,235,0.12)' : 'var(--dash-surface)', border: selectedCheckpoint === chk.id ? '1px solid var(--dash-accent)' : '1px solid var(--dash-border)', cursor: 'pointer', fontSize: 11 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input type="radio" name="chkpt" checked={selectedCheckpoint === chk.id} onChange={() => setSelectedCheckpoint(chk.id)} />
                        <div>
                          <strong style={{ color: 'var(--dash-text-primary)', fontFamily: 'var(--akaal-font-mono, monospace)' }}>{chk.id}</strong>
                          <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Stage: {chk.stage} · {chk.rows} Rows</div>
                        </div>
                      </div>
                      <span style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>{chk.time}</span>
                    </label>
                  ))}
                </div>
              )}

              {/* Special Controls for Export Replay Format */}
              {confirmAction === 'export_replay' && (
                <div style={{ border: '1px solid var(--dash-border)', borderRadius: 8, padding: 12, background: 'var(--dash-bg)', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Choose Export Format</div>
                  {[
                    { id: 'HTML', label: 'Interactive HTML Manifest', desc: 'Self-contained offline interactive timeline' },
                    { id: 'MP4', label: 'MP4 Video Recording', desc: 'Rendered video recording of Mission Control playback' },
                    { id: 'PDF', label: 'PDF Timeline Report', desc: 'Executive printable audit report document' },
                  ].map((fmt) => (
                    <label key={fmt.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 8, borderRadius: 6, background: exportFormat === fmt.id ? 'rgba(37,99,235,0.12)' : 'var(--dash-surface)', border: exportFormat === fmt.id ? '1px solid var(--dash-accent)' : '1px solid var(--dash-border)', cursor: 'pointer', fontSize: 11 }}>
                      <input type="radio" name="expfmt" checked={exportFormat === fmt.id} onChange={() => setExportFormat(fmt.id as any)} />
                      <div>
                        <strong style={{ color: 'var(--dash-text-primary)' }}>{fmt.label}</strong>
                        <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>{fmt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              )}

              {/* Enterprise Operational Safety Impact Matrix */}
              <div style={{ padding: 12, background: 'var(--dash-bg)', borderRadius: 8, border: '1px solid var(--dash-border)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 11 }}>
                <div>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>Runtime Impact</div>
                  <div style={{ fontWeight: 600, color: 'var(--dash-text-primary)', marginTop: 2 }}>
                    {confirmAction === 'pause' && 'Holds stream workers & checkpoints WAL'}
                    {confirmAction === 'resume' && 'Re-activates 8 parallel socket threads'}
                    {confirmAction === 'stop_batch' && 'Commits current batch before halt'}
                    {confirmAction === 'terminate' && 'Immediate process termination (Emergency)'}
                    {confirmAction === 'restart' && 'Recycles daemon process & mailbox'}
                    {confirmAction === 'recover' && 'Replays WAL & resets supervisor locks'}
                    {confirmAction === 'checkpoint' && 'Flushes LSN write-ahead buffer'}
                    {confirmAction === 'rollback' && 'Truncates target data & reverts DDL'}
                    {confirmAction === 'retry' && 'Re-executes active stage under supervisor'}
                    {confirmAction === 'maintenance' && 'Isolates IPC command mailbox queue'}
                    {confirmAction === 'run_again' && 'Creates new execution session ID'}
                    {confirmAction === 'clone' && 'Duplicates pipeline workspace template'}
                    {confirmAction === 'mission_replay' && 'Loads recorded event telemetry'}
                    {confirmAction === 'export_replay' && 'Generates offline timeline file'}
                    {confirmAction === 'download_cert' && 'Generates signed SHA-256 certificate'}
                  </div>
                </div>
                <div>
                  <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>Reversibility & Recovery</div>
                  <div style={{ fontWeight: 600, color: confirmAction === 'terminate' || confirmAction === 'rollback' ? '#EF4444' : '#10B981', marginTop: 2 }}>
                    {confirmAction === 'terminate' ? 'Irreversible (Requires Rollback)' : confirmAction === 'rollback' ? 'Reverts Target Changes' : '✓ Reversible / Safe Operation'}
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid var(--dash-border)', background: 'var(--dash-bg)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                onClick={() => setConfirmAction(null)}
                style={{ padding: '8px 16px', borderRadius: 8, background: 'var(--dash-surface)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => executeConfirmedAction(confirmAction)}
                style={{
                  padding: '9px 20px', borderRadius: 8,
                  background: confirmAction === 'terminate' || confirmAction === 'rollback' ? '#EF4444' : confirmAction === 'pause' || confirmAction === 'maintenance' ? '#F59E0B' : confirmAction === 'resume' || confirmAction === 'download_cert' ? '#10B981' : 'var(--dash-accent)',
                  color: '#FFF', border: 'none', fontSize: 12, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
                }}
              >
                {confirmAction === 'pause' && 'Pause Migration'}
                {confirmAction === 'resume' && 'Resume Migration'}
                {confirmAction === 'stop_batch' && 'Stop After Current Batch'}
                {confirmAction === 'terminate' && 'Terminate Runtime'}
                {confirmAction === 'restart' && 'Restart Runtime'}
                {confirmAction === 'recover' && 'Recover Runtime'}
                {confirmAction === 'checkpoint' && 'Create Checkpoint'}
                {confirmAction === 'rollback' && 'Rollback'}
                {confirmAction === 'retry' && 'Retry Step'}
                {confirmAction === 'maintenance' && 'Enable Maintenance Mode'}
                {confirmAction === 'run_again' && 'Run Again'}
                {confirmAction === 'clone' && 'Clone Migration'}
                {confirmAction === 'mission_replay' && 'Open Replay'}
                {confirmAction === 'export_replay' && 'Export'}
                {confirmAction === 'download_cert' && 'Download'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
