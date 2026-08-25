import type { FC, InputHTMLAttributes, Ref } from 'react';
import styles from './Form.module.css';

export interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
  ref?: Ref<HTMLInputElement>;
}

export const TextInput: FC<TextInputProps> = ({
  hasError = false,
  className = '',
  ref,
  ...props
}) => {
  const classNames = [
    styles.input,
    hasError ? styles.inputError : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return <input ref={ref} className={classNames} {...props} />;
};
