import { useState, type FC } from 'react';
import type { MigrationPipeline, MigrationDraftState } from '../../types/migration';
import { useMigrationProjects } from '../../hooks/useMigrationProjects';
import { MigrationLanding } from './MigrationLanding';
import { ProjectWorkspaceView } from './ProjectWorkspaceView';
import { NewMigrationConfigView } from './NewMigrationConfigView';
import { NewProjectConfigView } from './NewProjectConfigView';

import { GovernanceCenterView } from './GovernanceCenterView';

import { ConfirmDialog } from '../../components/ConfirmDialog';
import { runtimeSessionRepository } from '../../repositories/runtimeSessionRepository';

export interface MigrationModuleProps {
  searchFilter?: string;
}

export const MigrationModule: FC<MigrationModuleProps> = ({ searchFilter = '' }) => {
  const [viewState, setViewState] = useState<'landing' | 'new_migration' | 'new_project' | 'workspace' | 'governance'>('landing');
  const [parentContext, setParentContext] = useState<'landing' | 'workspace'>('landing');
  const [selectedPipeline, setSelectedPipeline] = useState<MigrationPipeline | null>(null);
  const [resumeDraftData, setResumeDraftData] = useState<MigrationDraftState | undefined>(undefined);
  const [openWorkspaceConfirm, setOpenWorkspaceConfirm] = useState<{ isOpen: boolean; pipe: MigrationPipeline | null }>({
    isOpen: false,
    pipe: null,
  });

  const { createProject, saveDraft } = useMigrationProjects('Aalok');

  const handleReturnFromConfig = () => {
    if (parentContext === 'workspace' && selectedPipeline) {
      setViewState('workspace');
    } else {
      setViewState('landing');
    }
  };

  if (viewState === 'governance') {
    return <GovernanceCenterView onBack={() => setViewState('landing')} />;
  }

  if (viewState === 'workspace' && selectedPipeline) {
    return (
      <ProjectWorkspaceView
        project={selectedPipeline}
        onBack={() => setViewState('landing')}
        onOpenNewMigration={() => {
          setParentContext('workspace');
          setViewState('new_migration');
        }}
      />
    );
  }

  if (viewState === 'new_project') {
    return (
      <NewProjectConfigView
        onBack={() => setViewState('landing')}
        onLaunch={(created) => {
          setSelectedPipeline(created);
          setViewState('workspace');
        }}
        createProject={createProject}
      />
    );
  }

  if (viewState === 'new_migration') {
    return (
      <NewMigrationConfigView
        onBack={handleReturnFromConfig}
        onLaunch={(created) => {
          setSelectedPipeline(created);
          setViewState('workspace');
        }}
        onSaveDraft={(draft) => {
          saveDraft(draft);
          handleReturnFromConfig();
        }}
        createProject={createProject}
        resumeDraftData={resumeDraftData}
      />
    );
  }

  return (
    <>
      <MigrationLanding
        onOpenProject={(pipe) => {
          setOpenWorkspaceConfirm({ isOpen: true, pipe });
        }}
        onOpenNewMigrationConfig={(draftData) => {
          setResumeDraftData(draftData);
          setParentContext('landing');
          setViewState('new_migration');
        }}
        onOpenNewProjectConfig={() => {
          setViewState('new_project');
        }}
        onOpenGovernanceCenter={() => {
          setViewState('governance');
        }}
        searchFilter={searchFilter}
      />

      {openWorkspaceConfirm.pipe && (
        <ConfirmDialog
          isOpen={openWorkspaceConfirm.isOpen}
          title="Open Project Workspace"
          affectedObject={`Project: ${openWorkspaceConfirm.pipe.name}`}
          message="This will open the migration workspace and load the latest runtime state."
          bulletPoints={[
            'load active runtime session context',
            'initialize live IPC socket listeners',
            'fetch project telemetry metrics',
          ]}
          consequence="Navigates to active execution workstation."
          confirmText="Open Workspace"
          severity="info"
          onConfirm={() => {
            const pipe = openWorkspaceConfirm.pipe!;
            setSelectedPipeline(pipe);
            setViewState('workspace');
            setOpenWorkspaceConfirm({ isOpen: false, pipe: null });
            runtimeSessionRepository.appendEvent(`sess-${pipe.id}`, {
              eventId: `evt-open-${Date.now()}`,
              timestamp: new Date().toISOString(),
              sessionId: `sess-${pipe.id}`,
              migrationId: pipe.id,
              severity: 'info',
              source: 'bridge',
              stageNumber: 1,
              eventType: 'WorkspaceOpened',
              payload: { project_name: pipe.name },
            });
          }}
          onClose={() => setOpenWorkspaceConfirm({ isOpen: false, pipe: null })}
        />
      )}
    </>
  );
};
