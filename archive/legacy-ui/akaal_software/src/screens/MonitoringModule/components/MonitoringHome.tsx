import React, { useState, useMemo } from 'react';
import styles from '../MonitoringModule.module.css';

export interface MigrationRunSummary {
  id: string;
  name?: string;
  label?: string;
  project_id?: string;
  project_name?: string;
  source_engine?: string;
  target_engine?: string;
  status: string;
  monitoring_mode?: 'LIVE' | 'HISTORICAL';
  rows_transferred?: number;
  rows_total?: number;
  progress_percent?: number;
  rows_per_sec?: number;
  throughput_mbps?: number;
  active_workers?: number;
  current_stage?: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  failed_stage?: string;
  error_message?: string;
}

export interface MonitoringHomeProps {
  migrations: MigrationRunSummary[];
  loading: boolean;
  error: string | null;
  onSelectMigration: (migrationId: string) => void;
  onRetryLoad?: () => void;
}

export type StatusFilterType = 'ALL' | 'LIVE' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'TERMINATED';

const fmtNumber = (n: number | null | undefined): string => {
  if (n == null || isNaN(n)) return '—';
  return n.toLocaleString();
};

export const MonitoringHome: React.FC<MonitoringHomeProps> = ({
  migrations,
  loading,
  error,
  onSelectMigration,
  onRetryLoad,
}) => {
  const [activeFilter, setActiveFilter] = useState<StatusFilterType>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Summaries derived from canonical migration records
  const counts = useMemo(() => {
    const total = migrations.length;
    let live = 0;
    let paused = 0;
    let completed = 0;
    let failed = 0;
    let terminated = 0;

    for (const m of migrations) {
      const st = (m.status || '').toUpperCase();
      if (st === 'RUNNING' || st === 'STARTING' || st === 'START_REQUESTED') live++;
      else if (st === 'PAUSED') paused++;
      else if (st === 'COMPLETED') completed++;
      else if (st === 'FAILED' || st === 'ERROR') failed++;
      else if (st === 'TERMINATED') terminated++;
    }

    return { total, live, paused, completed, failed, terminated };
  }, [migrations]);

  // Unified Filter & Search with Default Sorting (Live/Running first, then Paused, then Terminal)
  const filteredMigrations = useMemo(() => {
    return migrations
      .filter((m) => {
        const st = (m.status || '').toUpperCase();
        if (activeFilter === 'LIVE') return st === 'RUNNING' || st === 'STARTING' || st === 'START_REQUESTED';
        if (activeFilter === 'PAUSED') return st === 'PAUSED';
        if (activeFilter === 'COMPLETED') return st === 'COMPLETED';
        if (activeFilter === 'FAILED') return st === 'FAILED' || st === 'ERROR';
        if (activeFilter === 'TERMINATED') return st === 'TERMINATED';
        return true;
      })
      .filter((m) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        const idMatch = (m.id || '').toLowerCase().includes(q);
        const nameMatch = (m.name || m.label || '').toLowerCase().includes(q);
        const projMatch = (m.project_name || m.project_id || '').toLowerCase().includes(q);
        const srcMatch = (m.source_engine || '').toLowerCase().includes(q);
        const tgtMatch = (m.target_engine || '').toLowerCase().includes(q);
        return idMatch || nameMatch || projMatch || srcMatch || tgtMatch;
      })
      .sort((a, b) => {
        // Priority weight: RUNNING (1) > PAUSED (2) > TERMINAL (3)
        const getPriority = (st: string) => {
          const s = (st || '').toUpperCase();
          if (s === 'RUNNING' || s === 'STARTING' || s === 'START_REQUESTED') return 1;
          if (s === 'PAUSED') return 2;
          return 3;
        };
        const prioA = getPriority(a.status);
        const prioB = getPriority(b.status);
        if (prioA !== prioB) return prioA - prioB;
        return (b.started_at || '').localeCompare(a.started_at || '');
      });
  }, [migrations, activeFilter, searchQuery]);

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.centerBox}>
          <div className={styles.spinner} />
          <div className={styles.emptyTitle}>Connecting to Engine Gateway...</div>
          <div className={styles.emptySub}>Retrieving canonical migration run portfolio & telemetry summaries</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.centerBox}>
          <div className={styles.emptyTitle} style={{ color: 'var(--dash-tag-failed-text, #ef4444)' }}>
            Engine Bridge Unavailable
          </div>
          <div className={styles.emptySub}>{error}</div>
          {onRetryLoad && (
            <button className={styles.selectInput} style={{ marginTop: 16, padding: '8px 16px' }} onClick={onRetryLoad}>
              Retry Connection
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container} id="monitoring-home-root">
      {/* ── Top Header ────────────────────────────────────────────── */}
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Monitoring</h1>
          <p className={styles.subtitle}>Real-time and historical migration telemetry</p>
        </div>
      </div>

      {/* ── Summary KPI Cards ─────────────────────────────────────── */}
      <div className={styles.kpiGrid} style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', marginBottom: 24 }}>
        <div
          className={styles.card}
          style={{
            cursor: 'pointer',
            border: 'none',
            background: activeFilter === 'ALL' ? 'rgba(37, 99, 235, 0.15)' : undefined,
          }}
          onClick={() => setActiveFilter('ALL')}
        >
          <div className={styles.cardTitle}>Total Migrations</div>
          <div className={styles.cardValue}>{counts.total}</div>
          <div className={styles.cardSub}>Portfolio Total</div>
        </div>

        <div
          className={styles.card}
          style={{
            cursor: 'pointer',
            border: 'none',
            background: activeFilter === 'LIVE' ? 'rgba(16, 185, 129, 0.15)' : undefined,
          }}
          onClick={() => setActiveFilter('LIVE')}
        >
          <div className={styles.cardTitle} style={{ color: '#10b981' }}>Live / Running</div>
          <div className={styles.cardValue} style={{ color: '#10b981' }}>{counts.live}</div>
          <div className={styles.cardSub}>Active Streamers</div>
        </div>

        <div
          className={styles.card}
          style={{
            cursor: 'pointer',
            border: 'none',
            background: activeFilter === 'PAUSED' ? 'rgba(245, 158, 11, 0.15)' : undefined,
          }}
          onClick={() => setActiveFilter('PAUSED')}
        >
          <div className={styles.cardTitle} style={{ color: '#f59e0b' }}>Paused</div>
          <div className={styles.cardValue} style={{ color: '#f59e0b' }}>{counts.paused}</div>
          <div className={styles.cardSub}>Halted Progress</div>
        </div>

        <div
          className={styles.card}
          style={{
            cursor: 'pointer',
            border: 'none',
            background: activeFilter === 'COMPLETED' ? 'rgba(59, 130, 246, 0.15)' : undefined,
          }}
          onClick={() => setActiveFilter('COMPLETED')}
        >
          <div className={styles.cardTitle} style={{ color: '#3b82f6' }}>Completed</div>
          <div className={styles.cardValue} style={{ color: '#3b82f6' }}>{counts.completed}</div>
          <div className={styles.cardSub}>Verified Runs</div>
        </div>

        <div
          className={styles.card}
          style={{
            cursor: 'pointer',
            border: 'none',
            background: activeFilter === 'FAILED' ? 'rgba(239, 68, 68, 0.15)' : undefined,
          }}
          onClick={() => setActiveFilter('FAILED')}
        >
          <div className={styles.cardTitle} style={{ color: '#ef4444' }}>Failed</div>
          <div className={styles.cardValue} style={{ color: '#ef4444' }}>{counts.failed}</div>
          <div className={styles.cardSub}>Recorded Errors</div>
        </div>

        <div
          className={styles.card}
          style={{
            cursor: 'pointer',
            border: 'none',
            background: activeFilter === 'TERMINATED' ? 'rgba(148, 163, 184, 0.20)' : undefined,
          }}
          onClick={() => setActiveFilter('TERMINATED')}
        >
          <div className={styles.cardTitle}>Terminated</div>
          <div className={styles.cardValue}>{counts.terminated}</div>
          <div className={styles.cardSub}>Cancelled Runs</div>
        </div>
      </div>

      {/* ── Filters & Search Controls ──────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, gap: 16, flexWrap: 'wrap' }}>
        <div className={styles.tabsRow} style={{ marginBottom: 0 }}>
          {(['ALL', 'LIVE', 'PAUSED', 'COMPLETED', 'FAILED', 'TERMINATED'] as StatusFilterType[]).map((f) => (
            <button
              key={f}
              className={`${styles.tabBtn} ${activeFilter === f ? styles.tabBtnActive : ''}`}
              onClick={() => setActiveFilter(f)}
            >
              {f.charAt(0) + f.slice(1).toLowerCase()}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <input
            type="text"
            className={styles.selectInput}
            style={{ width: 240, padding: '8px 12px' }}
            placeholder="Search migration ID, engine, project..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* ── Unified Migration Run List ─────────────────────────────── */}
      {filteredMigrations.length === 0 ? (
        <div className={styles.tableContainer} style={{ padding: 48, textAlign: 'center', border: 'none' }}>
          <div className={styles.emptyTitle}>No migrations available for monitoring</div>
          <div className={styles.emptySub} style={{ margin: '8px auto 0' }}>
            {migrations.length === 0
              ? 'Your workspace has no registered database migration jobs yet.'
              : 'No migration runs match the selected filter criteria.'}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filteredMigrations.map((m) => {
            const st = (m.status || '').toUpperCase();
            const isLive = st === 'RUNNING' || st === 'STARTING' || st === 'START_REQUESTED';
            const isPaused = st === 'PAUSED';
            const isCompleted = st === 'COMPLETED';
            const isFailed = st === 'FAILED' || st === 'ERROR';

            return (
              <div
                key={m.id}
                className={styles.bannerCard}
                style={{
                  marginBottom: 0,
                  cursor: 'pointer',
                  border: 'none',
                  transition: 'transform 0.12s ease, background 0.12s ease',
                }}
                onClick={() => onSelectMigration(m.id)}
              >
                {/* Left Metadata Area */}
                <div className={styles.bannerMeta} style={{ gap: 20 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span className={styles.bannerTitle}>{m.id}</span>

                      {/* LIVE Tag Indicator */}
                      {isLive && (
                        <span className={`${styles.badge} ${styles.badgeRunning}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }} />
                          LIVE
                        </span>
                      )}

                      {/* Status Badges */}
                      {!isLive && (
                        <span
                          className={`${styles.badge} ${
                            isPaused
                              ? styles.badgePaused
                              : isCompleted
                              ? styles.badgeCompleted
                              : isFailed
                              ? styles.badgeFailed
                              : styles.badgeModeHist
                          }`}
                        >
                          {st}
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--dash-text-primary, #f8fafc)' }}>
                      {m.source_engine || 'Oracle'} → {m.target_engine || 'PostgreSQL'}
                      {m.project_name && <span style={{ color: 'var(--dash-text-secondary)', fontWeight: 400 }}> ({m.project_name})</span>}
                    </div>

                    {/* Progress Bar for Active Runs */}
                    {(isLive || isPaused) && m.rows_total ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: 280, marginTop: 4 }}>
                        <div className={styles.progressTrack}>
                          <div className={styles.progressFill} style={{ width: `${Math.min(100, m.progress_percent || 0)}%` }} />
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'monospace' }}>
                          {m.progress_percent != null ? `${m.progress_percent}%` : '—'}
                        </span>
                      </div>
                    ) : null}
                  </div>
                </div>

                {/* Right Telemetry Summary */}
                <div className={styles.bannerStats} style={{ gap: 32 }}>
                  <div className={styles.statItem}>
                    <span className={styles.statVal}>
                      {fmtNumber(m.rows_transferred)} / {fmtNumber(m.rows_total)}
                    </span>
                    <span className={styles.statLbl}>Rows Transferred</span>
                  </div>

                  {isLive && m.rows_per_sec != null && (
                    <div className={styles.statItem}>
                      <span className={styles.statVal}>{fmtNumber(m.rows_per_sec)}</span>
                      <span className={styles.statLbl}>Rows / sec</span>
                    </div>
                  )}

                  {isCompleted && m.duration_seconds != null && (
                    <div className={styles.statItem}>
                      <span className={styles.statVal}>{m.duration_seconds}s</span>
                      <span className={styles.statLbl}>Duration</span>
                    </div>
                  )}

                  <button
                    className={styles.primaryBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectMigration(m.id);
                    }}
                  >
                    Inspect Telemetry →
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
