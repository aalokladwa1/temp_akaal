import type { FC, ReactNode, ButtonHTMLAttributes, Ref } from 'react';
import styles from './Button.module.css';

export type ButtonVariant = 'primary' | 'secondary';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  fullWidth?: boolean;
  children: ReactNode;
  ref?: Ref<HTMLButtonElement>;
}

export const Button: FC<ButtonProps> = ({
  variant = 'primary',
  fullWidth = true,
  className = '',
  children,
  type = 'button',
  ref,
  ...props
}) => {
  const classNames = [
    styles.button,
    styles[variant],
    fullWidth ? styles.fullWidth : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button ref={ref} type={type} className={classNames} {...props}>
      {children}
    </button>
  );
};

export const PrimaryButton: FC<Omit<ButtonProps, 'variant'>> = (props) => (
  <Button variant="primary" {...props} />
);

export const SecondaryButton: FC<Omit<ButtonProps, 'variant'>> = (props) => (
  <Button variant="secondary" {...props} />
);
