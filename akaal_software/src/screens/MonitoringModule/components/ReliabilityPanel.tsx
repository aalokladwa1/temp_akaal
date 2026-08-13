import React from 'react';
import type { CanonicalMonitoringSnapshotDTO } from '../../../types/monitoring';
import styles from '../MonitoringModule.module.css';

interface ReliabilityPanelProps {
  snapshot: CanonicalMonitoringSnapshotDTO;
}

export const ReliabilityPanel: React.FC<ReliabilityPanelProps> = ({ snapshot }) => {
  const { checkpoints, retries, lob, connections } = snapshot;

  return (
    <div>
      <div className={styles.kpiGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Total Retries</div>
          <div className={styles.cardValue}>{retries.retry_count}</div>
          <div className={styles.cardSub}>Transient: {retries.transient_failures} | Permanent: {retries.permanent_failures}</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>WAL Checkpoints</div>
          <div className={styles.cardValue}>
            {checkpoints.current_checkpoint_id ? 'ACTIVE' : 'NONE'}
          </div>
          <div className={styles.cardSub}>Durable WAL SQLite CheckpointStore</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>LOB Chunks Processed</div>
          <div className={styles.cardValue}>{lob.lob_chunks_processed.toLocaleString()}</div>
          <div className={styles.cardSub}>Bytes: {lob.lob_bytes_processed.toLocaleString()} B</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Connection Pools</div>
          <div className={styles.cardValue}>
            {connections.source_pool_size} Src / {connections.target_pool_size} Tgt
          </div>
          <div className={styles.cardSub}>
            In Use: {connections.source_pool_in_use} Src / {connections.target_pool_in_use} Tgt
          </div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Reliability Authority</th>
              <th>Current Telemetry Value</th>
              <th>Invariant & Deduplication Guarantee</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Last Checkpoint ID</strong></td>
              <td><span className={styles.mono}>{checkpoints.current_checkpoint_id || '—'}</span></td>
              <td>Target commit strictly precedes WAL checkpoint advancement</td>
            </tr>
            <tr>
              <td><strong>Last Committed Key</strong></td>
              <td><span className={styles.mono}>{checkpoints.last_committed_key !== null ? String(checkpoints.last_committed_key) : '—'}</span></td>
              <td>Primary key High-Water-Mark (Sanitized)</td>
            </tr>
            <tr>
              <td><strong>Last Checkpoint Timestamp</strong></td>
              <td><span className={styles.mono}>{checkpoints.last_checkpoint_time || '—'}</span></td>
              <td>Durable persistence timestamp</td>
            </tr>
            <tr>
              <td><strong>Last Retry Reason</strong></td>
              <td><span>{retries.last_retry_reason || 'No failure retries recorded'}</span></td>
              <td>Exponential backoff classification</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
