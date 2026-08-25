import { useState, useRef, useEffect, type FC } from 'react';
import type { MigrationPipeline, MigrationDraftState } from '../../types/migration';
import { useMigrationProjects } from '../../hooks/useMigrationProjects';
import { notificationService } from '../../services/notificationService';
import { EmptyState } from '../../components/EmptyState/EmptyState';
import { ConfirmDialog, type ConfirmSeverity } from '../../components/ConfirmDialog';
import styles from './MigrationModule.module.css';

export interface MigrationLandingProps {
  onOpenProject: (pipeline: MigrationPipeline) => void;
  onOpenNewMigrationConfig: (resumeDraftData?: MigrationDraftState) => void;
  onOpenNewProjectConfig: () => void;
  onOpenGovernanceCenter?: () => void;
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
  onOpenGovernanceCenter,
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

  const [renameTarget, setRenameTarget] = useState<{ id: string; currentName: string; value: string; error?: string | null } | null>(null);
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

  const handleRenamePrompt = (id: string) => {
    const current = [...pinnedProjects, ...regularProjects, ...sharedProjects, ...archivedProjects, ...draftProjects].find(
      (p) => p.id === id
    );
    if (!current) return;
    setRenameTarget({ id, currentName: current.name, value: current.name, error: null });
  };

  const handleArchivePrompt = (id: string) => {
    const current = [...pinnedProjects, ...regularProjects, ...sharedProjects, ...draftProjects].find(
      (p) => p.id === id
    );
    if (!current) return;
    setConfirmState({
      isOpen: true,
      title: 'Archive Project Workspace',
      affectedObject: `Project Workspace: ${current.name}`,
      message: 'Archiving this Project Workspace will:',
      bulletPoints: [
        'move it into Archived Projects',
        'preserve all migrations',
        'preserve execution history',
      ],
      consequence: 'This operation preserves all migration history.',
      confirmText: 'Archive Project Workspace',
      severity: 'warning',
      onConfirm: () => {
        archiveProject(id);
      },
    });
  };

  const handleDeletePrompt = (id: string) => {
    const current = [...pinnedProjects, ...regularProjects, ...sharedProjects, ...archivedProjects, ...draftProjects].find(
      (p) => p.id === id
    );
    if (!current) return;
    setConfirmState({
      isOpen: true,
      title: 'Delete Project Workspace',
      affectedObject: `Project Workspace: ${current.name}`,
      message: 'Deleting this Project Workspace will permanently remove:',
      bulletPoints: [
        'workspace metadata',
        'migration definitions',
        'runtime history',
        'local workspace configuration',
      ],
      consequence: 'This action cannot be undone.',
      confirmText: 'Delete Project Workspace',
      severity: 'danger',
      onConfirm: () => {
        deleteProject(id);
      },
    });
  };

  const handleRestorePrompt = (id: string) => {
    const current = [...pinnedProjects, ...regularProjects, ...sharedProjects, ...archivedProjects, ...draftProjects].find(
      (p) => p.id === id
    );
    if (!current) return;
    setConfirmState({
      isOpen: true,
      title: 'Restore Project Workspace',
      affectedObject: `Project Workspace: ${current.name}`,
      message: 'Restoring this Project Workspace will:',
      bulletPoints: [
        'return it to Active Projects',
        'preserve all migrations',
        'preserve execution history',
      ],
      consequence: 'This operation preserves all migration history.',
      confirmText: 'Restore Project Workspace',
      severity: 'info',
      onConfirm: () => {
        unarchiveProject(id);
      },
    });
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
          id="act-card-governance"
          className={styles.actionCard}
          onClick={() => onOpenGovernanceCenter && onOpenGovernanceCenter()}
        >
          <div className={styles.actionIconBox}>
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75">
              <path d="M8 1.5L2 4v4.5c0 3.8 2.6 7.3 6 8 3.4-.7 6-4.2 6-8V4L8 1.5z" />
            </svg>
          </div>
          <div className={styles.actionCardTitle}>Governance Center</div>
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
                onArchive={handleArchivePrompt}
                onUnarchive={handleRestorePrompt}
                onDelete={handleDeletePrompt}
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
                onArchive={handleArchivePrompt}
                onUnarchive={handleRestorePrompt}
                onDelete={handleDeletePrompt}
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
                onArchive={handleArchivePrompt}
                onUnarchive={handleRestorePrompt}
                onDelete={handleDeletePrompt}
              />
            ))}
          </div>
        </section>
      ) : (
        filteredDrafts.length === 0 && (
          <EmptyState
            title="Your Workspace is Ready"
            description="Create your first project or migration workspace to begin automated database schema discovery and risk analysis."
            actionLabel="+ Create First Migration"
            onAction={() => onOpenNewMigrationConfig()}
            actionId="btn-empty-create-first-migration"
          />
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
                onArchive={handleArchivePrompt}
                onUnarchive={handleRestorePrompt}
                onDelete={handleDeletePrompt}
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
                    onArchive={handleArchivePrompt}
                    onUnarchive={handleRestorePrompt}
                    onDelete={handleDeletePrompt}
                  />
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* ── Modals ────────────────────────────────────────── */}
      {renameTarget && (
        <ConfirmDialog
          isOpen={!!renameTarget}
          title="Rename Project Workspace"
          affectedObject={`Project Workspace: ${renameTarget.currentName}`}
          message="Renaming this Project Workspace will:"
          bulletPoints={[
            'update the workspace name',
            'preserve identifiers',
            'preserve migrations',
            'preserve execution history',
          ]}
          consequence="This operation preserves all migration history."
          confirmText="Rename Project Workspace"
          severity="info"
          inputConfig={{
            label: 'Enter new project workspace name:',
            value: renameTarget.value,
            maxLength: 64,
            error: renameTarget.error,
            onChange: (val) => {
              const trimmed = val.trim();
              let err: string | null = null;
              if (!trimmed) {
                err = 'Project workspace name cannot be empty.';
              } else if (
                [...pinnedProjects, ...regularProjects, ...sharedProjects, ...archivedProjects, ...draftProjects].some(
                  (p) => p.name.trim().toLowerCase() === trimmed.toLowerCase() && p.name.trim().toLowerCase() !== renameTarget.currentName.trim().toLowerCase()
                )
              ) {
                err = `A project workspace named "${trimmed}" already exists.`;
              }
              setRenameTarget((prev) => (prev ? { ...prev, value: val, error: err } : null));
            },
          }}
          isConfirmDisabled={!renameTarget.value.trim() || !!renameTarget.error}
          onConfirm={() => {
            renameProject(renameTarget.id, renameTarget.value.trim());
            setRenameTarget(null);
          }}
          onClose={() => setRenameTarget(null)}
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
