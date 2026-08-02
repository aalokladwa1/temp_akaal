import { useState, type FC } from 'react';
import type { MigrationPipeline, EngineStageId } from '../../types/migration';
import { ENGINE_STAGE_METADATA } from '../../services/migrationService';
import styles from './MigrationModule.module.css';

export interface ProjectWorkspaceViewProps {
  project: MigrationPipeline;
  onBack: () => void;
  onOpenNewMigration?: () => void;
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

export type DockTabId = 'logs' | 'events' | 'notifications' | 'output' | 'timeline';

const STAGE_LIST: EngineStageId[] = [
  'scout',
  'advisor',
  'live_intel',
  'planner',
  'manager',
  'schema_exec',
  'data_migration',
  'validator',
  'healing',
  'certification',
];

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

// Reusable Connection Item
interface ReusableConnection {
  id: string;
  name: string;
  engine: string;
  endpoint: string;
  environment: string;
  latencyMs: number;
  status: 'Healthy' | 'Testing';
}

const DEMO_CONNECTIONS: ReusableConnection[] = [
  { id: 'conn-01', name: 'Oracle Enterprise ERP Core', engine: 'Oracle 19c', endpoint: 'db-oracle.enterprise.internal:1521/ORCL', environment: 'Production', latencyMs: 1.2, status: 'Healthy' },
  { id: 'conn-02', name: 'PostgreSQL Target Cluster', engine: 'PostgreSQL 16', endpoint: 'pg-cluster.enterprise.internal:5432/app_target_db', environment: 'Production', latencyMs: 0.8, status: 'Healthy' },
  { id: 'conn-03', name: 'SQL Server Payroll DB', engine: 'SQL Server 2019', endpoint: 'sql-payroll.corp.internal:1433/PayrollDB', environment: 'Production', latencyMs: 2.1, status: 'Healthy' },
];

export const ProjectWorkspaceView: FC<ProjectWorkspaceViewProps> = ({
  project,
  onBack,
  onOpenNewMigration,
}) => {
  const [activeNav, setActiveNav] = useState<ProjectNavSection>('overview');
  const [activeMigrationRuntime, setActiveMigrationRuntime] = useState<MigrationPipeline | null>(null);
  const [selectedStage, setSelectedStage] = useState<EngineStageId>(project.currentStage);
  const [dockTab, setDockTab] = useState<DockTabId>('logs');
  const [dockCollapsed, setDockCollapsed] = useState<boolean>(false);
  const [inspectorCollapsed, setInspectorCollapsed] = useState<boolean>(false);

  const currentStageIndex = STAGE_LIST.indexOf(selectedStage);
  const currentStageMeta = ENGINE_STAGE_METADATA[selectedStage] || ENGINE_STAGE_METADATA['scout'];

  return (
    <div className={styles.workspaceViewContainer} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--dash-bg)' }}>
      {/* ── Top Bar Header (Theme-Aware Branding Audit) ────────────────────── */}
      <div
        style={{
          padding: '14px 24px',
          background: 'var(--dash-topbar-bg)',
          borderBottom: '1px solid var(--dash-topbar-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button className={styles.backBtn} onClick={activeMigrationRuntime ? () => setActiveMigrationRuntime(null) : onBack} id="btn-back-to-migrations">
            ← {activeMigrationRuntime ? 'Back to Project' : 'Workspaces'}
          </button>
          <div style={{ width: 1, height: 18, background: 'var(--dash-border)' }} />

          {/* Theme-Aware Project Logo Box (Light Theme: Light Surface, Dark Text | Dark Theme: Dark Surface, Light Text) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 8,
                background: 'var(--dash-surface)',
                border: '1px solid var(--dash-border)',
                color: 'var(--dash-text-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: 14,
                boxShadow: 'var(--dash-card-shadow)',
              }}
            >
              {project.name.charAt(0)}
            </div>
            <div>
              <h1 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)', letterSpacing: '-0.01em' }}>
                {activeMigrationRuntime ? activeMigrationRuntime.name : project.name}
              </h1>
              <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>
                {activeMigrationRuntime
                  ? `Runtime Context • Stage ${currentStageIndex + 1} of 10`
                  : `Project Workspace • ${project.owner}`}
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

        {/* Center Main Workspace Pane */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--dash-bg)' }}>
          <div style={{ flex: 1, padding: 24, overflowY: 'auto' }}>

            {/* ── 1. SPECIFIC MIGRATION RUNTIME WORKSPACE ── */}
            {activeMigrationRuntime ? (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 4px 0', color: 'var(--dash-text-primary)' }}>
                      Migration Runtime Workspace
                    </h2>
                    <p style={{ fontSize: 13, color: 'var(--dash-text-secondary)', margin: 0 }}>
                      Executing {activeMigrationRuntime.sourceEngine} → {activeMigrationRuntime.targetEngine} Data Migration Pipeline.
                    </p>
                  </div>

                  <span
                    style={{
                      padding: '4px 12px',
                      borderRadius: 6,
                      fontSize: 12,
                      fontWeight: 600,
                      background: 'rgba(16, 185, 129, 0.12)',
                      color: '#10B981',
                      border: '1px solid rgba(16, 185, 129, 0.2)',
                    }}
                  >
                    ✓ Runtime Active
                  </span>
                </div>

                {/* 10-Stage AKAAL Engine Pipeline Bar (ONLY VISIBLE INSIDE RUNTIME) */}
                <div style={{ padding: 20, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)', marginBottom: 24 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--dash-text-secondary)', marginBottom: 14 }}>
                    10-Stage AKAAL Engine Runtime State
                  </div>

                  <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 4 }}>
                    {STAGE_LIST.map((stageId, idx) => {
                      const meta = ENGINE_STAGE_METADATA[stageId];
                      const isActive = stageId === activeMigrationRuntime.currentStage;
                      const isSelected = stageId === selectedStage;
                      const isPast = idx < currentStageIndex;

                      return (
                        <button
                          key={stageId}
                          onClick={() => setSelectedStage(stageId)}
                          style={{
                            flex: 1,
                            minWidth: 84,
                            padding: '10px 8px',
                            borderRadius: 8,
                            border: isSelected ? '1px solid #3B82F6' : '1px solid var(--dash-border)',
                            background: isActive ? 'rgba(59, 130, 246, 0.15)' : isPast ? 'rgba(16, 185, 129, 0.1)' : 'var(--dash-surface)',
                            color: isActive ? '#3B82F6' : isPast ? '#10B981' : 'var(--dash-text-secondary)',
                            cursor: 'pointer',
                            textAlign: 'center',
                          }}
                        >
                          <div style={{ fontSize: 10, fontWeight: 700 }}>ST {idx + 1}</div>
                          <div style={{ fontSize: 11, fontWeight: 600, marginTop: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {meta.label.split(' ')[0]}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Stage Detail Card */}
                <div style={{ padding: 20, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 8px 0', color: 'var(--dash-text-primary)' }}>{currentStageMeta.label} Overview</h3>
                  <p style={{ fontSize: 13, color: 'var(--dash-text-secondary)', margin: '0 0 16px 0' }}>{currentStageMeta.description}</p>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#3B82F6' }}>Owner Agent: {currentStageMeta.ownerAgent}</div>
                </div>
              </div>
            ) : (
              /* ── 2. PROJECT OVERVIEW (Simplified, Clean Project Management) ── */
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
                        <div style={{ fontSize: 20, fontWeight: 700, marginTop: 6, color: 'var(--dash-text-primary)' }}>{DEMO_CONNECTIONS.length} Endpoints</div>
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
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', background: 'var(--dash-surface)', borderRadius: 8 }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--dash-text-primary)' }}>{project.name}</div>
                            <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{project.sourceEndpoint} → {project.targetEndpoint}</div>
                          </div>
                          <button
                            onClick={() => setActiveMigrationRuntime(project)}
                            style={{ padding: '8px 16px', borderRadius: 6, background: 'var(--dash-card-bg)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                          >
                            Open Migration Runtime →
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── 3. REUSABLE CONNECTIONS ── */}
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
                      <button
                        style={{ padding: '8px 14px', borderRadius: 6, background: '#2563EB', color: '#fff', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
                      >
                        + Add Connection
                      </button>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                      {DEMO_CONNECTIONS.map((conn) => (
                        <div key={conn.id} style={{ padding: 18, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                            <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#3B82F6' }}>{conn.engine}</span>
                            <span style={{ fontSize: 11, fontWeight: 600, color: '#10B981' }}>✓ {conn.status}</span>
                          </div>
                          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{conn.name}</div>
                          <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>{conn.endpoint}</div>
                          <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 10 }}>Environment: {conn.environment} • Latency: {conn.latencyMs}ms</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ── 4. MIGRATIONS NAV ITEM ── */}
                {activeNav === 'migrations' && (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                      <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)' }}>Project Migrations</h2>
                      {onOpenNewMigration && (
                        <button onClick={onOpenNewMigration} style={{ padding: '8px 16px', borderRadius: 8, background: '#2563EB', color: '#fff', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                          + Create Migration
                        </button>
                      )}
                    </div>
                    <div style={{ padding: 16, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', background: 'var(--dash-surface)', borderRadius: 8 }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--dash-text-primary)' }}>{project.name}</div>
                          <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>{project.sourceEndpoint} → {project.targetEndpoint}</div>
                        </div>
                        <button onClick={() => setActiveMigrationRuntime(project)} style={{ padding: '8px 16px', borderRadius: 6, background: 'var(--dash-card-bg)', border: '1px solid var(--dash-border)', color: 'var(--dash-text-primary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                          Open Migration Runtime →
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* OTHER NAV SECTIONS */}
                {['team', 'reports', 'timeline', 'notes', 'settings'].includes(activeNav) && (
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 12px 0', textTransform: 'capitalize', color: 'var(--dash-text-primary)' }}>
                      {activeNav}
                    </h2>
                    <div style={{ padding: 24, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
                      <p style={{ fontSize: 13, color: 'var(--dash-text-secondary)', margin: 0 }}>
                        Project workspace {activeNav} settings for "{project.name}".
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        </div>

        {/* Right Contextual Inspector Pane */}
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
              <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)' }}>Selected Context</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginTop: 4, color: 'var(--dash-text-primary)' }}>
                {activeMigrationRuntime ? currentStageMeta.label : 'Project Workspace'}
              </div>
              <p style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                {activeMigrationRuntime ? currentStageMeta.description : 'Viewing top-level project metadata and connection pools.'}
              </p>
            </div>

            <div style={{ padding: 14, background: 'var(--dash-card-bg)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
              <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)' }}>Security & Cryptography</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#10B981', marginTop: 4 }}>✓ AES-256 Vault Encryption</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#10B981', marginTop: 4 }}>✓ Zero Raw Credentials Kept</div>
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom Runtime Dock (Logs | Events | Notifications | Output | Timeline) ──
          CRITICAL ARCHITECTURAL REQUIREMENT: Renders ONLY during active Migration Runtime!
      */}
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
              {(['logs', 'events', 'notifications', 'output', 'timeline'] as DockTabId[]).map((tab) => (
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
                  [AKAAL Engine] Initializing parallel partitioning transport worker thread #4...<br />
                  [SCOUT Agent] Source table checksum validation passed for ORCL.CUSTOMERS (12,450,000 rows)<br />
                  [GB VALIDATOR] Column hash verification algorithm: BLAKE3 (99.98% matching)
                </div>
              )}
              {dockTab === 'events' && <div>[EVENT STREAM] StageTransition → data_migration (data streaming active)</div>}
              {dockTab === 'notifications' && <div>[SYSTEM NOTIFICATION] Four-Eyes approval confirmed by Aalok.</div>}
              {dockTab === 'output' && <div>[CLI STDOUT] akaal-engine-runtime v1.0.4 initialized with 32 worker partitions.</div>}
              {dockTab === 'timeline' && <div>[AUDIT TIMELINE] 18:42:10 UTC - Project Workspace initialized by Aalok.</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
