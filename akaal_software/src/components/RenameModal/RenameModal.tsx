import { useState, type FC } from 'react';
import { ConfirmDialog } from '../ConfirmDialog';

export interface RenameModalProps {
  isOpen: boolean;
  initialName: string;
  title?: string;
  itemType?: 'project' | 'migration';
  existingNames?: string[];
  maxLength?: number;
  onConfirm: (newName: string) => Promise<void> | void;
  onClose: () => void;
}

export const RenameModal: FC<RenameModalProps> = ({
  isOpen,
  initialName,
  title = 'Rename Project Workspace',
  itemType = 'project',
  existingNames = [],
  maxLength = 64,
  onConfirm,
  onClose,
}) => {
  const [name, setName] = useState(initialName);
  const [error, setError] = useState<string | null>(null);

  return (
    <ConfirmDialog
      isOpen={isOpen}
      title={title}
      affectedObject={`${itemType === 'project' ? 'Project Workspace' : 'Migration'}: ${initialName}`}
      message={`Renaming this ${itemType === 'project' ? 'Project Workspace' : 'Migration'} will:`}
      bulletPoints={[
        `update the ${itemType} name`,
        'preserve identifiers',
        'preserve configuration',
        'preserve execution history',
      ]}
      consequence="This operation preserves all migration history."
      confirmText={title}
      severity="info"
      inputConfig={{
        label: `Enter new ${itemType} name:`,
        value: name,
        maxLength,
        error,
        onChange: (val) => {
          setName(val);
          const trimmed = val.trim();
          if (!trimmed) {
            setError('Name cannot be empty.');
          } else if (
            existingNames.some(
              (n) => n.trim().toLowerCase() === trimmed.toLowerCase() && n.trim().toLowerCase() !== initialName.trim().toLowerCase()
            )
          ) {
            setError(`A ${itemType} named "${trimmed}" already exists.`);
          } else {
            setError(null);
          }
        },
      }}
      isConfirmDisabled={!name.trim() || !!error}
      onConfirm={() => onConfirm(name.trim())}
      onClose={onClose}
    />
  );
};
