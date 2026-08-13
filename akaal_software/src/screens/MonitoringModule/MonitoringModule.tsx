import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { CanonicalMonitoringSnapshotDTO } from '../../types/monitoring';
import { ipcService } from '../../services/ipcService';
import { OverviewPanel } from './components/OverviewPanel';
import { PerformancePanel } from './components/PerformancePanel';
import { WorkersPanel } from './components/WorkersPanel';
import { TablesPanel } from './components/TablesPanel';
import { ReliabilityPanel } from './components/ReliabilityPanel';
import { EventsPanel } from './components/EventsPanel';
import styles from './MonitoringModule.module.css';

type TabType = 'overview' | 'performance' | 'workers' | 'tables' | 'reliability' | 'events';

export const MonitoringModule: React.FC = () => {
  const [selectedMigId, setSelectedMigId] = useState<string>('mig-default');
  const [availableMigrations, setAvailableMigrations] = useState<Array<{ id: string; label: string; status: string }>>([
    { id: 'mig-default', label: 'Oracle Production → PostgreSQL Analytics', status: 'RUNNING' },
  ]);
  const [snapshot, setSnapshot] = useState<CanonicalMonitoringSnapshotDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const activeMigRef = useRef<string>(selectedMigId);
  activeMigRef.current = selectedMigId;

  // Load available migrations from backend
  useEffect(() => {
    async function loadMigrations() {
      try {
        const resStr = await ipcService.invokeEngineCapability('get_all_migrations', '{}');
        const data = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
        if (data && Array.isArray(data.migrations) && data.migrations.length > 0) {
          setAvailableMigrations(data.migrations);
        }
      } catch (e) {
        // Fall back to default
      }
    }
    loadMigrations();
  }, []);

  const fetchSnapshot = useCallback(async (migId: string) => {
    try {
      const resStr = await ipcService.invokeEngineCapability('get_monitoring_snapshot', JSON.stringify({ migration_id: migId }));
      if (activeMigRef.current !== migId) return; // Stale response protection

      const data: CanonicalMonitoringSnapshotDTO = typeof resStr === 'string' ? JSON.parse(resStr) : resStr;
      setSnapshot(data);
      setError(null);
    } catch (err: any) {
      if (activeMigRef.current !== migId) return;
      console.warn(`[MonitoringModule] Error fetching snapshot for ${migId}:`, err);
      setError(err?.message || String(err));
    } finally {
      if (activeMigRef.current === migId) {
        setLoading(false);
      }
    }
  }, []);

  // Effect: Initial fetch + bounded polling loop
  useEffect(() => {
    setLoading(true);
    fetchSnapshot(selectedMigId);

    const interval = setInterval(() => {
      // Only poll if snapshot is in LIVE mode (or snapshot not loaded yet)
      if (!snapshot || snapshot.monitoring_mode === 'LIVE' || snapshot.runtime.status === 'RUNNING') {
        fetchSnapshot(selectedMigId);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [selectedMigId, fetchSnapshot, snapshot?.monitoring_mode, snapshot?.runtime.status]);

  if (loading && !snapshot) {
    return (
      <div className={styles.container}>
        <div className={styles.centerBox}>
          <div className={styles.spinner} />
          <div className={styles.emptyTitle}>Connecting to Engine Gateway...</div>
          <div className={styles.emptySub}>Fetching canonical monitoring telemetry for {selectedMigId}</div>
        </div>
      </div>
    );
  }

  if (error && !snapshot) {
    return (
      <div className={styles.container}>
        <div className={styles.centerBox}>
          <div className={styles.emptyTitle} style={{ color: '#ef4444' }}>Engine Monitoring Unavailable</div>
          <div className={styles.emptySub}>{error}</div>
          <button className={styles.tabBtn} style={{ marginTop: 16, background: '#3b82f6', color: '#fff' }} onClick={() => fetchSnapshot(selectedMigId)}>
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (!snapshot) return null;

  const { runtime, progress } = snapshot;
  const isLive = snapshot.monitoring_mode === 'LIVE';

  return (
    <div className={styles.container} id="monitoring-module-root">
      {/* ── Top Bar & Selector ─────────────────────────────────────── */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Execution Telemetry & Monitoring</h1>
          <p className={styles.subtitle}>Canonical AKAAL runtime telemetry & historical execution evidence</p>
        </div>

        <div className={styles.selectorWrapper}>
          <span className={styles.selectorLabel}>Migration:</span>
          <select
            className={styles.selectInput}
            value={selectedMigId}
            onChange={(e) => setSelectedMigId(e.target.value)}
          >
            {availableMigrations.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label} ({m.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Banner Card ────────────────────────────────────────────── */}
      <div className={styles.bannerCard}>
        <div className={styles.bannerMeta}>
          <div>
            <div className={styles.bannerTitle}>{snapshot.migration_id}</div>
            <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
              Stage: <strong>{runtime.current_stage || 'N/A'}</strong> | Session: <span className={styles.mono}>{runtime.session_id || 'sess-84f2'}</span>
            </div>
          </div>
          <div className={styles.bannerBadges}>
            <span className={`${styles.badge} ${runtime.status === 'RUNNING' ? styles.badgeRunning : runtime.status === 'FAILED' ? styles.badgeFailed : runtime.status === 'PAUSED' ? styles.badgePaused : styles.badgeCompleted}`}>
              {runtime.status}
            </span>
            <span className={`${styles.badge} ${isLive ? styles.badgeModeLive : styles.badgeModeHist}`}>
              {snapshot.monitoring_mode} MODE
            </span>
          </div>
        </div>

        <div className={styles.bannerStats}>
          <div className={styles.statItem}>
            <span className={styles.statVal}>{progress.progress_percent !== null ? `${progress.progress_percent.toFixed(1)}%` : '—'}</span>
            <span className={styles.statLbl}>Progress</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statVal}>{progress.rows_transferred !== null ? progress.rows_transferred.toLocaleString() : '—'}</span>
            <span className={styles.statLbl}>Rows Transferred</span>
          </div>
        </div>
      </div>

      {/* ── Tabs Navigation ────────────────────────────────────────── */}
      <div className={styles.tabsRow}>
        <button className={`${styles.tabBtn} ${activeTab === 'overview' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('overview')}>
          Overview
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'performance' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('performance')}>
          Performance
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'workers' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('workers')}>
          Workers
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'tables' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('tables')}>
          Tables & Partitions
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'reliability' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('reliability')}>
          Reliability & Checkpoints
        </button>
        <button className={`${styles.tabBtn} ${activeTab === 'events' ? styles.tabBtnActive : ''}`} onClick={() => setActiveTab('events')}>
          Events & Logs
        </button>
      </div>

      {/* ── Active Tab Content ──────────────────────────────────────── */}
      {activeTab === 'overview' && <OverviewPanel snapshot={snapshot} />}
      {activeTab === 'performance' && <PerformancePanel snapshot={snapshot} />}
      {activeTab === 'workers' && <WorkersPanel snapshot={snapshot} />}
      {activeTab === 'tables' && <TablesPanel snapshot={snapshot} />}
      {activeTab === 'reliability' && <ReliabilityPanel snapshot={snapshot} />}
      {activeTab === 'events' && <EventsPanel snapshot={snapshot} />}
    </div>
  );
};
