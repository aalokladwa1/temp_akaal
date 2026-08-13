import React from 'react';
import styles from '../MonitoringModule/MonitoringModule.module.css';

export const ReportsModule: React.FC = () => {
  return (
    <div className={styles.container} id="reports-module-root">
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Digital Trust & Compliance Reports</h1>
          <p className={styles.subtitle}>SHA-256 Digital Trust Seals, Audit Trails & Compliance Verification</p>
        </div>
      </div>

      <div className={styles.kpiGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Generated Certificates</div>
          <div className={styles.cardValue}>12</div>
          <div className={styles.cardSub}>Cryptographically signed SHA-256 seals</div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Audit Log Entries</div>
          <div className={styles.cardValue}>1,428</div>
          <div className={styles.cardSub}>Immutable governance history</div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Compliance Score</div>
          <div className={styles.cardValue}>100%</div>
          <div className={styles.cardSub}>GATE 1-3 Governance Verified</div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Certificate ID</th>
              <th>Migration Run</th>
              <th>Generated At</th>
              <th>SHA-256 Seal Hash</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>CERT-2026-001</strong></td>
              <td>Oracle Production → PostgreSQL Analytics</td>
              <td>2026-08-13 14:20:00</td>
              <td><span className={styles.mono}>e3b0c44298fc1c149afbf4c8996fb92427ae41e4...</span></td>
              <td><span className={`${styles.badge} ${styles.badgeRunning}`}>VERIFIED</span></td>
            </tr>
            <tr>
              <td><strong>CERT-2026-002</strong></td>
              <td>SQL Server CRM → PostgreSQL CRM</td>
              <td>2026-08-12 09:15:22</td>
              <td><span className={styles.mono}>8f434346648f6b96df89dda901c5176b10a6d839...</span></td>
              <td><span className={`${styles.badge} ${styles.badgeRunning}`}>VERIFIED</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
