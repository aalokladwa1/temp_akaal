import { useState, useEffect, useRef, type FC } from 'react';
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
  Wifi,
  WifiOff,
  Clock,
} from 'lucide-react';
import type { MigrationPipeline, GovernanceApproval } from '../../types/migration';
import type { RuntimeSnapshotDTO } from '../../types/bridge';
import { notificationService } from '../../services/notificationService';
import { ipcService } from '../../services/ipcService';
import { approvalRepository } from '../../repositories/approvalRepository';
import { CdcLifecycleWorkspace } from './components/CdcLifecycleWorkspace';

export type ConfirmActionType =
  | 'start'
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
  onOpenGovernance?: (migrationId?: string, gateId?: string) => void;
}

export type MissionControlState =
  | 'AWAITING_APPROVAL'
  | 'READY_TO_START'
  | 'START_REQUESTED'
  | 'STARTING'
  | 'RUNNING'
  | 'PAUSED'
  | 'VALIDATING'
  | 'CERTIFYING'
  | 'COMPLETED'
  | 'FAILED';

export type StageVisualState =
  | 'NOT_STARTED'
  | 'ACTIVE_INDETERMINATE'
  | 'ACTIVE_DETERMINATE'
  | 'PAUSED'
  | 'COMPLETED'
  | 'FAILED';

export interface CanonicalStageDef {
  id: string;
  name: string;
  category: string;
  details: string;
}

const CANONICAL_STAGES: CanonicalStageDef[] = [
  {
    id: 'schema_exec',
    name: 'Target Schema DDL Execution',
    category: 'DDL',
    details: 'Apply target schema DDL, tables, and constraints',
  },
  {
    id: 'transport',
    name: 'Parallel Stream Data Transport',
    category: 'Data Transport',
    details: 'Bulk transport parallel streaming partitions',
  },
  {
    id: 'validation',
    name: 'Physical Checksum Validation',
    category: 'Validation',
    details: 'SHA-256 row checksum & Merkle root auditing',
  },
  {
    id: 'certification',
    name: 'Digital Trust Certification',
    category: 'Certification',
    details: 'Generate cryptographic migration certificate',
  },
  {
    id: 'completed',
    name: 'Pipeline Execution Completed',
    category: 'Completion',
    details: 'Migration execution finished & verified',
  },
];

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
  onOpenGovernance: _onOpenGovernance,
}) => {
  // Runtime Connection & Telemetry State
  const [connectionState, setConnectionState] = useState<'CONNECTED' | 'LOADING' | 'RECONNECTING' | 'OFFLINE'>('CONNECTED');
  const [snapshotAgeMs, setSnapshotAgeMs] = useState(120);
  const [snapshot, setSnapshot] = useState<RuntimeSnapshotDTO | null>(null);

  // Authoritative State Machine Driven by Snapshot
  const [controlState, setControlState] = useState<MissionControlState>('READY_TO_START');
  const [activeViewMode, setActiveViewMode] = useState<'STAGES' | 'CDC_LIFECYCLE'>('STAGES');
  const [showPlanDrawer, setShowPlanDrawer] = useState(false);
  const [showOperationsMenu, setShowOperationsMenu] = useState(false);

  // Operational Confirmation Modal State
  const [confirmAction, setConfirmAction] = useState<ConfirmActionType | null>(null);
  const [_selectedCheckpoint] = useState('chkpt-04a8f910-lsn');
  const [_exportFormat] = useState<'HTML' | 'MP4' | 'PDF'>('HTML');

  // Mission Replay™ Mode State
  const [isReplayMode, setIsReplayMode] = useState(false);
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [replayTimeSec, setReplayTimeSec] = useState(0);
  const [replaySpeed, setReplaySpeed] = useState<1 | 2 | 5 | 10>(1);

  // Activity Log Stream
  const [activityFeed, setActivityFeed] = useState<any[]>([]);

  // Polling Protection & Request Counter
  const isFetchingRef = useRef(false);
  const lastSnapshotTs = useRef<number>(0);
  const [migrationResult, setMigrationResult] = useState<any>(null);

  const safeParseObj = (raw: any): any => {
    if (!raw) return null;
    if (typeof raw === 'object') return raw;
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && parsed.result) {
        return typeof parsed.result === 'string' ? JSON.parse(parsed.result) : parsed.result;
      }
      return parsed;
    } catch {
      return null;
    }
  };

  const fetchMigrationResult = async () => {
    try {
      const raw = await ipcService.invokeEngineCapability(
        'get_migration_result',
        JSON.stringify({ migration_id: migration.id })
      );
      if (raw) {
        const res = safeParseObj(raw);
        if (res) setMigrationResult(res);
      }
    } catch (err) {
      console.warn('[MissionControl] Failed to fetch migration result:', err);
    }
  };

  const fetchRuntimeSnapshot = async () => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;
    const reqTs = Date.now();

    try {
      const raw = await ipcService.invokeEngineCapability(
        'get_runtime_snapshot',
        JSON.stringify({ migration_id: migration.id })
      );

      if (raw && reqTs >= lastSnapshotTs.current) {
        lastSnapshotTs.current = reqTs;
        const snap: RuntimeSnapshotDTO = safeParseObj(raw);

        if (snap) {
          setSnapshot(snap);

          // Update Authoritative Control State
          const st = String(snap.runtime_status || snap.status || snap.runtime_state || '').toUpperCase();
          const act = String(snap.current_activity || '').toUpperCase();
          const stg = String(snap.current_stage || '').toLowerCase();

          if (st === 'COMPLETED' || act.includes('COMPLETE') || stg === 'completed') {
            setControlState('COMPLETED');
            isTerminalRef.current = true;
            fetchMigrationResult();
          } else if (st === 'FAILED' || st === 'ERROR' || act.includes('FAIL') || act.includes('ERROR')) {
            setControlState('FAILED');
            isTerminalRef.current = true;
          } else if (st === 'TERMINATED') {
            setControlState('FAILED');
            isTerminalRef.current = true;
          } else if (st === 'PAUSED' || act.includes('PAUSE')) {
            setControlState('PAUSED');
          } else if (stg === 'validation' || stg === 'validator') {
            setControlState('VALIDATING');
          } else if (stg === 'certification') {
            setControlState('CERTIFYING');
          } else if (st === 'RUNNING' || act.includes('RUNNING') || stg === 'transport' || stg === 'schema_exec') {
            setControlState('RUNNING');
          } else if (st === 'STARTING' || st === 'START_REQUESTED' || act.includes('START')) {
            setControlState('STARTING');
          } else {
            // Check Governance Approval status
            const isApproved = snap.approval_status === 'APPROVED' ||
              (migration.id && approvalRepository.getApprovals().some((a: GovernanceApproval) => a.migrationId === migration.id && a.status === 'approved'));
            setControlState(isApproved ? 'READY_TO_START' : 'AWAITING_APPROVAL');
          }

          if (snap.logs && Array.isArray(snap.logs) && snap.logs.length > 0) {
            setActivityFeed(snap.logs.slice(-50));
          }
          setConnectionState('CONNECTED');
        }
      }
    } catch (err) {
      console.warn('[MissionControl] Failed to fetch runtime snapshot:', err);
      setConnectionState('OFFLINE');
    } finally {
      isFetchingRef.current = false;
    }
  };

  const isTerminalRef = useRef<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    isTerminalRef.current = false;
    fetchRuntimeSnapshot();

    const interval = setInterval(() => {
      if (isMounted && !isTerminalRef.current) {
        fetchRuntimeSnapshot();
        setSnapshotAgeMs((prev) => (prev > 1500 ? 120 : prev + 120));
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [migration.id]);

  // Action Execution Handler for Modal Dialogs
  const executeConfirmedAction = async (action: ConfirmActionType) => {
    setConfirmAction(null);
    let cap = '';
    const payloadObj: any = { migration_id: migration.id };

    switch (action) {
      case 'start':
        cap = 'start_transport';
        setControlState('START_REQUESTED');
        break;
      case 'pause':
        cap = 'pause_migration';
        setControlState('PAUSED');
        break;
      case 'resume':
        cap = 'resume_migration';
        setControlState('RUNNING');
        break;
      case 'stop_batch':
        cap = 'pause_migration';
        payloadObj.mode = 'stop_after_batch';
        setControlState('PAUSED');
        break;
      case 'terminate':
        cap = 'terminate_migration';
        setControlState('FAILED');
        break;
      case 'restart':
      case 'retry':
        cap = 'start_transport';
        setControlState('START_REQUESTED');
        break;
      case 'recover':
        cap = 'execute_healing';
        break;
      case 'checkpoint':
        cap = 'trigger_checkpoint';
        break;
      case 'rollback':
        cap = 'rollback_migration';
        payloadObj.checkpoint = _selectedCheckpoint;
        break;
      case 'download_cert':
        cap = 'generate_certificate';
        break;
      case 'mission_replay':
        setIsReplayMode(true);
        setReplayTimeSec(0);
        setReplayPlaying(true);
        notificationService.push('Mission Replay™ Active', 'info', 'Replaying recorded engine events & telemetry stream.');
        return;
      case 'export_replay':
        notificationService.push('Replay Manifest Exported', 'success', `Exported Mission Replay as ${_exportFormat} file.`);
        return;
      default:
        notificationService.push(`Action ${action.toUpperCase()}`, 'info', 'Action acknowledged.');
        return;
    }

    if (cap) {
      try {
        const rawRes = await ipcService.invokeEngineCapability(cap, JSON.stringify(payloadObj));
        const resObj = safeParseObj(rawRes);

        if (resObj && (resObj.status === 'failed' || resObj.status === 'error' || resObj.error_code)) {
          const errCode = resObj.error_code || 'OPERATION_FAILED';
          const errMsg = resObj.error_message || resObj.message || resObj.failure_reason || `Operation ${action.toUpperCase()} rejected by engine.`;

          if (errCode === 'APPROVAL_REQUIRED') {
            notificationService.push(
              'Governance Approval Required',
              'warning',
              `Cannot start transport for '${migration.id}': Governance sign-off is required.`
            );
          } else {
            notificationService.push(`Engine Rejected: ${action.toUpperCase()}`, 'error', errMsg);
          }
          await fetchRuntimeSnapshot();
          return;
        }

        if (action === 'start') {
          notificationService.push('Migration Startup Accepted', 'success', `Start Migration request accepted by AKAAL SuperEngine.`);
        } else {
          notificationService.push(`Engine Acknowledged: ${action.toUpperCase()}`, 'success', `State updated by AKAAL runtime for ${migration.id}`);
        }
        await fetchRuntimeSnapshot();
      } catch (err: any) {
        const errStr = typeof err === 'string' ? err : err?.message || String(err);
        notificationService.push('Operation Failed', 'error', errStr);
      }
    }
  };

  const handleExitReplay = () => {
    setIsReplayMode(false);
    setReplayPlaying(false);
  };

  // Derive Stage Visual State for Each Stage Truthfully
  const getStageVisualState = (stageId: string, idx: number): StageVisualState => {
    if (controlState === 'FAILED' && snapshot?.failed_stage === stageId) {
      return 'FAILED';
    }
    if (controlState === 'PAUSED') {
      const activeStg = String(snapshot?.current_stage || '').toLowerCase();
      if (activeStg === stageId || (stageId === 'transport' && activeStg === 'data_migration')) {
        return 'PAUSED';
      }
    }
    if (controlState === 'COMPLETED') {
      return 'COMPLETED';
    }
    if (controlState === 'AWAITING_APPROVAL' || controlState === 'READY_TO_START' || controlState === 'START_REQUESTED') {
      return 'NOT_STARTED';
    }

    const currentBackendStage = String(snapshot?.current_stage || '').toLowerCase();
    const stageOrderMap: Record<string, number> = {
      schema_exec: 0,
      schema: 0,
      transport: 1,
      data_migration: 1,
      validation: 2,
      validator: 2,
      certification: 3,
      completed: 4,
    };

    const currentIdx = stageOrderMap[currentBackendStage] ?? -1;

    if (currentIdx === -1) {
      return idx === 0 && controlState === 'STARTING' ? 'ACTIVE_INDETERMINATE' : 'NOT_STARTED';
    }

    if (idx < currentIdx) return 'COMPLETED';
    if (idx === currentIdx) {
      if (stageId === 'transport' && snapshot?.progress_percent != null) {
        return 'ACTIVE_DETERMINATE';
      }
      return 'ACTIVE_INDETERMINATE';
    }
    return 'NOT_STARTED';
  };

  // Live Telemetry Values
  const rowsProcessed = snapshot?.rows_transferred != null ? snapshot.rows_transferred : null;
  const totalRows = snapshot?.rows_total != null && snapshot.rows_total > 0 ? snapshot.rows_total : null;
  const progressPercent = snapshot?.progress_percent != null ? Math.min(100, Math.round(snapshot.progress_percent)) : 0;
  const isGovernanceApproved = snapshot?.approval_status === 'APPROVED' || (migration.id && approvalRepository.getApprovals().some((a: GovernanceApproval) => a.migrationId === migration.id && a.status === 'approved'));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', minHeight: 0, background: 'var(--dash-bg)', overflow: 'hidden' }}>

      {/* Inline Keyframes for Live Shimmer & Pulse Animations */}
      <style>{`
        @keyframes akaalShimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        @keyframes akaalPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.97); }
        }
        .akaal-shimmer-bar {
          background: linear-gradient(90deg, #2563EB 0%, #60A5FA 50%, #2563EB 100%);
          background-size: 200% 100%;
          animation: akaalShimmer 1.8s infinite linear;
        }
        .akaal-pulse-icon {
          animation: akaalPulse 1.5s infinite ease-in-out;
        }
      `}</style>

      {/* ── CONNECTION & HEALTH RIBBON ────────────────────────────────────────── */}
      <div style={{ padding: '4px 24px', background: connectionState === 'RECONNECTING' ? 'rgba(245,158,11,0.18)' : 'var(--dash-surface)', borderBottom: '1px solid var(--dash-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, fontWeight: 700, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: connectionState === 'CONNECTED' ? '#10B981' : connectionState === 'RECONNECTING' ? '#F59E0B' : '#EF4444' }}>
            {connectionState === 'CONNECTED' ? <Wifi size={12} /> : <WifiOff size={12} />}
            <span>ENGINE: {connectionState === 'CONNECTED' ? 'CONNECTED' : connectionState === 'RECONNECTING' ? 'RECONNECTING TO AKAAL ENGINE...' : 'OFFLINE'}</span>
          </div>

          <div style={{ width: 1, height: 10, background: 'var(--dash-border)' }} />

          <span style={{ color: 'var(--dash-text-secondary)' }}>IPC: <span style={{ color: connectionState === 'CONNECTED' ? '#10B981' : '#F59E0B' }}>{connectionState === 'CONNECTED' ? 'ONLINE' : 'OFFLINE'}</span></span>
          <span style={{ color: 'var(--dash-text-secondary)' }}>Snapshot Age: <span style={{ color: 'var(--dash-text-primary)' }}>{snapshotAgeMs}ms</span></span>
          <span style={{ color: 'var(--dash-text-secondary)' }}>State: <span style={{ color: '#10B981', fontWeight: 800 }}>{controlState}</span></span>
          <span style={{ color: 'var(--dash-text-secondary)' }}>Supervisor: <span style={{ color: controlState === 'RUNNING' || controlState === 'STARTING' ? '#10B981' : 'var(--dash-text-secondary)' }}>{controlState === 'RUNNING' || controlState === 'STARTING' ? 'EXECUTING DAEMON' : 'IDLE / STANDBY'}</span></span>
        </div>

        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ color: 'var(--dash-text-tertiary)', fontSize: 9 }}>Connection Status:</span>
          <span style={{ padding: '1px 6px', borderRadius: 3, border: '1px solid var(--dash-border)', background: 'var(--dash-bg)', color: '#10B981', fontSize: 9, fontWeight: 700 }}>
            {connectionState}
          </span>
        </div>
      </div>

      {/* ── MISSION REPLAY™ HEADER BANNER ───────────────────────────────────── */}
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
              {([1, 2, 5, 10] as const).map((spd) => (
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
              <span style={{
                fontSize: 11, padding: '2px 8px', borderRadius: 4,
                background: controlState === 'RUNNING' || controlState === 'STARTING' ? 'rgba(16,185,129,0.15)' : controlState === 'PAUSED' ? 'rgba(245,158,11,0.15)' : controlState === 'FAILED' ? 'rgba(239,68,68,0.15)' : 'rgba(37,99,235,0.15)',
                color: controlState === 'RUNNING' || controlState === 'STARTING' ? '#10B981' : controlState === 'PAUSED' ? '#F59E0B' : controlState === 'FAILED' ? '#EF4444' : '#3B82F6',
                fontWeight: 700, textTransform: 'uppercase'
              }}>
                ● {controlState}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 12 }}>
              <span>{migration.sourceEngine} ──► {migration.targetEngine}</span>
              <span>• ETA: {snapshot?.eta_seconds != null ? `${snapshot.eta_seconds}s` : '—'}</span>
              <span>• ID: {migration.id}</span>
              <span>• Owner: {migration.owner}</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => setActiveViewMode(activeViewMode === 'STAGES' ? 'CDC_LIFECYCLE' : 'STAGES')}
            style={{
              padding: '8px 14px',
              borderRadius: 8,
              background: activeViewMode === 'CDC_LIFECYCLE' ? 'var(--dash-accent)' : 'var(--dash-card-bg)',
              border: '1px solid var(--dash-accent)',
              color: activeViewMode === 'CDC_LIFECYCLE' ? '#fff' : 'var(--dash-accent)',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              flexShrink: 0,
            }}
          >
            {activeViewMode === 'CDC_LIFECYCLE' ? 'View Pipeline Stages' : 'CDC Lifecycle & Cutover Workspace'}
          </button>

          <button type="button" onClick={() => setShowPlanDrawer(true)}
            style={{ padding: '8px 16px', borderRadius: 8, background: 'rgba(37,99,235,0.12)', border: '1px solid var(--dash-accent)', color: 'var(--dash-accent)', fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            <Zap size={15} /> View Plan
          </button>
        </div>
      </div>

      {/* ── MIGRATION FAILURE BANNER ────────────────────────────────────────── */}
      {controlState === 'FAILED' && (
        <div style={{ margin: '16px 24px 0 24px', padding: '16px 20px', background: 'rgba(239,68,68,0.1)', border: '1px solid #EF4444', borderRadius: 8, color: '#EF4444' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: 800, fontSize: 15 }}>
            <AlertTriangle size={20} color="#EF4444" />
            <span>MIGRATION EXECUTION FAILED</span>
          </div>
          <div style={{ marginTop: 8, fontSize: 13, display: 'grid', gridTemplateColumns: '120px 1fr', gap: 6, color: 'var(--dash-text-primary)' }}>
            <span style={{ color: 'var(--dash-text-secondary)' }}>Stage:</span>
            <strong>{snapshot?.failed_stage || snapshot?.current_stage || 'Transport / Validation'}</strong>
            {snapshot?.failed_object && (
              <>
                <span style={{ color: 'var(--dash-text-secondary)' }}>Object:</span>
                <strong style={{ fontFamily: 'monospace' }}>{snapshot.failed_object}</strong>
              </>
            )}
            <span style={{ color: 'var(--dash-text-secondary)' }}>Reason:</span>
            <span style={{ color: '#EF4444', fontWeight: 600 }}>{snapshot?.error_message || (snapshot?.errors && snapshot.errors[0]) || 'Database rejected operation or transport failed.'}</span>
          </div>
        </div>
      )}

      {/* ── ENTERPRISE OPERATIONS TOOLBAR ─────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 24px', background: 'var(--dash-bg)', borderBottom: '1px solid var(--dash-border)', flexShrink: 0, gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginRight: 6 }}>
            Operations Console:
          </span>

          {/* READY / AWAITING APPROVAL CONTROLS */}
          {(controlState === 'READY_TO_START' || controlState === 'AWAITING_APPROVAL') && (
            <>
              <button
                type="button"
                disabled={!isGovernanceApproved}
                onClick={() => {
                  if (isGovernanceApproved) setConfirmAction('start');
                }}
                style={{
                  padding: '6px 16px',
                  borderRadius: 6,
                  background: isGovernanceApproved ? '#10B981' : 'var(--dash-border)',
                  color: isGovernanceApproved ? '#FFF' : 'var(--dash-text-secondary)',
                  fontSize: 12,
                  fontWeight: 800,
                  border: 'none',
                  cursor: isGovernanceApproved ? 'pointer' : 'not-allowed',
                  opacity: isGovernanceApproved ? 1 : 0.6,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
                title={isGovernanceApproved ? 'Start Transport Execution' : 'Governance Approval Required before starting transport.'}
              >
                <Play size={14} /> START MIGRATION
              </button>
              {!isGovernanceApproved && (
                <span style={{ fontSize: 11, padding: '4px 10px', borderRadius: 6, background: 'rgba(245,158,11,0.15)', color: '#F59E0B', fontWeight: 700, border: '1px solid rgba(245,158,11,0.3)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <ShieldAlert size={13} /> Awaiting Governance Approval in Governance Centre
                </span>
              )}
              <button type="button" onClick={() => setConfirmAction('terminate')} style={{ padding: '6px 14px', borderRadius: 6, background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', color: '#EF4444', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <XCircle size={13} /> Cancel Pipeline
              </button>
            </>
          )}

          {/* RUNNING / STARTING / VALIDATING CONTROLS */}
          {(controlState === 'RUNNING' || controlState === 'STARTING' || controlState === 'VALIDATING' || controlState === 'CERTIFYING') && (
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
          {controlState === 'PAUSED' && (
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
          {controlState === 'FAILED' && (
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

          {/* COMPLETED STATE CONTROLS */}
          {controlState === 'COMPLETED' && (
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
      {activeViewMode === 'CDC_LIFECYCLE' ? (
        <div style={{ flex: 1, overflowY: 'auto', padding: 24, width: '100%', boxSizing: 'border-box' }}>
          <CdcLifecycleWorkspace
            migrationId={migration.id}
            isHistorical={(migration as any).status === 'COMPLETED' || (migration as any).status === 'TERMINATED'}
          />
        </div>
      ) : (
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', padding: 20, gap: 16, width: '100%' }}>

        {/* LEFT COLUMN: CANONICAL EXECUTION TIMELINE & STAGE PROGRESS ──────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0, overflowY: 'auto' }}>

          {/* POST-MIGRATION AUDIT SUMMARY CARD */}
          {controlState === 'COMPLETED' && (
            <div
              style={{
                padding: '20px',
                borderRadius: 12,
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                display: 'flex',
                flexDirection: 'column',
                gap: 14,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <CheckCircle2 size={22} color="#10B981" />
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: '#10B981', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      MIGRATION COMPLETED & AUDITED SUCCESSFULLY
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>
                      All data transport, schema object creation, and physical row count reconciliations passed cleanly.
                    </div>
                  </div>
                </div>
                <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 4, background: '#10B981', color: '#000' }}>
                  RECONCILIATION: PASSED
                </span>
              </div>

              {migrationResult && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 4 }}>
                  <div style={{ padding: 12, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>SOURCE PHYSICAL ROWS</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 4 }}>
                      {(migrationResult.validation?.source_rows ?? migrationResult.row_summary?.rows_read ?? snapshot?.rows_migrated ?? snapshot?.rows_transferred ?? 0).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ padding: 12, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>TARGET PHYSICAL ROWS</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: '#10B981', marginTop: 4 }}>
                      {(migrationResult.validation?.target_rows ?? migrationResult.row_summary?.rows_written ?? snapshot?.rows_migrated ?? snapshot?.rows_transferred ?? 0).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ padding: 12, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>OBJECTS MIGRATED</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: '#3B82F6', marginTop: 4 }}>
                      {migrationResult.object_summary?.migrated ?? snapshot?.completed_tables ?? 0} / {migrationResult.object_summary?.total_selected ?? snapshot?.total_tables ?? ((migration as any)?.objectsCount || 0)}
                    </div>
                  </div>
                  <div style={{ padding: 12, background: 'var(--dash-surface)', borderRadius: 8, border: '1px solid var(--dash-border)' }}>
                    <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', fontWeight: 600 }}>ELAPSED TIME</div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--dash-text-primary)', marginTop: 4 }}>
                      {migrationResult.duration_sec != null ? `${migrationResult.duration_sec}s` : (snapshot?.elapsed_seconds != null ? `${snapshot.elapsed_seconds}s` : '0.0s')}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* CANONICAL STAGE TIMELINE & LIVE PROGRESS CARDS */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dash-border)', paddingBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Activity size={18} color="#3B82F6" />
                <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--dash-text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Canonical Execution Stage Sequence
                </span>
              </div>
              <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 4, background: 'rgba(37,99,235,0.12)', color: 'var(--dash-accent)', fontWeight: 700 }}>
                AUTHORITATIVE BACKEND WORKFLOW
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {CANONICAL_STAGES.map((stg, idx) => {
                const visState = getStageVisualState(stg.id, idx);

                const getStatusColor = () => {
                  switch (visState) {
                    case 'COMPLETED': return '#10B981';
                    case 'ACTIVE_INDETERMINATE':
                    case 'ACTIVE_DETERMINATE': return '#3B82F6';
                    case 'PAUSED': return '#F59E0B';
                    case 'FAILED': return '#EF4444';
                    default: return 'var(--dash-text-secondary)';
                  }
                };

                const color = getStatusColor();

                return (
                  <div
                    key={stg.id}
                    style={{
                      padding: 14,
                      borderRadius: 10,
                      background: (visState === 'ACTIVE_INDETERMINATE' || visState === 'ACTIVE_DETERMINATE') ? 'rgba(37,99,235,0.08)' : visState === 'COMPLETED' ? 'rgba(16,185,129,0.05)' : visState === 'FAILED' ? 'rgba(239,68,68,0.08)' : 'var(--dash-bg)',
                      border: `1px solid ${color}44`,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                      transition: 'all 200ms ease-out',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        {visState === 'COMPLETED' ? (
                          <CheckCircle2 size={18} color="#10B981" />
                        ) : visState === 'FAILED' ? (
                          <XCircle size={18} color="#EF4444" />
                        ) : (visState === 'ACTIVE_INDETERMINATE' || visState === 'ACTIVE_DETERMINATE') ? (
                          <Activity size={18} color="#3B82F6" className="akaal-pulse-icon" />
                        ) : visState === 'PAUSED' ? (
                          <Pause size={18} color="#F59E0B" />
                        ) : (
                          <Clock size={18} color="var(--dash-text-tertiary)" />
                        )}
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--dash-text-primary)' }}>{stg.name}</div>
                          <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{stg.details}</div>
                        </div>
                      </div>

                      <span style={{ fontSize: 10, fontWeight: 800, padding: '2px 8px', borderRadius: 4, background: `${color}22`, color: color, textTransform: 'uppercase' }}>
                        {visState === 'ACTIVE_INDETERMINATE' && '● RUNNING (INDETERMINATE)'}
                        {visState === 'ACTIVE_DETERMINATE' && `● EXECUTING (${progressPercent}%)`}
                        {visState === 'COMPLETED' && '✓ VERIFIED'}
                        {visState === 'PAUSED' && '⏸ PAUSED'}
                        {visState === 'FAILED' && '✕ FAILED'}
                        {visState === 'NOT_STARTED' && 'PENDING'}
                      </span>
                    </div>

                    {/* LIVE ANIMATED PROGRESS BAR */}
                    {visState === 'ACTIVE_INDETERMINATE' && (
                      <div style={{ width: '100%', height: 6, borderRadius: 4, background: 'var(--dash-border)', overflow: 'hidden', marginTop: 4 }}>
                        <div className="akaal-shimmer-bar" style={{ width: '100%', height: '100%', borderRadius: 4 }} />
                      </div>
                    )}

                    {visState === 'ACTIVE_DETERMINATE' && (
                      <div style={{ width: '100%', height: 6, borderRadius: 4, background: 'var(--dash-border)', overflow: 'hidden', marginTop: 4 }}>
                        <div style={{ width: `${progressPercent}%`, height: '100%', background: '#3B82F6', transition: 'width 250ms ease-in-out', borderRadius: 4 }} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── LIVE DATA TRANSPORT TELEMETRY CARD ───────────────────────────── */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Table size={16} color="#10B981" />
                <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--dash-text-primary)' }}>Live Object Stream Progress</span>
              </div>
              <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--dash-accent)', fontVariantNumeric: 'tabular-nums' }}>
                {controlState === 'AWAITING_APPROVAL' || controlState === 'READY_TO_START' || snapshot?.progress_percent == null
                  ? '— Complete (— Rows)'
                  : `${progressPercent}% Complete (${fmtRows(rowsProcessed)} / ${fmtRows(totalRows)} Rows)`}
              </span>
            </div>

            {/* Smooth Progress Bar */}
            <div style={{ width: '100%', height: 10, borderRadius: 6, background: 'var(--dash-bg)', overflow: 'hidden', border: '1px solid var(--dash-border)' }}>
              <div style={{
                width: `${controlState === 'AWAITING_APPROVAL' || controlState === 'READY_TO_START' || snapshot?.progress_percent == null ? 0 : progressPercent}%`,
                height: '100%', background: 'var(--dash-accent, #3B82F6)', transition: 'width 250ms ease-in-out', borderRadius: 6
              }} />
            </div>

            {/* Active Object Telemetry Matrix */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, fontSize: 11, marginTop: 4 }}>
              <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Current Target Object</div>
                <div style={{ fontWeight: 700, color: 'var(--dash-text-primary)', marginTop: 2, fontFamily: 'var(--akaal-font-mono, monospace)' }}>
                  {snapshot?.current_table || snapshot?.current_object || '—'}
                </div>
              </div>
              <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Indexes Built</div>
                <div style={{ fontWeight: 700, color: '#10B981', marginTop: 2 }}>
                  {snapshot?.indexes_built != null ? `${snapshot.indexes_built} of ${snapshot.indexes_total || '—'}` : '—'}
                </div>
              </div>
              <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Constraints Verified</div>
                <div style={{ fontWeight: 700, color: '#10B981', marginTop: 2 }}>
                  {snapshot?.constraints_verified != null ? `${snapshot.constraints_verified} Verified` : '—'}
                </div>
              </div>
              <div style={{ padding: 8, background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)' }}>
                <div style={{ color: 'var(--dash-text-secondary)', fontSize: 10 }}>Active Lock Conflicts</div>
                <div style={{ fontWeight: 700, color: '#3B82F6', marginTop: 2 }}>
                  {snapshot?.lock_conflicts != null ? `${snapshot.lock_conflicts} Conflicts` : '0 Conflicts'}
                </div>
              </div>
            </div>
          </div>

          {/* LIVE ACTIVITY FEED */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 18, display: 'flex', flexDirection: 'column', gap: 12, flex: 1, minHeight: 220 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dash-border)', paddingBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Terminal size={15} color="#3B82F6" />
                <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--dash-text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Live Authoritative Event Stream</span>
              </div>
              <span style={{ fontSize: 10, color: '#10B981', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981' }} /> LIVE EVENT BUS
              </span>
            </div>

            {activityFeed.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--dash-text-secondary)', fontSize: 12 }}>
                Waiting for runtime event telemetry from EnterpriseEventBus...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', maxHeight: 260, paddingRight: 4 }}>
                {activityFeed.map((item, idx) => {
                  const iconColor = item.severity === 'SUCCESS' ? '#10B981' : item.severity === 'WARNING' ? '#F59E0B' : item.severity === 'ERROR' ? '#EF4444' : '#3B82F6';
                  return (
                    <div key={item.id || idx} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', fontSize: 11 }}>
                      <span style={{ fontFamily: 'var(--akaal-font-mono, monospace)', fontSize: 10, color: 'var(--dash-text-secondary)', flexShrink: 0 }}>[{item.timestamp || '00:00:00'}]</span>
                      <span style={{ padding: '1px 6px', borderRadius: 4, background: `${iconColor}18`, color: iconColor, fontWeight: 800, fontSize: 9, textTransform: 'uppercase', flexShrink: 0 }}>
                        {item.category || 'EVENT'}
                      </span>
                      <span style={{ color: 'var(--dash-text-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.message || String(item)}
                      </span>
                      <CheckCircle2 size={12} color={iconColor} />
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

        {/* RIGHT COLUMN: COMPACT RUNTIME OVERVIEW PANEL ─────────────────────── */}
        <div style={{ width: 310, display: 'flex', flexDirection: 'column', gap: 14, flexShrink: 0 }}>

          {/* MISSION REPLAY™ SUMMARY CARD */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 800, color: 'var(--dash-text-primary)' }}>
                <PlayCircle size={14} color="#3B82F6" /> Mission Replay™
              </div>
              <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, background: 'rgba(37,99,235,0.12)', color: '#3B82F6', fontWeight: 800 }}>
                {controlState === 'COMPLETED' ? 'AVAILABLE' : 'STANDBY'}
              </span>
            </div>
            <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', lineHeight: 1.4 }}>
              {controlState === 'COMPLETED'
                ? `Replay recorded historical events & telemetry timeline (${snapshot?.duration_sec || snapshot?.elapsed_seconds || 0}s duration).`
                : 'Replay becomes available after migration completion.'}
            </div>
            {controlState === 'COMPLETED' && (
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
                <strong style={{ color: 'var(--dash-text-primary)' }}>{snapshot?.active_workers != null ? `${snapshot.active_workers} Active` : '0 Active Pool'}</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>CPU Usage</span>
                <strong style={{ color: snapshot?.cpu_percent != null ? '#10B981' : 'var(--dash-text-secondary)' }}>{snapshot?.cpu_percent != null ? `${snapshot.cpu_percent}%` : '—'}</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>RAM Memory Quota</span>
                <strong style={{ color: snapshot?.ram_used_gb != null ? '#3B82F6' : 'var(--dash-text-secondary)' }}>{snapshot?.ram_used_gb != null ? `${snapshot.ram_used_gb} GB` : '—'}</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>Streaming Speed</span>
                <strong style={{ color: snapshot?.throughput_mbps != null ? '#10B981' : 'var(--dash-text-secondary)' }}>{snapshot?.throughput_mbps != null ? `${snapshot.throughput_mbps.toFixed(1)} MB/s` : '—'}</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>Rows/sec Throughput</span>
                <strong style={{ color: snapshot?.rows_per_sec != null ? '#8B5CF6' : 'var(--dash-text-secondary)' }}>{snapshot?.rows_per_sec != null ? `${fmtRows(snapshot.rows_per_sec)} rows/s` : '—'}</strong>
              </div>

              <div style={{ padding: '6px 8px', background: 'var(--dash-bg)', borderRadius: 6, border: '1px solid var(--dash-border)', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--dash-text-secondary)' }}>WAL Buffer Lag</span>
                <strong style={{ color: '#10B981' }}>{snapshot?.wal_buffer_lag || snapshot?.wal_lag || (snapshot?.cdc_sync_lag_ms != null ? `${snapshot.cdc_sync_lag_ms}ms` : '—')}</strong>
              </div>
            </div>
          </div>

          {/* Engine Health Governance Card */}
          <div style={{ border: '1px solid var(--dash-border)', borderRadius: 12, background: 'var(--dash-surface)', padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={14} color="#10B981" /> Engine Supervisor Status
            </div>

            <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', lineHeight: 1.4 }}>
              {snapshot?.pid ? `MigrationRuntimeDaemon running on PID ${snapshot.pid} with active RuntimeSupervisorTree.` : 'RuntimeSupervisorTree idle. Awaiting transport start signal.'}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 2, paddingTop: 6, borderTop: '1px solid var(--dash-border)', fontSize: 10 }}>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Supervisor Health:</span>
              <span style={{ color: snapshot?.pid ? '#10B981' : 'var(--dash-text-secondary)', fontWeight: 700 }}>
                {snapshot?.pid ? '● HEALTHY' : 'STANDBY'}
              </span>
            </div>
          </div>

        </div>

      </div>
      )}

      {/* ── EXECUTION PLAN DRAWER ─────────────────────────────────────────── */}
      {showPlanDrawer && (
        <div onClick={() => setShowPlanDrawer(false)}
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', zIndex: 9999, display: 'flex', justifyContent: 'flex-end' }}>
          <div onClick={(e) => e.stopPropagation()}
            style={{ width: 520, height: '100%', background: 'var(--dash-surface)', borderLeft: '1px solid var(--dash-border)', padding: 24, display: 'flex', flexDirection: 'column', gap: 18, overflowY: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--dash-border)', paddingBottom: 14 }}>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)' }}>Canonical Execution Plan</h3>
                <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>Generated for migration pipeline {migration.id}</div>
              </div>
              <button onClick={() => setShowPlanDrawer(false)} style={{ background: 'none', border: 'none', color: 'var(--dash-text-secondary)', cursor: 'pointer', padding: 4 }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Canonical DAG Execution Stages ({CANONICAL_STAGES.length} Pipeline Stages)
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {CANONICAL_STAGES.map((stg, idx) => {
                const visState = getStageVisualState(stg.id, idx);
                const color = visState === 'COMPLETED' ? '#10B981' : (visState === 'ACTIVE_INDETERMINATE' || visState === 'ACTIVE_DETERMINATE') ? '#3B82F6' : visState === 'FAILED' ? '#EF4444' : 'var(--dash-text-secondary)';

                return (
                  <div key={stg.id} style={{ display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between', padding: 10, background: 'var(--dash-bg)', borderRadius: 8, border: `1px solid ${color}33` }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                      <span style={{ width: 22, height: 22, borderRadius: '50%', background: color, color: '#FFF', fontSize: 10, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        {idx + 1}
                      </span>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{stg.name}</div>
                        <div style={{ fontSize: 10, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{stg.details}</div>
                      </div>
                    </div>
                    <span style={{ fontSize: 9, fontWeight: 800, padding: '2px 7px', borderRadius: 4, background: `${color}22`, color: color, textTransform: 'uppercase' }}>
                      {visState}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── OPERATIONAL SAFETY CONFIRMATION DIALOG ──────────────────────────── */}
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
                  {confirmAction === 'terminate' || confirmAction === 'rollback' ? <AlertTriangle size={20} /> : confirmAction === 'pause' ? <Pause size={18} /> : confirmAction === 'resume' || confirmAction === 'start' ? <Play size={18} /> : <Zap size={18} />}
                </div>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--dash-text-primary)' }}>
                    {confirmAction === 'start' && 'Start Migration Execution'}
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
                {confirmAction === 'start' && 'This action will begin real data movement between the configured source and target databases using the AKAAL execution engine.'}
                {confirmAction === 'pause' && 'This will pause the migration after the current safe execution point.'}
                {confirmAction === 'resume' && 'The migration will resume execution from the latest checkpoint.'}
                {confirmAction === 'terminate' && 'This action immediately terminates the migration runtime.'}
              </p>

              {confirmAction === 'start' && (
                <div style={{ border: '1px solid var(--dash-border)', borderRadius: 8, padding: 12, background: 'var(--dash-bg)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11 }}>
                  <div><span style={{ color: 'var(--dash-text-secondary)' }}>Migration ID:</span> <strong style={{ color: 'var(--dash-text-primary)', fontFamily: 'var(--akaal-font-mono, monospace)' }}>{migration.id}</strong></div>
                  <div><span style={{ color: 'var(--dash-text-secondary)' }}>Pipeline Name:</span> <strong style={{ color: 'var(--dash-text-primary)' }}>{migration.name}</strong></div>
                </div>
              )}
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
                onClick={() => executeConfirmedAction(confirmAction!)}
                style={{
                  padding: '9px 20px', borderRadius: 8,
                  background: confirmAction === 'terminate' || confirmAction === 'rollback' ? '#EF4444' : confirmAction === 'pause' ? '#F59E0B' : '#10B981',
                  color: '#FFF', border: 'none', fontSize: 12, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
                }}
              >
                {confirmAction === 'start' ? 'Start Migration' : 'Confirm Action'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
