import type { FC, ChangeEvent } from 'react';
import { SecondaryButton } from '../Button';
import { TextInput } from './TextInput';
import styles from './Form.module.css';

export interface DirectoryPickerProps {
  value: string;
  onChange: (value: string) => void;
  onBrowse: () => void;
  onBlur?: () => void;
  placeholder?: string;
  hasError?: boolean;
  id?: string;
}

export const DirectoryPicker: FC<DirectoryPickerProps> = ({
  value,
  onChange,
  onBrowse,
  onBlur,
  placeholder = 'Select local workspace directory...',
  hasError = false,
  id,
}) => {
  return (
    <div className={styles.pickerRow}>
      <TextInput
        id={id}
        value={value}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        hasError={hasError}
        className={styles.pickerInput}
      />
      <SecondaryButton
        type="button"
        onClick={onBrowse}
        className={styles.browseButton}
      >
        Browse...
      </SecondaryButton>
    </div>
  );
};


