import type { FC } from 'react';
import type { ThemePreference } from '../../types/workspace';
import styles from './Form.module.css';

export interface ThemeOption {
  value: ThemePreference;
  label: string;
  description: string;
}

const OPTIONS: ThemeOption[] = [
  {
    value: 'light',
    label: 'Light',
    description: 'Enterprise Blue light theme for optimal clarity in daytime environments.',
  },
  {
    value: 'dark',
    label: 'Dark',
    description: 'Midnight Glass dark theme for reduced eye strain in low-light environments.',
  },
  {
    value: 'system',
    label: 'Follow System',
    description: 'Automatically synchronizes appearance with operating system preferences.',
  },
];

export interface ThemeRadioGroupProps {
  value: ThemePreference;
  onChange: (value: ThemePreference) => void;
  name?: string;
}

export const ThemeRadioGroup: FC<ThemeRadioGroupProps> = ({
  value,
  onChange,
  name = 'theme-preference',
}) => {
  return (
    <div className={styles.radioGroup} role="radiogroup" aria-label="Appearance Theme Preference">
      {OPTIONS.map((opt) => {
        const isSelected = value === opt.value;
        return (
          <label
            key={opt.value}
            className={`${styles.radioOption} ${isSelected ? styles.radioOptionSelected : ''}`}
          >
            <input
              type="radio"
              name={name}
              value={opt.value}
              checked={isSelected}
              onChange={() => onChange(opt.value)}
              className={styles.radioInput}
            />
            <div>
              <div className={styles.radioLabel}>{opt.label}</div>
              <div className={styles.helperText}>{opt.description}</div>
            </div>
          </label>
        );
      })}
    </div>
  );
};
