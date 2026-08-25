import React from 'react';
import styles from '../MonitoringModule/MonitoringModule.module.css';

export const SettingsModule: React.FC = () => {
  return (
    <div className={styles.container} id="settings-module-root">
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Workspace Settings & Preferences</h1>
          <p className={styles.subtitle}>Desktop Environment Configurations, IPC Engine Pipe & Storage Directories</p>
        </div>
      </div>

      <div className={styles.kpiGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>IPC Engine Pipe</div>
          <div className={styles.cardValue}>Connected</div>
          <div className={styles.cardSub}>\\.\pipe\akaal_engine</div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Storage Directory</div>
          <div className={styles.cardValue}>artifacts/</div>
          <div className={styles.cardSub}>SQLite WAL State & Checkpoints</div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Theme Mode</div>
          <div className={styles.cardValue}>Midnight Glass</div>
          <div className={styles.cardSub}>Enterprise Dark Accent</div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>Setting Category</th>
              <th>Configured Parameter</th>
              <th>Current Value</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>IPC Socket Pipe</strong></td>
              <td>Windows Named Pipe Name</td>
              <td><span className={styles.mono}>\\.\pipe\akaal_engine</span></td>
            </tr>
            <tr>
              <td><strong>State Persistence</strong></td>
              <td>SQLite WAL Database Path</td>
              <td><span className={styles.mono}>artifacts/state.db</span></td>
            </tr>
            <tr>
              <td><strong>Checkpoint Storage</strong></td>
              <td>Checkpoint Database Path</td>
              <td><span className={styles.mono}>artifacts/checkpoints.db</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
