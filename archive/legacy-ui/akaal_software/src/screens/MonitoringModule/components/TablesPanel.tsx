import React from 'react';
import type { CanonicalMonitoringSnapshotDTO } from '../../../types/monitoring';
import styles from '../MonitoringModule.module.css';

interface TablesPanelProps {
  snapshot: CanonicalMonitoringSnapshotDTO;
}

export const TablesPanel: React.FC<TablesPanelProps> = ({ snapshot }) => {
  const { progress, partitions } = snapshot;

  return (
    <div>
      <div className={styles.kpiGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Total Tables</div>
          <div className={styles.cardValue}>{progress.total_tables}</div>
          <div className={styles.cardSub}>Discovered in Scout Catalog</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Completed Tables</div>
          <div className={styles.cardValue}>{progress.completed_tables}</div>
          <div className={styles.cardSub}>Fully committed to target</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Partitions Total</div>
          <div className={styles.cardValue}>{partitions.partitions_total}</div>
          <div className={styles.cardSub}>Range & Intra-table chunks</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Partitions Completed</div>
          <div className={styles.cardValue}>{partitions.partitions_completed}</div>
          <div className={styles.cardSub}>Active: {partitions.partitions_active}</div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Table Name</th>
              <th>Status</th>
              <th>Rows Migrated</th>
              <th>Total Rows</th>
              <th>Progress</th>
            </tr>
          </thead>
          <tbody>
            {progress.current_table ? (
              <tr>
                <td><strong>{progress.current_table}</strong></td>
                <td><span className={`${styles.badge} ${styles.badgeRunning}`}>IN_PROGRESS</span></td>
                <td><span className={styles.mono}>{progress.rows_transferred ? progress.rows_transferred.toLocaleString() : '0'}</span></td>
                <td><span className={styles.mono}>{progress.rows_total ? progress.rows_total.toLocaleString() : '—'}</span></td>
                <td>
                  <div className={styles.progressTrack} style={{ width: 120 }}>
                    <div className={styles.progressFill} style={{ width: `${progress.progress_percent || 0}%` }} />
                  </div>
                </td>
              </tr>
            ) : (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', color: '#94a3b8', padding: '24px' }}>
                  {snapshot.runtime.status === 'COMPLETED'
                    ? `All ${progress.total_tables} tables migrated and verified cleanly.`
                    : 'Table partition scheduler initialized.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
