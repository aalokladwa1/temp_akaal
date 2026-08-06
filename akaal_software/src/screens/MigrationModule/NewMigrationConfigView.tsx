import type { FC } from 'react';
import type { MigrationPipeline, DatabaseEngine, MigrationDraftState } from '../../types/migration';
import { NewMigrationWizard } from './NewMigrationWizard';

export interface NewMigrationConfigViewProps {
  onBack: () => void;
  onLaunch: (newPipeline: MigrationPipeline) => void;
  onSaveDraft?: (draft: MigrationDraftState) => void;
  createProject: (name: string, sourceEngine: DatabaseEngine, targetEngine: DatabaseEngine) => MigrationPipeline;
  resumeDraftData?: MigrationDraftState;
}

export const NewMigrationConfigView: FC<NewMigrationConfigViewProps> = ({
  onBack,
  onLaunch,
  createProject,
}) => {
  return (
    <NewMigrationWizard
      onClose={onBack}
      onLaunch={onLaunch}
      createProject={createProject}
    />
  );
};

export { NewMigrationWizard } from './NewMigrationWizard';
