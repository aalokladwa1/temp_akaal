import React from 'react';
import type { CanonicalMonitoringSnapshotDTO } from '../../../types/monitoring';
import styles from '../MonitoringModule.module.css';

interface PerformancePanelProps {
  snapshot: CanonicalMonitoringSnapshotDTO;
}

function fmtNum(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return val.toLocaleString();
}

export const PerformancePanel: React.FC<PerformancePanelProps> = ({ snapshot }) => {
  const { throughput, batching, resources, backpressure } = snapshot;
  const isLive = snapshot.monitoring_mode === 'LIVE';

  return (
    <div>
      <div className={styles.kpiGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>{isLive ? 'Live Speed' : 'Peak Speed'}</div>
          <div className={styles.cardValue}>
            {fmtNum(isLive ? throughput.rows_per_sec : throughput.peak_rows_per_sec)}
          </div>
          <div className={styles.cardSub}>rows / sec</div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>{isLive ? 'Live Bandwidth' : 'Peak Throughput'}</div>
          <div className={styles.cardValue}>
            {isLive
              ? (throughput.bandwidth_formatted || '—')
              : (throughput.peak_throughput_mbps ? `${throughput.peak_throughput_mbps.toFixed(1)} MB/s` : '—')}
          </div>
          <div className={styles.cardSub}>
            {isLive ? 'Instantaneous Rate' : 'Peak Recorded Batch Rate'}
          </div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Batch Sizing</div>
          <div className={styles.cardValue}>{fmtNum(batching.current_batch_size)}</div>
          <div className={styles.cardSub}>
            Recommended: {fmtNum(batching.recommended_batch_size)} | Fetch: {fmtNum(batching.fetch_size)}
          </div>
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>{isLive ? 'Host CPU' : 'CPU History'}</div>
          <div className={styles.cardValue}>
            {isLive ? (resources.cpu_percent !== null ? `${resources.cpu_percent.toFixed(1)}%` : '—') : 'N/A'}
          </div>
          <div className={styles.cardSub}>
            {isLive ? 'psutil System Probes' : 'Ephemerally probe-backed during LIVE mode'}
          </div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Performance Parameter</th>
              <th>Current Metric Value</th>
              <th>Operational Bounds & Semantics</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Batch Latency</strong></td>
              <td><span className={styles.mono}>{batching.batch_latency_ms !== null ? `${batching.batch_latency_ms} ms` : '—'}</span></td>
              <td>Average round-trip duration per target commit batch</td>
            </tr>
            <tr>
              <td><strong>Flow Queue Depth</strong></td>
              <td><span className={styles.mono}>{backpressure.queue_depth} / {backpressure.queue_capacity}</span></td>
              <td>Bounded queue depth watermarking state: {backpressure.backpressure_state}</td>
            </tr>
            <tr>
              <td><strong>Throttling Delay</strong></td>
              <td><span className={styles.mono}>{backpressure.throttle_delay_sec} s</span></td>
              <td>Pacing sleep delay applied under queue saturation</td>
            </tr>
            <tr>
              <td><strong>Host RAM Utilization</strong></td>
              <td><span className={styles.mono}>{isLive ? (resources.ram_used_gb !== null ? `${resources.ram_used_gb.toFixed(2)} GB` : '—') : 'N/A'}</span></td>
              <td>Host system memory in use (Live probe)</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
