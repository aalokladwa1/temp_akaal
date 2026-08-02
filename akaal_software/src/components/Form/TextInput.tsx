import type { FC, InputHTMLAttributes } from 'react';
import styles from './Form.module.css';

export interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
}

export const TextInput: FC<TextInputProps> = ({
  hasError = false,
  className = '',
  ...props
}) => {
  const classNames = [
    styles.input,
    hasError ? styles.inputError : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return <input className={classNames} {...props} />;
};
