'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';

// ─── Types ────────────────────────────────────────────────────────────────────

type DBVendor = 'postgresql' | 'mysql' | 'oracle' | 'mssql' | 'mongodb' | 'mariadb' | 'sqlite' | 'amazon-rds' | 'azure-sql' | 'google-cloud-sql' | 'cockroachdb';
type DBEnvironment = 'production' | 'staging' | 'development' | 'testing' | 'archived';
type DBStatus = 'connected' | 'disconnected' | 'error' | 'warning' | 'unknown';
type DBHealth = 'healthy' | 'degraded' | 'critical' | 'offline' | 'unknown';
type SortDir = 'asc' | 'desc';
type DetailTab = 'overview' | 'health' | 'security' | 'activity';
type TestStage = 'connecting' | 'authenticating' | 'permissions' | 'metadata' | 'read' | 'write' | 'complete';
type TestStatus = 'idle' | 'running' | 'success' | 'failed';
type CategoryFilter = DBEnvironment | 'all' | 'favorites';

interface DBConnection {
  id: string;
  name: string;
  vendor: DBVendor;
  environment: DBEnvironment;
  host: string;
  port: number;
  database: string;
  status: DBStatus;
  health: DBHealth;
  latencyMs: number | null;
  owner: string;
  createdAt: string;
  lastChecked: string;
  isFavorite: boolean;
  tags: string[];
  version?: string;
  schemaCount?: number;
  tableCount?: number;
  sslEnabled: boolean;
  authMethod: string;
  certExpiry?: string;
  replicationStatus?: string;
  cdcStatus?: string;
  storageUsedGB?: number;
  storageTotalGB?: number;
}

interface AddDBForm {
  name: string;
  vendor: DBVendor | '';
  environment: DBEnvironment | '';
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
  authMethod: string;
  sslEnabled: boolean;
  sslMode: string;
  connectionTimeout: string;
  showAdvanced: boolean;
  maxPoolSize: string;
  minPoolSize: string;
  idleTimeout: string;
  tags: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_CONNECTIONS: DBConnection[] = [
  {
    id: 'db1', name: 'prod-postgres-primary', vendor: 'postgresql', environment: 'production',
    host: 'pg-prod-01.internal', port: 5432, database: 'akaal_prod', status: 'connected', health: 'healthy',
    latencyMs: 4, owner: 'sarah.chen', createdAt: '2026-01-15', lastChecked: '16:42:01',
    isFavorite: true, tags: ['primary', 'critical'], version: 'PostgreSQL 15.4',
    schemaCount: 8, tableCount: 142, sslEnabled: true, authMethod: 'Password',
    certExpiry: '2027-03-01', replicationStatus: 'Active', cdcStatus: 'Enabled',
    storageUsedGB: 847, storageTotalGB: 2048,
  },
  {
    id: 'db2', name: 'prod-oracle-legacy', vendor: 'oracle', environment: 'production',
    host: 'oracle-prod-01.internal', port: 1521, database: 'ORCL', status: 'connected', health: 'degraded',
    latencyMs: 38, owner: 'james.okafor', createdAt: '2025-08-20', lastChecked: '16:41:55',
    isFavorite: true, tags: ['legacy', 'migration-source'], version: 'Oracle 19c Enterprise',
    schemaCount: 12, tableCount: 389, sslEnabled: true, authMethod: 'Password',
    certExpiry: '2026-09-15', replicationStatus: 'Standby', cdcStatus: 'Enabled',
    storageUsedGB: 2100, storageTotalGB: 4096,
  },
  {
    id: 'db3', name: 'prod-mssql-crm', vendor: 'mssql', environment: 'production',
    host: 'mssql-prod-02.internal', port: 1433, database: 'CRM_Production', status: 'error', health: 'critical',
    latencyMs: null, owner: 'priya.nair', createdAt: '2025-11-03', lastChecked: '16:40:12',
    isFavorite: false, tags: ['crm', 'critical'], version: 'SQL Server 2019',
    schemaCount: 4, tableCount: 67, sslEnabled: true, authMethod: 'Windows Auth',
    certExpiry: '2026-12-01', replicationStatus: 'Error', cdcStatus: 'Disabled',
    storageUsedGB: 312, storageTotalGB: 1024,
  },
  {
    id: 'db4', name: 'stg-postgres-replica', vendor: 'postgresql', environment: 'staging',
    host: 'pg-stg-01.internal', port: 5432, database: 'akaal_staging', status: 'connected', health: 'healthy',
    latencyMs: 7, owner: 'alex.morgan', createdAt: '2026-02-10', lastChecked: '16:42:00',
    isFavorite: false, tags: ['replica', 'staging'], version: 'PostgreSQL 15.4',
    schemaCount: 8, tableCount: 142, sslEnabled: true, authMethod: 'Password',
    certExpiry: '2027-03-01', replicationStatus: 'Active', cdcStatus: 'Disabled',
    storageUsedGB: 210, storageTotalGB: 512,
  },
  {
    id: 'db5', name: 'stg-mysql-analytics', vendor: 'mysql', environment: 'staging',
    host: 'mysql-stg-01.internal', port: 3306, database: 'analytics_stg', status: 'connected', health: 'healthy',
    latencyMs: 12, owner: 'sarah.chen', createdAt: '2026-03-05', lastChecked: '16:41:58',
    isFavorite: false, tags: ['analytics'], version: 'MySQL 8.0.35',
    schemaCount: 3, tableCount: 28, sslEnabled: false, authMethod: 'Password',
    replicationStatus: 'None', cdcStatus: 'Disabled',
    storageUsedGB: 45, storageTotalGB: 256,
  },
  {
    id: 'db6', name: 'dev-cockroach-cluster', vendor: 'cockroachdb', environment: 'development',
    host: 'cockroach-dev.internal', port: 26257, database: 'defaultdb', status: 'connected', health: 'healthy',
    latencyMs: 22, owner: 'dev.ops', createdAt: '2026-04-18', lastChecked: '16:41:50',
    isFavorite: false, tags: ['distributed', 'dev'], version: 'CockroachDB 23.2',
    schemaCount: 2, tableCount: 15, sslEnabled: true, authMethod: 'Certificate',
    certExpiry: '2026-11-20', replicationStatus: 'Active', cdcStatus: 'Enabled',
    storageUsedGB: 8, storageTotalGB: 100,
  },
  {
    id: 'db7', name: 'dev-mongodb-events', vendor: 'mongodb', environment: 'development',
    host: 'mongo-dev-01.internal', port: 27017, database: 'events_dev', status: 'warning', health: 'degraded',
    latencyMs: 89, owner: 'alex.morgan', createdAt: '2026-05-22', lastChecked: '16:41:45',
    isFavorite: false, tags: ['nosql', 'events'], version: 'MongoDB 7.0',
    schemaCount: 1, tableCount: 12, sslEnabled: false, authMethod: 'SCRAM-SHA-256',
    replicationStatus: 'Primary', cdcStatus: 'Enabled',
    storageUsedGB: 34, storageTotalGB: 200,
  },
  {
    id: 'db8', name: 'test-mariadb-qa', vendor: 'mariadb', environment: 'testing',
    host: 'mariadb-test-01.internal', port: 3306, database: 'qa_tests', status: 'connected', health: 'healthy',
    latencyMs: 9, owner: 'qa.team', createdAt: '2026-06-01', lastChecked: '16:41:40',
    isFavorite: false, tags: ['qa', 'testing'], version: 'MariaDB 11.2',
    schemaCount: 2, tableCount: 31, sslEnabled: false, authMethod: 'Password',
    replicationStatus: 'None', cdcStatus: 'Disabled',
    storageUsedGB: 12, storageTotalGB: 64,
  },
  {
    id: 'db9', name: 'aws-rds-reporting', vendor: 'amazon-rds', environment: 'production',
    host: 'akaal-rds.cluster-xyz.us-east-1.rds.amazonaws.com', port: 5432, database: 'reporting', status: 'connected', health: 'healthy',
    latencyMs: 18, owner: 'james.okafor', createdAt: '2026-01-28', lastChecked: '16:42:02',
    isFavorite: true, tags: ['aws', 'reporting', 'managed'], version: 'Aurora PostgreSQL 15.4',
    schemaCount: 5, tableCount: 78, sslEnabled: true, authMethod: 'IAM',
    certExpiry: '2027-01-28', replicationStatus: 'Multi-AZ', cdcStatus: 'Enabled',
    storageUsedGB: 420, storageTotalGB: 1024,
  },
  {
    id: 'db10', name: 'azure-sql-finance', vendor: 'azure-sql', environment: 'production',
    host: 'akaal-finance.database.windows.net', port: 1433, database: 'FinanceDB', status: 'connected', health: 'healthy',
    latencyMs: 24, owner: 'priya.nair', createdAt: '2026-02-14', lastChecked: '16:41:59',
    isFavorite: false, tags: ['azure', 'finance', 'managed'], version: 'Azure SQL Database',
    schemaCount: 6, tableCount: 94, sslEnabled: true, authMethod: 'Azure AD',
    certExpiry: '2027-02-14', replicationStatus: 'Geo-Redundant', cdcStatus: 'Enabled',
    storageUsedGB: 156, storageTotalGB: 500,
  },
  {
    id: 'db11', name: 'gcp-cloudsql-ml', vendor: 'google-cloud-sql', environment: 'staging',
    host: 'akaal-ml:us-central1:ml-postgres', port: 5432, database: 'ml_features', status: 'disconnected', health: 'offline',
    latencyMs: null, owner: 'sarah.chen', createdAt: '2026-03-20', lastChecked: '15:30:00',
    isFavorite: false, tags: ['gcp', 'ml', 'managed'], version: 'Cloud SQL PostgreSQL 15',
    schemaCount: 3, tableCount: 22, sslEnabled: true, authMethod: 'Cloud IAM',
    replicationStatus: 'None', cdcStatus: 'Disabled',
    storageUsedGB: 67, storageTotalGB: 200,
  },
  {
    id: 'db12', name: 'arch-sqlite-legacy', vendor: 'sqlite', environment: 'archived',
    host: 'file://archive/legacy.db', port: 0, database: 'legacy.db', status: 'disconnected', health: 'unknown',
    latencyMs: null, owner: 'dev.ops', createdAt: '2024-06-01', lastChecked: '2025-12-01',
    isFavorite: false, tags: ['archived', 'legacy'], version: 'SQLite 3.43',
    schemaCount: 1, tableCount: 8, sslEnabled: false, authMethod: 'None',
    replicationStatus: 'None', cdcStatus: 'Disabled',
    storageUsedGB: 0.4, storageTotalGB: 1,
  },
];

const VENDOR_META: Record<DBVendor, { label: string; color: string; abbr: string }> = {
  postgresql:       { label: 'PostgreSQL',       color: '#336791', abbr: 'PG' },
  mysql:            { label: 'MySQL',             color: '#4479A1', abbr: 'MY' },
  oracle:           { label: 'Oracle',            color: '#F80000', abbr: 'OR' },
  mssql:            { label: 'SQL Server',        color: '#CC2927', abbr: 'MS' },
  mongodb:          { label: 'MongoDB',           color: '#47A248', abbr: 'MG' },
  mariadb:          { label: 'MariaDB',           color: '#003545', abbr: 'MA' },
  sqlite:           { label: 'SQLite',            color: '#0F80CC', abbr: 'SL' },
  'amazon-rds':     { label: 'Amazon RDS',        color: '#FF9900', abbr: 'RD' },
  'azure-sql':      { label: 'Azure SQL',         color: '#0078D4', abbr: 'AZ' },
  'google-cloud-sql': { label: 'Cloud SQL',       color: '#4285F4', abbr: 'GC' },
  cockroachdb:      { label: 'CockroachDB',       color: '#6933FF', abbr: 'CR' },
};

const ENV_META: Record<DBEnvironment, { label: string; color: string; bg: string; border: string }> = {
  production: { label: 'Production', color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)' },
  staging:    { label: 'Staging',    color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)' },
  development:{ label: 'Development',color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  border: 'rgba(56,189,248,0.2)' },
  testing:    { label: 'Testing',    color: '#A78BFA', bg: 'rgba(167,139,250,0.08)', border: 'rgba(167,139,250,0.2)' },
  archived:   { label: 'Archived',   color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)' },
};

const STATUS_META: Record<DBStatus, { label: string; color: string; bg: string; border: string; dot: string }> = {
  connected:    { label: 'Connected',    color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)',   dot: '#22C55E' },
  disconnected: { label: 'Disconnected', color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)', dot: '#64748B' },
  error:        { label: 'Error',        color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)',   dot: '#EF4444' },
  warning:      { label: 'Warning',      color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  dot: '#F59E0B' },
  unknown:      { label: 'Unknown',      color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)', dot: '#94A3B8' },
};

const HEALTH_META: Record<DBHealth, { label: string; color: string; bg: string; border: string }> = {
  healthy:  { label: 'Healthy',  color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)' },
  degraded: { label: 'Degraded', color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)' },
  critical: { label: 'Critical', color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)' },
  offline:  { label: 'Offline',  color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)' },
  unknown:  { label: 'Unknown',  color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)' },
};

const TEST_STAGES: { id: TestStage; label: string }[] = [
  { id: 'connecting',     label: 'Connecting to host' },
  { id: 'authenticating', label: 'Authenticating credentials' },
  { id: 'permissions',    label: 'Checking permissions' },
  { id: 'metadata',       label: 'Reading metadata' },
  { id: 'read',           label: 'Testing read access' },
  { id: 'write',          label: 'Testing write access' },
  { id: 'complete',       label: 'Validation complete' },
];

const MOCK_ACTIVITY = [
  { id: 'act1', time: '16:42:01', type: 'health_check',    label: 'Health check passed',       db: 'prod-postgres-primary', severity: 'success' as const },
  { id: 'act2', time: '16:40:12', type: 'error',           label: 'Connection lost',            db: 'prod-mssql-crm',        severity: 'error' as const },
  { id: 'act3', time: '16:35:00', type: 'cert_warning',    label: 'Certificate expiry warning', db: 'prod-oracle-legacy',    severity: 'warning' as const },
  { id: 'act4', time: '15:58:22', type: 'password_update', label: 'Password rotated',           db: 'prod-postgres-primary', severity: 'info' as const },
  { id: 'act5', time: '15:30:00', type: 'disconnected',    label: 'Connection lost',            db: 'gcp-cloudsql-ml',       severity: 'error' as const },
  { id: 'act6', time: '14:22:11', type: 'created',         label: 'Connection created',         db: 'dev-cockroach-cluster', severity: 'info' as const },
  { id: 'act7', time: '13:10:05', type: 'validation',      label: 'Validation passed',          db: 'aws-rds-reporting',     severity: 'success' as const },
  { id: 'act8', time: '12:05:44', type: 'cert_updated',    label: 'Certificate updated',        db: 'azure-sql-finance',     severity: 'info' as const },
];

// ─── Utility Components ───────────────────────────────────────────────────────

function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded ${className ?? ''}`}
      style={{
        background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite',
        ...style,
      }}
      aria-hidden="true"
    />
  );
}

function StatusChip({ status }: { status: DBStatus }) {
  const cfg = STATUS_META[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.dot }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function HealthChip({ health }: { health: DBHealth }) {
  const cfg = HEALTH_META[health];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function EnvChip({ env }: { env: DBEnvironment }) {
  const cfg = ENV_META[env];
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}
    >
      {cfg.label}
    </span>
  );
}

function DBTypeIcon({ vendor }: { vendor: DBVendor }) {
  const meta = VENDOR_META[vendor];
  return (
    <div className="flex items-center gap-2">
      <div
        className="flex-shrink-0 w-5 h-5 rounded flex items-center justify-center font-bold"
        style={{ background: meta.color, fontSize: '8px', fontFamily: "'JetBrains Mono', monospace", color: '#fff' }}
        aria-hidden="true"
      >
        {meta.abbr}
      </div>
      <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{meta.label}</span>
    </div>
  );
}

function LatencyBadge({ ms }: { ms: number | null }) {
  if (ms === null) return <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>—</span>;
  let color = ms < 10 ? '#22C55E' : ms < 50 ? '#F59E0B' : '#EF4444';
  return (
    <span className="text-xs tabular-nums" style={{ color, fontFamily: "'JetBrains Mono', monospace" }}>{ms}ms</span>
  );
}

function FormField({ label, id, children, required, hint }: { label: string; id: string; children: React.ReactNode; required?: boolean; hint?: string }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>
        {label}{required && <span className="ml-0.5" style={{ color: '#EF4444' }} aria-hidden="true">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs mt-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{hint}</p>}
    </div>
  );
}

function TextInput({ id, type = 'text', placeholder, value, onChange, disabled }: { id: string; type?: string; placeholder?: string; value: string; onChange: (v: string) => void; disabled?: boolean }) {
  return (
    <input
      id={id} type={type} placeholder={placeholder} value={value}
      onChange={e => onChange(e.target.value)} disabled={disabled}
      className="w-full text-xs rounded-md px-3 py-2 outline-none transition-all duration-150"
      style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: disabled ? 'var(--akaal-text-muted)' : 'var(--akaal-text)', fontFamily: type === 'password' ? "'JetBrains Mono', monospace" : "'Inter', sans-serif", cursor: disabled ? 'not-allowed' : 'text' }}
      onFocus={e => { if (!disabled) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; } }}
      onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
    />
  );
}

function Input({ id, type = 'text', placeholder, value, onChange, disabled }: { id: string; type?: string; placeholder?: string; value: string; onChange: (v: string) => void; disabled?: boolean }) {
  return (
    <TextInput id={id} type={type} placeholder={placeholder} value={value} onChange={onChange} disabled={disabled} />
  );
}

function VendorBadge({ vendor }: { vendor: DBVendor }) {
  return <DBTypeIcon vendor={vendor} />;
}

function SelectInput({ id, value, onChange, disabled, children }: { id: string; value: string; onChange: (v: string) => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <select
      id={id} value={value} onChange={e => onChange(e.target.value)} disabled={disabled}
      className="w-full text-xs rounded-md px-3 py-2 outline-none transition-all duration-150 appearance-none"
      style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: disabled ? 'var(--akaal-text-muted)' : 'var(--akaal-text)', fontFamily: "'Inter', sans-serif", cursor: disabled ? 'not-allowed' : 'pointer' }}
      onFocus={e => { if (!disabled) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; } }}
      onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
    >
      {children}
    </select>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function AppSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const navItems = [
    { href: '/dashboard', label: 'Dashboard', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/migrations', label: 'Migrations', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/execution-center', label: 'Execution', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M6 5.5l5 2.5-5 2.5V5.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { href: '/databases', label: 'Databases', active: true, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="6" ry="2" stroke="currentColor" strokeWidth="1.3" /><path d="M2 4v4c0 1.1 2.7 2 6 2s6-.9 6-2V4" stroke="currentColor" strokeWidth="1.3" /><path d="M2 8v4c0 1.1 2.7 2 6 2s6-.9 6-2V8" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/live-monitor', label: 'Live Monitor', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M4 8l2-2 2 2 2-3 2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/agents', label: 'Agents', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/reports', label: 'Reports', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/system', label: 'System', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="3" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="4.5" r="0.8" fill="currentColor" /><circle cx="4" cy="9.5" r="0.8" fill="currentColor" /><path d="M5 13h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/settings', label: 'Settings', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.4 3.4l.85.85M11.75 11.75l.85.85M3.4 12.6l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
  ];
  return (
    <aside className="flex flex-col flex-shrink-0 h-full" style={{ width: collapsed ? '56px' : '220px', background: 'var(--akaal-sidebar-gradient)', borderRight: '1px solid var(--akaal-sidebar-border)', transition: 'width 0.2s ease', overflow: 'hidden' }} aria-label="Main navigation">
      <div className="flex items-center gap-3 px-3 py-4 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-sidebar-border)', minHeight: '57px' }}>
        <AppImage src="/assets/images/app_logo.png" alt="AKAAL" width={28} height={28} className="flex-shrink-0" style={{ filter: 'drop-shadow(0 1px 4px rgba(37,99,235,0.3))' }} />
        {!collapsed && <span className="font-bold tracking-widest uppercase text-sm" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.15em', whiteSpace: 'nowrap' }}>AKAAL</span>}
      </div>
      <nav className="flex-1 py-3 overflow-y-auto" aria-label="Primary navigation">
        <ul className="space-y-0.5 px-2" role="list">
          {navItems.map(item => (
            <li key={item.href}>
              <Link href={item.href} className="flex items-center gap-3 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
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
        <button type="button" onClick={onToggle} className="w-full flex items-center justify-center p-2 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2" style={{ color: 'var(--akaal-text-muted)' }} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
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
    <header className="flex items-center gap-4 px-4 flex-shrink-0" style={{ height: '57px', background: 'var(--akaal-nav-bg)', borderBottom: '1px solid var(--akaal-nav-border)' }} role="banner">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 flex-shrink-0">
        <Link href="/dashboard" className="text-xs transition-colors" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }} onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}>Platform</Link>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Database Management</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
          <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <input type="search" placeholder="Search databases, hosts…" value={searchValue} onChange={e => setSearchValue(e.target.value)}
          className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
          style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
          aria-label="Global search"
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
        />
        <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs px-1 rounded" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>⌘K</kbd>
      </div>
      <div className="flex-1" />
      {/* Theme Switcher */}
      <ThemeSwitcher />
      <div className="relative">
        <button type="button" onClick={() => { setNotifOpen(v => !v); setProfileOpen(false); }}
          className="relative flex items-center justify-center w-8 h-8 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: 'var(--akaal-text-muted)' }} aria-label="Notifications" aria-expanded={notifOpen}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M8 1.5a5 5 0 0 0-5 5v3l-1.5 2h13L13 9.5v-3a5 5 0 0 0-5-5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
            <path d="M6.5 13.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.3" />
          </svg>
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full" style={{ background: 'var(--akaal-error)', border: '1.5px solid var(--akaal-nav-bg)' }} aria-hidden="true" />
        </button>
        {notifOpen && (
          <div className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50" style={{ width: '300px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }} role="dialog" aria-label="Notifications">
            <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}><p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Notifications</p></div>
            {[
              { title: 'Connection Lost', detail: 'prod-mssql-crm is unreachable', time: '2m ago', color: 'var(--akaal-error)' },
              { title: 'Certificate Expiry', detail: 'prod-oracle-legacy cert expires in 52 days', time: '1h ago', color: 'var(--akaal-warning)' },
              { title: 'Health Degraded', detail: 'dev-mongodb-events latency spike: 89ms', time: '3h ago', color: 'var(--akaal-warning)' },
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
      <div className="relative">
        <button type="button" onClick={() => { setProfileOpen(v => !v); setNotifOpen(false); }}
          className="flex items-center gap-2 px-2 py-1.5 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: 'var(--akaal-text-muted)' }} aria-label="User profile menu" aria-expanded={profileOpen}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
        >
          <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }} aria-hidden="true">SC</div>
          <span className="text-xs font-medium hidden sm:block" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>sarah.chen</span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
        </button>
        {profileOpen && (
          <div className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50" style={{ width: '200px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }} role="menu" aria-label="User menu">
            <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>sarah.chen</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Platform Administrator</p>
            </div>
            {['Profile Settings', 'API Keys', 'Audit Log', 'Sign Out'].map((item, i) => (
              <button key={i} type="button" role="menuitem" className="w-full text-left px-3 py-2 text-xs transition-colors"
                style={{ color: item === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", borderBottom: i < 3 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = item === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-secondary)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = item === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)'; }}
              >{item}</button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

// ─── Left Panel ───────────────────────────────────────────────────────────────

function LeftPanel({
  category, onCategory, vendorFilter, onVendorFilter, envFilter, onEnvFilter, healthFilter, onHealthFilter, connections,
}: {
  category: CategoryFilter; onCategory: (c: CategoryFilter) => void;
  vendorFilter: string; onVendorFilter: (v: string) => void;
  envFilter: string; onEnvFilter: (v: string) => void;
  healthFilter: string; onHealthFilter: (v: string) => void;
  connections: DBConnection[];
}) {
  const categories: { id: CategoryFilter; label: string; icon: React.ReactNode; count: number }[] = [
    { id: 'all',        label: 'All Connections', count: connections.length, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><ellipse cx="7" cy="3.5" rx="5" ry="1.5" stroke="currentColor" strokeWidth="1.2" /><path d="M2 3.5v3c0 .83 2.24 1.5 5 1.5s5-.67 5-1.5v-3" stroke="currentColor" strokeWidth="1.2" /><path d="M2 6.5v3c0 .83 2.24 1.5 5 1.5s5-.67 5-1.5v-3" stroke="currentColor" strokeWidth="1.2" /></svg> },
    { id: 'favorites',  label: 'Favorites',       count: connections.filter(c => c.isFavorite).length, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2l1.5 3 3.5.5-2.5 2.5.5 3.5L7 10l-3 1.5.5-3.5L2 5.5 5.5 5 7 2Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /></svg> },
    { id: 'production', label: 'Production',      count: connections.filter(c => c.environment === 'production').length, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.2" /><path d="M7 4v3l2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
    { id: 'staging',    label: 'Staging',         count: connections.filter(c => c.environment === 'staging').length, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="2" y="2" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.2" /><path d="M5 7h4M7 5v4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
    { id: 'development',label: 'Development',     count: connections.filter(c => c.environment === 'development').length, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M4 5l-2 2 2 2M10 5l2 2-2 2M8 3l-2 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
    { id: 'testing',    label: 'Testing',         count: connections.filter(c => c.environment === 'testing').length, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 2v4L2 12h10L9 6V2" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /><path d="M4.5 2h5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
    { id: 'archived',   label: 'Archived',        count: connections.filter(c => c.environment === 'archived').length, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1.5" y="3" width="11" height="2.5" rx="0.75" stroke="currentColor" strokeWidth="1.2" /><path d="M2.5 5.5v5.5h9V5.5" stroke="currentColor" strokeWidth="1.2" /><path d="M5.5 8h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
  ];

  return (
    <aside className="flex flex-col flex-shrink-0 overflow-y-auto" style={{ width: '200px', background: '#111827', borderRight: '1px solid #2A3647' }} aria-label="Database categories">
      <div className="px-3 py-3 flex-shrink-0" style={{ borderBottom: '1px solid #2A3647' }}>
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em' }}>Categories</p>
      </div>
      <nav className="py-1.5" aria-label="Database category filters">
        {categories.map(cat => {
          const isActive = category === cat.id;
          return (
            <button key={cat.id} type="button" onClick={() => onCategory(cat.id)}
              className="w-full flex items-center justify-between px-3 py-2 text-left transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset"
              style={{ background: isActive ? 'var(--akaal-primary-subtle)' : 'transparent', borderLeft: isActive ? '2px solid var(--akaal-primary)' : '2px solid transparent', color: isActive ? 'var(--akaal-text)' : 'var(--akaal-text-muted)' }}
              aria-current={isActive ? 'true' : undefined}
              onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; } }}
              onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; } }}
            >
              <div className="flex items-center gap-2.5">
                <span className="flex-shrink-0" style={{ color: isActive ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)' }}>{cat.icon}</span>
                <span className="text-xs font-medium" style={{ fontFamily: "'Inter', sans-serif" }}>{cat.label}</span>
              </div>
              <span className="text-xs tabular-nums flex-shrink-0" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cat.count}</span>
            </button>
          );
        })}
      </nav>

      <div className="px-3 py-3 flex-shrink-0" style={{ borderTop: '1px solid #2A3647', borderBottom: '1px solid #2A3647', marginTop: '4px' }}>
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em' }}>Filters</p>
      </div>
      <div className="p-3 space-y-3">
        <div>
          <label className="block text-xs mb-1.5" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>Vendor</label>
          <SelectInput id="filter-vendor" value={vendorFilter} onChange={onVendorFilter}>
            <option value="">All Vendors</option>
            {Object.entries(VENDOR_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </SelectInput>
        </div>
        <div>
          <label className="block text-xs mb-1.5" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>Environment</label>
          <SelectInput id="filter-env" value={envFilter} onChange={onEnvFilter}>
            <option value="">All Environments</option>
            {Object.entries(ENV_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </SelectInput>
        </div>
        <div>
          <label className="block text-xs mb-1.5" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>Health</label>
          <SelectInput id="filter-health" value={healthFilter} onChange={onHealthFilter}>
            <option value="">All Health</option>
            {Object.entries(HEALTH_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </SelectInput>
        </div>
        {(vendorFilter || envFilter || healthFilter) && (
          <button type="button" onClick={() => { onVendorFilter(''); onEnvFilter(''); onHealthFilter(''); }}
            className="w-full text-xs py-1.5 rounded transition-all duration-150"
            style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-active-bg)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
          >Clear Filters</button>
        )}
      </div>
    </aside>
  );
}

// ─── Add Database Drawer ──────────────────────────────────────────────────────

function AddDBDrawer({
  open, onClose, onSave,
}: {
  open: boolean; onClose: () => void; onSave: (conn: Partial<DBConnection>) => void;
}) {
  const [form, setForm] = useState<AddDBForm>({
    name: '', vendor: '', environment: '', host: '', port: '', database: '',
    username: '', password: '', authMethod: 'password', sslEnabled: false, sslMode: 'require',
    connectionTimeout: '30', showAdvanced: false, maxPoolSize: '10', minPoolSize: '2', idleTimeout: '600', tags: '',
  });
  const [testStatus, setTestStatus] = useState<TestStatus>('idle');
  const [testStageIdx, setTestStageIdx] = useState(-1);
  const [failedStage, setFailedStage] = useState<number | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const set = (k: keyof AddDBForm, v: string | boolean) => setForm(f => ({ ...f, [k]: v }));

  const handleTest = useCallback(() => {
    setTestStatus('running');
    setTestStageIdx(0);
    setFailedStage(null);
    let idx = 0;
    const advance = () => {
      idx++;
      if (idx >= TEST_STAGES.length) {
        setTestStageIdx(TEST_STAGES.length - 1);
        setTestStatus('success');
        return;
      }
      setTestStageIdx(idx);
      // Simulate failure on 'write' stage if no host
      if (TEST_STAGES[idx].id === 'write' && !form.host) {
        setFailedStage(idx);
        setTestStatus('failed');
        return;
      }
      timerRef.current = setTimeout(advance, 600);
    };
    timerRef.current = setTimeout(advance, 600);
  }, [form.host]);

  useEffect(() => {
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, []);

  const handleSave = () => {
    if (!form.name || !form.vendor || !form.environment || !form.host) return;
    onSave({
      name: form.name,
      vendor: form.vendor as DBVendor,
      environment: form.environment as DBEnvironment,
      host: form.host,
      port: parseInt(form.port) || 5432,
      database: form.database,
      status: 'unknown',
      health: 'unknown',
      latencyMs: null,
      owner: 'sarah.chen',
      createdAt: new Date().toISOString().split('T')[0],
      lastChecked: '—',
      isFavorite: false,
      tags: form.tags ? form.tags.split(',').map(t => t.trim()) : [],
      sslEnabled: form.sslEnabled,
      authMethod: form.authMethod,
    });
    onClose();
  };

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-40" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={onClose} aria-hidden="true" />
      <aside
        className="fixed right-0 top-0 h-full z-50 flex flex-col overflow-hidden"
        style={{ width: '480px', background: '#111827', borderLeft: '1px solid #2A3647', boxShadow: '-8px 0 32px rgba(0,0,0,0.5)' }}
        role="dialog" aria-modal="true" aria-label="Add Database Connection"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
          <div>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Add Database Connection</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Configure a new enterprise database connection</p>
          </div>
          <button type="button" onClick={onClose} className="flex items-center justify-center w-7 h-7 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2" style={{ color: 'var(--akaal-text-muted)' }} aria-label="Close drawer"
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {/* Basic Info */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em' }}>Connection Details</p>
            <div className="space-y-3">
              <FormField label="Connection Name" id="add-name" required>
                <Input id="add-name" placeholder="prod-postgres-primary" value={form.name} onChange={v => set('name', v)} />
              </FormField>
              <div className="grid grid-cols-2 gap-3">
                <FormField label="Database Type" id="add-vendor" required>
                  <SelectInput id="add-vendor" value={form.vendor} onChange={v => set('vendor', v)}>
                    <option value="">Select type…</option>
                    {Object.entries(VENDOR_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </SelectInput>
                </FormField>
                <FormField label="Environment" id="add-env" required>
                  <SelectInput id="add-env" value={form.environment} onChange={v => set('environment', v)}>
                    <option value="">Select env…</option>
                    {Object.entries(ENV_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </SelectInput>
                </FormField>
              </div>
            </div>
          </div>

          {/* Connection */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em' }}>Host Configuration</p>
            <div className="space-y-3">
              <FormField label="Host / IP Address" id="add-host" required>
                <Input id="add-host" placeholder="db-prod-01.internal" value={form.host} onChange={v => set('host', v)} />
              </FormField>
              <div className="grid grid-cols-2 gap-3">
                <FormField label="Port" id="add-port" required>
                  <Input id="add-port" placeholder="5432" value={form.port} onChange={v => set('port', v)} />
                </FormField>
                <FormField label="Database Name" id="add-db" required>
                  <Input id="add-db" placeholder="mydb" value={form.database} onChange={v => set('database', v)} />
                </FormField>
              </div>
            </div>
          </div>

          {/* Auth */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em' }}>Authentication</p>
            <div className="space-y-3">
              <FormField label="Authentication Method" id="add-auth">
                <SelectInput id="add-auth" value={form.authMethod} onChange={v => set('authMethod', v)}>
                  <option value="password">Username / Password</option>
                  <option value="iam">IAM / Cloud Identity</option>
                  <option value="certificate">Certificate</option>
                  <option value="windows">Windows Authentication</option>
                  <option value="azure-ad">Azure Active Directory</option>
                  <option value="scram">SCRAM-SHA-256</option>
                </SelectInput>
              </FormField>
              <div className="grid grid-cols-2 gap-3">
                <FormField label="Username" id="add-user">
                  <Input id="add-user" placeholder="migration_user" value={form.username} onChange={v => set('username', v)} />
                </FormField>
                <FormField label="Password" id="add-pass">
                  <div className="relative">
                    <input
                      id="add-pass" type={showPassword ? 'text' : 'password'} placeholder="••••••••••••" value={form.password}
                      onChange={e => set('password', e.target.value)}
                      className="w-full text-xs rounded-md px-3 py-2 pr-8 outline-none transition-all duration-150"
                      style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}
                      onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
                      onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
                    />
                    <button type="button" onClick={() => setShowPassword(v => !v)} className="absolute right-2 top-1/2 -translate-y-1/2" style={{ color: '#64748B' }} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                        {showPassword
                          ? <><path d="M1 6.5C2.5 3.5 4.5 2 6.5 2s4 1.5 5.5 4.5c-1.5 3-3.5 4.5-5.5 4.5S2.5 9.5 1 6.5Z" stroke="currentColor" strokeWidth="1.2" /><circle cx="6.5" cy="6.5" r="1.5" stroke="currentColor" strokeWidth="1.2" /><path d="M2 2l9 9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></>
                          : <><path d="M1 6.5C2.5 3.5 4.5 2 6.5 2s4 1.5 5.5 4.5c-1.5 3-3.5 4.5-5.5 4.5S2.5 9.5 1 6.5Z" stroke="currentColor" strokeWidth="1.2" /><circle cx="6.5" cy="6.5" r="1.5" stroke="currentColor" strokeWidth="1.2" /></>
                        }
                      </svg>
                    </button>
                  </div>
                </FormField>
              </div>
            </div>
          </div>

          {/* SSL */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em' }}>SSL Configuration</p>
            <div className="space-y-3">
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input type="checkbox" checked={form.sslEnabled} onChange={e => set('sslEnabled', e.target.checked)} className="w-3.5 h-3.5 rounded" style={{ accentColor: 'var(--akaal-primary)' }} id="add-ssl" />
                <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Enable SSL/TLS encryption</span>
              </label>
              {form.sslEnabled && (
                <FormField label="SSL Mode" id="add-ssl-mode">
                  <SelectInput id="add-ssl-mode" value={form.sslMode} onChange={v => set('sslMode', v)}>
                    <option value="require">Require</option>
                    <option value="verify-ca">Verify CA</option>
                    <option value="verify-full">Verify Full</option>
                    <option value="disable">Disable</option>
                  </SelectInput>
                </FormField>
              )}
            </div>
          </div>

          {/* Timeout */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em' }}>Timeouts</p>
            <FormField label="Connection Timeout (seconds)" id="add-timeout">
              <Input id="add-timeout" placeholder="30" value={form.connectionTimeout} onChange={v => set('connectionTimeout', v)} />
            </FormField>
          </div>

          {/* Advanced */}
          <div>
            <button type="button" onClick={() => set('showAdvanced', !form.showAdvanced)}
              className="flex items-center gap-2 text-xs transition-colors focus:outline-none focus-visible:ring-2"
              style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ transform: form.showAdvanced ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }}>
                <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
              </svg>
              Advanced Options
            </button>
            {form.showAdvanced && (
              <div className="mt-3 space-y-3 pl-4" style={{ borderLeft: '1px solid #2A3647' }}>
                <div className="grid grid-cols-2 gap-3">
                  <FormField label="Max Pool Size" id="add-maxpool">
                    <Input id="add-maxpool" placeholder="10" value={form.maxPoolSize} onChange={v => set('maxPoolSize', v)} />
                  </FormField>
                  <FormField label="Min Pool Size" id="add-minpool">
                    <Input id="add-minpool" placeholder="2" value={form.minPoolSize} onChange={v => set('minPoolSize', v)} />
                  </FormField>
                </div>
                <FormField label="Idle Timeout (seconds)" id="add-idle">
                  <Input id="add-idle" placeholder="600" value={form.idleTimeout} onChange={v => set('idleTimeout', v)} />
                </FormField>
                <FormField label="Tags (comma-separated)" id="add-tags" hint="e.g. primary, critical, managed">
                  <Input id="add-tags" placeholder="primary, critical" value={form.tags} onChange={v => set('tags', v)} />
                </FormField>
              </div>
            )}
          </div>

          {/* Connection Test */}
          <div className="rounded-lg p-4" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Connection Test</p>
              {testStatus === 'success' && <span className="text-xs" style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>✓ All checks passed</span>}
              {testStatus === 'failed' && <span className="text-xs" style={{ color: '#EF4444', fontFamily: "'JetBrains Mono', monospace" }}>✕ Test failed</span>}
            </div>
            {testStatus !== 'idle' && (
              <div className="space-y-1.5 mb-3">
                {TEST_STAGES.map((stage, i) => {
                  const isDone = i < testStageIdx || testStatus === 'success';
                  const isCurrent = i === testStageIdx && testStatus === 'running';
                  const isFailed = failedStage === i;
                  let color = '#64748B';
                  let icon = <span style={{ color: '#374151', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>○</span>;
                  if (isDone && !isFailed) { color = '#22C55E'; icon = <span style={{ color: '#22C55E', fontSize: '10px' }}>✓</span>; }
                  if (isCurrent) { color = '#38BDF8'; icon = <span className="inline-block" style={{ color: '#38BDF8', fontSize: '10px', animation: 'spin 1s linear infinite' }}>◌</span>; }
                  if (isFailed) { color = '#EF4444'; icon = <span style={{ color: '#EF4444', fontSize: '10px' }}>✕</span>; }
                  return (
                    <div key={stage.id} className="flex items-center gap-2">
                      <span className="w-4 flex-shrink-0 text-center">{icon}</span>
                      <span className="text-xs" style={{ color, fontFamily: "'Inter', sans-serif" }}>{stage.label}</span>
                      {isFailed && <span className="text-xs ml-auto" style={{ color: '#EF4444', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>FAILED</span>}
                    </div>
                  );
                })}
              </div>
            )}
            <button type="button" onClick={handleTest} disabled={testStatus === 'running'}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'rgba(37,99,235,0.15)', border: '1px solid rgba(37,99,235,0.3)', color: '#60A5FA', fontFamily: "'Inter', sans-serif", cursor: testStatus === 'running' ? 'not-allowed' : 'pointer', opacity: testStatus === 'running' ? 0.6 : 1 }}
              onMouseEnter={e => { if (testStatus !== 'running') e.currentTarget.style.background = 'rgba(37,99,235,0.25)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(37,99,235,0.15)'; }}
            >
              {testStatus === 'running' ? (
                <><svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="animate-spin"><circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="14 8" /></svg>Testing…</>
              ) : 'Test Connection'}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-4 flex-shrink-0" style={{ borderTop: '1px solid var(--akaal-border)' }}>
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'transparent', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
          >Cancel</button>
          <button type="button" onClick={handleSave}
            className="px-4 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.filter = 'brightness(1.1)'; }}
            onMouseLeave={e => { e.currentTarget.style.filter = 'none'; }}
          >Save Connection</button>
        </div>
      </aside>
    </>
  );
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────

function DetailPanel({ conn, onClose }: { conn: DBConnection; onClose: () => void }) {
  const [tab, setTab] = useState<DetailTab>('overview');
  const tabs: { id: DetailTab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'health', label: 'Health' },
    { id: 'security', label: 'Security' },
    { id: 'activity', label: 'Activity' },
  ];
  const vm = VENDOR_META[conn.vendor];
  const activity = MOCK_ACTIVITY.filter(a => a.db === conn.name);

  return (
    <aside className="flex flex-col flex-shrink-0 overflow-hidden" style={{ width: '340px', background: '#111827', borderLeft: '1px solid #2A3647' }} role="complementary" aria-label={`Details for ${conn.name}`}>
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center font-bold text-xs" style={{ background: vm.color, fontFamily: "'JetBrains Mono', monospace", color: '#fff' }} aria-hidden="true">{vm.abbr}</div>
          <div className="min-w-0">
            <p className="text-xs font-semibold truncate" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{conn.name}</p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{vm.label}</p>
          </div>
        </div>
        <button type="button" onClick={onClose} className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded transition-all duration-150 focus:outline-none focus-visible:ring-2 ml-2" style={{ color: '#64748B' }} aria-label="Close detail panel"
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = '#94A3B8'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#64748B'; }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 2l8 8M10 2L2 10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
        </button>
      </div>

      {/* Status row */}
      <div className="flex items-center gap-2 px-4 py-2.5 flex-shrink-0" style={{ borderBottom: '1px solid #2A3647', background: '#0F1929' }}>
        <StatusChip status={conn.status} />
        <HealthChip health={conn.health} />
        <EnvChip env={conn.environment} />
      </div>

      {/* Tabs */}
      <div className="flex flex-shrink-0" style={{ borderBottom: '1px solid #2A3647' }}>
        {tabs.map(t => (
          <button key={t.id} type="button" onClick={() => setTab(t.id)}
            className="flex-1 py-2.5 text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset"
            style={{ color: tab === t.id ? 'var(--akaal-text)' : 'var(--akaal-text-muted)', borderBottom: tab === t.id ? '2px solid var(--akaal-primary)' : '2px solid transparent', fontFamily: "'Inter', sans-serif", background: 'transparent' }}
            aria-selected={tab === t.id} role="tab"
          >{t.label}</button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {tab === 'overview' && (
          <div className="p-4 space-y-4">
            <div className="rounded-lg p-3 space-y-2" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Connection Info</p>
              {[
                { label: 'Host', value: conn.host },
                { label: 'Port', value: String(conn.port) },
                { label: 'Database', value: conn.database },
                { label: 'Version', value: conn.version ?? '—' },
                { label: 'Owner', value: conn.owner },
                { label: 'Created', value: conn.createdAt },
                { label: 'Last Checked', value: conn.lastChecked },
              ].map(row => (
                <div key={row.label} className="flex items-start justify-between gap-2">
                  <span className="text-xs flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", minWidth: '80px' }}>{row.label}</span>
                  <span className="text-xs text-right break-all" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{row.value}</span>
                </div>
              ))}
            </div>
            <div className="rounded-lg p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Statistics</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Schemas', value: conn.schemaCount ?? '—' },
                  { label: 'Tables', value: conn.tableCount ?? '—' },
                  { label: 'Storage Used', value: conn.storageUsedGB ? `${conn.storageUsedGB} GB` : '—' },
                  { label: 'Storage Total', value: conn.storageTotalGB ? `${conn.storageTotalGB} GB` : '—' },
                ].map(s => (
                  <div key={s.label} className="rounded p-2" style={{ background: 'var(--akaal-bg)', border: '1px solid var(--akaal-border)' }}>
                    <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{s.label}</p>
                    <p className="text-sm font-semibold mt-0.5" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{String(s.value)}</p>
                  </div>
                ))}
              </div>
            </div>
            {conn.storageUsedGB && conn.storageTotalGB && (
              <div className="rounded-lg p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Storage</p>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{Math.round((conn.storageUsedGB / conn.storageTotalGB) * 100)}%</span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-border)' }}>
                  <div className="h-full rounded-full" style={{ width: `${(conn.storageUsedGB / conn.storageTotalGB) * 100}%`, background: conn.storageUsedGB / conn.storageTotalGB > 0.85 ? '#EF4444' : conn.storageUsedGB / conn.storageTotalGB > 0.7 ? '#F59E0B' : '#2563EB' }} />
                </div>
                <p className="text-xs mt-1" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{conn.storageUsedGB} GB / {conn.storageTotalGB} GB</p>
              </div>
            )}
            {conn.tags.length > 0 && (
              <div>
                <p className="text-xs mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {conn.tags.map(tag => (
                    <span key={tag} className="px-2 py-0.5 rounded text-xs" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{tag}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'health' && (
          <div className="p-4 space-y-4">
            <div className="rounded-lg p-3 space-y-2.5" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Health Metrics</p>
              {[
                { label: 'Connection Status', value: <StatusChip status={conn.status} /> },
                { label: 'Health', value: <HealthChip health={conn.health} /> },
                { label: 'Latency', value: <LatencyBadge ms={conn.latencyMs} /> },
                { label: 'Last Checked', value: <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{conn.lastChecked}</span> },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{row.label}</span>
                  {row.value}
                </div>
              ))}
            </div>
            <div className="rounded-lg p-3 space-y-2.5" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Replication & CDC</p>
              {[
                { label: 'Replication', value: conn.replicationStatus ?? '—' },
                { label: 'CDC Status', value: conn.cdcStatus ?? '—' },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{row.label}</span>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{row.value}</span>
                </div>
              ))}
            </div>
            {conn.certExpiry && (
              <div className="rounded-lg p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Certificate</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Expiry</span>
                  <span className="text-xs" style={{ color: '#F59E0B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{conn.certExpiry}</span>
                </div>
                <div className="flex items-center justify-between mt-1.5">
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>SSL</span>
                  <span className="text-xs" style={{ color: conn.sslEnabled ? '#22C55E' : '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{conn.sslEnabled ? 'Enabled' : 'Disabled'}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'security' && (
          <div className="p-4 space-y-4">
            <div className="rounded-lg p-3 space-y-2.5" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Credentials</p>
              {[
                { label: 'Auth Method', value: conn.authMethod },
                { label: 'Password', value: '••••••••••••' },
                { label: 'SSL Encryption', value: conn.sslEnabled ? 'Enabled' : 'Disabled' },
                { label: 'Cert Expiry', value: conn.certExpiry ?? '—' },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{row.label}</span>
                  <span className="text-xs" style={{ color: row.label === 'Password' ? '#64748B' : 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{row.value}</span>
                </div>
              ))}
            </div>
            <div className="rounded-lg p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Audit</p>
              {[
                { label: 'Created By', value: conn.owner },
                { label: 'Created At', value: conn.createdAt },
                { label: 'Last Modified', value: conn.lastChecked },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between mb-1.5 last:mb-0">
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{row.label}</span>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'activity' && (
          <div className="p-4">
            {activity.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true" className="mb-3" style={{ color: '#374151' }}>
                  <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M16 10v6l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <p className="text-xs font-medium" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>No recent activity</p>
                <p className="text-xs mt-1" style={{ color: '#374151', fontFamily: "'Inter', sans-serif" }}>Activity events will appear here</p>
              </div>
            ) : (
              <div className="space-y-0">
                {activity.map((evt, i) => {
                  const colors: Record<string, string> = { success: '#22C55E', error: '#EF4444', warning: '#F59E0B', info: '#38BDF8' };
                  let color = colors[evt.severity];
                  return (
                    <div key={evt.id} className="flex gap-3">
                      <div className="flex flex-col items-center flex-shrink-0">
                        <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: `${color}18`, border: `1px solid ${color}40` }}>
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} aria-hidden="true" />
                        </div>
                        {i < activity.length - 1 && <div className="w-px flex-1 my-1" style={{ background: '#2A3647', minHeight: '16px' }} aria-hidden="true" />}
                      </div>
                      <div className="pb-3 min-w-0">
                        <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{evt.label}</p>
                        <p className="text-xs mt-0.5" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{evt.time}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

// ─── Main Table ───────────────────────────────────────────────────────────────

type SortKey = 'name' | 'vendor' | 'environment' | 'host' | 'status' | 'health' | 'latencyMs' | 'owner' | 'createdAt' | 'lastChecked';

function ConnectionTable({
  connections, loading, onSelect, selectedId, onToggleFavorite,
}: {
  connections: DBConnection[];
  loading: boolean;
  onSelect: (conn: DBConnection) => void;
  selectedId: string | null;
  onToggleFavorite: (id: string) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkMenuOpen, setBulkMenuOpen] = useState(false);
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(new Set());
  const [colMenuOpen, setColMenuOpen] = useState(false);

  const allCols = ['vendor', 'environment', 'host', 'port', 'database', 'status', 'health', 'latency', 'owner', 'created', 'lastChecked'];

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const filtered = connections.filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return c.name.toLowerCase().includes(q) || c.host.toLowerCase().includes(q) || c.database.toLowerCase().includes(q) || c.owner.toLowerCase().includes(q) || VENDOR_META[c.vendor].label.toLowerCase().includes(q);
  });

  const sorted = [...filtered].sort((a, b) => {
    let av: string | number = a[sortKey] ?? '';
    let bv: string | number = b[sortKey] ?? '';
    if (sortKey === 'latencyMs') { av = a.latencyMs ?? 9999; bv = b.latencyMs ?? 9999; }
    if (typeof av === 'string' && typeof bv === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number);
  });

  const allSelected = sorted.length > 0 && sorted.every(c => selected.has(c.id));
  const someSelected = sorted.some(c => selected.has(c.id));

  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(sorted.map(c => c.id)));
  };

  const toggleRow = (id: string) => {
    setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  };

  const SortIcon = ({ col }: { col: SortKey }) => (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" style={{ opacity: sortKey === col ? 1 : 0.3 }}>
      {sortKey === col && sortDir === 'asc'
        ? <path d="M5 2l3 4H2l3-4Z" fill="currentColor" />
        : <path d="M5 8L2 4h6L5 8Z" fill="currentColor" />
      }
    </svg>
  );

  const thStyle: React.CSSProperties = { color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap', padding: '8px 12px', background: '#1A2333', borderBottom: '1px solid #2A3647', cursor: 'pointer', userSelect: 'none' };
  const tdStyle: React.CSSProperties = { padding: '8px 12px', verticalAlign: 'middle', whiteSpace: 'nowrap' };

  return (
    <div className="flex flex-col flex-1 overflow-hidden" style={{ background: '#1F2937', border: '1px solid #2A3647', borderRadius: '8px' }}>
      {/* Table toolbar */}
      <div className="flex items-center gap-3 px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid #2A3647' }}>
        <div className="relative flex-1 max-w-xs">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: '#64748B' }}>
            <circle cx="5.5" cy="5.5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
            <path d="M8.5 8.5l2.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
          <input type="search" placeholder="Search connections…" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full text-xs rounded-md pl-7 pr-3 py-1.5 outline-none transition-all duration-150"
            style={{ background: '#111827', border: '1px solid #2A3647', color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}
            aria-label="Search connections"
            onFocus={e => { e.currentTarget.style.borderColor = '#2563EB'; e.currentTarget.style.boxShadow = '0 0 0 2px rgba(37,99,235,0.2)'; }}
            onBlur={e => { e.currentTarget.style.borderColor = '#2A3647'; e.currentTarget.style.boxShadow = 'none'; }}
          />
        </div>
        <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{sorted.length} connection{sorted.length !== 1 ? 's' : ''}</span>
        {someSelected && (
          <div className="relative">
            <button type="button" onClick={() => setBulkMenuOpen(v => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'rgba(37,99,235,0.15)', border: '1px solid rgba(37,99,235,0.3)', color: '#60A5FA', fontFamily: "'Inter', sans-serif" }}
              aria-expanded={bulkMenuOpen}
            >
              {selected.size} selected
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
            </button>
            {bulkMenuOpen && (
              <div className="absolute left-0 top-full mt-1 rounded-lg overflow-hidden z-30" style={{ width: '180px', background: '#1A2333', border: '1px solid #2A3647', boxShadow: '0 8px 24px rgba(0,0,0,0.4)' }}>
                {['Test All Connections', 'Refresh Health', 'Export Selected', 'Archive Selected', 'Delete Selected'].map((action, i) => (
                  <button key={i} type="button" onClick={() => setBulkMenuOpen(false)}
                    className="w-full text-left px-3 py-2 text-xs transition-colors"
                    style={{ color: action === 'Delete Selected' ? '#EF4444' : '#94A3B8', fontFamily: "'Inter', sans-serif", borderBottom: i < 4 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'; (e.currentTarget as HTMLElement).style.color = action === 'Delete Selected' ? '#EF4444' : '#CBD5E1'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = action === 'Delete Selected' ? '#EF4444' : '#94A3B8'; }}
                  >{action}</button>
                ))}
              </div>
            )}
          </div>
        )}
        <div className="flex-1" />
        {/* Column visibility */}
        <div className="relative">
          <button type="button" onClick={() => setColMenuOpen(v => !v)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'transparent', border: '1px solid #2A3647', color: '#64748B', fontFamily: "'Inter', sans-serif" }}
            aria-label="Toggle column visibility" aria-expanded={colMenuOpen}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#94A3B8'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#64748B'; }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><rect x="1" y="2" width="10" height="1.5" rx="0.75" fill="currentColor" /><rect x="1" y="5.25" width="10" height="1.5" rx="0.75" fill="currentColor" /><rect x="1" y="8.5" width="10" height="1.5" rx="0.75" fill="currentColor" /></svg>
            Columns
          </button>
          {colMenuOpen && (
            <div className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-30" style={{ width: '160px', background: '#1A2333', border: '1px solid #2A3647', boxShadow: '0 8px 24px rgba(0,0,0,0.4)' }}>
              <div className="px-3 py-2" style={{ borderBottom: '1px solid #2A3647' }}>
                <p className="text-xs font-semibold" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>Visible Columns</p>
              </div>
              {allCols.map(col => (
                <label key={col} className="flex items-center gap-2.5 px-3 py-2 cursor-pointer transition-colors"
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <input type="checkbox" checked={!hiddenCols.has(col)} onChange={() => setHiddenCols(s => { const n = new Set(s); n.has(col) ? n.delete(col) : n.add(col); return n; })}
                    className="w-3 h-3 rounded" style={{ accentColor: '#2563EB' }} />
                  <span className="text-xs capitalize" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>{col}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton style={{ width: '16px', height: '16px', borderRadius: '4px' }} />
                <Skeleton style={{ width: '180px', height: '14px' }} />
                <Skeleton style={{ width: '80px', height: '14px' }} />
                <Skeleton style={{ width: '100px', height: '14px' }} />
                <Skeleton style={{ width: '160px', height: '14px' }} />
                <Skeleton style={{ width: '60px', height: '20px', borderRadius: '4px' }} />
                <Skeleton style={{ width: '60px', height: '20px', borderRadius: '4px' }} />
                <Skeleton style={{ width: '40px', height: '14px' }} />
              </div>
            ))}
          </div>
        ) : sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-16 text-center">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true" className="mb-4" style={{ color: '#2A3647' }}>
              <ellipse cx="20" cy="10" rx="14" ry="5" stroke="currentColor" strokeWidth="1.5" />
              <path d="M6 10v10c0 2.76 6.27 5 14 5s14-2.24 14-5V10" stroke="currentColor" strokeWidth="1.5" />
              <path d="M6 20v10c0 2.76 6.27 5 14 5s14-2.24 14-5V20" stroke="currentColor" strokeWidth="1.5" />
              <path d="M14 20l12 0M14 26l8 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <p className="text-sm font-semibold" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>
              {search ? 'No connections match your search' : 'No database connections configured'}
            </p>
            <p className="text-xs mt-1.5 max-w-xs" style={{ color: '#374151', fontFamily: "'Inter', sans-serif" }}>
              {search ? 'Adjust your search query or clear filters to see all connections.' : 'Add your first database connection to begin managing enterprise infrastructure.'}
            </p>
          </div>
        ) : (
          <table className="w-full border-collapse" role="grid" aria-label="Database connections">
            <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
              <tr>
                <th style={{ ...thStyle, width: '36px', cursor: 'default' }}>
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} className="w-3 h-3 rounded" style={{ accentColor: '#2563EB' }} aria-label="Select all connections" />
                </th>
                <th style={{ ...thStyle, width: '20px', cursor: 'default' }} aria-label="Favorite" />
                <th style={thStyle} onClick={() => handleSort('name')}>
                  <div className="flex items-center gap-1.5">Name <SortIcon col="name" /></div>
                </th>
                {!hiddenCols.has('vendor') && <th style={thStyle} onClick={() => handleSort('vendor')}><div className="flex items-center gap-1.5">Vendor <SortIcon col="vendor" /></div></th>}
                {!hiddenCols.has('environment') && <th style={thStyle} onClick={() => handleSort('environment')}><div className="flex items-center gap-1.5">Env <SortIcon col="environment" /></div></th>}
                {!hiddenCols.has('host') && <th style={thStyle} onClick={() => handleSort('host')}><div className="flex items-center gap-1.5">Host <SortIcon col="host" /></div></th>}
                {!hiddenCols.has('port') && <th style={thStyle}>Port</th>}
                {!hiddenCols.has('database') && <th style={thStyle}>Database</th>}
                {!hiddenCols.has('status') && <th style={thStyle} onClick={() => handleSort('status')}><div className="flex items-center gap-1.5">Status <SortIcon col="status" /></div></th>}
                {!hiddenCols.has('health') && <th style={thStyle} onClick={() => handleSort('health')}><div className="flex items-center gap-1.5">Health <SortIcon col="health" /></div></th>}
                {!hiddenCols.has('latency') && <th style={thStyle} onClick={() => handleSort('latencyMs')}><div className="flex items-center gap-1.5">Latency <SortIcon col="latencyMs" /></div></th>}
                {!hiddenCols.has('owner') && <th style={thStyle} onClick={() => handleSort('owner')}><div className="flex items-center gap-1.5">Owner <SortIcon col="owner" /></div></th>}
                {!hiddenCols.has('created') && <th style={thStyle} onClick={() => handleSort('createdAt')}><div className="flex items-center gap-1.5">Created <SortIcon col="createdAt" /></div></th>}
                {!hiddenCols.has('lastChecked') && <th style={thStyle} onClick={() => handleSort('lastChecked')}><div className="flex items-center gap-1.5">Last Checked <SortIcon col="lastChecked" /></div></th>}
                <th style={{ ...thStyle, cursor: 'default' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(conn => {
                const isSelected = selected.has(conn.id);
                const isActive = selectedId === conn.id;
                return (
                  <tr key={conn.id}
                    className="transition-colors cursor-pointer"
                    style={{ background: isActive ? 'rgba(37,99,235,0.08)' : isSelected ? 'rgba(37,99,235,0.04)' : 'transparent', borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                    onClick={() => onSelect(conn)}
                    onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
                    onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = isSelected ? 'rgba(37,99,235,0.04)' : 'transparent'; }}
                    aria-selected={isActive}
                  >
                    <td style={tdStyle} onClick={e => { e.stopPropagation(); toggleRow(conn.id); }}>
                      <input type="checkbox" checked={isSelected} onChange={() => toggleRow(conn.id)} className="w-3 h-3 rounded" style={{ accentColor: '#2563EB' }} aria-label={`Select ${conn.name}`} />
                    </td>
                    <td style={tdStyle} onClick={e => { e.stopPropagation(); onToggleFavorite(conn.id); }}>
                      <button type="button" aria-label={conn.isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                        className="transition-colors focus:outline-none focus-visible:ring-1"
                        style={{ color: conn.isFavorite ? '#F59E0B' : '#374151' }}
                        onMouseEnter={e => { if (!conn.isFavorite) e.currentTarget.style.color = '#64748B'; }}
                        onMouseLeave={e => { if (!conn.isFavorite) e.currentTarget.style.color = '#374151'; }}
                      >
                        <svg width="12" height="12" viewBox="0 0 12 12" fill={conn.isFavorite ? 'currentColor' : 'none'} aria-hidden="true">
                          <path d="M6 1.5l1.2 2.5 2.8.4-2 2 .5 2.8L6 8l-2.5 1.2.5-2.8-2-2 2.8-.4L6 1.5Z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" />
                        </svg>
                      </button>
                    </td>
                    <td style={tdStyle}>
                      <span className="text-xs font-medium" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>{conn.name}</span>
                    </td>
                    {!hiddenCols.has('vendor') && <td style={tdStyle}><VendorBadge vendor={conn.vendor} /></td>}
                    {!hiddenCols.has('environment') && <td style={tdStyle}><EnvChip env={conn.environment} /></td>}
                    {!hiddenCols.has('host') && <td style={tdStyle}><span className="text-xs" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', maxWidth: '160px', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}>{conn.host}</span></td>}
                    {!hiddenCols.has('port') && <td style={tdStyle}><span className="text-xs tabular-nums" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{conn.port || '—'}</span></td>}
                    {!hiddenCols.has('database') && <td style={tdStyle}><span className="text-xs" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{conn.database}</span></td>}
                    {!hiddenCols.has('status') && <td style={tdStyle}><StatusChip status={conn.status} /></td>}
                    {!hiddenCols.has('health') && <td style={tdStyle}><HealthChip health={conn.health} /></td>}
                    {!hiddenCols.has('latency') && <td style={tdStyle}><LatencyBadge ms={conn.latencyMs} /></td>}
                    {!hiddenCols.has('owner') && <td style={tdStyle}><span className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>{conn.owner}</span></td>}
                    {!hiddenCols.has('created') && <td style={tdStyle}><span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{conn.createdAt}</span></td>}
                    {!hiddenCols.has('lastChecked') && <td style={tdStyle}><span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{conn.lastChecked}</span></td>}
                    <td style={tdStyle} onClick={e => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        {['Test', 'Edit', 'Delete'].map(action => (
                          <button key={action} type="button"
                            className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none focus-visible:ring-1"
                            style={{ color: action === 'Delete' ? '#EF4444' : '#64748B', background: 'transparent', fontFamily: "'Inter', sans-serif" }}
                            aria-label={`${action} ${conn.name}`}
                            onMouseEnter={e => { e.currentTarget.style.background = action === 'Delete' ? 'rgba(239,68,68,0.08)' : 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = action === 'Delete' ? '#EF4444' : '#CBD5E1'; }}
                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = action === 'Delete' ? '#EF4444' : '#64748B'; }}
                          >{action}</button>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DatabasesPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [category, setCategory] = useState<CategoryFilter>('all');
  const [vendorFilter, setVendorFilter] = useState('');
  const [envFilter, setEnvFilter] = useState('');
  const [healthFilter, setHealthFilter] = useState('');
  const [connections, setConnections] = useState<DBConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedConn, setSelectedConn] = useState<DBConnection | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      setConnections(MOCK_CONNECTIONS);
      setLoading(false);
    }, 900);
    return () => clearTimeout(t);
  }, []);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1200);
  }, []);

  const handleToggleFavorite = useCallback((id: string) => {
    setConnections(cs => cs.map(c => c.id === id ? { ...c, isFavorite: !c.isFavorite } : c));
  }, []);

  const handleAddConnection = useCallback((partial: Partial<DBConnection>) => {
    const newConn: DBConnection = {
      id: `db${Date.now()}`,
      name: partial.name ?? 'new-connection',
      vendor: partial.vendor ?? 'postgresql',
      environment: partial.environment ?? 'development',
      host: partial.host ?? '',
      port: partial.port ?? 5432,
      database: partial.database ?? '',
      status: 'unknown',
      health: 'unknown',
      latencyMs: null,
      owner: partial.owner ?? 'sarah.chen',
      createdAt: partial.createdAt ?? new Date().toISOString().split('T')[0],
      lastChecked: '—',
      isFavorite: false,
      tags: partial.tags ?? [],
      sslEnabled: partial.sslEnabled ?? false,
      authMethod: partial.authMethod ?? 'Password',
    };
    setConnections(cs => [newConn, ...cs]);
  }, []);

  const filteredConnections = connections.filter(c => {
    if (category === 'favorites') return c.isFavorite;
    if (category !== 'all') return c.environment === category;
    return true;
  }).filter(c => {
    if (vendorFilter && c.vendor !== vendorFilter) return false;
    if (envFilter && c.environment !== envFilter) return false;
    if (healthFilter && c.health !== healthFilter) return false;
    return true;
  });

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}>
      {/* Background lighting */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true" style={{ zIndex: 0 }}>
        <div style={{ position: 'absolute', top: 0, left: 0, width: '600px', height: '400px', background: 'radial-gradient(ellipse at 0% 0%, rgba(37,99,235,0.06) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', top: 0, right: 0, width: '400px', height: '300px', background: 'radial-gradient(ellipse at 100% 0%, rgba(56,189,248,0.03) 0%, transparent 70%)', pointerEvents: 'none' }} />
      </div>

      <style>{`
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .animate-spin { animation: spin 1s linear infinite; }
        * { scrollbar-width: thin; scrollbar-color: #2A3647 transparent; }
        *::-webkit-scrollbar { width: 4px; height: 4px; }
        *::-webkit-scrollbar-track { background: transparent; }
        *::-webkit-scrollbar-thumb { background: #2A3647; border-radius: 2px; }
        *::-webkit-scrollbar-thumb:hover { background: #374151; }
        :focus-visible { outline: none; box-shadow: 0 0 0 2px rgba(37,99,235,0.45); border-radius: 4px; }
      `}</style>

      <div className="relative z-10 flex w-full h-full">
        {/* App Sidebar */}
        <AppSidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />

        {/* Main content */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <TopNav />

          {/* Page Header */}
          <div className="flex items-center justify-between px-6 py-4 flex-shrink-0" style={{ background: '#111827', borderBottom: '1px solid #2A3647' }}>
            <div>
              <h1 className="text-base font-semibold" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>Database Management</h1>
              <p className="text-xs mt-0.5" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>Manage enterprise database connections, credentials and health.</p>
            </div>
            <div className="flex items-center gap-2">
              {/* Secondary actions */}
              {['Import Connections', 'Export', 'Refresh Health'].map(action => (
                <button key={action} type="button"
                  onClick={action === 'Refresh Health' ? handleRefresh : undefined}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                  style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#CBD5E1'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
                >
                  {action === 'Refresh Health' && isRefreshing ? (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="animate-spin"><circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="14 8" /></svg>
                  ) : action === 'Refresh Health' ? (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M10 6A4 4 0 1 1 6 2a4 4 0 0 1 3 1.3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M10 2v2.5H7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  ) : action === 'Export' ? (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1v7M3 5l3 3 3-3M2 10h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  ) : (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 11V1M3 7l3 3 3-3M2 2h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  )}
                  {action}
                </button>
              ))}
              {/* Primary: Add Database */}
              <button type="button" onClick={() => setDrawerOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ background: '#2563EB', color: '#fff', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = '#1D4ED8'; }}
                onMouseLeave={e => { e.currentTarget.style.background = '#2563EB'; }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                Add Database
              </button>
            </div>
          </div>

          {/* Body: Left Panel + Table + Detail */}
          <div className="flex flex-1 min-h-0 overflow-hidden">
            {/* Left Panel */}
            <LeftPanel
              category={category} onCategory={setCategory}
              vendorFilter={vendorFilter} onVendorFilter={setVendorFilter}
              envFilter={envFilter} onEnvFilter={setEnvFilter}
              healthFilter={healthFilter} onHealthFilter={setHealthFilter}
              connections={connections}
            />

            {/* Main content area */}
            <main className="flex flex-col flex-1 min-w-0 overflow-hidden p-4 gap-4" aria-label="Database connections">
              {/* Summary chips */}
              <div className="flex items-center gap-3 flex-shrink-0 flex-wrap">
                {[
                  { label: 'Connected', count: connections.filter(c => c.status === 'connected').length, color: '#22C55E' },
                  { label: 'Errors', count: connections.filter(c => c.status === 'error').length, color: '#EF4444' },
                  { label: 'Warnings', count: connections.filter(c => c.status === 'warning').length, color: '#F59E0B' },
                  { label: 'Offline', count: connections.filter(c => c.status === 'disconnected').length, color: '#64748B' },
                ].map(s => (
                  <div key={s.label} className="flex items-center gap-1.5 px-2.5 py-1 rounded" style={{ background: '#1F2937', border: '1px solid #2A3647' }}>
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: s.color }} aria-hidden="true" />
                    <span className="text-xs" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>{s.label}</span>
                    <span className="text-xs font-semibold tabular-nums" style={{ color: '#F8FAFC', fontFamily: "'JetBrains Mono', monospace" }}>{loading ? '—' : s.count}</span>
                  </div>
                ))}
                {isRefreshing && (
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded" style={{ background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.2)' }}>
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" className="animate-spin" style={{ color: '#38BDF8' }}><circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="11 6" /></svg>
                    <span className="text-xs" style={{ color: '#38BDF8', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>Refreshing health…</span>
                  </div>
                )}
              </div>

              {/* Table */}
              <ConnectionTable
                connections={filteredConnections}
                loading={loading}
                onSelect={conn => setSelectedConn(prev => prev?.id === conn.id ? null : conn)}
                selectedId={selectedConn?.id ?? null}
                onToggleFavorite={handleToggleFavorite}
              />
            </main>

            {/* Detail Panel */}
            {selectedConn && (
              <DetailPanel conn={selectedConn} onClose={() => setSelectedConn(null)} />
            )}
          </div>
        </div>
      </div>

      {/* Add Database Drawer */}
      <AddDBDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} onSave={handleAddConnection} />
    </div>
  );
}
