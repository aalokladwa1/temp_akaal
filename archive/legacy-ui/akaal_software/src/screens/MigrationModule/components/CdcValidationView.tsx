import React, { useState, useEffect } from 'react';
import { ipcService } from '../../../services/ipcService';
import {
  RefreshCw,
  Play,
} from 'lucide-react';
import styles from '../MigrationModule.module.css';

interface CdcValidationViewProps {
  migrationId: string;
  isHistorical?: boolean;
}

export const CdcValidationView: React.FC<CdcValidationViewProps> = ({ migrationId, isHistorical }) => {
  const [valData, setValData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedLevel, setSelectedLevel] = useState<string>('LEVEL_2_TABLE_CHECKSUM');
  const [activeTab, setActiveTab] = useState<'summary' | 'tables' | 'mismatches' | 'repair'>('summary');
  const [repairMsg, setRepairMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const resStr = await ipcService.invokeEngineCapability(
        'get_cdc_validation_status',
        JSON.stringify({ cdc_session_id: `cdc-${migrationId}`, migration_id: migrationId })
      );
      setValData(typeof resStr === 'string' ? JSON.parse(resStr) : resStr);
    } catch (e: any) {
      console.warn('Failed to fetch validation status:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [migrationId]);

  const handleRunValidation = async (level: string) => {
    if (isHistorical) return;
    setLoading(true);
    setRepairMsg(null);
    setErrorMsg(null);
    try {
      const resStr = await ipcService.invokeEngineCapability(
        'start_cdc_validation',
        JSON.stringify({
          migration_id: migrationId,
          cdc_session_id: `cdc-${migrationId}`,
          level,
        })
      );
      const data = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
      setValData(data);
      setRepairMsg(`Validation run '${data.validation_run_id}' completed with status: ${data.status}`);
    } catch (e: any) {
      setErrorMsg(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSafeRepair = async (reconId: string) => {
    if (isHistorical) return;
    setLoading(true);
    setRepairMsg(null);
    setErrorMsg(null);
    try {
      const resStr = await ipcService.invokeEngineCapability(
        'request_reconciliation_repair',
        JSON.stringify({
          migration_id: migrationId,
          cdc_session_id: `cdc-${migrationId}`,
          reconciliation_id: reconId,
          fencing_epoch: 1,
        })
      );
      const data = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
      setRepairMsg(`Repair action completed: ${data.status} (${data.repair_status || ''})`);
      fetchStatus();
    } catch (e: any) {
      setErrorMsg(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const status = valData?.status || 'PENDING';
  const isMatched = status === 'MATCHED';
  const isMismatched = status === 'MISMATCHED';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--dash-card-bg)', padding: '16px 20px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>
            CDC Stream Validation & Reconciliation
          </div>
          <div style={{ fontSize: '13px', color: 'var(--dash-text-secondary)' }}>
            Logically consistent verification window • Progressive Levels 1–5 • Governed Remediation
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            disabled={isHistorical || loading}
            style={{ padding: '6px 12px', borderRadius: '6px', fontSize: '13px' }}
          >
            <option value="LEVEL_1_ROW_COUNT">Level 1: Row Counts</option>
            <option value="LEVEL_2_TABLE_CHECKSUM">Level 2: Table Checksum (Merkle)</option>
            <option value="LEVEL_3_ROW_RECONCILIATION">Level 3: Row Reconciliation</option>
            <option value="LEVEL_4_COLUMN_DIAGNOSIS">Level 4: Column Diagnosis</option>
            <option value="LEVEL_5_POST_REPAIR_REVALIDATION">Level 5: Post-Repair Revalidation</option>
          </select>

          <button
            onClick={() => handleRunValidation(selectedLevel)}
            disabled={isHistorical || loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              borderRadius: '6px',
              background: 'var(--dash-accent)',
              color: '#fff',
              border: 'none',
              cursor: isHistorical || loading ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '13px',
            }}
          >
            <Play size={14} /> Run Validation
          </button>

          <button
            onClick={fetchStatus}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 12px',
              borderRadius: '6px',
              background: 'transparent',
              color: 'var(--dash-text-secondary)',
              border: '1px solid var(--dash-border)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <RefreshCw size={14} className={loading ? styles.spinIcon : ''} /> Refresh
          </button>
        </div>
      </div>

      {repairMsg && (
        <div style={{ background: 'rgba(34, 197, 94, 0.1)', border: '1px solid #22c55e', color: '#22c55e', padding: '10px 14px', borderRadius: '6px', fontSize: '13px' }}>
          {repairMsg}
        </div>
      )}

      {errorMsg && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', color: '#ef4444', padding: '10px 14px', borderRadius: '6px', fontSize: '13px' }}>
          {errorMsg}
        </div>
      )}

      {/* Sub-tab Navigation */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--dash-border)', paddingBottom: '8px' }}>
        {[
          { id: 'summary', label: 'Summary' },
          { id: 'tables', label: `Tables (${valData?.tables_validated?.length || 0})` },
          { id: 'mismatches', label: `Divergences (${valData?.total_mismatches || 0})` },
          { id: 'repair', label: 'Governed Repair' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === t.id ? 'var(--dash-card-bg)' : 'transparent',
              color: activeTab === t.id ? 'var(--dash-accent)' : 'var(--dash-text-secondary)',
              fontWeight: activeTab === t.id ? 600 : 400,
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Contents */}
      {activeTab === 'summary' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
          <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>VALIDATION STATUS</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: isMatched ? '#22c55e' : (isMismatched ? '#ef4444' : '#eab308') }}>
              {status}
            </div>
          </div>
          <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>TABLES MATCHED</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--dash-text-primary)' }}>
              {valData?.matched_tables || 0} / {valData?.total_tables || 0}
            </div>
          </div>
          <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>TOTAL MISMATCHES</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: (valData?.total_mismatches || 0) > 0 ? '#ef4444' : '#22c55e' }}>
              {valData?.total_mismatches || 0}
            </div>
          </div>
          <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
            <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginBottom: '4px' }}>CONSISTENCY WINDOW</div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: valData?.window?.is_consistent ? '#22c55e' : '#ef4444' }}>
              {valData?.window?.is_consistent ? 'FROZEN & CONSISTENT' : 'MOVING / BLOCKED'}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'tables' && (
        <div style={{ background: 'var(--dash-card-bg)', borderRadius: '8px', border: '1px solid var(--dash-border)', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--dash-border)', color: 'var(--dash-text-secondary)' }}>
                <th style={{ padding: '10px 14px' }}>Table Name</th>
                <th style={{ padding: '10px 14px' }}>Status</th>
                <th style={{ padding: '10px 14px' }}>Source Rows</th>
                <th style={{ padding: '10px 14px' }}>Target Rows</th>
                <th style={{ padding: '10px 14px' }}>Checksum Match</th>
                <th style={{ padding: '10px 14px' }}>Mismatches</th>
              </tr>
            </thead>
            <tbody>
              {(valData?.tables_validated || []).map((t: any, idx: number) => (
                <tr key={idx} style={{ borderBottom: '1px solid var(--dash-border)' }}>
                  <td style={{ padding: '10px 14px', fontWeight: 600 }}>{t.table_name}</td>
                  <td style={{ padding: '10px 14px', color: t.status === 'MATCHED' ? '#22c55e' : '#ef4444' }}>{t.status}</td>
                  <td style={{ padding: '10px 14px' }}>{t.source_row_count}</td>
                  <td style={{ padding: '10px 14px' }}>{t.target_row_count}</td>
                  <td style={{ padding: '10px 14px' }}>{t.source_checksum === t.target_checksum ? 'MATCHED' : 'DIFFER'}</td>
                  <td style={{ padding: '10px 14px', color: t.mismatch_count > 0 ? '#ef4444' : 'inherit' }}>{t.mismatch_count}</td>
                </tr>
              ))}
              {(!valData?.tables_validated || valData.tables_validated.length === 0) && (
                <tr>
                  <td colSpan={6} style={{ padding: '20px', textAlign: 'center', color: 'var(--dash-text-secondary)' }}>
                    No tables validated yet. Run Level 1 or Level 2 validation.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'mismatches' && (
        <div style={{ background: 'var(--dash-card-bg)', borderRadius: '8px', border: '1px solid var(--dash-border)', padding: '16px' }}>
          {(valData?.reconciliations || []).length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px', color: 'var(--dash-text-secondary)' }}>
              No entity divergences detected in active stream.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {valData.reconciliations.map((r: any, idx: number) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid var(--dash-border)' }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#ef4444', fontSize: '13px' }}>{r.mismatch_class} — {r.table_name}</div>
                    <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)' }}>Key: {r.entity_key_fingerprint} • State: {r.resolution_state}</div>
                  </div>
                  {!isHistorical && r.repair_action && (
                    <button
                      onClick={() => handleSafeRepair(r.reconciliation_id)}
                      style={{ padding: '6px 12px', background: 'var(--dash-accent)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                    >
                      Repair: {r.repair_action}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'repair' && (
        <div style={{ background: 'var(--dash-card-bg)', padding: '16px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
          <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '6px' }}>Governed Remediation & Safe Repair Policy</div>
          <div style={{ fontSize: '13px', color: 'var(--dash-text-secondary)', lineHeight: 1.5 }}>
            All automatic repairs are identity-bound, idempotent, fenced, and validation-backed. Ambiguous or destructive divergence automatically requires manual governance approval before execution.
          </div>
        </div>
      )}
    </div>
  );
};
