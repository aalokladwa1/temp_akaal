'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';

// ─── Types ────────────────────────────────────────────────────────────────────

type MigrationStatus = 'running' | 'completed' | 'failed' | 'scheduled' | 'draft' | 'paused';

interface Migration {
  id: string;
  name: string;
  source: string;
  target: string;
  status: MigrationStatus;
  progress: number;
  owner: string;
  updated: string;
  duration?: string;
  scheduledFor?: string;
  errorMsg?: string;
}

interface Template {
  id: string;
  name: string;
  description: string;
  sourceType: string;
  targetType: string;
  usageCount: number;
  lastUsed: string;
}

interface ActivityEvent {
  id: string;
  timestamp: string;
  type: 'started' | 'completed' | 'failed' | 'scheduled' | 'warning' | 'info';
  description: string;
  migration: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_RUNNING: Migration[] = [
  { id: 'r1', name: 'prod-oracle-to-postgres', source: 'Oracle 19c', target: 'PostgreSQL 15', status: 'running', progress: 67, owner: 'sarah.chen', updated: '2 min ago', duration: '1h 55m' },
  { id: 'r2', name: 'dw-redshift-consolidation', source: 'Redshift', target: 'BigQuery', status: 'running', progress: 12, owner: 'sarah.chen', updated: '5 min ago', duration: '19m' },
];

const MOCK_SCHEDULED: Migration[] = [
  { id: 's1', name: 'crm-postgres-upgrade', source: 'PostgreSQL 12', target: 'PostgreSQL 15', status: 'scheduled', progress: 0, owner: 'alex.morgan', updated: '1h ago', scheduledFor: '2026-07-26 22:00 UTC' },
  { id: 's2', name: 'erp-mssql-to-azure', source: 'SQL Server 2019', target: 'Azure SQL', status: 'scheduled', progress: 0, owner: 'james.okafor', updated: '3h ago', scheduledFor: '2026-07-27 04:00 UTC' },
  { id: 's3', name: 'bi-mysql-warehouse', source: 'MySQL 8.0', target: 'Snowflake', status: 'scheduled', progress: 0, owner: 'priya.nair', updated: '6h ago', scheduledFor: '2026-07-27 06:30 UTC' },
];

const MOCK_FAILED: Migration[] = [
  { id: 'f1', name: 'legacy-mssql-migration', source: 'SQL Server 2019', target: 'Azure SQL', status: 'failed', progress: 34, owner: 'priya.nair', updated: '45m ago', errorMsg: 'Circular FK dependency detected' },
  { id: 'f2', name: 'iot-timescale-archive', source: 'TimescaleDB', target: 'ClickHouse', status: 'failed', progress: 78, owner: 'dev.ops', updated: '2h ago', errorMsg: 'Target schema mismatch on 3 tables' },
];

const MOCK_COMPLETED: Migration[] = [
  { id: 'c1', name: 'analytics-mysql-warehouse', source: 'MySQL 8.0', target: 'Snowflake', status: 'completed', progress: 100, owner: 'james.okafor', updated: '3h ago', duration: '3h 12m' },
  { id: 'c2', name: 'hr-oracle-to-pg', source: 'Oracle 12c', target: 'PostgreSQL 14', status: 'completed', progress: 100, owner: 'sarah.chen', updated: '1d ago', duration: '5h 44m' },
  { id: 'c3', name: 'finance-db-consolidation', source: 'MySQL 5.7', target: 'PostgreSQL 15', status: 'completed', progress: 100, owner: 'alex.morgan', updated: '2d ago', duration: '2h 08m' },
];

const MOCK_DRAFTS: Migration[] = [
  { id: 'd1', name: 'staging-mongo-to-pg', source: 'MongoDB 6.0', target: 'PostgreSQL 15', status: 'draft', progress: 0, owner: 'dev.ops', updated: '30m ago' },
  { id: 'd2', name: 'logs-elastic-migration', source: 'Elasticsearch 8', target: 'OpenSearch', status: 'draft', progress: 0, owner: 'priya.nair', updated: '4h ago' },
];

const MOCK_TEMPLATES: Template[] = [
  { id: 't1', name: 'Oracle → PostgreSQL', description: 'Full schema + data migration with type mapping and FK resolution', sourceType: 'Oracle', targetType: 'PostgreSQL', usageCount: 24, lastUsed: '2h ago' },
  { id: 't2', name: 'MySQL → Snowflake', description: 'Analytics warehouse migration with column transformations', sourceType: 'MySQL', targetType: 'Snowflake', usageCount: 18, lastUsed: '1d ago' },
  { id: 't3', name: 'SQL Server → Azure SQL', description: 'Cloud lift-and-shift with minimal schema changes', sourceType: 'SQL Server', targetType: 'Azure SQL', usageCount: 11, lastUsed: '3d ago' },
  { id: 't4', name: 'PostgreSQL Upgrade', description: 'In-place major version upgrade with zero-downtime strategy', sourceType: 'PostgreSQL', targetType: 'PostgreSQL', usageCount: 9, lastUsed: '5d ago' },
];

const MOCK_ACTIVITY: ActivityEvent[] = [
  { id: 'a1', timestamp: '16:17:02', type: 'started', description: 'Migration started — initial schema validation passed', migration: 'dw-redshift-consolidation' },
  { id: 'a2', timestamp: '16:14:38', type: 'completed', description: 'Validation completed — 0 schema conflicts detected', migration: 'prod-oracle-to-postgres' },
  { id: 'a3', timestamp: '16:09:11', type: 'failed', description: 'Circular FK dependency detected — migration halted', migration: 'legacy-mssql-migration' },
  { id: 'a4', timestamp: '15:58:44', type: 'scheduled', description: 'Migration scheduled for 2026-07-26 22:00 UTC', migration: 'crm-postgres-upgrade' },
  { id: 'a5', timestamp: '15:45:22', type: 'warning', description: 'SSL certificate validation skipped — self-signed cert', migration: 'prod-oracle-to-postgres' },
  { id: 'a6', timestamp: '15:30:00', type: 'completed', description: 'Migration completed successfully — 8.5M rows transferred', migration: 'analytics-mysql-warehouse' },
  { id: 'a7', timestamp: '14:22:15', type: 'info', description: 'Draft workspace created', migration: 'staging-mongo-to-pg' },
];

// ─── Utility Components ───────────────────────────────────────────────────────

function StatusChip({ status }: { status: MigrationStatus }) {
  const configs: Record<MigrationStatus, { label: string; color: string; bg: string; border: string; dot?: boolean }> = {
    running:   { label: 'Running',   color: '#38BDF8', bg: 'rgba(56,189,248,0.10)',  border: 'rgba(56,189,248,0.25)',  dot: true },
    completed: { label: 'Completed', color: '#22C55E', bg: 'rgba(34,197,94,0.10)',   border: 'rgba(34,197,94,0.25)' },
    failed:    { label: 'Failed',    color: '#EF4444', bg: 'rgba(239,68,68,0.10)',   border: 'rgba(239,68,68,0.25)' },
    scheduled: { label: 'Scheduled', color: '#A78BFA', bg: 'rgba(167,139,250,0.10)', border: 'rgba(167,139,250,0.25)' },
    draft:     { label: 'Draft',     color: '#94A3B8', bg: 'rgba(148,163,184,0.10)', border: 'rgba(148,163,184,0.25)' },
    paused:    { label: 'Paused',    color: '#F59E0B', bg: 'rgba(245,158,11,0.10)',  border: 'rgba(245,158,11,0.25)' },
  };
  const cfg = configs[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}
    >
      {cfg.dot ? (
        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse" style={{ background: cfg.color }} aria-hidden="true" />
      ) : (
        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color }} aria-hidden="true" />
      )}
      {cfg.label}
    </span>
  );
}

function ProgressBar({ value, status }: { value: number; status: MigrationStatus }) {
  const color = status === 'failed' ? 'var(--akaal-error)' : status === 'completed' ? 'var(--akaal-success)' : 'var(--akaal-primary)';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'var(--akaal-border)', minWidth: '60px' }}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${value}%`, background: color }} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} />
      </div>
      <span className="text-xs tabular-nums flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{value}%</span>
    </div>
  );
}

function ActivityDot({ type }: { type: ActivityEvent['type'] }) {
  const colors: Record<ActivityEvent['type'], string> = {
    started: 'var(--akaal-info)', completed: 'var(--akaal-success)', failed: 'var(--akaal-error)',
    scheduled: '#A78BFA', warning: 'var(--akaal-warning)', info: 'var(--akaal-text-muted)',
  };
  return <span className="w-2 h-2 rounded-full flex-shrink-0 mt-1" style={{ background: colors[type] }} aria-hidden="true" />;
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function AppSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const navItems = [
    { href: '/dashboard', label: 'Dashboard', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/migrations', label: 'Migrations', active: true, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/execution-center', label: 'Execution', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M6 5.5l5 2.5-5 2.5V5.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { href: '/databases', label: 'Databases', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="6" ry="2" stroke="currentColor" strokeWidth="1.3" /><path d="M2 4v4c0 1.1 2.7 2 6 2s6-.9 6-2V4" stroke="currentColor" strokeWidth="1.3" /><path d="M2 8v4c0 1.1 2.7 2 6 2s6-.9 6-2V8" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/live-monitor', label: 'Live Monitor', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M4 8l2-2 2 2 2-3 2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/agents', label: 'Agents', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/reports', label: 'Reports', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/system', label: 'System', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="3" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="4.5" r="0.8" fill="currentColor" /><circle cx="4" cy="9.5" r="0.8" fill="currentColor" /><path d="M5 13h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/settings', label: 'Settings', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.4 3.4l.85.85M11.75 11.75l.85.85M3.4 12.6l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
  ];

  return (
    <aside
      className="flex flex-col flex-shrink-0 h-full"
      style={{ width: collapsed ? '56px' : '220px', background: 'var(--akaal-sidebar-gradient)', borderRight: '1px solid var(--akaal-sidebar-border)', transition: 'width 0.2s ease', overflow: 'hidden' }}
      aria-label="Main navigation"
    >
      <div className="flex items-center gap-3 px-3 py-4 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-sidebar-border)', minHeight: '57px' }}>
        <AppImage src="/assets/images/app_logo.png" alt="AKAAL" width={28} height={28} className="flex-shrink-0" style={{ filter: 'drop-shadow(0 1px 4px rgba(37,99,235,0.3))' }} />
        {!collapsed && <span className="font-bold tracking-widest uppercase text-sm" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.15em', whiteSpace: 'nowrap' }}>AKAAL</span>}
      </div>
      <nav className="flex-1 py-3 overflow-y-auto" aria-label="Primary navigation">
        <ul className="space-y-0.5 px-2" role="list">
          {navItems.map(item => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="flex items-center gap-3 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ color: item.active ? 'var(--akaal-text)' : 'var(--akaal-text-muted)', background: item.active ? 'var(--akaal-primary-subtle)' : 'transparent', borderLeft: item.active ? '2px solid var(--akaal-primary)' : '2px solid transparent', fontFamily: "'Inter', sans-serif", whiteSpace: 'nowrap' }}
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

// ─── Top Nav ──────────────────────────────────────────────────────────────────

function TopNav() {
  const [searchValue, setSearchValue] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header
      className="flex items-center gap-4 px-4 flex-shrink-0"
      style={{ height: '57px', background: 'var(--akaal-nav-bg)', borderBottom: '1px solid var(--akaal-nav-border)' }}
      role="banner"
    >
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 flex-shrink-0">
        <Link href="/dashboard" className="text-xs transition-colors" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >Platform</Link>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Migrations</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
          <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          placeholder="Search migrations…"
          value={searchValue}
          onChange={e => setSearchValue(e.target.value)}
          className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
          style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
          aria-label="Search migrations"
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
        />
        <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs px-1 rounded" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>⌘K</kbd>
      </div>
      <div className="flex-1" />
      <ThemeSwitcher />
      <button
        type="button"
        className="relative flex items-center justify-center w-8 h-8 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
        style={{ color: 'var(--akaal-text-muted)' }}
        aria-label="Notifications"
        onClick={() => setNotifOpen(v => !v)}
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M8 1.5a5 5 0 0 0-5 5v3l-1.5 2h13L13 9.5v-3a5 5 0 0 0-5-5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
          <path d="M6.5 13.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.3" />
        </svg>
        <span className="absolute top-1 right-1 w-2 h-2 rounded-full" style={{ background: 'var(--akaal-error)', border: '1.5px solid var(--akaal-nav-bg)' }} aria-hidden="true" />
      </button>
      <button
        type="button"
        onClick={() => setProfileOpen(v => !v)}
        className="flex items-center gap-2 px-2 py-1.5 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
        style={{ color: 'var(--akaal-text-muted)' }}
        aria-label="User profile menu"
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
      >
        <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }} aria-hidden="true">SC</div>
        <span className="text-xs font-medium hidden sm:block" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>sarah.chen</span>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
      </button>
    </header>
  );
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color, icon }: { label: string; value: string | number; sub: string; color: string; icon: React.ReactNode }) {
  return (
    <div
      className="rounded-lg p-4 flex flex-col gap-2 transition-all duration-150"
      style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}
      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = color; }}
      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--akaal-card-border)'; }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{label}</span>
        <span className="w-7 h-7 rounded-md flex items-center justify-center" style={{ background: `${color}18`, color }}>{icon}</span>
      </div>
      <div className="text-2xl font-bold tabular-nums" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
      <div className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{sub}</div>
    </div>
  );
}

// ─── Section Card ─────────────────────────────────────────────────────────────

function SectionCard({ title, subtitle, action, children }: { title: string; subtitle?: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-lg overflow-hidden" style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}>
      <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{title}</h3>
          {subtitle && <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

// ─── Migration Row ────────────────────────────────────────────────────────────

function MigrationRow({ m, showProgress = false, showError = false, showScheduled = false }: {
  m: Migration; showProgress?: boolean; showError?: boolean; showScheduled?: boolean;
}) {
  return (
    <div
      className="flex items-center gap-3 px-4 py-3 transition-colors duration-100"
      style={{ borderBottom: '1px solid var(--akaal-table-border)' }}
      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = 'var(--akaal-table-row-hover)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-medium truncate" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{m.name}</span>
          <StatusChip status={m.status} />
        </div>
        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
          <span>{m.source}</span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 5h6M6 3l2 2-2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
          <span>{m.target}</span>
        </div>
        {showError && m.errorMsg && (
          <div className="mt-1 text-xs" style={{ color: 'var(--akaal-error)', fontFamily: "'Inter', sans-serif" }}>
            ⚠ {m.errorMsg}
          </div>
        )}
        {showScheduled && m.scheduledFor && (
          <div className="mt-1 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
            🕐 {m.scheduledFor}
          </div>
        )}
      </div>
      {showProgress && (
        <div className="w-28 flex-shrink-0">
          <ProgressBar value={m.progress} status={m.status} />
        </div>
      )}
      <div className="flex-shrink-0 text-right">
        <div className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.owner}</div>
        <div className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>{m.updated}</div>
      </div>
      <Link
        href={m.status === 'running' ? `/live-monitor?migration=${m.id}` : m.status === 'failed' ? `/execution-center?job=${m.id}` : m.status === 'completed' ? '/reports' : `/migration-workspace?id=${m.id}`}
        className="flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
        style={{ color: 'var(--akaal-text-muted)' }}
        aria-label={`Open ${m.name}`}
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
      </Link>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function MigrationsPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const quickActions = [
    {
      label: 'New Migration',
      description: 'Start the migration wizard',
      href: '/migration-workspace',
      color: 'var(--akaal-primary)',
      icon: (
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
          <path d="M9 3v12M3 9h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      label: 'Import Migration',
      description: 'Import from file or URL',
      href: '/migration-workspace',
      color: '#38BDF8',
      icon: (
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
          <path d="M9 3v9M6 9l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M3 14h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      label: 'Clone Migration',
      description: 'Duplicate an existing migration',
      href: '/migration-workspace',
      color: '#A78BFA',
      icon: (
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
          <rect x="2" y="5" width="10" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
          <path d="M6 5V3.5A1.5 1.5 0 0 1 7.5 2h7A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      label: 'Create Template',
      description: 'Save a reusable migration template',
      href: '/migration-workspace',
      color: '#22C55E',
      icon: (
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
          <path d="M4 2h7l4 4v10H4V2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          <path d="M11 2v4h4M6 9h6M6 12h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
    },
  ];

  if (!mounted) return null;

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}>
      <AppSidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-y-auto p-5 space-y-5" aria-label="Migrations overview">

          {/* ── Page Header ── */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Migrations</h1>
              <p className="text-sm mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Operational home for all database migrations</p>
            </div>
            <Link
              href="/migration-workspace"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.opacity = '0.9'; }}
              onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              New Migration
            </Link>
          </div>

          {/* ── KPI Summary ── */}
          <section aria-label="KPI Summary">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <KpiCard label="Total Migrations" value={42} sub="All time" color="var(--akaal-primary)"
                icon={<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>}
              />
              <KpiCard label="Running" value={2} sub="In progress now" color="#38BDF8"
                icon={<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 4.5l4 2.5-4 2.5V4.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg>}
              />
              <KpiCard label="Scheduled" value={3} sub="Upcoming" color="#A78BFA"
                icon={<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M7 4v3l2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>}
              />
              <KpiCard label="Failed" value={2} sub="Needs attention" color="var(--akaal-error)"
                icon={<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M7 4v3M7 9.5v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>}
              />
              <KpiCard label="Completed" value={27} sub="Successfully done" color="var(--akaal-success)"
                icon={<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M4.5 7l2 2 3-3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>}
              />
              <KpiCard label="Drafts" value={8} sub="In progress" color="var(--akaal-text-muted)"
                icon={<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 2h6l3 3v7H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M9 2v3h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>}
              />
            </div>
          </section>

          {/* ── Quick Actions ── */}
          <section aria-label="Quick Actions">
            <h2 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", letterSpacing: '0.08em' }}>Quick Actions</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {quickActions.map(action => (
                <Link
                  key={action.label}
                  href={action.href}
                  className="flex flex-col gap-2 p-4 rounded-lg transition-all duration-150 focus:outline-none focus-visible:ring-2 group"
                  style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = action.color; e.currentTarget.style.background = `${action.color}08`; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--akaal-card-border)'; e.currentTarget.style.background = 'var(--akaal-card-bg)'; }}
                >
                  <span className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${action.color}18`, color: action.color }}>
                    {action.icon}
                  </span>
                  <div>
                    <div className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{action.label}</div>
                    <div className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{action.description}</div>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          {/* ── Running + Scheduled ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Running Migrations */}
            <SectionCard
              title="Running Migrations"
              subtitle={`${MOCK_RUNNING.length} active`}
              action={
                <Link href="/execution-center" className="text-xs transition-colors" style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif" }}
                  onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
                  onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                >View all →</Link>
              }
            >
              {MOCK_RUNNING.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm" style={{ color: 'var(--akaal-text-muted)' }}>No running migrations</div>
              ) : (
                MOCK_RUNNING.map(m => <MigrationRow key={m.id} m={m} showProgress />)
              )}
            </SectionCard>

            {/* Scheduled Migrations */}
            <SectionCard
              title="Scheduled Migrations"
              subtitle={`${MOCK_SCHEDULED.length} upcoming`}
              action={
                <Link href="/execution-center" className="text-xs transition-colors" style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif" }}
                  onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
                  onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                >View all →</Link>
              }
            >
              {MOCK_SCHEDULED.map(m => <MigrationRow key={m.id} m={m} showScheduled />)}
            </SectionCard>
          </div>

          {/* ── Failed + Draft Workspaces ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Failed Migrations */}
            <SectionCard
              title="Failed Migrations"
              subtitle="Requires attention"
              action={
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium" style={{ background: 'var(--akaal-error-bg)', color: 'var(--akaal-error)', border: '1px solid rgba(239,68,68,0.2)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
                  {MOCK_FAILED.length} failed
                </span>
              }
            >
              {MOCK_FAILED.map(m => <MigrationRow key={m.id} m={m} showError />)}
            </SectionCard>

            {/* Draft Workspaces */}
            <SectionCard
              title="Draft Workspaces"
              subtitle="Incomplete configurations"
              action={
                <Link href="/migration-workspace" className="text-xs transition-colors" style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif" }}
                  onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
                  onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                >New draft →</Link>
              }
            >
              {MOCK_DRAFTS.map(m => <MigrationRow key={m.id} m={m} />)}
            </SectionCard>
          </div>

          {/* ── Completed Migrations ── */}
          <SectionCard
            title="Completed Migrations"
            subtitle="Recent successful migrations"
            action={
              <Link href="/reports" className="text-xs transition-colors" style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
                onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
              >View reports →</Link>
            }
          >
            {MOCK_COMPLETED.map(m => (
              <div
                key={m.id}
                className="flex items-center gap-3 px-4 py-3 transition-colors duration-100"
                style={{ borderBottom: '1px solid var(--akaal-table-border)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = 'var(--akaal-table-row-hover)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-medium truncate" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{m.name}</span>
                    <StatusChip status={m.status} />
                  </div>
                  <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
                    <span>{m.source}</span>
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 5h6M6 3l2 2-2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                    <span>{m.target}</span>
                  </div>
                </div>
                <div className="flex-shrink-0 text-right">
                  {m.duration && <div className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{m.duration}</div>}
                  <div className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>{m.updated}</div>
                </div>
                <div className="flex-shrink-0 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.owner}</div>
                <Link
                  href="/migration-workspace"
                  className="flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-md transition-all duration-150"
                  style={{ color: 'var(--akaal-text-muted)' }}
                  aria-label={`View ${m.name}`}
                  onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
                </Link>
              </div>
            ))}
          </SectionCard>

          {/* ── Templates + Activity ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Migration Templates */}
            <SectionCard
              title="Migration Templates"
              subtitle="Reusable migration configurations"
              action={
                <Link href="/migration-workspace" className="text-xs transition-colors" style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif" }}
                  onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
                  onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                >Create template →</Link>
              }
            >
              {MOCK_TEMPLATES.map(t => (
                <div
                  key={t.id}
                  className="flex items-start gap-3 px-4 py-3 transition-colors duration-100 cursor-pointer"
                  style={{ borderBottom: '1px solid var(--akaal-table-border)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = 'var(--akaal-table-row-hover)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
                >
                  <div className="w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)' }}>
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 2h5l3 3v7H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M8 2v3h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{t.name}</div>
                    <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{t.description}</div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>Used {t.usageCount}×</span>
                      <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Last: {t.lastUsed}</span>
                    </div>
                  </div>
                  <Link
                    href="/migration-workspace"
                    className="flex-shrink-0 flex items-center gap-1 px-2 py-1 rounded text-xs transition-all duration-150"
                    style={{ color: 'var(--akaal-primary)', background: 'var(--akaal-primary-subtle)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
                    onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                  >
                    Use
                  </Link>
                </div>
              ))}
            </SectionCard>

            {/* Recent Activity */}
            <SectionCard
              title="Recent Activity"
              subtitle="Latest migration events"
            >
              <div className="px-4 py-3 space-y-3">
                {MOCK_ACTIVITY.map(event => (
                  <div key={event.id} className="flex items-start gap-3">
                    <ActivityDot type={event.type} />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{event.description}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{event.migration}</span>
                        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>· {event.timestamp}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>

        </main>
      </div>
    </div>
  );
}
