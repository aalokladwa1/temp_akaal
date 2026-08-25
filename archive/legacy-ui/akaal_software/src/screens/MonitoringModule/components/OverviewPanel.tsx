import React from 'react';
import type { CanonicalMonitoringSnapshotDTO } from '../../../types/monitoring';
import styles from '../MonitoringModule.module.css';

interface OverviewPanelProps {
  snapshot: CanonicalMonitoringSnapshotDTO;
}

function fmtNum(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return val.toLocaleString();
}

function fmtDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return 'N/A';
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

export const OverviewPanel: React.FC<OverviewPanelProps> = ({ snapshot }) => {
  const { progress, throughput, workers, runtime, retries, backpressure } = snapshot;
  const isLive = snapshot.monitoring_mode === 'LIVE';

  return (
    <div>
      {/* ── KPI Grid ────────────────────────────────────────── */}
      <div className={styles.kpiGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Overall Progress</div>
          <div className={styles.cardValue}>{progress.progress_percent !== null ? `${progress.progress_percent.toFixed(1)}%` : '—'}</div>
          <div className={styles.progressTrack}>
            <div className={styles.progressFill} style={{ width: `${progress.progress_percent || 0}%` }} />
          </div>
          <div className={styles.cardSub}>
            {fmtNum(progress.rows_transferred)} / {fmtNum(progress.rows_total)} rows
          </div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Tables Completed</div>
          <div className={styles.cardValue}>
            {progress.completed_tables} / {progress.total_tables}
          </div>
          <div className={styles.cardSub}>
            Current: {progress.current_table || (runtime.status === 'COMPLETED' ? 'Completed' : '—')}
          </div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>{isLive ? 'Current Speed' : 'Average Speed'}</div>
          <div className={styles.cardValue}>
            {fmtNum(isLive ? throughput.rows_per_sec : throughput.average_rows_per_sec)}
          </div>
          <div className={styles.cardSub}>rows / sec</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>{isLive ? 'Current Throughput' : 'Average Throughput'}</div>
          <div className={styles.cardValue}>
            {isLive
              ? (throughput.throughput_mbps ? `${throughput.throughput_mbps.toFixed(1)} MB/s` : '—')
              : (throughput.average_throughput_mbps ? `${throughput.average_throughput_mbps.toFixed(1)} MB/s` : '—')}
          </div>
          <div className={styles.cardSub}>
            {isLive ? (throughput.eta_seconds ? `ETA: ${fmtDuration(throughput.eta_seconds)}` : 'ETA: —') : `Duration: ${fmtDuration(runtime.duration_seconds)}`}
          </div>
        </div>
      </div>

      {/* ── Operational Status Table ────────────────────────────── */}
      <div className={styles.tableContainer} style={{ marginTop: 16 }}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Domain</th>
              <th>Status / Value</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Worker Pool</strong></td>
              <td><span className={styles.mono}>{workers.active_workers} Active / {workers.configured_workers} Configured</span></td>
              <td>{workers.failed_workers > 0 ? `${workers.failed_workers} Workers Failed` : 'All workers healthy'}</td>
            </tr>
            <tr>
              <td><strong>Flow & Backpressure</strong></td>
              <td><span className={styles.mono}>{backpressure.backpressure_state}</span></td>
              <td>Queue Depth: {backpressure.queue_depth} / {backpressure.queue_capacity} (Throttle: {backpressure.throttle_delay_sec}s)</td>
            </tr>
            <tr>
              <td><strong>Reliability & Retries</strong></td>
              <td><span className={styles.mono}>{retries.retry_count} Retries</span></td>
              <td>Transient: {retries.transient_failures} | Permanent: {retries.permanent_failures}</td>
            </tr>
            <tr>
              <td><strong>Health Status</strong></td>
              <td>
                <span className={`${styles.badge} ${runtime.health_status === 'HEALTHY' ? styles.badgeRunning : runtime.health_status === 'ERROR' ? styles.badgeFailed : styles.badgePaused}`}>
                  {runtime.health_status}
                </span>
              </td>
              <td>Approval Status: {runtime.approval_status}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
