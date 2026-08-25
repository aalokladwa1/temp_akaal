import { useState, type FC } from 'react';
import type { MigrationPipeline, DatabaseEngine } from '../../types/migration';
import { notificationService } from '../../services/notificationService';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import styles from './MigrationModule.module.css';

export interface NewProjectConfigViewProps {
  onBack: () => void;
  onLaunch: (created: MigrationPipeline) => void;
  createProject: (name: string, sourceEngine: DatabaseEngine, targetEngine: DatabaseEngine) => MigrationPipeline;
}

export const NewProjectConfigView: FC<NewProjectConfigViewProps> = ({
  onBack,
  onLaunch,
  createProject,
}) => {
  const [projectName, setProjectName] = useState('Core Banking Modernization');
  const [projectDescription, setProjectDescription] = useState('Centralized enterprise database migration project.');
  const [owner, setOwner] = useState('Aalok');
  const [tags, setTags] = useState('Production, Core, Oracle-PG');
  const [showConfirm, setShowConfirm] = useState(false);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) {
      notificationService.push('Validation Error', 'error', 'Project name is required.');
      return;
    }
    setShowConfirm(true);
  };

  const executeCreation = async () => {
    setShowConfirm(false);
    const created = createProject(projectName.trim(), 'Oracle 19c', 'PostgreSQL 16');
    notificationService.push('Project Created', 'success', `Project "${created.name}" created.`);
    onLaunch(created);
  };

  return (
    <div className={styles.workspaceViewContainer} style={{ maxWidth: 720, margin: '0 auto', padding: '36px 32px' }}>
      {/* Top Navigation */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28, paddingBottom: 16, borderBottom: '1px solid var(--dash-border)' }}>
        <button className={styles.backBtn} onClick={onBack} id="btn-back-to-landing">
          ← Back to Projects
        </button>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          New Project Setup
        </span>
      </div>

      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 8px 0', letterSpacing: '-0.02em', color: 'var(--dash-text-primary)' }}>
          Create Project
        </h1>
        <p style={{ fontSize: 14, color: 'var(--dash-text-secondary)', margin: 0, lineHeight: 1.5 }}>
          Projects contain database connections, migrations, compliance reports, timelines, and team governance policies.
        </p>
      </div>

      <form onSubmit={handleCreate}>
        <div style={{ padding: 24, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)', marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
              Project Name *
            </label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. Core Banking Modernization"
              required
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                border: '1px solid var(--dash-border)',
                background: 'var(--dash-surface)',
                color: 'var(--dash-text-primary)',
                fontSize: 14,
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
              Description
            </label>
            <textarea
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              rows={3}
              placeholder="Describe the scope and objective of this project..."
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                border: '1px solid var(--dash-border)',
                background: 'var(--dash-surface)',
                color: 'var(--dash-text-primary)',
                fontSize: 13,
                fontFamily: 'inherit',
                boxSizing: 'border-box',
                resize: 'vertical',
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
                Owner / Lead Engineer
              </label>
              <input
                type="text"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--dash-border)',
                  background: 'var(--dash-surface)',
                  color: 'var(--dash-text-primary)',
                  fontSize: 13,
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
                Tags (Comma Separated)
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g. Production, Core, Oracle"
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--dash-border)',
                  background: 'var(--dash-surface)',
                  color: 'var(--dash-text-primary)',
                  fontSize: 13,
                  boxSizing: 'border-box',
                }}
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 14 }}>
          <button
            type="button"
            onClick={onBack}
            style={{
              padding: '10px 20px',
              borderRadius: 8,
              background: 'none',
              border: '1px solid var(--dash-border)',
              color: 'var(--dash-text-secondary)',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            id="btn-confirm-create-project"
            style={{
              padding: '10px 24px',
              borderRadius: 8,
              background: '#2563EB',
              color: '#ffffff',
              border: 'none',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Create Project →
          </button>
        </div>
      </form>

      <ConfirmDialog
        isOpen={showConfirm}
        title="Create Project?"
        affectedObject={`Project: ${projectName}`}
        message={`Description: ${projectDescription || 'No description provided.'}`}
        bulletPoints={[
          `Owner: ${owner}`,
          `Tags: ${tags}`,
          'Establishes permanent project container boundary',
        ]}
        confirmText="Create Project"
        severity="info"
        onConfirm={executeCreation}
        onClose={() => setShowConfirm(false)}
      />
    </div>
  );
};
