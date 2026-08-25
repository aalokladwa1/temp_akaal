import React from 'react';
import styles from '../MonitoringModule/MonitoringModule.module.css';

export const AdministrationModule: React.FC = () => {
  return (
    <div className={styles.container} id="admin-module-root">
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Administration & Governance</h1>
          <p className={styles.subtitle}>Role-Based Access Control (RBAC), Custody Gates & Identity Providers</p>
        </div>
      </div>

      <div className={styles.kpiGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Active Custodians</div>
          <div className={styles.cardValue}>4 Users</div>
          <div className={styles.cardSub}>Multi-custody approval quorum</div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Approval Gates</div>
          <div className={styles.cardValue}>GATE 1 — 3</div>
          <div className={styles.cardSub}>Enforced fail-closed policy</div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Identity Provider</div>
          <div className={styles.cardValue}>Active Directory</div>
          <div className={styles.cardSub}>SAML 2.0 / OIDC SSO Connected</div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>User Name</th>
              <th>Role</th>
              <th>Custody Level</th>
              <th>Gate Approvals</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Aalok Ladwa (Admin)</strong></td>
              <td>System Administrator</td>
              <td>Level 3 (Primary Custodian)</td>
              <td>GATE 1, GATE 2, GATE 3</td>
              <td><span className={`${styles.badge} ${styles.badgeRunning}`}>ACTIVE</span></td>
            </tr>
            <tr>
              <td><strong>Enterprise Security Officer</strong></td>
              <td>Compliance Auditor</td>
              <td>Level 2 (Security Signoff)</td>
              <td>GATE 2</td>
              <td><span className={`${styles.badge} ${styles.badgeRunning}`}>ACTIVE</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
