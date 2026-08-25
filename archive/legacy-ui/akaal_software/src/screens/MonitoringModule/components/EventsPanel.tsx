import React from 'react';
import type { CanonicalMonitoringSnapshotDTO } from '../../../types/monitoring';
import styles from '../MonitoringModule.module.css';

interface EventsPanelProps {
  snapshot: CanonicalMonitoringSnapshotDTO;
}

export const EventsPanel: React.FC<EventsPanelProps> = ({ snapshot }) => {
  const { errors } = snapshot;

  return (
    <div>
      {errors.error_message && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: 16, borderRadius: 12, marginBottom: 20 }}>
          <div style={{ color: '#ef4444', fontWeight: 700, fontSize: 14, marginBottom: 4 }}>
            Execution Failure Recorded: {errors.failed_stage || 'Transport'}
          </div>
          <div style={{ color: 'var(--dash-text-primary, #F8FAFC)', fontSize: 13, fontFamily: 'monospace' }}>
            {errors.error_message}
          </div>
          {errors.failed_object && (
            <div style={{ color: 'var(--dash-text-secondary, #9CA3AF)', fontSize: 12, marginTop: 6 }}>
              Failed Object: {errors.failed_schema ? `${errors.failed_schema}.${errors.failed_object}` : errors.failed_object}
            </div>
          )}
        </div>
      )}

      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Category</th>
              <th>Severity</th>
              <th>Worker / Target</th>
              <th>Event Message</th>
            </tr>
          </thead>
          <tbody>
            {errors.logs_sample && errors.logs_sample.length > 0 ? (
              errors.logs_sample.map((evt, idx) => (
                <tr key={evt.id || idx}>
                  <td><span className={styles.mono}>{evt.timestamp || '—'}</span></td>
                  <td>{evt.category || 'SYSTEM'}</td>
                  <td>
                    <span className={`${styles.badge} ${evt.severity === 'ERROR' ? styles.badgeFailed : styles.badgeRunning}`}>
                      {evt.severity || 'INFO'}
                    </span>
                  </td>
                  <td><span className={styles.mono}>{evt.workerName || 'worker-1'}</span></td>
                  <td>{evt.message || '—'}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: '#94a3b8', padding: '24px' }}>
                  No execution events or log anomalies recorded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
