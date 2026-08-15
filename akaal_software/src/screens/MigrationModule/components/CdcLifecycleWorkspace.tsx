import React, { useState, useEffect } from 'react';
import { ipcService } from '../../../services/ipcService';
import {
  CheckCircle2,
  Circle,
  Clock,
  ShieldCheck,
  Zap,
  RefreshCw,
  Layers,
  RotateCcw,
  Activity,
} from 'lucide-react';
import { CdcValidationView } from './CdcValidationView';
import { CdcCutoverView } from './CdcCutoverView';
import { CdcRecoveryView } from './CdcRecoveryView';
import { CdcGovernanceView } from './CdcGovernanceView';
import { CdcHistoryView } from './CdcHistoryView';
import styles from '../MigrationModule.module.css';

interface CdcLifecycleWorkspaceProps {
  migrationId: string;
  isHistorical?: boolean;
}

export type LifecycleTab = 'overview' | 'validation' | 'cutover' | 'recovery' | 'governance' | 'history';

export const CdcLifecycleWorkspace: React.FC<CdcLifecycleWorkspaceProps> = ({ migrationId, isHistorical }) => {
  const [activeTab, setActiveTab] = useState<LifecycleTab>('overview');
  const [lifecycle, setLifecycle] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchLifecycle = async () => {
    try {
      setLoading(true);
      const resStr = await ipcService.invokeEngineCapability(
        'get_migration_lifecycle',
        JSON.stringify({ migration_id: migrationId })
      );
      setLifecycle(typeof resStr === 'string' ? JSON.parse(resStr) : resStr);
    } catch (e: any) {
      console.warn('Failed to fetch lifecycle:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLifecycle();
  }, [migrationId]);

  const currentState = lifecycle?.current_state || 'CONFIGURING';

  const stages = [
    { id: 'CONFIGURING', label: 'Configuration' },
    { id: 'PREFLIGHT', label: 'Preflight' },
    { id: 'SCHEMA_PREPARING', label: 'Schema' },
    { id: 'INITIAL_LOAD', label: 'Initial Load' },
    { id: 'INITIAL_VALIDATION', label: 'Initial Validation' },
    { id: 'CDC_SYNCHRONIZED', label: 'CDC Sync' },
    { id: 'PRE_CUTOVER_VALIDATING', label: 'Pre-Cutover Val' },
    { id: 'CUTOVER_READY', label: 'Cutover Ready' },
    { id: 'FINAL_DRAIN', label: 'Final Drain' },
    { id: 'TARGET_PRIMARY', label: 'Target Primary' },
    { id: 'COMPLETED', label: 'Completed' },
  ];

  const currentIdx = stages.findIndex((s) => s.id === currentState);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Lifecycle Flow Bar */}
      <div style={{ background: 'var(--dash-card-bg)', padding: '18px 22px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>
              End-to-End Migration Lifecycle
            </div>
            <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)' }}>
              Current State: <span style={{ fontWeight: 700, color: 'var(--dash-accent)' }}>{currentState}</span>
            </div>
          </div>
          <button
            onClick={fetchLifecycle}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              background: 'transparent',
              color: 'var(--dash-text-secondary)',
              border: '1px solid var(--dash-border)',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            <RefreshCw size={12} className={loading ? styles.spinIcon : ''} /> Refresh Lifecycle
          </button>
        </div>

        {/* Step Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', overflowX: 'auto', paddingBottom: '6px' }}>
          {stages.map((st, idx) => {
            const isDone = currentIdx > idx;
            const isCurrent = currentIdx === idx;
            return (
              <React.Fragment key={st.id}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                  {isDone ? (
                    <CheckCircle2 size={16} color="#22c55e" />
                  ) : isCurrent ? (
                    <Circle size={16} color="var(--dash-accent)" fill="var(--dash-accent)" />
                  ) : (
                    <Circle size={16} color="var(--dash-text-secondary)" />
                  )}
                  <span style={{ fontSize: '12px', fontWeight: isCurrent ? 700 : 400, color: isCurrent ? 'var(--dash-text-primary)' : 'var(--dash-text-secondary)' }}>
                    {st.label}
                  </span>
                </div>
                {idx < stages.length - 1 && (
                  <div style={{ flex: 1, minWidth: '16px', height: '1px', background: isDone ? '#22c55e' : 'var(--dash-border)', margin: '0 8px' }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Primary Sub-Tab Navigation */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--dash-border)', paddingBottom: '8px' }}>
        {[
          { id: 'overview', label: 'Overview', icon: <Layers size={14} /> },
          { id: 'validation', label: 'Validation & Reconciliation', icon: <ShieldCheck size={14} /> },
          { id: 'cutover', label: 'Controlled Cutover', icon: <Zap size={14} /> },
          { id: 'recovery', label: 'Failback & Recovery', icon: <RotateCcw size={14} /> },
          { id: 'governance', label: 'Governance & Approvals', icon: <Activity size={14} /> },
          { id: 'history', label: 'Audit History', icon: <Clock size={14} /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === tab.id ? 'var(--dash-card-bg)' : 'transparent',
              color: activeTab === tab.id ? 'var(--dash-accent)' : 'var(--dash-text-secondary)',
              fontWeight: activeTab === tab.id ? 600 : 400,
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
          <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>LIFECYCLE STAGE</div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--dash-text-primary)' }}>{currentState}</div>
          </div>
          <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>CUTOVER READINESS</div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: currentState === 'CUTOVER_READY' ? '#22c55e' : '#eab308' }}>
              {currentState === 'CUTOVER_READY' ? 'READY' : 'GATED'}
            </div>
          </div>
          <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>AUTHORITY</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>CentralStateStore (Durable)</div>
          </div>
        </div>
      )}

      {activeTab === 'validation' && (
        <CdcValidationView migrationId={migrationId} isHistorical={isHistorical} />
      )}

      {activeTab === 'cutover' && (
        <CdcCutoverView migrationId={migrationId} isHistorical={isHistorical} />
      )}

      {activeTab === 'recovery' && (
        <CdcRecoveryView migrationId={migrationId} isHistorical={isHistorical} />
      )}

      {activeTab === 'governance' && (
        <CdcGovernanceView migrationId={migrationId} isHistorical={isHistorical} />
      )}

      {activeTab === 'history' && (
        <CdcHistoryView migrationId={migrationId} />
      )}
    </div>
  );
};
