import React, { useState, useEffect } from 'react';
import { ipcService } from '../../../services/ipcService';

interface CdcRecoveryViewProps {
  migrationId: string;
  isHistorical?: boolean;
}

export const CdcRecoveryView: React.FC<CdcRecoveryViewProps> = ({ migrationId, isHistorical }) => {
  const [failbackData, setFailbackData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const resStr = await ipcService.invokeEngineCapability(
        'get_cdc_failback_status',
        JSON.stringify({ cdc_session_id: `cdc-${migrationId}`, migration_id: migrationId })
      );
      setFailbackData(typeof resStr === 'string' ? JSON.parse(resStr) : resStr);
    } catch (e: any) {
      console.warn('Failed to fetch failback status:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [migrationId]);

  const handleEvaluateFailback = async () => {
    setLoading(true);
    setActionMsg(null);
    setActionError(null);
    try {
      const resStr = await ipcService.invokeEngineCapability(
        'evaluate_cdc_failback',
        JSON.stringify({ cdc_session_id: `cdc-${migrationId}`, migration_id: migrationId })
      );
      const data = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
      setFailbackData(data);
      setActionMsg(`Failback evaluation completed: ${data.status} (${data.classification || ''})`);
    } catch (e: any) {
      setActionError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteFailback = async () => {
    if (isHistorical) return;
    setLoading(true);
    setActionMsg(null);
    setActionError(null);
    try {
      const resStr = await ipcService.invokeEngineCapability(
        'execute_cdc_failback',
        JSON.stringify({ cdc_session_id: `cdc-${migrationId}`, migration_id: migrationId })
      );
      const data = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
      setActionMsg(`Failback execution completed: ${data.status || 'OK'}`);
      fetchStatus();
    } catch (e: any) {
      setActionError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const isSafe = failbackData?.safe_auto_failback === true;
  const status = failbackData?.status || 'NOT_EVALUATED';
  const role = failbackData?.current_role || 'SOURCE_PRIMARY';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--dash-card-bg)', padding: '16px 20px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>
            Failback & Disaster Recovery Management
          </div>
          <div style={{ fontSize: '13px', color: 'var(--dash-text-secondary)' }}>
            Primary Role Authority • Divergence Tracking • Governed Failback Execution
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleEvaluateFailback}
            disabled={loading}
            style={{ padding: '7px 14px', borderRadius: '6px', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', border: '1px solid var(--dash-border)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
          >
            Evaluate Failback
          </button>
          <button
            onClick={handleExecuteFailback}
            disabled={isHistorical || loading || !isSafe}
            style={{
              padding: '7px 14px',
              borderRadius: '6px',
              background: isSafe ? '#dc2626' : '#4b5563',
              color: '#fff',
              border: 'none',
              cursor: isHistorical || loading || !isSafe ? 'not-allowed' : 'pointer',
              fontSize: '13px',
              fontWeight: 600,
            }}
          >
            Execute Failback
          </button>
        </div>
      </div>

      {actionMsg && (
        <div style={{ background: 'rgba(34, 197, 94, 0.1)', border: '1px solid #22c55e', color: '#22c55e', padding: '10px 14px', borderRadius: '6px', fontSize: '13px' }}>
          {actionMsg}
        </div>
      )}

      {actionError && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#ef4444', padding: '10px 14px', borderRadius: '6px', fontSize: '13px' }}>
          {actionError}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' }}>
        <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>CURRENT PRIMARY ROLE</div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--dash-text-primary)' }}>{role}</div>
        </div>
        <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>FAILBACK ELIGIBILITY</div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: isSafe ? '#22c55e' : '#ef4444' }}>{status}</div>
        </div>
        <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>CLASSIFICATION</div>
          <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>{failbackData?.classification || 'N/A'}</div>
        </div>
      </div>
    </div>
  );
};
