'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';

// ─── Types ────────────────────────────────────────────────────────────────────

type StatusType = 'healthy' | 'warning' | 'critical' | 'offline' | 'running' | 'completed' | 'failed' | 'pending' | 'paused';
type SeverityType = 'info' | 'success' | 'warning' | 'error';
type ErrorStateType = 'backend_unavailable' | 'metrics_unavailable' | 'permission_denied' | 'partial_data' | 'network_disconnected' | null;

interface MetricCard {
  id: string;
  label: string;
  value: string | number;
  trend: number;
  trendLabel: string;
  supportingText: string;
  icon: React.ReactNode;
  accentColor: string;
}

interface HealthItem {
  id: string;
  label: string;
  status: StatusType;
  detail: string;
}

interface Migration {
  id: string;
  name: string;
  source: string;
  target: string;
  status: StatusType;
  progress: number;
  started: string;
  duration: string;
  owner: string;
}

interface ActivityEvent {
  id: string;
  timestamp: string;
  icon: React.ReactNode;
  description: string;
  migration: string;
  severity: SeverityType;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_MIGRATIONS: Migration[] = [
  { id: 'm1', name: 'prod-oracle-to-postgres', source: 'Oracle 19c', target: 'PostgreSQL 15', status: 'running', progress: 67, started: '2026-07-25 14:22', duration: '1h 55m', owner: 'sarah.chen' },
  { id: 'm2', name: 'analytics-mysql-warehouse', source: 'MySQL 8.0', target: 'Snowflake', status: 'completed', progress: 100, started: '2026-07-25 11:00', duration: '3h 12m', owner: 'james.okafor' },
  { id: 'm3', name: 'legacy-mssql-migration', source: 'SQL Server 2019', target: 'Azure SQL', status: 'failed', progress: 34, started: '2026-07-25 13:45', duration: '32m', owner: 'priya.nair' },
  { id: 'm4', name: 'crm-postgres-upgrade', source: 'PostgreSQL 12', target: 'PostgreSQL 15', status: 'pending', progress: 0, started: '—', duration: '—', owner: 'alex.morgan' },
  { id: 'm5', name: 'dw-redshift-consolidation', source: 'Redshift', target: 'BigQuery', status: 'running', progress: 12, started: '2026-07-25 15:58', duration: '19m', owner: 'sarah.chen' },
  { id: 'm6', name: 'iot-timescale-archive', source: 'TimescaleDB', target: 'ClickHouse', status: 'paused', progress: 51, started: '2026-07-25 09:30', duration: '2h 41m', owner: 'dev.ops' },
];

const MOCK_ACTIVITY: ActivityEvent[] = [
  {
    id: 'a1', timestamp: '16:17:02',
    icon: <ActivityIcon type="started" />,
    description: 'Migration started — initial schema validation passed',
    migration: 'dw-redshift-consolidation',
    severity: 'info',
  },
  {
    id: 'a2', timestamp: '16:14:38',
    icon: <ActivityIcon type="success" />,
    description: 'Validation completed — 0 schema conflicts detected',
    migration: 'prod-oracle-to-postgres',
    severity: 'success',
  },
  {
    id: 'a3', timestamp: '16:09:11',
    icon: <ActivityIcon type="warning" />,
    description: 'CDC lag spike detected — 4.2s replication delay',
    migration: 'prod-oracle-to-postgres',
    severity: 'warning',
  },
  {
    id: 'a4', timestamp: '15:58:44',
    icon: <ActivityIcon type="error" />,
    description: 'Failure detected — foreign key constraint violation on table orders',
    migration: 'legacy-mssql-migration',
    severity: 'error',
  },
  {
    id: 'a5', timestamp: '15:47:20',
    icon: <ActivityIcon type="approval" />,
    description: 'Approval granted — production cutover authorized',
    migration: 'analytics-mysql-warehouse',
    severity: 'success',
  },
  {
    id: 'a6', timestamp: '15:33:05',
    icon: <ActivityIcon type="cdc" />,
    description: 'CDC connected — change data capture stream established',
    migration: 'prod-oracle-to-postgres',
    severity: 'info',
  },
  {
    id: 'a7', timestamp: '14:22:00',
    icon: <ActivityIcon type="started" />,
    description: 'Migration started — pre-flight checks passed',
    migration: 'prod-oracle-to-postgres',
    severity: 'info',
  },
];

// ─── Icon Components ──────────────────────────────────────────────────────────

function ActivityIcon({ type }: { type: string }) {
  const configs: Record<string, { color: string; bg: string; path: React.ReactNode }> = {
    started: {
      color: '#38BDF8', bg: 'rgba(56,189,248,0.12)',
      path: <path d="M8 3v5l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />,
    },
    success: {
      color: '#22C55E', bg: 'rgba(34,197,94,0.12)',
      path: <path d="M3 8l3.5 3.5L13 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />,
    },
    warning: {
      color: '#F59E0B', bg: 'rgba(245,158,11,0.12)',
      path: <><path d="M8 5v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /><circle cx="8" cy="11" r="0.75" fill="currentColor" /></>,
    },
    error: {
      color: '#EF4444', bg: 'rgba(239,68,68,0.12)',
      path: <path d="M5 5l6 6M11 5l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />,
    },
    approval: {
      color: '#22C55E', bg: 'rgba(34,197,94,0.12)',
      path: <path d="M4 8l2.5 2.5L12 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />,
    },
    cdc: {
      color: '#38BDF8', bg: 'rgba(56,189,248,0.12)',
      path: <><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" /><path d="M8 3v2M8 11v2M3 8h2M11 8h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></>,
    },
    rollback: {
      color: '#F59E0B', bg: 'rgba(245,158,11,0.12)',
      path: <path d="M4 8h8M4 8l3-3M4 8l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />,
    },
  };
  const cfg = configs[type] || configs.started;
  return (
    <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center" style={{ background: cfg.bg }}>
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true" style={{ color: cfg.color }}>
        {cfg.path}
      </svg>
    </div>
  );
}

// ─── Status Chip ──────────────────────────────────────────────────────────────

function StatusChip({ status }: { status: StatusType }) {
  const configs: Record<StatusType, { label: string; color: string; bg: string; border: string; dot: string }> = {
    healthy:   { label: 'Healthy',   color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)',   dot: '#22C55E' },
    running:   { label: 'Running',   color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  border: 'rgba(56,189,248,0.2)',  dot: '#38BDF8' },
    completed: { label: 'Completed', color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)',   dot: '#22C55E' },
    failed:    { label: 'Failed',    color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)',   dot: '#EF4444' },
    pending:   { label: 'Pending',   color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)', dot: '#94A3B8' },
    warning:   { label: 'Warning',   color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  dot: '#F59E0B' },
    critical:  { label: 'Critical',  color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)',   dot: '#EF4444' },
    offline:   { label: 'Offline',   color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)', dot: '#64748B' },
    paused:    { label: 'Paused',    color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  dot: '#F59E0B' },
  };
  const cfg = configs[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium"
      style={{
        color: cfg.color,
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: '0.04em',
        fontSize: '10px',
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.dot }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────

function ProgressBar({ value, status }: { value: number; status: StatusType }) {
  const color = status === 'failed' ? 'var(--akaal-error)' : status === 'completed' ? 'var(--akaal-success)' : 'var(--akaal-primary)';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-border)', minWidth: '60px' }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${value}%`, background: color }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${value}% complete`}
        />
      </div>
      <span className="text-xs tabular-nums flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
        {value}%
      </span>
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded ${className ?? ''}`}
      style={{
        background: 'linear-gradient(90deg, var(--akaal-skeleton-base) 25%, var(--akaal-skeleton-shine) 50%, var(--akaal-skeleton-base) 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite',
        ...style,
      }}
      aria-hidden="true"
    />
  );
}

// ─── Metric Card Skeleton ─────────────────────────────────────────────────────

function MetricCardSkeleton() {
  return (
    <div
      className="rounded-lg p-4"
      style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}
    >
      <div className="flex items-start justify-between mb-3">
        <Skeleton style={{ width: '32px', height: '32px', borderRadius: '8px' }} />
        <Skeleton style={{ width: '48px', height: '18px' }} />
      </div>
      <Skeleton style={{ width: '60px', height: '28px', marginBottom: '6px' }} />
      <Skeleton style={{ width: '100px', height: '12px' }} />
    </div>
  );
}

// ─── Sparkline Chart (SVG) ────────────────────────────────────────────────────

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 80;
  const h = 28;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.8"
      />
    </svg>
  );
}

// ─── Mini Bar Chart ───────────────────────────────────────────────────────────

function MiniBarChart({ data, color, label }: { data: number[]; color: string; label: string }) {
  const max = Math.max(...data);
  return (
    <div>
      <p className="text-xs mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{label}</p>
      <div className="flex items-end gap-1" style={{ height: '48px' }}>
        {data.map((v, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm transition-all duration-300"
            style={{
              height: `${(v / max) * 100}%`,
              background: color,
              opacity: i === data.length - 1 ? 1 : 0.4 + (i / data.length) * 0.4,
              minHeight: '2px',
            }}
            aria-hidden="true"
          />
        ))}
      </div>
    </div>
  );
}

// ─── Error State ──────────────────────────────────────────────────────────────

function ErrorState({ type, onRetry }: { type: NonNullable<ErrorStateType>; onRetry: () => void }) {
  const configs: Record<NonNullable<ErrorStateType>, { title: string; detail: string; icon: React.ReactNode; color: string }> = {
    backend_unavailable: {
      title: 'Backend Unavailable',
      detail: 'The migration platform API is not responding. Operations are paused until connectivity is restored.',
      color: '#EF4444',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M10 2a8 8 0 1 0 0 16A8 8 0 0 0 10 2Zm0 4v4m0 4h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
    metrics_unavailable: {
      title: 'Metrics Unavailable',
      detail: 'Dashboard metrics could not be loaded. The telemetry service may be temporarily offline.',
      color: '#F59E0B',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M3 17l4-8 4 4 3-6 3 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ),
    },
    permission_denied: {
      title: 'Access Denied',
      detail: 'You do not have permission to view this dashboard. Contact your administrator to request access.',
      color: '#EF4444',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <rect x="4" y="9" width="12" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
          <path d="M7 9V6a3 3 0 0 1 6 0v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
    partial_data: {
      title: 'Partial Data Loaded',
      detail: 'Some dashboard sections could not be loaded. Displaying available data. Retry to load missing sections.',
      color: '#F59E0B',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" />
          <path d="M10 6v4l2.5 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
    network_disconnected: {
      title: 'Network Disconnected',
      detail: 'No network connection detected. Dashboard data cannot be refreshed until connectivity is restored.',
      color: '#EF4444',
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M2 2l16 16M8.5 8.5A5 5 0 0 0 5 12M11.5 11.5A5 5 0 0 1 15 8M3 5a11 11 0 0 1 5.5-2.5M17 5a11 11 0 0 0-5.5-2.5M10 16h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
  };
  const cfg = configs[type];
  return (
    <div
      className="flex items-start gap-4 rounded-lg p-4"
      role="alert"
      style={{ background: `rgba(${type === 'permission_denied' || type === 'backend_unavailable' || type === 'network_disconnected' ? '239,68,68' : '245,158,11'},0.06)`, border: `1px solid ${cfg.color}22` }}
    >
      <div className="flex-shrink-0 mt-0.5" style={{ color: cfg.color }}>{cfg.icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold mb-0.5" style={{ color: cfg.color, fontFamily: "'JetBrains Mono', monospace" }}>{cfg.title}</p>
        <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{cfg.detail}</p>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="flex-shrink-0 text-xs font-medium px-3 py-1.5 rounded transition-all duration-150 focus:outline-none focus-visible:ring-2"
        style={{
          background: 'var(--akaal-hover-bg)',
          border: '1px solid var(--akaal-border)',
          color: 'var(--akaal-text-secondary)',
          fontFamily: "'Inter', sans-serif",
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-active-bg)'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
      >
        Retry
      </button>
    </div>
  );
}

// ─── Card Shell ───────────────────────────────────────────────────────────────

function Card({ children, className, style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded-lg ${className ?? ''}`}
      style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)', ...style }}
    >
      {children}
    </div>
  );
}

// ─── Section Header ───────────────────────────────────────────────────────────

function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--akaal-card-border)' }}>
      <div>
        <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{title}</h2>
        {subtitle && <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const navItems = [
    { href: '/dashboard', label: 'Dashboard', active: true, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/migrations', label: 'Migrations', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/execution-center', label: 'Execution', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M6 5.5l5 2.5-5 2.5V5.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { href: '/databases', label: 'Databases', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="6" ry="2" stroke="currentColor" strokeWidth="1.3" /><path d="M2 4v4c0 1.1 2.7 2 6 2s6-.9 6-2V4" stroke="currentColor" strokeWidth="1.3" /><path d="M2 8v4c0 1.1 2.7 2 6 2s6-.9 6-2V8" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/live-monitor', label: 'Live Monitor', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M4 8l2-2 2 2 2-3 2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/agents', label: 'Agents', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/reports', label: 'Reports', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/system', label: 'System', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="3" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="4.5" r="0.8" fill="currentColor" /><circle cx="4" cy="9.5" r="0.8" fill="currentColor" /><path d="M5 13h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/settings', label: 'Settings', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.4 3.4l.85.85M11.75 11.75l.85.85M3.4 12.4l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
  ];

  return (
    <aside
      className="flex flex-col flex-shrink-0 h-full"
      style={{
        width: collapsed ? '56px' : '220px',
        background: 'var(--akaal-sidebar-gradient)',
        borderRight: '1px solid var(--akaal-sidebar-border)',
        transition: 'width 0.2s ease',
        overflow: 'hidden',
      }}
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div
        className="flex items-center gap-3 px-3 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--akaal-sidebar-border)', minHeight: '57px' }}
      >
        <AppImage
          src="/assets/images/app_logo.png"
          alt="AKAAL"
          width={28}
          height={28}
          className="flex-shrink-0"
          style={{ filter: 'drop-shadow(0 1px 4px rgba(37,99,235,0.3))' }}
        />
        {!collapsed && (
          <span
            className="font-bold tracking-widest uppercase text-sm"
            style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.15em', whiteSpace: 'nowrap' }}
          >
            AKAAL
          </span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto" aria-label="Primary navigation">
        <ul className="space-y-0.5 px-2" role="list">
          {navItems.map(item => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="flex items-center gap-3 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 group"
                style={{
                  color: item.active ? 'var(--akaal-text)' : 'var(--akaal-text-muted)',
                  background: item.active ? 'var(--akaal-primary-subtle)' : 'transparent',
                  borderLeft: item.active ? '2px solid var(--akaal-primary)' : '2px solid transparent',
                  fontFamily: "'Inter', sans-serif",
                  whiteSpace: 'nowrap',
                }}
                aria-current={item.active ? 'page' : undefined}
                onMouseEnter={e => { if (!item.active) { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; } }}
                onMouseLeave={e => { if (!item.active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; } }}
              >
                <span className="flex-shrink-0">{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <div className="px-2 py-3 flex-shrink-0" style={{ borderTop: '1px solid var(--akaal-sidebar-border)' }}>
        <button
          type="button"
          onClick={onToggle}
          className="w-full flex items-center justify-center p-2 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: 'var(--akaal-text-muted)' }}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
            <path d="M9 2L4 7l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </aside>
  );
}

// ─── Top Navigation ───────────────────────────────────────────────────────────

function TopNav({ onRefresh, isRefreshing }: { onRefresh: () => void; isRefreshing: boolean }) {
  const [searchValue, setSearchValue] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header
      className="flex items-center gap-4 px-4 flex-shrink-0"
      style={{
        height: '57px',
        background: 'var(--akaal-nav-bg)',
        borderBottom: '1px solid var(--akaal-nav-border)',
      }}
      role="banner"
    >
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 flex-shrink-0">
        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Platform</span>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Dashboard</span>
      </nav>

      {/* Global Search */}
      <div className="flex-1 max-w-xs relative">
        <div className="relative">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
            <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
            <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            placeholder="Search migrations, databases…"
            value={searchValue}
            onChange={e => setSearchValue(e.target.value)}
            className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
            style={{
              background: 'var(--akaal-input-bg)',
              border: '1px solid var(--akaal-input-border)',
              color: 'var(--akaal-text)',
              fontFamily: "'Inter', sans-serif",
            }}
            aria-label="Global search"
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs px-1 rounded" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>⌘K</kbd>
        </div>
      </div>

      <div className="flex-1" />

      {/* Theme Switcher */}
      <ThemeSwitcher />

      {/* Notifications */}
      <div className="relative">
        <button
          type="button"
          onClick={() => { setNotifOpen(v => !v); setProfileOpen(false); }}
          className="relative flex items-center justify-center w-8 h-8 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: 'var(--akaal-text-muted)' }}
          aria-label="Notifications (3 unread)"
          aria-expanded={notifOpen}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M8 1.5a5 5 0 0 0-5 5v3l-1.5 2h13L13 9.5v-3a5 5 0 0 0-5-5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
            <path d="M6.5 13.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.3" />
          </svg>
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full flex-shrink-0" style={{ background: 'var(--akaal-error)', border: '1.5px solid var(--akaal-nav-bg)' }} aria-hidden="true" />
        </button>
        {notifOpen && (
          <div
            className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50"
            style={{ width: '300px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }}
            role="dialog"
            aria-label="Notifications"
          >
            <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Notifications</p>
            </div>
            {[
              { title: 'Migration Failed', detail: 'legacy-mssql-migration encountered a constraint error', time: '7m ago', color: 'var(--akaal-error)' },
              { title: 'CDC Lag Warning', detail: 'prod-oracle-to-postgres replication delay: 4.2s', time: '23m ago', color: 'var(--akaal-warning)' },
              { title: 'Approval Required', detail: 'crm-postgres-upgrade awaiting production sign-off', time: '1h ago', color: 'var(--akaal-secondary)' },
            ].map((n, i) => (
              <div key={i} className="px-3 py-2.5 transition-colors cursor-pointer" style={{ borderBottom: i < 2 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                <div className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: n.color }} aria-hidden="true" />
                  <div>
                    <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{n.title}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{n.detail}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{n.time}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User Profile */}
      <div className="relative">
        <button
          type="button"
          onClick={() => { setProfileOpen(v => !v); setNotifOpen(false); }}
          className="flex items-center gap-2 px-2 py-1.5 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: 'var(--akaal-text-muted)' }}
          aria-label="User profile menu"
          aria-expanded={profileOpen}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
        >
          <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }} aria-hidden="true">SC</div>
          <span className="text-xs font-medium hidden sm:block" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>sarah.chen</span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
        </button>
        {profileOpen && (
          <div
            className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50"
            style={{ width: '200px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }}
            role="menu"
            aria-label="User menu"
          >
            <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>sarah.chen</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Platform Administrator</p>
            </div>
            {['Profile Settings', 'API Keys', 'Audit Log', 'Sign Out'].map((item, i) => (
              <button key={i} type="button" role="menuitem" className="w-full text-left px-3 py-2 text-xs transition-colors"
                style={{ color: item === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", borderBottom: i < 3 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = item === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-secondary)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = item === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)'; }}
              >
                {item}
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorState, setErrorState] = useState<ErrorStateType>(null);
  const [sortField, setSortField] = useState<keyof Migration>('started');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<StatusType | 'all'>('all');
  const [lastRefreshed, setLastRefreshed] = useState('');

  // Simulate initial load
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
      setLastRefreshed(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
    }, 1400);
    return () => clearTimeout(timer);
  }, []);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      setLastRefreshed(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
    }, 1000);
  }, []);

  const handleRetry = useCallback(() => {
    setErrorState(null);
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1000);
  }, []);

  // Sort & filter migrations
  const filteredMigrations = MOCK_MIGRATIONS
    .filter(m => statusFilter === 'all' || m.status === statusFilter)
    .sort((a, b) => {
      const av = a[sortField] as string;
      const bv = b[sortField] as string;
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });

  const handleSort = (field: keyof Migration) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  // Metric data
  const metrics: MetricCard[] = [
    {
      id: 'active', label: 'Active Migrations', value: 2, trend: 1, trendLabel: '+1 from yesterday',
      supportingText: '2 running, 1 paused',
      accentColor: '#38BDF8',
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    },
    {
      id: 'completed', label: 'Completed Today', value: 1, trend: -2, trendLabel: '-2 from yesterday',
      supportingText: '1 successful, 0 partial',
      accentColor: '#22C55E',
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 8l3.5 3.5L13 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    },
    {
      id: 'failed', label: 'Failed Jobs', value: 1, trend: 1, trendLabel: '+1 from yesterday',
      supportingText: 'Requires immediate review',
      accentColor: '#EF4444',
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M5 5l6 6M11 5l-6 6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>,
    },
    {
      id: 'approvals', label: 'Pending Approvals', value: 1, trend: 0, trendLabel: 'No change',
      supportingText: 'Awaiting sign-off',
      accentColor: '#F59E0B',
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 2v4l3 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.4" /></svg>,
    },
    {
      id: 'databases', label: 'Connected Databases', value: 14, trend: 2, trendLabel: '+2 this week',
      supportingText: '12 active, 2 standby',
      accentColor: '#2563EB',
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="5" ry="1.8" stroke="currentColor" strokeWidth="1.3" /><path d="M3 4v4c0 1 2.2 1.8 5 1.8s5-.8 5-1.8V4" stroke="currentColor" strokeWidth="1.3" /><path d="M3 8v4c0 1 2.2 1.8 5 1.8s5-.8 5-1.8V8" stroke="currentColor" strokeWidth="1.3" /></svg>,
    },
    {
      id: 'agents', label: 'Active Agents', value: 6, trend: 0, trendLabel: 'Stable',
      supportingText: '6 of 8 agents online',
      accentColor: '#A78BFA',
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.6 3.6l1.1 1.1M11.3 11.3l1.1 1.1M3.6 12.4l1.1-1.1M11.3 4.7l1.1-1.1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>,
    },
  ];

  // Health items
  const healthItems: HealthItem[] = [
    { id: 'sys', label: 'System Status', status: 'healthy', detail: 'All services operational' },
    { id: 'agent', label: 'Agent Health', status: 'warning', detail: '2 agents degraded' },
    { id: 'cdc', label: 'CDC Status', status: 'warning', detail: 'Replication lag: 4.2s' },
    { id: 'queue', label: 'Queue Health', status: 'healthy', detail: '0 stalled jobs' },
    { id: 'db', label: 'DB Connectivity', status: 'healthy', detail: '14/14 connected' },
    { id: 'storage', label: 'Storage Usage', status: 'healthy', detail: '62% utilized' },
  ];

  // Chart data
  const throughputData = [42, 58, 51, 73, 68, 82, 77, 91, 85, 94, 88, 96];
  const rowsData = [120, 145, 132, 178, 165, 201, 188, 215, 198, 234, 221, 248];
  const queueData = [8, 12, 6, 15, 9, 11, 7, 13, 5, 8, 10, 6];
  const successData = [95, 92, 97, 89, 94, 96, 91, 98, 93, 97, 95, 99];

  const tableColumns: { key: keyof Migration; label: string; sortable: boolean }[] = [
    { key: 'name', label: 'Migration Name', sortable: true },
    { key: 'source', label: 'Source', sortable: true },
    { key: 'target', label: 'Target', sortable: true },
    { key: 'status', label: 'Status', sortable: true },
    { key: 'progress', label: 'Progress', sortable: false },
    { key: 'started', label: 'Started', sortable: true },
    { key: 'duration', label: 'Duration', sortable: false },
    { key: 'owner', label: 'Owner', sortable: true },
  ];

  const quickActions = [
    { label: 'Create Migration', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>, color: '#2563EB', href: '/migrations/new' },
    { label: 'Connect Database', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="5" ry="1.8" stroke="currentColor" strokeWidth="1.3" /><path d="M3 4v4c0 1 2.2 1.8 5 1.8s5-.8 5-1.8V4" stroke="currentColor" strokeWidth="1.3" /><path d="M3 8v4c0 1 2.2 1.8 5 1.8s5-.8 5-1.8V8" stroke="currentColor" strokeWidth="1.3" /></svg>, color: '#38BDF8', href: '/databases/connect' },
    { label: 'Open Reports', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>, color: '#A78BFA', href: '/reports' },
    { label: 'Manage Agents', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>, color: '#22C55E', href: '/agents' },
    { label: 'Review Failures', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M5 5l6 6M11 5l-6 6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>, color: '#EF4444', href: '/migrations?status=failed' },
    { label: 'System Settings', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.6 3.6l1.1 1.1M11.3 11.3l1.1 1.1M3.6 12.4l1.1-1.1M11.3 4.7l1.1-1.1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>, color: '#94A3B8', href: '/settings' },
  ];

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}
    >
      {/* Background lighting */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0" style={{ background: 'radial-gradient(ellipse 80% 50% at 10% 0%, rgba(37,99,235,0.06) 0%, transparent 60%)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0" style={{ background: 'radial-gradient(ellipse 40% 30% at 90% 0%, rgba(56,189,248,0.03) 0%, transparent 60%)' }} />

      {/* Sidebar */}
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />

      {/* Main content */}
      <div className="flex flex-col flex-1 min-w-0 relative z-10">
        {/* Top Nav */}
        <TopNav onRefresh={handleRefresh} isRefreshing={isRefreshing} />

        {/* Scrollable content */}
        <main
          className="flex-1 overflow-y-auto overflow-x-hidden"
          style={{ background: 'transparent' }}
          id="main-content"
          aria-label="Dashboard main content"
        >
          <div className="px-4 sm:px-6 py-5 max-w-screen-2xl mx-auto">

            {/* ── Page Header ── */}
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
              <div>
                <h1 className="text-xl font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Dashboard</h1>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Enterprise Migration Operations Overview</p>
                {lastRefreshed && (
                  <p className="text-xs mt-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
                    Last refreshed {lastRefreshed}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {/* New Migration */}
                <Link
                  href="/migration-workspace"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2"
                  style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif", boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.filter = 'brightness(1.1)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.filter = 'none'; }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 2v8M2 6h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                  New Migration
                </Link>
                {/* Refresh */}
                <button
                  type="button"
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 disabled:opacity-50"
                  style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                  aria-label={isRefreshing ? 'Refreshing dashboard' : 'Refresh dashboard'}
                  onMouseEnter={e => { if (!isRefreshing) { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-active-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-secondary)'; } }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className={isRefreshing ? 'animate-spin' : ''}>
                    <path d="M10 6A4 4 0 1 1 6 2M10 2v4H6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  {isRefreshing ? 'Refreshing…' : 'Refresh'}
                </button>
                {/* Export */}
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                  style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                  aria-label="Export dashboard summary"
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-active-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-secondary)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1v7M3 5l3 3 3-3M1 9v1a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  Export Summary
                </button>
              </div>
            </div>

            {/* Global error state */}
            {errorState && (
              <div className="mb-6">
                <ErrorState type={errorState} onRetry={handleRetry} />
              </div>
            )}

            {/* ── ROW 1: Primary Metrics ── */}
            <section aria-label="Primary metrics" className="mb-6">
              <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
                {isLoading
                  ? Array(6).fill(0).map((_, i) => <MetricCardSkeleton key={i} />)
                  : metrics.map(m => (
                    <Card key={m.id} className="p-4 transition-all duration-150 cursor-default">
                      <div className="flex items-start justify-between mb-3">
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                          style={{ background: `${m.accentColor}14`, color: m.accentColor }}
                          aria-hidden="true"
                        >
                          {m.icon}
                        </div>
                        {/* Trend */}
                        <div className="flex items-center gap-1">
                          {m.trend > 0 ? (
                            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 7l3-4 3 4" stroke="#22C55E" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          ) : m.trend < 0 ? (
                            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 3l3 4 3-4" stroke="#EF4444" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          ) : (
                            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 5h6" stroke="#64748B" strokeWidth="1.3" strokeLinecap="round" /></svg>
                          )}
                          <span
                            className="text-xs"
                            style={{
                              color: m.trend > 0 ? '#22C55E' : m.trend < 0 ? '#EF4444' : 'var(--akaal-text-muted)',
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: '10px',
                            }}
                            aria-label={m.trendLabel}
                          >
                            {m.trend > 0 ? `+${m.trend}` : m.trend === 0 ? '—' : m.trend}
                          </span>
                        </div>
                      </div>
                      <p
                        className="text-2xl font-bold tabular-nums mb-1"
                        style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}
                        aria-label={`${m.label}: ${m.value}`}
                      >
                        {m.value}
                      </p>
                      <p className="text-xs font-medium mb-0.5" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{m.label}</p>
                      <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.supportingText}</p>
                    </Card>
                  ))
                }
              </div>
            </section>

            {/* ── ROW 2: System Health ── */}
            <section aria-label="System health" className="mb-6">
              <Card>
                <SectionHeader title="System Health" subtitle="Real-time platform status" />
                <div className="p-4">
                  {isLoading ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
                      {Array(6).fill(0).map((_, i) => (
                        <div key={i} className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                          <Skeleton style={{ width: '80px', height: '10px', marginBottom: '8px' }} />
                          <Skeleton style={{ width: '60px', height: '18px', marginBottom: '6px' }} />
                          <Skeleton style={{ width: '100px', height: '10px' }} />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
                      {healthItems.map(item => (
                        <div
                          key={item.id}
                          className="rounded-md p-3 transition-all duration-150"
                          style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}
                        >
                          <p className="text-xs mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</p>
                          <StatusChip status={item.status} />
                          <p className="text-xs mt-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.detail}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>
            </section>

            {/* ── ROW 3: Recent Migrations ── */}
            <section aria-label="Recent migrations" className="mb-6">
              <Card>
                <SectionHeader
                  title="Recent Migrations"
                  subtitle={`${filteredMigrations.length} migration${filteredMigrations.length !== 1 ? 's' : ''}`}
                  action={
                    <div className="flex items-center gap-2">
                      {/* Status filter */}
                      <select
                        value={statusFilter}
                        onChange={e => setStatusFilter(e.target.value as StatusType | 'all')}
                        className="text-xs rounded-md px-2 py-1 outline-none transition-all duration-150 focus-visible:ring-2"
                        style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}
                        aria-label="Filter by status"
                      >
                        <option value="all">All Status</option>
                        <option value="running">Running</option>
                        <option value="completed">Completed</option>
                        <option value="failed">Failed</option>
                        <option value="pending">Pending</option>
                        <option value="paused">Paused</option>
                      </select>
                    </div>
                  }
                />
                {isLoading ? (
                  <div className="p-4 space-y-3">
                    {Array(4).fill(0).map((_, i) => (
                      <div key={i} className="flex items-center gap-4">
                        <Skeleton style={{ flex: 2, height: '14px' }} />
                        <Skeleton style={{ flex: 1, height: '14px' }} />
                        <Skeleton style={{ flex: 1, height: '14px' }} />
                        <Skeleton style={{ width: '60px', height: '18px' }} />
                        <Skeleton style={{ flex: 1, height: '8px' }} />
                        <Skeleton style={{ flex: 1, height: '14px' }} />
                      </div>
                    ))}
                  </div>
                ) : filteredMigrations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 px-4">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center mb-3" style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)' }}>
                      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)' }}>
                        <path d="M2 9h14M10 4l5 5-5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <p className="text-sm font-medium mb-1" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>No migrations are currently running.</p>
                    <p className="text-xs mb-4" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Create a new migration to get started.</p>
                    <Link
                      href="/migration-workspace"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-150"
                      style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
                    >
                      Create Migration
                    </Link>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs" role="table" aria-label="Recent migrations table">
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--akaal-border)', background: 'var(--akaal-table-header)' }}>
                          {tableColumns.map(col => (
                            <th
                              key={col.key}
                              className="px-4 py-2.5 text-left font-medium whitespace-nowrap"
                              style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                              scope="col"
                            >
                              {col.sortable ? (
                                <button
                                  type="button"
                                  onClick={() => handleSort(col.key)}
                                  className="flex items-center gap-1 transition-colors focus:outline-none focus-visible:underline"
                                  style={{ color: sortField === col.key ? 'var(--akaal-text-secondary)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                                  aria-label={`Sort by ${col.label} ${sortField === col.key ? (sortDir === 'asc' ? 'descending' : 'ascending') : 'ascending'}`}
                                >
                                  {col.label}
                                  <svg width="8" height="10" viewBox="0 0 8 10" fill="none" aria-hidden="true">
                                    <path d="M4 1v8M1 4l3-3 3 3" stroke={sortField === col.key && sortDir === 'asc' ? 'var(--akaal-primary)' : 'currentColor'} strokeWidth="1.2" strokeLinecap="round" />
                                    <path d="M1 6l3 3 3-3" stroke={sortField === col.key && sortDir === 'desc' ? 'var(--akaal-primary)' : 'currentColor'} strokeWidth="1.2" strokeLinecap="round" />
                                  </svg>
                                </button>
                              ) : col.label}
                            </th>
                          ))}
                          <th className="px-4 py-2.5 text-left font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }} scope="col">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredMigrations.map((m, idx) => (
                          <tr
                            key={m.id}
                            className="transition-colors"
                            style={{ borderBottom: idx < filteredMigrations.length - 1 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
                            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                          >
                            <td className="px-4 py-2.5 font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', maxWidth: '200px' }}>
                              <span className="truncate block" title={m.name}>{m.name}</span>
                            </td>
                            <td className="px-4 py-2.5 whitespace-nowrap" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.source}</td>
                            <td className="px-4 py-2.5 whitespace-nowrap" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.target}</td>
                            <td className="px-4 py-2.5 whitespace-nowrap"><StatusChip status={m.status} /></td>
                            <td className="px-4 py-2.5" style={{ minWidth: '120px' }}><ProgressBar value={m.progress} status={m.status} /></td>
                            <td className="px-4 py-2.5 whitespace-nowrap" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.started}</td>
                            <td className="px-4 py-2.5 whitespace-nowrap" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.duration}</td>
                            <td className="px-4 py-2.5 whitespace-nowrap" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.owner}</td>
                            <td className="px-4 py-2.5 whitespace-nowrap">
                              <div className="flex items-center gap-1">
                                <button
                                  type="button"
                                  className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none focus-visible:ring-1"
                                  style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                                  aria-label={`View details for ${m.name}`}
                                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-secondary)'; }}
                                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                                >
                                  View
                                </button>
                                {m.status === 'failed' && (
                                  <button
                                    type="button"
                                    className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none focus-visible:ring-1"
                                    style={{ color: '#EF4444', fontFamily: "'Inter', sans-serif" }}
                                    aria-label={`Retry ${m.name}`}
                                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(239,68,68,0.08)'; }}
                                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                                  >
                                    Retry
                                  </button>
                                )}
                                {m.status === 'running' && (
                                  <button
                                    type="button"
                                    className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none focus-visible:ring-1"
                                    style={{ color: '#F59E0B', fontFamily: "'Inter', sans-serif" }}
                                    aria-label={`Pause ${m.name}`}
                                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(245,158,11,0.08)'; }}
                                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                                  >
                                    Pause
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </section>

            {/* ── ROW 4 + 5: Activity + Performance ── */}
            <div className="grid grid-cols-1 xl:grid-cols-5 gap-6 mb-6">

              {/* Live Activity Timeline */}
              <section aria-label="Live activity" className="xl:col-span-2">
                <Card className="h-full">
                  <SectionHeader title="Live Activity" subtitle="Recent platform events" />
                  <div className="p-4">
                    {isLoading ? (
                      <div className="space-y-4">
                        {Array(5).fill(0).map((_, i) => (
                          <div key={i} className="flex items-start gap-3">
                            <Skeleton style={{ width: '28px', height: '28px', borderRadius: '50%', flexShrink: 0 }} />
                            <div className="flex-1">
                              <Skeleton style={{ width: '80%', height: '12px', marginBottom: '6px' }} />
                              <Skeleton style={{ width: '50%', height: '10px' }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <ol className="space-y-0" aria-label="Activity timeline">
                        {MOCK_ACTIVITY.map((event, idx) => (
                          <li key={event.id} className="flex items-start gap-3 relative">
                            {/* Connector line */}
                            {idx < MOCK_ACTIVITY.length - 1 && (
                              <div
                                className="absolute left-3.5 top-7 w-px"
                                style={{ height: 'calc(100% - 4px)', background: 'var(--akaal-border-subtle)' }}
                                aria-hidden="true"
                              />
                            )}
                            <div className="flex-shrink-0 relative z-10 py-2">{event.icon}</div>
                            <div className="flex-1 min-w-0 py-2">
                              <div className="flex items-start justify-between gap-2">
                                <p className="text-xs leading-snug" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{event.description}</p>
                                <span className="text-xs flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{event.timestamp}</span>
                              </div>
                              <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{event.migration}</p>
                            </div>
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                </Card>
              </section>

              {/* Performance Charts */}
              <section aria-label="Performance metrics" className="xl:col-span-3">
                <Card className="h-full">
                  <SectionHeader title="Performance" subtitle="Last 12 intervals" />
                  <div className="p-4">
                    {isLoading ? (
                      <div className="grid grid-cols-2 gap-4">
                        {Array(4).fill(0).map((_, i) => (
                          <div key={i} className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                            <Skeleton style={{ width: '80px', height: '10px', marginBottom: '12px' }} />
                            <Skeleton style={{ width: '100%', height: '48px' }} />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 gap-4">
                        {/* Throughput */}
                        <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                          <div className="flex items-center justify-between mb-2">
                            <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Migration Throughput</p>
                            <span className="text-xs font-bold tabular-nums" style={{ color: '#38BDF8', fontFamily: "'JetBrains Mono', monospace" }}>96 MB/s</span>
                          </div>
                          <MiniBarChart data={throughputData} color="#38BDF8" label="MB/s over time" />
                        </div>
                        {/* Rows Migrated */}
                        <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                          <div className="flex items-center justify-between mb-2">
                            <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Rows Migrated</p>
                            <span className="text-xs font-bold tabular-nums" style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>248K</span>
                          </div>
                          <MiniBarChart data={rowsData} color="#22C55E" label="Rows (thousands)" />
                        </div>
                        {/* Success Rate */}
                        <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                          <div className="flex items-center justify-between mb-2">
                            <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Success Rate</p>
                            <span className="text-xs font-bold tabular-nums" style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>99%</span>
                          </div>
                          <div className="flex items-end gap-1" style={{ height: '48px' }}>
                            {successData.map((v, i) => (
                              <div
                                key={i}
                                className="flex-1 rounded-sm"
                                style={{
                                  height: `${v}%`,
                                  background: v >= 95 ? '#22C55E' : v >= 90 ? '#F59E0B' : '#EF4444',
                                  opacity: i === successData.length - 1 ? 1 : 0.4 + (i / successData.length) * 0.5,
                                  minHeight: '2px',
                                }}
                                aria-hidden="true"
                              />
                            ))}
                          </div>
                          <p className="text-xs mt-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>% success over time</p>
                        </div>
                        {/* Queue Depth */}
                        <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                          <div className="flex items-center justify-between mb-2">
                            <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Queue Depth</p>
                            <span className="text-xs font-bold tabular-nums" style={{ color: '#F59E0B', fontFamily: "'JetBrains Mono', monospace" }}>6 jobs</span>
                          </div>
                          <MiniBarChart data={queueData} color="#F59E0B" label="Queued jobs" />
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              </section>
            </div>

            {/* ── ROW 6: Quick Actions ── */}
            <section aria-label="Quick actions" className="mb-6">
              <Card>
                <SectionHeader title="Quick Actions" subtitle="Common platform operations" />
                <div className="p-4">
                  <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
                    {quickActions.map((action, i) => (
                      <Link
                        key={i}
                        href={action.href}
                        className="flex flex-col items-center gap-2.5 p-3 rounded-md text-center transition-all duration-150 focus:outline-none focus-visible:ring-2 group"
                        style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.borderColor = 'var(--akaal-primary)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface-elevated)'; (e.currentTarget as HTMLElement).style.borderColor = 'var(--akaal-border)'; }}
                      >
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-150"
                          style={{ background: `${action.color}14`, color: action.color }}
                          aria-hidden="true"
                        >
                          {action.icon}
                        </div>
                        <span className="text-xs font-medium leading-tight" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{action.label}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              </Card>
            </section>

          </div>
        </main>
      </div>
    </div>
  );
}
