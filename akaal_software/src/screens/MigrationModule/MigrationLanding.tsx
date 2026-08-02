import { useState, useRef, useEffect, type FC } from 'react';
import type { MigrationPipeline, MigrationDraftState } from '../../types/migration';
import { useMigrationProjects } from '../../hooks/useMigrationProjects';
import { notificationService } from '../../services/notificationService';
import styles from './MigrationModule.module.css';

export interface MigrationLandingProps {
  onOpenProject: (pipeline: MigrationPipeline) => void;
  onOpenNewMigrationConfig: (resumeDraftData?: MigrationDraftState) => void;
  onOpenNewProjectConfig: () => void;
  searchFilter?: string;
}

// ── Cohesive Smart Status Badges ─────────────────────────────

const StatusPill: FC<{ label: string; variant?: 'running' | 'planning' | 'completed' | 'paused' | 'failed' | 'archived' }> = ({
  label,
  variant = 'running',
}) => {
  const clsMap = {
    running:   styles.statusRunning,
    planning:  styles.statusPlanning,
    completed: styles.statusCompleted,
    paused:    styles.statusPaused,
    failed:    styles.statusFailed,
    archived:  styles.statusArchived,
  };

  return (
    <span className={[styles.statusBadge, clsMap[variant]].join(' ')}>
      <span className={styles.statusDot} />
      {label}
    </span>
  );
};

// ── SVG Icons ────────────────────────────────────────────────

const IconPlus = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75">
    <path d="M8 3v10M3 8h10" strokeLinecap="round" />
  </svg>
);

const IconFolderPlus = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M2 4a1 1 0 011-1h3.5l1.5 2H13a1 1 0 011 1v7a1 1 0 01-1 1H3a1 1 0 01-1-1V4z" />
    <path d="M8 7v4M6 9h4" strokeLinecap="round" />
  </svg>
);

const IconImport = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M8 2v8M5 7l3 3 3-3M2 13h12" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const IconTemplate = () => (
  <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="2" width="12" height="12" rx="2" />
    <path d="M2 6h12M6 6v8" strokeLinecap="round" />
  </svg>
);

const IconPin = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style={{ color: '#F59E0B' }}>
    <path d="M8 .5L10.2 5l5 .7-3.6 3.5.9 5-4.5-2.4L3.5 14.2l.9-5L.8 5.7l5-.7L8 .5z" />
  </svg>
);

const IconArrowRight = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// ── Enterprise Pipeline Card Component ───────────────────────

interface PipelineCardProps {
  pipeline: MigrationPipeline;
  onOpen: (p: MigrationPipeline) => void;
  onResumeDraft?: (draft?: MigrationDraftState) => void;
  onPinToggle: (id: string) => void;
  onRename: (id: string) => void;
  onDuplicate: (id: string) => void;
  onArchive: (id: string) => void;
  onUnarchive: (id: string) => void;
  onDelete: (id: string) => void;
}

const PipelineCard: FC<PipelineCardProps> = ({
  pipeline,
  onOpen,
  onResumeDraft,
  onPinToggle,
  onRename,
  onDuplicate,
  onArchive,
  onUnarchive,
  onDelete,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  const handlePrimaryClick = () => {
    if (pipeline.isDraft && onResumeDraft) {
      onResumeDraft(pipeline.draftData);
    } else {
      onOpen(pipeline);
    }
  };

  return (
    <div
      className={styles.projectCard}
      onClick={handlePrimaryClick}
      tabIndex={0}
      role="button"
      onKeyDown={(e) => e.key === 'Enter' && handlePrimaryClick()}
    >
      <div>
        <div className={styles.projectCardTop}>
          <div className={styles.projectTitleGroup}>
            {pipeline.isPinned && <span className={styles.pinStar} title="Pinned Pipeline"><IconPin /></span>}
            <span className={styles.projectName}>{pipeline.name}</span>
          </div>

          <div className={styles.projectCardHoverActions} onClick={(e) => e.stopPropagation()}>
            <button className={styles.openBtn} onClick={handlePrimaryClick}>
              {pipeline.isDraft ? 'Resume Draft' : 'Open'}
            </button>
            <button
              className={styles.overflowMenuBtn}
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Pipeline menu"
            >
              ⋮
            </button>
          </div>

          {menuOpen && (
            <div className={styles.overflowMenuDropdown} ref={menuRef} onClick={(e) => e.stopPropagation()}>
              <button
                className={styles.overflowItem}
                onClick={() => { setMenuOpen(false); handlePrimaryClick(); }}
              >
                {pipeline.isDraft ? 'Resume Setup' : 'Open Workspace'}
              </button>
              {!pipeline.isDraft && (
                <>
                  <button
                    className={styles.overflowItem}
                    onClick={() => { setMenuOpen(false); onPinToggle(pipeline.id); }}
                  >
                    {pipeline.isPinned ? 'Unpin' : 'Pin Pipeline'}
                  </button>
                  <button
                    className={styles.overflowItem}
                    onClick={() => { setMenuOpen(false); onRename(pipeline.id); }}
                  >
                    Rename
                  </button>
                  <button
                    className={styles.overflowItem}
                    onClick={() => { setMenuOpen(false); onDuplicate(pipeline.id); }}
                  >
                    Duplicate
                  </button>
                  {!pipeline.isArchived ? (
                    <button
                      className={styles.overflowItem}
                      onClick={() => { setMenuOpen(false); onArchive(pipeline.id); }}
                    >
                      Archive
                    </button>
                  ) : (
                    <button
                      className={styles.overflowItem}
                      onClick={() => { setMenuOpen(false); onUnarchive(pipeline.id); }}
                    >
                      Restore
                    </button>
                  )}
                </>
              )}
              <button
                className={`${styles.overflowItem} ${styles.overflowItemDanger}`}
                onClick={() => { setMenuOpen(false); onDelete(pipeline.id); }}
              >
                Delete
              </button>
            </div>
          )}
        </div>

        <div className={styles.projectDbPair}>
          {pipeline.sourceEngine} → {pipeline.targetEngine}
        </div>
      </div>

      <div className={styles.projectCardBottom}>
        <StatusPill
          label={pipeline.isDraft ? 'Draft Configuration' : pipeline.currentStageLabel}
          variant={pipeline.isDraft ? 'paused' : pipeline.health === 'healthy' ? 'running' : 'planning'}
        />

        <div className={styles.projectMetaGroup}>
          <div className={styles.metaItem}>
            <span className={styles.metaItemLabel}>Owner</span>
            <span className={styles.metaItemValue}>{pipeline.owner}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Migration Landing Page Component ─────────────────────────

export const MigrationLanding: FC<MigrationLandingProps> = ({
  onOpenProject,
  onOpenNewMigrationConfig,
  onOpenNewProjectConfig,
  searchFilter = '',
}) => {
  const {
    continueWorkingProject,
    draftProjects,
    pinnedProjects,
    regularProjects,
    sharedProjects,
    archivedProjects,
    activeProjectsCount,
    togglePin,
    renameProject,
    duplicateProject,
    archiveProject,
    unarchiveProject,
    deleteProject,
  } = useMigrationProjects('Aalok');

  const [archivedExpanded, setArchivedExpanded] = useState(false);

  const filterFn = (p: MigrationPipeline) => {
    if (!searchFilter || !searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    const name = (p.name || '').toLowerCase();
    const src = (p.sourceEngine || '').toLowerCase();
    const tgt = (p.targetEngine || '').toLowerCase();
    const stage = (p.currentStageLabel || '').toLowerCase();
    const owner = (p.owner || '').toLowerCase();
    return (
      name.includes(q) ||
      src.includes(q) ||
      tgt.includes(q) ||
      stage.includes(q) ||
      owner.includes(q)
    );
  };

  const filteredDrafts = draftProjects.filter(filterFn);
  const filteredPinned = pinnedProjects.filter(filterFn);
  const filteredRegular = regularProjects.filter(filterFn);
  const filteredShared = sharedProjects.filter(filterFn);
  const filteredArchived = archivedProjects.filter(filterFn);

  const handleRenamePrompt = (id: string) => {
    const current = [...pinnedProjects, ...regularProjects, ...sharedProjects, ...archivedProjects].find(
      (p) => p.id === id
    );
    if (!current) return;

    const input = window.prompt('Enter new migration pipeline name:', current.name);
    if (input && input.trim()) {
      renameProject(id, input.trim());
      notificationService.push('Pipeline Renamed', 'info', `Renamed to "${input.trim()}".`);
    }
  };



  return (
    <div className={styles.container}>
      {/* ── Header ────────────────────────────────────────── */}
      <header className={styles.headerRow}>
        <div>
          <h1 className={styles.headerTitle}>Migration Workspaces</h1>
          <p className={styles.headerSubtitle}>
            Plan, profile and orchestrate enterprise database migrations.
          </p>
        </div>
      </header>

      {/* ── 4 Primary Action Cards (Icon + Title Only - Requirement #4) ──── */}
      <section aria-label="Primary Migration Actions" className={styles.primaryActionGrid}>
        <button
          id="act-card-new-migration"
          className={styles.actionCard}
          onClick={() => onOpenNewMigrationConfig()}
        >
          <div className={styles.actionIconBox}><IconPlus /></div>
          <div className={styles.actionCardTitle}>New Migration</div>
        </button>

        <button
          id="act-card-new-project"
          className={styles.actionCard}
          onClick={() => onOpenNewProjectConfig()}
        >
          <div className={styles.actionIconBox}><IconFolderPlus /></div>
          <div className={styles.actionCardTitle}>New Project</div>
        </button>

        <button
          id="act-card-import-project"
          className={styles.actionCard}
          onClick={() => notificationService.push('Import Project', 'info', 'Upload AKAAL Workflow Manifest.')}
        >
          <div className={styles.actionIconBox}><IconImport /></div>
          <div className={styles.actionCardTitle}>Import Project</div>
        </button>

        <button
          id="act-card-templates"
          className={styles.actionCard}
          onClick={() => notificationService.push('Templates', 'info', 'Enterprise schema & policy templates available.')}
        >
          <div className={styles.actionIconBox}><IconTemplate /></div>
          <div className={styles.actionCardTitle}>Templates</div>
        </button>
      </section>

      {/* ── Continue Working (Requirement #5: Identical Treatment for All 3 Indicators) ──── */}
      {continueWorkingProject && (
        <section className={styles.heroSection} aria-label="Continue working">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Continue Working</span>
          </div>
          <div className={styles.heroCard}>
            <div className={styles.heroLeft}>
              <div className={styles.heroMeta}>
                <StatusPill
                  label={`Stage: ${continueWorkingProject.currentStageLabel}`}
                  variant={continueWorkingProject.health === 'healthy' ? 'running' : 'planning'}
                />
                <StatusPill
                  label={`Health: ${continueWorkingProject.healthLabel}`}
                  variant={continueWorkingProject.health === 'healthy' ? 'running' : 'paused'}
                />
                <StatusPill
                  label={`Activity: ${continueWorkingProject.lastActivity}`}
                  variant="completed"
                />
              </div>
              <div className={styles.heroProjectName}>{continueWorkingProject.name}</div>
              <div className={styles.heroSubInfo}>
                {continueWorkingProject.sourceEngine} → {continueWorkingProject.targetEngine} • {continueWorkingProject.lastEvent}
              </div>
              <div className={styles.heroProgressRow}>
                <div className={styles.heroProgressTrack}>
                  <div
                    className={styles.heroProgressFill}
                    style={{ width: `${continueWorkingProject.progress}%` }}
                  />
                </div>
                <span className={styles.heroProgressText}>{continueWorkingProject.progress}% Lifecycle Progress</span>
              </div>
            </div>
            <div>
              <button
                id="btn-hero-resume"
                className={styles.resumeBtn}
                onClick={() => onOpenProject(continueWorkingProject)}
              >
                Resume Pipeline <IconArrowRight />
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ── Draft Migrations Section (Requirement #3) ─────── */}
      {filteredDrafts.length > 0 && (
        <section className={styles.projectsSection} aria-label="Draft Migrations">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Draft Migrations ({filteredDrafts.length})</span>
          </div>
          <div className={styles.projectGrid}>
            {filteredDrafts.map((pipe) => (
              <PipelineCard
                key={pipe.id}
                pipeline={pipe}
                onOpen={onOpenProject}
                onResumeDraft={onOpenNewMigrationConfig}
                onPinToggle={togglePin}
                onRename={handleRenamePrompt}
                onDuplicate={duplicateProject}
                onArchive={archiveProject}
                onUnarchive={unarchiveProject}
                onDelete={deleteProject}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Active Projects Section (Requirement #6: Spacious & Clean) ── */}
      {activeProjectsCount > 0 ? (
        <section className={styles.projectsSection} aria-label="Active Projects">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Active Projects</span>
          </div>

          <div className={styles.projectGrid}>
            {filteredPinned.map((pipe) => (
              <PipelineCard
                key={pipe.id}
                pipeline={pipe}
                onOpen={onOpenProject}
                onPinToggle={togglePin}
                onRename={handleRenamePrompt}
                onDuplicate={duplicateProject}
                onArchive={archiveProject}
                onUnarchive={unarchiveProject}
                onDelete={deleteProject}
              />
            ))}

            {filteredRegular.map((pipe) => (
              <PipelineCard
                key={pipe.id}
                pipeline={pipe}
                onOpen={onOpenProject}
                onPinToggle={togglePin}
                onRename={handleRenamePrompt}
                onDuplicate={duplicateProject}
                onArchive={archiveProject}
                onUnarchive={unarchiveProject}
                onDelete={deleteProject}
              />
            ))}
          </div>
        </section>
      ) : (
        filteredDrafts.length === 0 && (
          <div style={{ padding: '64px 32px', textAlign: 'center', background: 'var(--dash-card-bg)', border: '1px dashed var(--dash-border-hover)', borderRadius: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 8px 0' }}>Your workspace is ready.</h2>
            <p style={{ fontSize: 13, color: 'var(--dash-text-secondary)', margin: '0 0 24px 0' }}>
              Create your first migration workspace to begin database discovery.
            </p>
            <button
              className={styles.resumeBtn}
              onClick={() => onOpenNewMigrationConfig()}
            >
              <IconPlus /> Create First Migration
            </button>
          </div>
        )
      )}

      {/* ── Shared Projects Section ───────────────────────── */}
      {filteredShared.length > 0 && (
        <section className={styles.sharedSection} aria-label="Shared Projects">
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Shared Projects</span>
          </div>
          <div className={styles.projectGrid}>
            {filteredShared.map((pipe) => (
              <PipelineCard
                key={pipe.id}
                pipeline={pipe}
                onOpen={onOpenProject}
                onPinToggle={togglePin}
                onRename={handleRenamePrompt}
                onDuplicate={duplicateProject}
                onArchive={archiveProject}
                onUnarchive={unarchiveProject}
                onDelete={deleteProject}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Archived Projects Section ─────────────────────── */}
      {filteredArchived.length > 0 && (
        <section className={styles.archivedSection} aria-label="Archived projects">
          <button
            className={styles.archivedHeader}
            onClick={() => setArchivedExpanded((v) => !v)}
            aria-expanded={archivedExpanded}
          >
            <span className={[styles.archivedCaret, archivedExpanded ? styles.archivedCaretExpanded : ''].join(' ')}>
              ▶
            </span>
            <span>{filteredArchived.length} Archived {filteredArchived.length === 1 ? 'Project' : 'Projects'}</span>
          </button>

          {archivedExpanded && (
            <div className={styles.archivedBody}>
              <div className={styles.projectGrid}>
                {filteredArchived.map((pipe) => (
                  <PipelineCard
                    key={pipe.id}
                    pipeline={pipe}
                    onOpen={onOpenProject}
                    onPinToggle={togglePin}
                    onRename={handleRenamePrompt}
                    onDuplicate={duplicateProject}
                    onArchive={archiveProject}
                    onUnarchive={unarchiveProject}
                    onDelete={deleteProject}
                  />
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
};
