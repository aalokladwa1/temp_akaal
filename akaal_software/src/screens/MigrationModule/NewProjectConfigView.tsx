import { useState, type FC } from 'react';
import type { MigrationPipeline, DatabaseEngine } from '../../types/migration';
import { notificationService } from '../../services/notificationService';
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
  const [projectName, setProjectName] = useState('Enterprise Core Migration Workspace');
  const [projectDescription, setProjectDescription] = useState('Centralized database migration project workspace.');
  const [environment, setEnvironment] = useState<'Production' | 'Staging' | 'UAT' | 'Development'>('Production');
  const [storagePath, setStoragePath] = useState('C:\\AKAAL_Workspace\\Projects\\CoreMigration');
  const [governanceMode, setGovernanceMode] = useState<'four_eyes' | 'standard'>('four_eyes');
  const [ownerName, setOwnerName] = useState('Aalok');

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) {
      notificationService.push('Validation Error', 'error', 'Project name is required.');
      return;
    }

    const created = createProject(projectName.trim(), 'Oracle 19c', 'PostgreSQL 16');
    notificationService.push('Project Workspace Created', 'success', `Project Workspace "${created.name}" initialized.`);
    onLaunch(created);
  };

  return (
    <div className={styles.workspaceViewContainer} style={{ maxWidth: 960, margin: '0 auto', padding: '36px 32px' }}>
      {/* Workspace Top Navigation */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28, paddingBottom: 16, borderBottom: '1px solid var(--dash-border)' }}>
        <button className={styles.backBtn} onClick={onBack} id="btn-back-to-landing">
          ← Back to Migration Workspaces
        </button>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Dedicated Project Workspace Setup
        </span>
      </div>

      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 8px 0', letterSpacing: '-0.02em' }}>
          Create Enterprise Project Workspace
        </h1>
        <p style={{ fontSize: 14, color: 'var(--dash-text-secondary)', margin: 0, lineHeight: 1.5 }}>
          An AKAAL Project Workspace manages database connections, team governance policies, compliance audit reports, and multiple migration pipelines.
        </p>
      </div>

      <form onSubmit={handleCreate}>
        {/* Section 1: Identity & Scope */}
        <div style={{ padding: 24, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)', marginBottom: 24 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 16px 0', color: 'var(--dash-text-primary)' }}>
            1. Project Workspace Identity & Metadata
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
                Project Workspace Name *
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
                  fontSize: 13,
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
                Target Infrastructure Environment
              </label>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value as any)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--dash-border)',
                  background: 'var(--dash-surface)',
                  color: 'var(--dash-text-primary)',
                  fontSize: 13,
                }}
              >
                <option value="Production">Production Enterprise Workload</option>
                <option value="Staging">Staging & Pre-Prod Sandbox</option>
                <option value="UAT">UAT Validation Cluster</option>
                <option value="Development">Development Lab</option>
              </select>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
              Project Owner
            </label>
            <input
              type="text"
              value={ownerName}
              onChange={(e) => setOwnerName(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                border: '1px solid var(--dash-border)',
                background: 'var(--dash-surface)',
                color: 'var(--dash-text-primary)',
                fontSize: 13,
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
              Architectural Scope & Objectives
            </label>
            <textarea
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              rows={2}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                border: '1px solid var(--dash-border)',
                background: 'var(--dash-surface)',
                color: 'var(--dash-text-primary)',
                fontSize: 13,
                resize: 'vertical',
                fontFamily: 'inherit',
              }}
            />
          </div>
        </div>

        {/* Section 2: Storage & Governance */}
        <div style={{ padding: 24, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)', marginBottom: 32 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 16px 0', color: 'var(--dash-text-primary)' }}>
            2. Local Artifact Storage & Four-Eyes Governance
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
                Workspace Local Artifact Directory
              </label>
              <input
                type="text"
                value={storagePath}
                onChange={(e) => setStoragePath(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--dash-border)',
                  background: 'var(--dash-surface)',
                  color: 'var(--dash-text-primary)',
                  fontSize: 13,
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-secondary)', marginBottom: 6 }}>
                Governance Approval Policy
              </label>
              <select
                value={governanceMode}
                onChange={(e) => setGovernanceMode(e.target.value as any)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid var(--dash-border)',
                  background: 'var(--dash-surface)',
                  color: 'var(--dash-text-primary)',
                  fontSize: 13,
                }}
              >
                <option value="four_eyes">Enforce Four-Eyes Manager Sign-off Policy</option>
                <option value="standard">Standard Single-User Direct Execution</option>
              </select>
            </div>
          </div>
        </div>

        {/* Action Controls */}
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
              boxShadow: '0 2px 4px rgba(37, 99, 235, 0.2)',
            }}
          >
            Initialize Project Workspace →
          </button>
        </div>
      </form>
    </div>
  );
};
