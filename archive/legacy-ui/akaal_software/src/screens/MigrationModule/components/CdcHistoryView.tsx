import React, { useState, useEffect } from 'react';
import { ipcService } from '../../../services/ipcService';
import { RefreshCw } from 'lucide-react';
import styles from '../MigrationModule.module.css';

interface CdcHistoryViewProps {
  migrationId: string;
}

export const CdcHistoryView: React.FC<CdcHistoryViewProps> = ({ migrationId }) => {
  const [historyData, setHistoryData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const resStr = await ipcService.invokeEngineCapability(
        'get_cdc_migration_history',
        JSON.stringify({ migration_id: migrationId })
      );
      setHistoryData(typeof resStr === 'string' ? JSON.parse(resStr) : resStr);
    } catch (e: any) {
      console.warn('Failed to fetch lifecycle history:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [migrationId]);

  const history = historyData?.history || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--dash-card-bg)', padding: '16px 20px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        <div>
          <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>
            Lifecycle & Operation Audit History
          </div>
          <div style={{ fontSize: '13px', color: 'var(--dash-text-secondary)', marginTop: '4px' }}>
            Durable audit trail from CentralStateStore • Immutable historical log
          </div>
        </div>

        <button
          onClick={fetchHistory}
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

      <div style={{ background: 'var(--dash-card-bg)', padding: '20px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        {history.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--dash-text-secondary)' }}>
            No lifecycle transitions recorded yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {history.map((h: any, idx: number) => (
              <div key={idx} style={{ display: 'flex', gap: '14px', alignItems: 'flex-start', borderLeft: '2px solid var(--dash-accent)', paddingLeft: '14px', position: 'relative' }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>
                    {h.from_state ? `${h.from_state} → ${h.to_state}` : h.to_state}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)', marginTop: '2px' }}>
                    {h.reason} • {new Date(h.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
