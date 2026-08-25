import React, { useState, useEffect } from 'react';
import { ipcService } from '../../../services/ipcService';
import { CheckCircle2, XCircle } from 'lucide-react';

interface CdcCutoverViewProps {
  migrationId: string;
  isHistorical?: boolean;
}

export const CdcCutoverView: React.FC<CdcCutoverViewProps> = ({ migrationId, isHistorical }) => {
  const [readiness, setReadiness] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchReadiness = async () => {
    try {
      setLoading(true);
      const resStr = await ipcService.invokeEngineCapability(
        'get_cdc_cutover_readiness',
        JSON.stringify({ cdc_session_id: `cdc-${migrationId}`, migration_id: migrationId })
      );
      setReadiness(typeof resStr === 'string' ? JSON.parse(resStr) : resStr);
    } catch (e: any) {
      console.warn('Failed to fetch cutover readiness:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReadiness();
  }, [migrationId]);

  const executeAction = async (capability: string, payload: any = {}) => {
    if (isHistorical) return;
    setLoading(true);
    setActionMsg(null);
    setActionError(null);
    try {
      const fullPayload = {
        migration_id: migrationId,
        cdc_session_id: `cdc-${migrationId}`,
        job_id: 'job-p310',
        run_id: 'run-p310',
        ...payload,
      };
      const resStr = await ipcService.invokeEngineCapability(capability, JSON.stringify(fullPayload));
      const data = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
      setActionMsg(`Action '${capability}' completed: ${data.status || 'OK'}`);
      fetchReadiness();
    } catch (e: any) {
      setActionError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const isReady = readiness?.ready === true;
  const gates = readiness?.gates || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Overview Card */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--dash-card-bg)', padding: '18px 22px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        <div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: isReady ? '#22c55e' : '#ef4444' }}>
            Cutover Readiness: {isReady ? 'READY FOR CUTOVER' : 'BLOCKED'}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--dash-text-secondary)', marginTop: '4px' }}>
            17-Gate Readiness Evaluation • Single-Primary Commit Point • Governed Quiescence
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => executeAction('prepare_cdc_cutover')}
            disabled={isHistorical || loading}
            style={{ padding: '7px 14px', borderRadius: '6px', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', border: '1px solid var(--dash-border)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
          >
            Prepare Plan
          </button>
          <button
            onClick={() => executeAction('begin_cdc_source_quiescence')}
            disabled={isHistorical || loading}
            style={{ padding: '7px 14px', borderRadius: '6px', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', border: '1px solid var(--dash-border)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
          >
            Source Quiescence
          </button>
          <button
            onClick={() => executeAction('run_cdc_final_drain')}
            disabled={isHistorical || loading}
            style={{ padding: '7px 14px', borderRadius: '6px', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', border: '1px solid var(--dash-border)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
          >
            Final Drain
          </button>
          <button
            onClick={() => executeAction('run_cdc_final_validation')}
            disabled={isHistorical || loading}
            style={{ padding: '7px 14px', borderRadius: '6px', background: 'var(--dash-card-bg)', color: 'var(--dash-text-primary)', border: '1px solid var(--dash-border)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
          >
            Final Validation
          </button>
          <button
            onClick={() => executeAction('commit_cdc_cutover')}
            disabled={isHistorical || loading || !isReady}
            style={{
              padding: '7px 16px',
              borderRadius: '6px',
              background: isReady ? 'var(--dash-accent)' : '#4b5563',
              color: '#fff',
              border: 'none',
              cursor: isHistorical || loading || !isReady ? 'not-allowed' : 'pointer',
              fontSize: '13px',
              fontWeight: 700,
            }}
          >
            Commit Cutover
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

      {/* 17-Gate Readiness Checklist */}
      <div style={{ background: 'var(--dash-card-bg)', padding: '20px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        <div style={{ fontSize: '15px', fontWeight: 600, marginBottom: '14px' }}>
          Canonical Cutover Readiness Gates
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
          {Object.entries(gates).map(([gateId, g]: [string, any]) => {
            const isGateReady = g.status === 'READY';
            return (
              <div
                key={gateId}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '12px',
                  borderRadius: '6px',
                  background: 'rgba(255,255,255,0.02)',
                  border: `1px solid ${isGateReady ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.3)'}`,
                }}
              >
                {isGateReady ? (
                  <CheckCircle2 size={18} color="#22c55e" style={{ flexShrink: 0, marginTop: '2px' }} />
                ) : (
                  <XCircle size={18} color="#ef4444" style={{ flexShrink: 0, marginTop: '2px' }} />
                )}
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: isGateReady ? 'var(--dash-text-primary)' : '#ef4444' }}>
                    {gateId.replace(/_/g, ' ').toUpperCase()}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginTop: '2px' }}>
                    {g.reason}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
