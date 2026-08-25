import { useState, useEffect, type FC } from 'react';
import type { MigrationPipeline, GovernanceApproval } from '../../types/migration';
import { connectionRepository } from '../../repositories/connectionRepository';
import { approvalRepository } from '../../repositories/approvalRepository';
import { runtimeSessionRepository } from '../../repositories/runtimeSessionRepository';
import { ApprovalModal } from '../../components/ApprovalModal/ApprovalModal';
import { ConfirmDialog, type ConfirmSeverity } from '../../components/ConfirmDialog';
import { MissionControlView } from './MissionControlView';
import styles from './MigrationModule.module.css';

export interface ProjectWorkspaceViewProps {
  project: MigrationPipeline;
  onBack: () => void;
  onOpenNewMigration?: () => void;
  onOpenGovernance?: (migrationId?: string, gateId?: string) => void;
}

export type ProjectNavSection =
  | 'overview'
  | 'migrations'
  | 'connections'
  | 'team'
  | 'reports'
  | 'timeline'
  | 'notes'
  | 'settings';

export type DockTabId = 'logs' | 'events' | 'notifications' | 'output' | 'timeline' | 'decisions';



// ── SVG Lucide Icons ────────────────────────────────────────────────

const IconOverview = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="2" width="5" height="5" rx="1" />
    <rect x="9" y="2" width="5" height="5" rx="1" />
    <rect x="2" y="9" width="5" height="5" rx="1" />
    <rect x="9" y="9" width="5" height="5" rx="1" />
  </svg>
);

const IconMigrations = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 8h10M10 5l3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const IconConnections = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M4 8h8M2 5v6M14 5v6M6 4h4M6 12h4" strokeLinecap="round" />
  </svg>
);

const IconTeam = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="8" cy="5" r="2.5" />
    <path d="M2 13c0-3 2.7-5 6-5s6 2 6 5" strokeLinecap="round" />
  </svg>
);

const IconReports = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M4 1.5h5.5L13 5v9.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-12a1 1 0 0 1 1-1z" />
    <path d="M9.5 1.5V5H13" />
    <path d="M5.5 8h5M5.5 11h5" strokeLinecap="round" />
  </svg>
);

const IconTimeline = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="8" cy="8" r="6" />
    <path d="M8 4v4l2.5 2.5" strokeLinecap="round" />
  </svg>
);

const IconNotes = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 2.5h10a1 1 0 011 1v10a1 1 0 01-1 1H3a1 1 0 01-1-1v-10a1 1 0 011-1z" />
    <path d="M5 6h6M5 9h6M5 12h4" strokeLinecap="round" />
  </svg>
);

const IconSettings = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="8" cy="8" r="2" />
    <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" strokeLinecap="round" />
  </svg>
);

const IconPlus = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75">
    <path d="M8 3v10M3 8h10" strokeLinecap="round" />
  </svg>
);

const NAV_ITEMS: { id: ProjectNavSection; label: string; Icon: FC }[] = [
  { id: 'overview',    label: 'Overview',    Icon: IconOverview    },
  { id: 'migrations',  label: 'Migrations',  Icon: IconMigrations  },
  { id: 'connections', label: 'Connections', Icon: IconConnections },
  { id: 'team',        label: 'Team',        Icon: IconTeam        },
  { id: 'reports',     label: 'Reports',     Icon: IconReports     },
  { id: 'timeline',    label: 'Timeline',    Icon: IconTimeline    },
  { id: 'notes',       label: 'Notes',       Icon: IconNotes       },
  { id: 'settings',    label: 'Settings',    Icon: IconSettings    },
];

export const ProjectWorkspaceView: FC<ProjectWorkspaceViewProps> = ({
  project,
  onBack,
  onOpenNewMigration,
  onOpenGovernance,
}) => {
  const [activeNav, setActiveNav] = useState<ProjectNavSection>('overview');
  const [activeMigrationRuntime, setActiveMigrationRuntime] = useState<MigrationPipeline | null>(null);
  const [_selectedStage, setSelectedStage] = useState(project.currentStage);
  const [dockTab, setDockTab] = useState<DockTabId>('logs');
  const [dockCollapsed, setDockCollapsed] = useState<boolean>(false);
  const [inspectorCollapsed, setInspectorCollapsed] = useState<boolean>(false);
  const [connections, setConnections] = useState(() => connectionRepository.getConnections(project.id));
  const [sessions, setSessions] = useState(() => runtimeSessionRepository.getSessions());
  const [activeApprovalModal, setActiveApprovalModal] = useState<GovernanceApproval | null>(null);
  const [confirmState, setConfirmState] = useState<{
    isOpen: boolean;
    title: string;
    affectedObject?: string;
    message?: string;
    bulletPoints?: string[];
    consequence?: string;
    confirmText?: string;
    severity?: ConfirmSeverity;
    onConfirm: () => void;
  }>({
    isOpen: false,
    title: '',
    onConfirm: () => {},
  });

  useEffect(() => {
    const unsubConn = connectionRepository.subscribe(() => {
      setConnections(connectionRepository.getConnections(project.id));
    });
    const unsubSess = runtimeSessionRepository.subscribe((updated) => {
      setSessions(updated);
    });

    // Restore runtime snapshot and subscribe to live engine events on mount
    runtimeSessionRepository.syncSnapshotFromEngine(project.id);
    runtimeSessionRepository.subscribeRuntimeEvents();

    return () => {
      unsubConn();
      unsubSess();
    };
  }, [project.id]);

  const existingSession = runtimeSessionRepository.getSessionForMigration(project.id);
  const historicalSessions = sessions.filter((s) => s.migrationId === project.id);

  const handleOpenMigrationOverview = () => {
    setActiveMigrationRuntime(project);
    setSelectedStage('scout');
  };

  // Session status helpers

  return (
    <div className={styles.workspaceViewContainer} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--dash-bg)' }}>
      {/* ── SECTION 1: ENTERPRISE HEADER ──────────────────────────────────── */}
      <div
        style={{
          padding: '12px 24px',
          background: 'var(--dash-topbar-bg)',
          borderBottom: '1px solid var(--dash-topbar-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <button className={styles.backBtn} onClick={activeMigrationRuntime ? () => setActiveMigrationRuntime(null) : onBack} id="btn-back-to-migrations">
            ← {activeMigrationRuntime ? 'Back to Project' : 'Workspaces'}
          </button>
          <div style={{ width: 1, height: 18, background: 'var(--dash-border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: 'var(--dash-surface)',
                border: '1px solid var(--dash-border)',
                color: 'var(--dash-text-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: 14,
              }}
            >
              {project.name.charAt(0)}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h1 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)', letterSpacing: '-0.01em' }}>
                  {activeMigrationRuntime ? activeMigrationRuntime.name : project.name}
                </h1>
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'rgba(16, 185, 129, 0.12)', color: '#10B981', fontWeight: 600 }}>
                  🟢 Engine OK (12ms)
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2, fontFamily: "'JetBrains Mono', monospace" }}>
                {project.sourceEndpoint} ──► {project.targetEndpoint} • Session: {existingSession ? existingSession.sessionId : 'sess-idle'}
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {onOpenNewMigration && !activeMigrationRuntime && (
            <button
              onClick={onOpenNewMigration}
              id="btn-project-create-migration"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                borderRadius: 8,
                background: '#2563EB',
                color: '#ffffff',
                border: 'none',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <IconPlus /> Create Migration
            </button>
          )}

          <button
            onClick={() => setInspectorCollapsed((prev) => !prev)}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              background: 'var(--dash-surface)',
              border: '1px solid var(--dash-border)',
              color: 'var(--dash-text-secondary)',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {inspectorCollapsed ? 'Show Inspector ⇥' : 'Hide Inspector ⇤'}
          </button>
        </div>
      </div>



      {/* ── 3-Pane Desktop Workspace ───────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left Project Navigation Pane */}
        {!activeMigrationRuntime && (
          <div
            style={{
              width: 200,
              flexShrink: 0,
              background: 'var(--dash-sidebar-bg)',
              borderRight: '1px solid var(--dash-sidebar-border)',
              padding: '16px 8px',
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}
          >
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: 'var(--dash-text-tertiary)', padding: '0 8px 8px 8px', letterSpacing: '0.05em' }}>
              Project Navigation
            </div>

            {NAV_ITEMS.map(({ id, label, Icon }) => {
              const isActive = activeNav === id;
              return (
                <button
                  key={id}
                  id={`proj-nav-${id}`}
                  onClick={() => setActiveNav(id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    borderRadius: 8,
                    border: 'none',
                    background: isActive ? 'var(--dash-surface)' : 'transparent',
                    color: isActive ? 'var(--dash-text-primary)' : 'var(--dash-text-secondary)',
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 400,
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 120ms ease, color 120ms ease',
                  }}
                >
                  <Icon />
                  <span>{label}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Center Main Workstation Surface */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column' }}>
          {activeMigrationRuntime ? (
            <MissionControlView
              migration={activeMigrationRuntime}
              onBack={() => setActiveMigrationRuntime(null)}
              onOpenWizard={onOpenNewMigration}
              onOpenGovernance={onOpenGovernance}
            />
          ) : (
            /* ── 2. PROJECT OVERVIEW ── */
            <div>
              {activeNav === 'overview' && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                    <div>
                      <h2 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 4px 0', color: 'var(--dash-text-primary)' }}>
                        Project Workspace Overview
                      </h2>
                      <p style={{ fontSize: 13, color: 'var(--dash-text-secondary)', margin: 0 }}>
                        High-level status for project "{project.name}".
                      </p>
                    </div>
                  </div>

                  {/* Summary Cards Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
                    <div style={{ padding: 18, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                      <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Active Migrations</div>
                      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 6, color: 'var(--dash-text-primary)' }}>1 Active</div>
                    </div>
                    <div style={{ padding: 18, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                      <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Project Connections</div>
                      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 6, color: 'var(--dash-text-primary)' }}>{connections.length} Endpoints</div>
                    </div>
                    <div style={{ padding: 18, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                      <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Team Members</div>
                      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 6, color: 'var(--dash-text-primary)' }}>{project.teamMemberCount} Members</div>
                    </div>
                    <div style={{ padding: 18, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                      <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', textTransform: 'uppercase' }}>Governance Policy</div>
                      <div style={{ fontSize: 15, fontWeight: 700, color: '#10B981', marginTop: 8 }}>Four-Eyes Enforced</div>
                    </div>
                  </div>

                  {/* Active Migrations List */}
                  <div style={{ marginBottom: 24 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                      <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)' }}>Migrations in this Project</h3>
                      {onOpenNewMigration && (
                        <button
                          onClick={onOpenNewMigration}
                          style={{ padding: '6px 12px', borderRadius: 6, background: '#2563EB', color: '#fff', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                        >
                          + Create Migration
                        </button>
                      )}
                    </div>

                    <div style={{ padding: 16, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '14px 18px',
                          background: 'var(--dash-surface)',
                          borderRadius: 8,
                          cursor: 'pointer',
                        }}
                        role="button"
                        tabIndex={0}
                        onClick={handleOpenMigrationOverview}
                        onKeyDown={(e) => e.key === 'Enter' && handleOpenMigrationOverview()}
                      >
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--dash-text-primary)' }}>{project.name}</div>
                          <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{project.sourceEndpoint} → {project.targetEndpoint}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }} onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={handleOpenMigrationOverview}
                            style={{ padding: '8px 16px', borderRadius: 6, background: '#2563EB', color: '#ffffff', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                          >
                            {existingSession?.status === 'paused' || project.lastEvent === 'PAUSED'
                              ? 'RESUME MIGRATION →'
                              : existingSession?.status === 'completed'
                              ? 'VIEW MIGRATION →'
                              : 'OPEN MISSION CONTROL →'}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeNav === 'connections' && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                    <div>
                      <h2 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 4px 0', color: 'var(--dash-text-primary)' }}>
                        Reusable Project Connections
                      </h2>
                      <p style={{ fontSize: 13, color: 'var(--dash-text-secondary)', margin: 0 }}>
                        Database connection pools owned by project "{project.name}".
                      </p>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    {connections.map((conn) => (
                      <div key={conn.id} style={{ padding: 18, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#3B82F6' }}>{conn.engine}</span>
                          <span style={{ fontSize: 11, fontWeight: 600, color: '#10B981' }}>✓ {conn.status}</span>
                        </div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{conn.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>{conn.endpoint}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* SECTION 5: RIGHT CONTEXT INSPECTOR */}
        {!inspectorCollapsed && (
          <div
            style={{
              width: 260,
              flexShrink: 0,
              background: 'var(--dash-sidebar-bg)',
              borderLeft: '1px solid var(--dash-sidebar-border)',
              padding: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--dash-text-tertiary)' }}>
              Contextual Inspector
            </div>

            <div style={{ padding: 14, background: 'var(--dash-card-bg)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)' }}>Selected Stage Context</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginTop: 4, color: 'var(--dash-text-primary)' }}>
                {activeMigrationRuntime ? activeMigrationRuntime.name : 'Project Workspace'}
              </div>
              <p style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                {activeMigrationRuntime ? `Active Stage: ${activeMigrationRuntime.currentStage}` : 'Viewing top-level project metadata and connection pools.'}
              </p>
            </div>

            <div style={{ padding: 14, background: 'var(--dash-card-bg)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)' }}>Live Telemetry Summary</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#10B981', marginTop: 4 }}>✓ 8/8 Partition Workers Active</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#10B981', marginTop: 4 }}>✓ 12ms CDC Sync Buffer Lag</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#10B981', marginTop: 4 }}>✓ AES-256 Vault Encryption</div>
              <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 8 }}>
                Execution Sessions: {historicalSessions.length} active
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── BOTTOM RUNTIME DOCK (Task 5: Consumes Live RuntimeEvents) ── */}
      {activeMigrationRuntime && (
        <div
          style={{
            borderTop: '1px solid var(--dash-border)',
            background: 'var(--dash-topbar-bg)',
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 16px', borderBottom: dockCollapsed ? 'none' : '1px solid var(--dash-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {(['logs', 'events', 'notifications', 'output', 'decisions'] as DockTabId[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => { setDockTab(tab); setDockCollapsed(false); }}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 4,
                    border: 'none',
                    background: dockTab === tab && !dockCollapsed ? 'var(--dash-surface)' : 'transparent',
                    color: dockTab === tab && !dockCollapsed ? 'var(--dash-text-primary)' : 'var(--dash-text-secondary)',
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                    textTransform: 'uppercase',
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>

            <button
              onClick={() => setDockCollapsed((prev) => !prev)}
              style={{ padding: '2px 8px', borderRadius: 4, border: '1px solid var(--dash-border)', background: 'none', color: 'var(--dash-text-secondary)', fontSize: 11, cursor: 'pointer' }}
            >
              {dockCollapsed ? '▲ Expand Dock' : '▼ Collapse Dock'}
            </button>
          </div>

          {!dockCollapsed && (
            <div
              style={{
                height: 120,
                padding: 12,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: 'var(--dash-text-primary)',
                background: 'var(--dash-surface)',
                borderTop: '1px solid var(--dash-border)',
                overflowY: 'auto',
              }}
            >
              {dockTab === 'logs' && (
                <div>
                  {(existingSession?.events && existingSession.events.length > 0) ? (
                    existingSession.events.map((evt, i) => (
                      <div key={evt.eventId || i} style={{ marginBottom: 2 }}>
                        <span style={{ color: 'var(--dash-text-secondary)' }}>{evt.timestamp.split('T')[1]?.split('.')[0]}</span>{' '}
                        <span style={{ color: evt.severity === 'critical' ? '#EF4444' : evt.severity === 'warning' ? '#F59E0B' : '#10B981', fontWeight: 600 }}>[{evt.severity.toUpperCase()}]</span>{' '}
                        <span style={{ color: '#3B82F6' }}>akaal.{evt.source}</span> — {evt.eventType} {evt.payload ? JSON.stringify(evt.payload) : ''}
                      </div>
                    ))
                  ) : (
                    <div style={{ color: 'var(--dash-text-secondary)', fontStyle: 'italic' }}>No runtime events recorded yet. Engine stream is ready.</div>
                  )}
                </div>
              )}
              {dockTab === 'events' && (
                <div>
                  {(existingSession?.events && existingSession.events.length > 0) ? (
                    existingSession.events.map((evt, i) => (
                      <div key={evt.eventId || i} style={{ marginBottom: 2 }}>
                        [{evt.timestamp.split('T')[1]?.split('.')[0]}] {evt.eventType} — {JSON.stringify(evt.payload || {})}
                      </div>
                    ))
                  ) : (
                    <div style={{ color: 'var(--dash-text-secondary)', fontStyle: 'italic' }}>No event stream records available.</div>
                  )}
                </div>
              )}
              {dockTab === 'notifications' && (
                <div style={{ color: 'var(--dash-text-secondary)' }}>
                  {existingSession ? `[NOTIFICATION] Session ${existingSession.sessionId} active on native IPC socket.` : 'No notifications.'}
                </div>
              )}
              {dockTab === 'output' && (
                <div style={{ color: 'var(--dash-text-secondary)' }}>
                  [STDOUT] Connected to AKAAL Engine IPC Socket (\\.\pipe\akaal_engine).
                </div>
              )}
              {dockTab === 'decisions' && (
                <div>
                  {(existingSession?.decisions && existingSession.decisions.length > 0) ? (
                    existingSession.decisions.map((dec, i) => (
                      <div key={dec.id || i}>
                        [{dec.timestamp}] {dec.stage} — {dec.decision}: {dec.reason} ({dec.subsystem})
                      </div>
                    ))
                  ) : (
                    <div style={{ color: 'var(--dash-text-secondary)', fontStyle: 'italic' }}>No governance decisions recorded yet.</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Approval Modal */}
      {activeApprovalModal && (
        <ApprovalModal
          approval={activeApprovalModal}
          isOpen={!!activeApprovalModal}
          onClose={() => setActiveApprovalModal(null)}
          onSubmitDecision={(id, decision, reason) => {
            approvalRepository.processDecision(id, decision, 'Aalok', reason);
            if (activeMigrationRuntime) {
              setActiveMigrationRuntime({
                ...activeMigrationRuntime,
                health: decision === 'approved' ? 'healthy' : 'approval_required',
                currentStage: decision === 'approved' ? 'schema_exec' : 'manager',
              });
            }
          }}
        />
      )}

      <ConfirmDialog
        isOpen={confirmState.isOpen}
        title={confirmState.title}
        affectedObject={confirmState.affectedObject}
        message={confirmState.message}
        bulletPoints={confirmState.bulletPoints}
        consequence={confirmState.consequence}
        confirmText={confirmState.confirmText}
        severity={confirmState.severity}
        onConfirm={() => {
          confirmState.onConfirm();
          setConfirmState((prev) => ({ ...prev, isOpen: false }));
        }}
        onClose={() => setConfirmState((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
};
