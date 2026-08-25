import type { FC, ReactNode } from 'react';
import styles from './Card.module.css';

export interface CardProps {
  className?: string;
  children: ReactNode;
}

export const Card: FC<CardProps> = ({ className = '', children }) => {
  return <div className={`${styles.card} ${className}`.trim()}>{children}</div>;
};
