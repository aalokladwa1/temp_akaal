import { type FC, type ReactNode } from 'react';

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  actionId?: string;
}

export const EmptyState: FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  actionId,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        borderRadius: 14,
        background: 'var(--dash-card-bg)',
        border: '1px border var(--dash-card-border)',
        boxShadow: 'var(--dash-card-shadow)',
        textAlign: 'center',
        margin: '20px 0',
      }}
    >
      {icon && (
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: 'var(--dash-surface)',
            border: '1px solid var(--dash-border)',
            color: 'var(--dash-text-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 16,
          }}
        >
          {icon}
        </div>
      )}
      <h3
        style={{
          fontSize: 16,
          fontWeight: 700,
          color: 'var(--dash-text-primary)',
          margin: '0 0 6px 0',
          letterSpacing: '-0.01em',
        }}
      >
        {title}
      </h3>
      <p
        style={{
          fontSize: 13,
          color: 'var(--dash-text-secondary)',
          margin: '0 0 20px 0',
          maxWidth: 420,
          lineHeight: 1.4,
        }}
      >
        {description}
      </p>

      {actionLabel && onAction && (
        <button
          id={actionId}
          onClick={onAction}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 18px',
            borderRadius: 8,
            background: '#2563EB',
            color: '#FFFFFF',
            border: 'none',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 2px 4px rgba(37, 99, 235, 0.2)',
            transition: 'background 120ms ease, transform 120ms ease',
          }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
