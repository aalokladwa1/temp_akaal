import { useState, type FC } from 'react';
import type { MigrationPipeline, MigrationDraftState } from '../../types/migration';
import { useMigrationProjects } from '../../hooks/useMigrationProjects';
import { MigrationLanding } from './MigrationLanding';
import { ProjectWorkspaceView } from './ProjectWorkspaceView';
import { NewMigrationConfigView } from './NewMigrationConfigView';
import { NewProjectConfigView } from './NewProjectConfigView';

import { GovernanceCenterView } from './GovernanceCenterView';

export interface MigrationModuleProps {
  searchFilter?: string;
}

export const MigrationModule: FC<MigrationModuleProps> = ({ searchFilter = '' }) => {
  const [viewState, setViewState] = useState<'landing' | 'new_migration' | 'new_project' | 'workspace' | 'governance'>('landing');
  const [parentContext, setParentContext] = useState<'landing' | 'workspace'>('landing');
  const [selectedPipeline, setSelectedPipeline] = useState<MigrationPipeline | null>(null);
  const [resumeDraftData, setResumeDraftData] = useState<MigrationDraftState | undefined>(undefined);
  const [govTargetMigrationId, setGovTargetMigrationId] = useState<string | undefined>(undefined);
  const [govTargetGateId, setGovTargetGateId] = useState<string | undefined>(undefined);

  const { createProject, saveDraft } = useMigrationProjects('Aalok');

  const handleReturnFromConfig = () => {
    if (parentContext === 'workspace' && selectedPipeline) {
      setViewState('workspace');
    } else {
      setViewState('landing');
    }
  };

  const handleOpenGovernanceTarget = (migId?: string, gateId?: string) => {
    setGovTargetMigrationId(migId);
    setGovTargetGateId(gateId);
    setViewState('governance');
  };

  if (viewState === 'governance') {
    return (
      <GovernanceCenterView
        onBack={() => setViewState('landing')}
        initialMigrationId={govTargetMigrationId}
        initialGateId={govTargetGateId}
        onNavigateToMissionControl={(migId) => {
          if (selectedPipeline && selectedPipeline.id === migId) {
            setViewState('workspace');
          } else {
            setViewState('landing');
          }
        }}
      />
    );
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
        onOpenGovernance={handleOpenGovernanceTarget}
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
    <MigrationLanding
      onOpenProject={(pipe) => {
        setSelectedPipeline(pipe);
        setViewState('workspace');
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
  );
};
