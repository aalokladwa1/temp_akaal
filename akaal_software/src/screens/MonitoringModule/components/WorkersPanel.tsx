import React from 'react';
import type { CanonicalMonitoringSnapshotDTO } from '../../../types/monitoring';
import styles from '../MonitoringModule.module.css';

interface WorkersPanelProps {
  snapshot: CanonicalMonitoringSnapshotDTO;
}

export const WorkersPanel: React.FC<WorkersPanelProps> = ({ snapshot }) => {
  const { workers } = snapshot;
  const isLive = snapshot.monitoring_mode === 'LIVE';

  return (
    <div>
      <div className={styles.kpiGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Configured Worker Pool</div>
          <div className={styles.cardValue}>{workers.configured_workers}</div>
          <div className={styles.cardSub}>ProcessPoolExecutor Workers</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Active Workers</div>
          <div className={styles.cardValue}>{workers.active_workers}</div>
          <div className={styles.cardSub}>{isLive ? 'Currently executing partition tasks' : '0 (Execution completed)'}</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Idle Workers</div>
          <div className={styles.cardValue}>{workers.idle_workers}</div>
          <div className={styles.cardSub}>Available capacity</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Worker Failures</div>
          <div className={styles.cardValue}>{workers.failed_workers}</div>
          <div className={styles.cardSub}>{workers.failed_workers > 0 ? 'Worker process exceptions logged' : '0 process crashes'}</div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Worker ID</th>
              <th>Execution Status</th>
              <th>Active Partition</th>
              <th>Rows Processed</th>
            </tr>
          </thead>
          <tbody>
            {workers.worker_statuses && workers.worker_statuses.length > 0 ? (
              workers.worker_statuses.map((w, idx) => (
                <tr key={w.worker_id || idx}>
                  <td><strong>{w.worker_id}</strong></td>
                  <td>
                    <span className={`${styles.badge} ${w.status === 'RUNNING' ? styles.badgeRunning : w.status === 'FAILED' ? styles.badgeFailed : styles.badgeCompleted}`}>
                      {w.status}
                    </span>
                  </td>
                  <td><span className={styles.mono}>{w.partition_id || '—'}</span></td>
                  <td><span className={styles.mono}>{w.rows_processed ? w.rows_processed.toLocaleString() : '—'}</span></td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', color: '#94a3b8', padding: '24px' }}>
                  {isLive ? 'Worker processes initialized. Tasks running in ParallelReplicationScheduler pool.' : 'Execution finished. ProcessPool workers released.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
