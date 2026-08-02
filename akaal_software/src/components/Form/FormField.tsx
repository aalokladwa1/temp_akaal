import type { FC, ReactNode } from 'react';
import styles from './Form.module.css';

export interface FormFieldProps {
  label: string;
  htmlFor?: string;
  error?: string;
  helperText?: string;
  children: ReactNode;
}

export const FormField: FC<FormFieldProps> = ({
  label,
  htmlFor,
  error,
  helperText,
  children,
}) => {
  return (
    <div className={styles.fieldContainer}>
      <label htmlFor={htmlFor} className={styles.label}>
        {label}
      </label>
      {children}
      {error ? (
        <span className={styles.errorText} role="alert" id={htmlFor ? `${htmlFor}-error` : undefined}>
          {error}
        </span>
      ) : helperText ? (
        <span className={styles.helperText}>{helperText}</span>
      ) : null}
    </div>
  );
};
