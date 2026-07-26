'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';
import { SchemaExplorer, SchemaObject } from '@/components/ui/SchemaExplorer';
import { TransformationRuleBuilder, TransformationRule } from '@/components/ui/TransformationRuleBuilder';
import { ValidationCenter, ValidationItem } from '@/components/ui/ValidationCenter';

// ─── Types ────────────────────────────────────────────────────────────────────

type StepStatus = 'completed' | 'current' | 'pending' | 'error';
type StatusType = 'draft' | 'validated' | 'approved' | 'ready' | 'running' | 'failed' | 'completed' | 'cancelled';
type ValidationResult = 'passed' | 'warning' | 'failed';
type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

interface WorkflowStep {
  id: number;
  label: string;
  status: StepStatus;
  errorCount?: number;
}

interface DBConfig {
  type: string;
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
  sslMode: string;
}

interface DBObject {
  id: string;
  schema: string;
  name: string;
  type: 'table' | 'view' | 'function' | 'procedure' | 'sequence' | 'index' | 'trigger';
  rows?: number;
  selected: boolean;
  expanded?: boolean;
}

interface ValidationCheck {
  category: string;
  name: string;
  result: ValidationResult;
  message: string;
  recommendation?: string;
}

interface LogEntry {
  id: string;
  time: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const INITIAL_STEPS: WorkflowStep[] = [
  { id: 1, label: 'Source Database', status: 'current' },
  { id: 2, label: 'Target Database', status: 'pending' },
  { id: 3, label: 'Object Selection', status: 'pending' },
  { id: 4, label: 'Schema Mapping', status: 'pending' },
  { id: 5, label: 'Data Transformation', status: 'pending' },
  { id: 6, label: 'Validation', status: 'pending' },
  { id: 7, label: 'Risk Assessment', status: 'pending' },
  { id: 8, label: 'Execution Plan', status: 'pending' },
  { id: 9, label: 'Review & Launch', status: 'pending' },
];

const MOCK_OBJECTS: DBObject[] = [
  { id: 'o1', schema: 'public', name: 'users', type: 'table', rows: 1_240_000, selected: false },
  { id: 'o2', schema: 'public', name: 'orders', type: 'table', rows: 8_500_000, selected: false },
  { id: 'o3', schema: 'public', name: 'products', type: 'table', rows: 45_200, selected: false },
  { id: 'o4', schema: 'public', name: 'order_items', type: 'table', rows: 22_100_000, selected: false },
  { id: 'o5', schema: 'public', name: 'customers', type: 'table', rows: 980_000, selected: false },
  { id: 'o6', schema: 'public', name: 'v_active_orders', type: 'view', selected: false },
  { id: 'o7', schema: 'public', name: 'v_customer_summary', type: 'view', selected: false },
  { id: 'o8', schema: 'analytics', name: 'events', type: 'table', rows: 150_000_000, selected: false },
  { id: 'o9', schema: 'analytics', name: 'sessions', type: 'table', rows: 42_000_000, selected: false },
  { id: 'o10', schema: 'analytics', name: 'fn_calc_ltv', type: 'function', selected: false },
  { id: 'o11', schema: 'analytics', name: 'sp_refresh_summary', type: 'procedure', selected: false },
  { id: 'o12', schema: 'public', name: 'users_id_seq', type: 'sequence', selected: false },
  { id: 'o13', schema: 'public', name: 'idx_orders_user_id', type: 'index', selected: false },
  { id: 'o14', schema: 'public', name: 'trg_audit_users', type: 'trigger', selected: false },
];

const MOCK_VALIDATION: ValidationCheck[] = [
  { category: 'Connection', name: 'Source connectivity', result: 'passed', message: 'Connection established successfully.' },
  { category: 'Connection', name: 'Target connectivity', result: 'passed', message: 'Connection established successfully.' },
  { category: 'Schema', name: 'Schema compatibility', result: 'warning', message: '3 columns use Oracle-specific types.', recommendation: 'Review NUMBER(38,0) → BIGINT conversions.' },
  { category: 'Data Types', name: 'Type mapping coverage', result: 'passed', message: 'All 47 data types have valid mappings.' },
  { category: 'Data Types', name: 'Precision loss risk', result: 'warning', message: 'FLOAT(126) may lose precision in PostgreSQL DOUBLE PRECISION.', recommendation: 'Use NUMERIC(38,10) for financial columns.' },
  { category: 'Constraints', name: 'Primary key coverage', result: 'passed', message: 'All 12 tables have primary keys.' },
  { category: 'Constraints', name: 'Foreign key compatibility', result: 'failed', message: 'Circular FK dependency detected: orders → order_items → orders.', recommendation: 'Disable FK checks during migration, re-enable post-load.' },
  { category: 'Dependencies', name: 'Stored procedure dependencies', result: 'warning', message: '2 procedures reference Oracle-specific packages.', recommendation: 'Rewrite DBMS_OUTPUT calls before migration.' },
  { category: 'Permissions', name: 'Source read permissions', result: 'passed', message: 'SELECT granted on all 14 selected objects.' },
  { category: 'Permissions', name: 'Target write permissions', result: 'passed', message: 'INSERT, CREATE, TRUNCATE granted on target schema.' },
  { category: 'Storage', name: 'Target storage capacity', result: 'passed', message: 'Estimated 142 GB required, 2.1 TB available.' },
  { category: 'Performance', name: 'Index rebuild estimate', result: 'warning', message: 'Rebuilding 8 indexes may add ~45 min to total duration.', recommendation: 'Consider parallel index creation post-migration.' },
];

const MOCK_LOGS: LogEntry[] = [
  { id: 'l1', time: '16:23:01', level: 'info', message: 'Migration workspace initialized — draft mode' },
  { id: 'l2', time: '16:23:04', level: 'info', message: 'Source database configuration loaded' },
  { id: 'l3', time: '16:23:12', level: 'info', message: 'Testing source connection: oracle-prod-01.internal:1521' },
  { id: 'l4', time: '16:23:14', level: 'info', message: 'Source connection established — Oracle 19c Enterprise Edition' },
  { id: 'l5', time: '16:23:15', level: 'warn', message: 'SSL certificate validation skipped — self-signed cert detected' },
  { id: 'l6', time: '16:23:18', level: 'info', message: 'Schema discovery started — scanning 3 schemas' },
  { id: 'l7', time: '16:23:22', level: 'info', message: 'Discovered 14 objects across 2 schemas' },
  { id: 'l8', time: '16:23:25', level: 'error', message: 'Circular FK dependency detected: orders ↔ order_items' },
];

const MOCK_SQL_PREVIEW = `-- AKAAL Migration Workspace — SQL Preview
-- Generated: 2026-07-25 16:23:49 UTC
-- Source: Oracle 19c → Target: PostgreSQL 15

-- ─── Schema Creation ──────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS analytics;

-- ─── Table: public.users ──────────────────────────────────────────────────────
CREATE TABLE public.users (
  id            BIGSERIAL PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  username      VARCHAR(100) NOT NULL,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  status        SMALLINT     NOT NULL DEFAULT 1,
  profile_data  JSONB
);

CREATE INDEX idx_users_email ON public.users (email);
CREATE INDEX idx_users_status ON public.users (status);

-- ─── Table: public.orders ─────────────────────────────────────────────────────
CREATE TABLE public.orders (
  id            BIGSERIAL PRIMARY KEY,
  user_id       BIGINT       NOT NULL REFERENCES public.users(id),
  status        VARCHAR(50)  NOT NULL DEFAULT 'pending',
  total_amount  NUMERIC(18,4) NOT NULL DEFAULT 0,
  currency      CHAR(3)      NOT NULL DEFAULT 'USD',
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);`;

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

function StatusChip({ status }: { status: StatusType }) {
  const configs: Record<StatusType, { label: string; color: string; bg: string; border: string }> = {
    draft:      { label: 'Draft',      color: '#94A3B8', bg: 'rgba(148,163,184,0.12)', border: 'rgba(148,163,184,0.2)' },
    validated:  { label: 'Validated',  color: '#38BDF8', bg: 'rgba(56,189,248,0.12)',  border: 'rgba(56,189,248,0.2)' },
    approved:   { label: 'Approved',   color: '#22C55E', bg: 'rgba(34,197,94,0.12)',   border: 'rgba(34,197,94,0.2)' },
    ready:      { label: 'Ready',      color: '#A78BFA', bg: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.2)' },
    running:    { label: 'Running',    color: '#38BDF8', bg: 'rgba(56,189,248,0.12)',  border: 'rgba(56,189,248,0.2)' },
    failed:     { label: 'Failed',     color: '#EF4444', bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.2)' },
    completed:  { label: 'Completed',  color: '#22C55E', bg: 'rgba(34,197,94,0.12)',   border: 'rgba(34,197,94,0.2)' },
    cancelled:  { label: 'Cancelled',  color: '#64748B', bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.2)' },
  };
  const cfg = configs[status];
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

function ValidationBadge({ result }: { result: ValidationResult }) {
  const cfg = {
    passed:  { label: 'Passed',  color: '#22C55E', bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.2)',  icon: '✓' },
    warning: { label: 'Warning', color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.2)', icon: '!' },
    failed:  { label: 'Failed',  color: '#EF4444', bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.2)',  icon: '✕' },
  }[result];
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}
    >
      {cfg.icon} {cfg.label}
    </span>
  );
}

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
        />
      </div>
      <span className="text-xs tabular-nums flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{value}%</span>
    </div>
  );
}

function FormField({
  label, id, children, required, error, hint,
}: {
  label: string; id: string; children: React.ReactNode; required?: boolean; error?: string; hint?: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>
        {label}{required && <span className="ml-0.5" style={{ color: 'var(--akaal-error)' }} aria-hidden="true">*</span>}
      </label>
      {children}
      {error && <p className="mt-1 text-xs" style={{ color: 'var(--akaal-error)', fontFamily: "'Inter', sans-serif" }} role="alert">{error}</p>}
      {hint && !error && <p className="mt-1 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{hint}</p>}
    </div>
  );
}

function Input({
  id, type = 'text', placeholder, value, onChange, disabled, autoComplete,
}: {
  id: string; type?: string; placeholder?: string; value: string; onChange: (v: string) => void; disabled?: boolean; autoComplete?: string;
}) {
  return (
    <input
      id={id}
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      autoComplete={autoComplete}
      className="w-full text-xs rounded-md px-3 py-2 outline-none transition-all duration-150"
      style={{
        background: 'var(--akaal-input-bg)',
        border: '1px solid var(--akaal-input-border)',
        color: disabled ? 'var(--akaal-text-muted)' : 'var(--akaal-text)',
        fontFamily: type === 'password' ? "'JetBrains Mono', monospace" : "'Inter', sans-serif",
        cursor: disabled ? 'not-allowed' : 'text',
      }}
      onFocus={e => { if (!disabled) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; } }}
      onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
    />
  );
}

function Select({
  id, value, onChange, children, disabled,
}: {
  id: string; value: string; onChange: (v: string) => void; children: React.ReactNode; disabled?: boolean;
}) {
  return (
    <select
      id={id}
      value={value}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      className="w-full text-xs rounded-md px-3 py-2 outline-none transition-all duration-150 appearance-none"
      style={{
        background: 'var(--akaal-input-bg)',
        border: '1px solid var(--akaal-input-border)',
        color: disabled ? 'var(--akaal-text-muted)' : 'var(--akaal-text)',
        fontFamily: "'Inter', sans-serif",
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
      onFocus={e => { if (!disabled) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; } }}
      onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
    >
      {children}
    </select>
  );
}

function SectionCard({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-lg ${className ?? ''}`}
      style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}
    >
      {children}
    </div>
  );
}

function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
      <div>
        <h3 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{title}</h3>
        {subtitle && <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
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
        <Link href="/migrations" className="text-xs transition-colors" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >Migrations</Link>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>New Workspace</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
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
        <button
          type="button"
          onClick={() => { setNotifOpen(v => !v); setProfileOpen(false); }}
          className="relative flex items-center justify-center w-8 h-8 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: 'var(--akaal-text-muted)' }}
          aria-label="Notifications"
          aria-expanded={notifOpen}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M8 1.5a5 5 0 0 0-5 5v3l-1.5 2h13L13 9.5v-3a5 5 0 0 0-5-5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
            <path d="M6.5 13.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.3" />
          </svg>
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full" style={{ background: 'var(--akaal-error)', border: '1.5px solid var(--akaal-nav-bg)' }} aria-hidden="true" />
        </button>
      </div>
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
          <div className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50" style={{ width: '200px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }} role="menu" aria-label="User menu">
            <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>sarah.chen</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Platform Administrator</p>
            </div>
            {[
              { label: 'Profile Settings', href: '/settings' },
              { label: 'API Keys', href: '/settings' },
              { label: 'Audit Log', href: '/reports' },
              { label: 'Sign Out', href: '/sign-in' },
            ].map((item, i) => (
              <Link key={i} href={item.href} onClick={() => setProfileOpen(false)} role="menuitem" className="block w-full text-left px-3 py-2 text-xs transition-colors"
                style={{ color: item.label === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", borderBottom: i < 3 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = item.label === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-secondary)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = item.label === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)'; }}
              >{item.label}</Link>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

// ─── Workflow Step Navigator ──────────────────────────────────────────────────

function WorkflowNav({
  steps, currentStep, onStepClick,
}: {
  steps: WorkflowStep[];
  currentStep: number;
  onStepClick: (id: number) => void;
}) {
  return (
    <nav
      className="flex flex-col flex-shrink-0 overflow-y-auto"
      style={{ width: '220px', background: 'var(--akaal-nav-bg)', borderRight: '1px solid var(--akaal-nav-border)' }}
      aria-label="Migration workflow steps"
    >
      <div className="px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-nav-border)' }}>
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em' }}>Workflow</p>
      </div>
      <ol className="flex-1 py-2" role="list">
        {steps.map((step, idx) => {
          const isCurrent = step.id === currentStep;
          const isCompleted = step.status === 'completed';
          const isError = step.status === 'error';

          let dotColor = 'var(--akaal-border)';
          let dotBg = 'transparent';
          let dotBorder = 'var(--akaal-border)';
          let labelColor = 'var(--akaal-text-muted)';

          if (isCompleted) { dotColor = 'var(--akaal-success)'; dotBg = 'var(--akaal-success-bg)'; dotBorder = 'var(--akaal-success)'; labelColor = 'var(--akaal-text-muted)'; }
          if (isCurrent) { dotColor = 'var(--akaal-primary)'; dotBg = 'var(--akaal-primary-subtle)'; dotBorder = 'var(--akaal-primary)'; labelColor = 'var(--akaal-text)'; }
          if (isError) { dotColor = 'var(--akaal-error)'; dotBg = 'var(--akaal-error-bg)'; dotBorder = 'var(--akaal-error)'; labelColor = 'var(--akaal-text)'; }

          return (
            <li key={step.id}>
              <button
                type="button"
                onClick={() => onStepClick(step.id)}
                className="w-full flex items-center gap-3 px-3 py-2.5 text-left transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset group"
                style={{
                  background: isCurrent ? 'var(--akaal-primary-subtle)' : 'transparent',
                  borderLeft: isCurrent ? '2px solid var(--akaal-primary)' : isError ? '2px solid var(--akaal-error)' : '2px solid transparent',
                }}
                aria-current={isCurrent ? 'step' : undefined}
                aria-label={`Step ${step.id}: ${step.label}${isCompleted ? ' (completed)' : isCurrent ? ' (current)' : isError ? ' (has errors)' : ' (pending)'}`}
                onMouseEnter={e => { if (!isCurrent) e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { if (!isCurrent) e.currentTarget.style.background = 'transparent'; }}
              >
                {/* Step number / status dot */}
                <div
                  className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-150"
                  style={{ background: dotBg, border: `1.5px solid ${dotBorder}`, color: dotColor, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}
                  aria-hidden="true"
                >
                  {isCompleted ? (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  ) : isError ? (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M3 3l4 4M7 3l-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                  ) : (
                    step.id
                  )}
                </div>
                {/* Label */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate" style={{ color: labelColor, fontFamily: "'Inter', sans-serif" }}>{step.label}</p>
                  {isError && step.errorCount && (
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-error)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{step.errorCount} error{step.errorCount > 1 ? 's' : ''}</p>
                  )}
                  {isCurrent && !isError && (
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-primary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>In progress</p>
                  )}
                </div>
              </button>
              {/* Connector line */}
              {idx < steps.length - 1 && (
                <div className="ml-6 w-px h-2" style={{ background: isCompleted ? 'var(--akaal-success-bg)' : 'var(--akaal-border-subtle)' }} aria-hidden="true" />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

// ─── Step 1: Source Database ──────────────────────────────────────────────────

function StepSourceDB({
  config, onChange, onTest, testState,
}: {
  config: DBConfig;
  onChange: (k: keyof DBConfig, v: string | boolean) => void;
  onTest: () => void;
  testState: 'idle' | 'testing' | 'success' | 'failed';
}) {
  return (
    <div className="space-y-4">
      <SectionCard>
        <CardHeader title="Source Database Configuration" subtitle="Configure the database you are migrating from" />
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Database Type" id="src-type" required>
            <Select id="src-type" value={config.type} onChange={v => onChange('type', v)}>
              <option value="">Select database type…</option>
              <option value="oracle">Oracle Database</option>
              <option value="mssql">Microsoft SQL Server</option>
              <option value="mysql">MySQL</option>
              <option value="postgres">PostgreSQL</option>
              <option value="mongodb">MongoDB</option>
              <option value="db2">IBM Db2</option>
              <option value="sybase">SAP Sybase ASE</option>
            </Select>
          </FormField>
          <FormField label="Host / IP Address" id="src-host" required>
            <Input id="src-host" placeholder="oracle-prod-01.internal" value={config.host} onChange={v => onChange('host', v)} />
          </FormField>
          <FormField label="Port" id="src-port" required>
            <Input id="src-port" placeholder="1521" value={config.port} onChange={v => onChange('port', v)} />
          </FormField>
          <FormField label="Database / Service Name" id="src-db" required>
            <Input id="src-db" placeholder="ORCL" value={config.database} onChange={v => onChange('database', v)} />
          </FormField>
          <FormField label="Username" id="src-user" required>
            <Input id="src-user" autoComplete="username" placeholder="migration_user" value={config.username} onChange={v => onChange('username', v)} />
          </FormField>
          <FormField label="Password" id="src-pass" required>
            <Input id="src-pass" type="password" autoComplete="current-password" placeholder="••••••••••••" value={config.password} onChange={v => onChange('password', v)} />
          </FormField>
          <div className="md:col-span-2">
            <FormField label="SSL / TLS" id="src-ssl">
              <div className="flex items-center gap-6 mt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    id="src-ssl"
                    checked={config.ssl}
                    onChange={e => onChange('ssl', e.target.checked)}
                    className="w-3.5 h-3.5 rounded"
                    style={{ accentColor: '#2563EB' }}
                  />
                  <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Enable SSL/TLS encryption</span>
                </label>
                {config.ssl && (
                  <div className="flex items-center gap-2">
                    <label className="text-xs" htmlFor="src-ssl-mode" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>Mode:</label>
                    <select
                      id="src-ssl-mode"
                      value={config.sslMode}
                      onChange={e => onChange('sslMode', e.target.value)}
                      className="text-xs rounded px-2 py-1 outline-none"
                      style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
                    >
                      <option value="require">Require</option>
                      <option value="verify-ca">Verify CA</option>
                      <option value="verify-full">Verify Full</option>
                      <option value="disable">Disable</option>
                    </select>
                  </div>
                )}
              </div>
            </FormField>
          </div>
        </div>
      </SectionCard>

      {/* Connection Test */}
      <SectionCard>
        <CardHeader title="Connection Test" subtitle="Validate connectivity before proceeding" />
        <div className="p-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onTest}
              disabled={testState === 'testing'}
              className="flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{
                background: testState === 'testing' ? 'rgba(37,99,235,0.5)' : 'var(--akaal-primary)',
                color: '#fff',
                fontFamily: "'Inter', sans-serif",
                cursor: testState === 'testing' ? 'not-allowed' : 'pointer',
                opacity: testState === 'testing' ? 0.7 : 1,
              }}
              aria-busy={testState === 'testing'}
            >
              {testState === 'testing' ? (
                <>
                  <svg className="animate-spin" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                    <circle cx="6" cy="6" r="4.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
                    <path d="M6 1.5A4.5 4.5 0 0 1 10.5 6" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                  Testing Connection…
                </>
              ) : (
                <>
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                    <path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Test Connection
                </>
              )}
            </button>
            {testState === 'success' && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md" style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)' }} role="status">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6l2.5 2.5L10 3" stroke="#22C55E" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                <span className="text-xs font-medium" style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>Connected — Oracle 19c Enterprise Edition</span>
              </div>
            )}
            {testState === 'failed' && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }} role="alert">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6" stroke="#EF4444" strokeWidth="1.5" strokeLinecap="round" /></svg>
                <span className="text-xs font-medium" style={{ color: '#EF4444', fontFamily: "'JetBrains Mono', monospace" }}>Connection refused — verify host and credentials</span>
              </div>
            )}
          </div>
          {testState === 'success' && (
            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Version', value: 'Oracle 19.3.0' },
                { label: 'Latency', value: '12ms' },
                { label: 'Schemas', value: '3 accessible' },
                { label: 'Objects', value: '14 discovered' },
              ].map(item => (
                <div key={item.label} className="rounded-md px-3 py-2" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                  <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</p>
                  <p className="text-xs font-semibold mt-0.5" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Step 2: Target Database ──────────────────────────────────────────────────

function StepTargetDB({
  config, onChange, onTest, testState,
}: {
  config: DBConfig;
  onChange: (k: keyof DBConfig, v: string | boolean) => void;
  onTest: () => void;
  testState: 'idle' | 'testing' | 'success' | 'failed';
}) {
  return (
    <div className="space-y-4">
      <SectionCard>
        <CardHeader title="Target Database Configuration" subtitle="Configure the destination database" />
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField label="Database Type" id="tgt-type" required>
            <Select id="tgt-type" value={config.type} onChange={v => onChange('type', v)}>
              <option value="">Select database type…</option>
              <option value="postgres">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="mssql">Microsoft SQL Server</option>
              <option value="aurora">Amazon Aurora</option>
              <option value="alloydb">Google AlloyDB</option>
              <option value="cloudsql">Google Cloud SQL</option>
              <option value="azure-sql">Azure SQL Database</option>
            </Select>
          </FormField>
          <FormField label="Host / IP Address" id="tgt-host" required>
            <Input id="tgt-host" placeholder="postgres-prod-01.internal" value={config.host} onChange={v => onChange('host', v)} />
          </FormField>
          <FormField label="Port" id="tgt-port" required>
            <Input id="tgt-port" placeholder="5432" value={config.port} onChange={v => onChange('port', v)} />
          </FormField>
          <FormField label="Database Name" id="tgt-db" required>
            <Input id="tgt-db" placeholder="migration_target" value={config.database} onChange={v => onChange('database', v)} />
          </FormField>
          <FormField label="Username" id="tgt-user" required>
            <Input id="tgt-user" autoComplete="username" placeholder="migration_user" value={config.username} onChange={v => onChange('username', v)} />
          </FormField>
          <FormField label="Password" id="tgt-pass" required>
            <Input id="tgt-pass" type="password" autoComplete="current-password" placeholder="••••••••••••" value={config.password} onChange={v => onChange('password', v)} />
          </FormField>
        </div>
      </SectionCard>

      {/* Compatibility Summary */}
      <SectionCard>
        <CardHeader title="Compatibility Summary" subtitle="Oracle 19c → PostgreSQL 15" />
        <div className="p-4 space-y-2">
          {[
            { label: 'Data Type Compatibility', status: 'warning' as const, detail: '3 types require manual mapping' },
            { label: 'Stored Procedures', status: 'warning' as const, detail: 'PL/SQL → PL/pgSQL conversion required' },
            { label: 'Sequences', status: 'passed' as const, detail: 'Full compatibility — auto-mapped' },
            { label: 'Indexes', status: 'passed' as const, detail: 'All index types supported' },
            { label: 'Triggers', status: 'warning' as const, detail: 'Syntax differences require review' },
            { label: 'Constraints', status: 'failed' as const, detail: 'Circular FK dependency detected' },
          ].map(item => (
            <div key={item.label} className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.detail}</span>
                <ValidationBadge result={item.status === 'passed' ? 'passed' : item.status === 'warning' ? 'warning' : 'failed'} />
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Connection Test */}
      <SectionCard>
        <CardHeader title="Connection Test" />
        <div className="p-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onTest}
              disabled={testState === 'testing'}
              className="flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: testState === 'testing' ? 'rgba(37,99,235,0.5)' : 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif", cursor: testState === 'testing' ? 'not-allowed' : 'pointer', opacity: testState === 'testing' ? 0.7 : 1 }}
              aria-busy={testState === 'testing'}
            >
              {testState === 'testing' ? (
                <><svg className="animate-spin" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="6" cy="6" r="4.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" /><path d="M6 1.5A4.5 4.5 0 0 1 10.5 6" stroke="white" strokeWidth="1.5" strokeLinecap="round" /></svg>Testing…</>
              ) : 'Test Connection'}
            </button>
            {testState === 'success' && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md" style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)' }} role="status">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6l2.5 2.5L10 3" stroke="#22C55E" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                <span className="text-xs font-medium" style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>Connected — PostgreSQL 15.4</span>
              </div>
            )}
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Step 3: Object Selection ─────────────────────────────────────────────────

function StepObjectSelection({
  objects, onToggle, onToggleAll,
}: {
  objects: DBObject[];
  onToggle: (id: string) => void;
  onToggleAll: (selected: boolean) => void;
}) {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set(['public', 'analytics']));

  const filtered = objects.filter(o => {
    const matchSearch = o.name.toLowerCase().includes(search.toLowerCase()) || o.schema.toLowerCase().includes(search.toLowerCase());
    const matchType = typeFilter === 'all' || o.type === typeFilter;
    return matchSearch && matchType;
  });

  const selectedCount = objects.filter(o => o.selected).length;
  const schemas = [...new Set(filtered.map(o => o.schema))];

  const typeIcon = (type: DBObject['type']) => {
    const icons: Record<string, React.ReactNode> = {
      table: <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><rect x="1" y="2" width="10" height="8" rx="1" stroke="currentColor" strokeWidth="1.2" /><path d="M1 5h10M4 2v8" stroke="currentColor" strokeWidth="1.2" /></svg>,
      view: <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M1 6s2-4 5-4 5 4 5 4-2 4-5 4-5-4-5-4Z" stroke="currentColor" strokeWidth="1.2" /><circle cx="6" cy="6" r="1.5" stroke="currentColor" strokeWidth="1.2" /></svg>,
      function: <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 3h2l2 6 2-6h2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>,
      procedure: <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 2h6v2H3zM3 5h6v2H3zM3 8h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>,
      sequence: <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6h2l2-3 2 6 2-3h2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>,
      index: <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 3h8M2 6h6M2 9h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>,
      trigger: <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M7 1L3 7h4l-2 4 6-6H7l2-4z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /></svg>,
    };
    return icons[type] || null;
  };

  const typeColor = (type: DBObject['type']) => {
    const colors: Record<string, string> = {
      table: '#38BDF8', view: '#A78BFA', function: '#22C55E', procedure: '#F59E0B',
      sequence: '#94A3B8', index: '#64748B', trigger: '#EF4444',
    };
    return colors[type] || '#94A3B8';
  };

  return (
    <div className="space-y-4">
      <SectionCard>
        <CardHeader
          title="Object Selection"
          subtitle="Select database objects to include in this migration"
          action={
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                {selectedCount} / {objects.length} selected
              </span>
              <button
                type="button"
                onClick={() => onToggleAll(selectedCount < objects.length)}
                className="text-xs px-2.5 py-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-active-bg)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
              >
                {selectedCount < objects.length ? 'Select All' : 'Deselect All'}
              </button>
            </div>
          }
        />
        {/* Filters */}
        <div className="flex items-center gap-3 px-4 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
          <div className="relative flex-1 max-w-xs">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
              <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
              <path d="M8 8l2.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              placeholder="Search objects…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full text-xs rounded-md pl-7 pr-3 py-1.5 outline-none transition-all duration-150"
              style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
              aria-label="Search database objects"
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
            />
          </div>
          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            className="text-xs rounded-md px-2.5 py-1.5 outline-none"
            style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
            aria-label="Filter by object type"
          >
            <option value="all">All Types</option>
            <option value="table">Tables</option>
            <option value="view">Views</option>
            <option value="function">Functions</option>
            <option value="procedure">Procedures</option>
            <option value="sequence">Sequences</option>
            <option value="index">Indexes</option>
            <option value="trigger">Triggers</option>
          </select>
        </div>
        {/* Tree */}
        <div className="overflow-y-auto" style={{ maxHeight: '400px' }}>
          {schemas.map(schema => {
            const schemaObjects = filtered.filter(o => o.schema === schema);
            const isExpanded = expandedSchemas.has(schema);
            const schemaSelected = schemaObjects.filter(o => o.selected).length;
            return (
              <div key={schema}>
                {/* Schema row */}
                <button
                  type="button"
                  onClick={() => setExpandedSchemas(prev => {
                    const next = new Set(prev);
                    if (next.has(schema)) next.delete(schema); else next.add(schema);
                    return next;
                  })}
                  className="w-full flex items-center gap-2 px-4 py-2 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-inset"
                  style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                  aria-expanded={isExpanded}
                >
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" style={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s', color: 'var(--akaal-text-muted)', flexShrink: 0 }}>
                    <path d="M3 2l4 3-4 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ color: '#F59E0B', flexShrink: 0 }}>
                    <path d="M2 3h8v6H2z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
                    <path d="M2 3l2-1.5h4L10 3" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
                  </svg>
                  <span className="text-xs font-semibold" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{schema}</span>
                  <span className="text-xs ml-auto" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{schemaSelected}/{schemaObjects.length}</span>
                </button>
                {/* Objects */}
                {isExpanded && schemaObjects.map(obj => (
                  <label
                    key={obj.id}
                    className="flex items-center gap-3 px-6 py-2 cursor-pointer transition-colors"
                    style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  >
                    <input
                      type="checkbox"
                      checked={obj.selected}
                      onChange={() => onToggle(obj.id)}
                      className="w-3.5 h-3.5 rounded flex-shrink-0"
                      style={{ accentColor: 'var(--akaal-primary)' }}
                      aria-label={`Select ${obj.schema}.${obj.name}`}
                    />
                    <span style={{ color: typeColor(obj.type), flexShrink: 0 }}>{typeIcon(obj.type)}</span>
                    <span className="text-xs flex-1 truncate" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{obj.name}</span>
                    <span className="text-xs flex-shrink-0 px-1.5 py-0.5 rounded" style={{ color: typeColor(obj.type), background: `${typeColor(obj.type)}14`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{obj.type}</span>
                    {obj.rows !== undefined && (
                      <span className="text-xs flex-shrink-0 tabular-nums" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
                        {obj.rows >= 1_000_000 ? `${(obj.rows / 1_000_000).toFixed(1)}M` : obj.rows >= 1_000 ? `${(obj.rows / 1_000).toFixed(0)}K` : obj.rows} rows
                      </span>
                    )}
                  </label>
                ))}
              </div>
            );
          })}
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Step 4: Schema Mapping ───────────────────────────────────────────────────

function StepSchemaMapping() {
  const mappings = [
    { source: 'public.users.id', sourceType: 'NUMBER(10)', target: 'public.users.id', targetType: 'BIGINT', auto: true, status: 'passed' as ValidationResult },
    { source: 'public.users.email', sourceType: 'VARCHAR2(255)', target: 'public.users.email', targetType: 'VARCHAR(255)', auto: true, status: 'passed' as ValidationResult },
    { source: 'public.users.created_at', sourceType: 'DATE', target: 'public.users.created_at', targetType: 'TIMESTAMPTZ', auto: true, status: 'warning' as ValidationResult },
    { source: 'public.orders.total_amount', sourceType: 'NUMBER(18,4)', target: 'public.orders.total_amount', targetType: 'NUMERIC(18,4)', auto: true, status: 'passed' as ValidationResult },
    { source: 'public.orders.status', sourceType: 'VARCHAR2(50)', target: 'public.orders.status', targetType: 'VARCHAR(50)', auto: true, status: 'passed' as ValidationResult },
    { source: 'analytics.events.payload', sourceType: 'CLOB', target: 'analytics.events.payload', targetType: 'JSONB', auto: false, status: 'warning' as ValidationResult },
  ];

  return (
    <div className="space-y-4">
      <SectionCard>
        <CardHeader
          title="Schema Mapping"
          subtitle="Review and configure column-level mappings between source and target"
          action={
            <button type="button" className="text-xs px-2.5 py-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-2" style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-active-bg)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
              >Auto-Map All</button>
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--akaal-border)', background: 'var(--akaal-table-header)' }}>
                {['Source Column', 'Source Type', '', 'Target Column', 'Target Type', 'Status', 'Auto'].map((col, i) => (
                  <th key={i} className="px-4 py-2.5 text-left font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px', letterSpacing: '0.05em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mappings.map((m, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <td className="px-4 py-2.5" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{m.source}</td>
                  <td className="px-4 py-2.5">
                    <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'rgba(56,189,248,0.08)', color: '#38BDF8', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.sourceType}</span>
                  </td>
                  <td className="px-2 py-2.5 text-center">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-border)' }}>
                      <path d="M3 7h8M8 4l3 3-3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </td>
                  <td className="px-4 py-2.5" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{m.target}</td>
                  <td className="px-4 py-2.5">
                    <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'rgba(167,139,250,0.08)', color: '#A78BFA', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.targetType}</span>
                  </td>
                  <td className="px-4 py-2.5"><ValidationBadge result={m.status} /></td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs" style={{ color: m.auto ? '#22C55E' : '#F59E0B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.auto ? 'Auto' : 'Manual'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Step 5: Data Transformation ─────────────────────────────────────────────

function StepDataTransformation() {
  const [rules] = useState([
    { id: 'r1', name: 'Mask PII Emails', type: 'Masking', column: 'users.email', expression: 'MASK(email, \'***@***.***\')', active: true },
    { id: 'r2', name: 'Normalize Phone', type: 'Transform', column: 'users.phone', expression: 'REGEXP_REPLACE(phone, \'[^0-9]\', \'\')', active: true },
    { id: 'r3', name: 'Default Status', type: 'Default Value', column: 'orders.status', expression: '\'pending\'', active: false },
    { id: 'r4', name: 'Convert Timestamps', type: 'Type Cast', column: 'events.created_at', expression: 'CAST(created_at AS TIMESTAMPTZ)', active: true },
  ]);

  return (
    <div className="space-y-4">
      <SectionCard>
        <CardHeader
          title="Transformation Rules"
          subtitle="Define column-level transformations, masking, and default values"
          action={
            <button type="button" className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-2" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.filter = 'brightness(1.1)'; }}
              onMouseLeave={e => { e.currentTarget.style.filter = 'none'; }}
            >
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M5 2v6M2 5h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              Add Rule
            </button>
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--akaal-border)', background: 'var(--akaal-table-header)' }}>
                {['Rule Name', 'Type', 'Target Column', 'Expression / Value', 'Active'].map((col, i) => (
                  <th key={i} className="px-4 py-2.5 text-left font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px', letterSpacing: '0.05em', textTransform: 'uppercase' }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.map(rule => (
                <tr key={rule.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <td className="px-4 py-2.5 font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{rule.name}</td>
                  <td className="px-4 py-2.5">
                    <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'rgba(167,139,250,0.08)', color: '#A78BFA', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{rule.type}</span>
                  </td>
                  <td className="px-4 py-2.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{rule.column}</td>
                  <td className="px-4 py-2.5" style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{rule.expression}</td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs" style={{ color: rule.active ? '#22C55E' : 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{rule.active ? 'Active' : 'Disabled'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      {/* Preview */}
      <SectionCard>
        <CardHeader title="Transformation Preview" subtitle="Sample of transformed data (first 5 rows)" />
        <div className="p-4 overflow-x-auto">
          <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--akaal-border)' }}>
                {['id', 'email (masked)', 'phone (normalized)', 'status (default)'].map(col => (
                  <th key={col} className="px-3 py-2 text-left" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ['1', '***@***.***', '14155552671', 'pending'],
                ['2', '***@***.***', '16505550199', 'pending'],
                ['3', '***@***.***', '12125550182', 'active'],
                ['4', '***@***.***', '13105550187', 'pending'],
                ['5', '***@***.***', '18005550199', 'inactive'],
              ].map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  {row.map((cell, j) => (
                    <td key={j} className="px-3 py-2" style={{ color: j === 1 ? '#F59E0B' : 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Step 6: Validation ───────────────────────────────────────────────────────

function StepValidation({
  checks, isRunning, onRun,
}: {
  checks: ValidationCheck[];
  isRunning: boolean;
  onRun: () => void;
}) {
  const categories = [...new Set(checks.map(c => c.category))];
  const passed = checks.filter(c => c.result === 'passed').length;
  const warnings = checks.filter(c => c.result === 'warning').length;
  const failed = checks.filter(c => c.result === 'failed').length;

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Passed', value: passed, color: '#22C55E', bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.2)' },
          { label: 'Warnings', value: warnings, color: '#F59E0B', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)' },
          { label: 'Failed', value: failed, color: '#EF4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)' },
        ].map(item => (
          <div key={item.label} className="rounded-lg px-4 py-3 flex items-center justify-between" style={{ background: item.bg, border: `1px solid ${item.border}` }}>
            <span className="text-xs font-medium" style={{ color: item.color, fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
            <span className="text-xl font-bold tabular-nums" style={{ color: item.color, fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</span>
          </div>
        ))}
      </div>

      <SectionCard>
        <CardHeader
          title="Validation Checks"
          subtitle="Pre-migration validation across all categories"
          action={
            <button
              type="button"
              onClick={onRun}
              disabled={isRunning}
              className="flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: isRunning ? 'rgba(37,99,235,0.5)' : 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif", cursor: isRunning ? 'not-allowed' : 'pointer' }}
              aria-busy={isRunning}
            >
              {isRunning ? (
                <><svg className="animate-spin" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="6" cy="6" r="4.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" /><path d="M6 1.5A4.5 4.5 0 0 1 10.5 6" stroke="white" strokeWidth="1.5" strokeLinecap="round" /></svg>Running…</>
              ) : (
                <><svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 2l7 4-7 4V2z" fill="currentColor" /></svg>Run Validation</>
              )}
            </button>
          }
        />
        <div>
          {categories.map(cat => {
            const catChecks = checks.filter(c => c.category === cat);
            return (
              <div key={cat}>
                <div className="px-4 py-2" style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.1em' }}>{cat}</p>
                </div>
                {catChecks.map((check, i) => (
                  <div key={i} className="px-4 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{check.name}</p>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{check.message}</p>
                        {check.recommendation && (
                          <p className="text-xs mt-1 flex items-start gap-1.5" style={{ color: '#F59E0B', fontFamily: "'Inter', sans-serif" }}>
                            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5"><path d="M5 1v4M5 7.5v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
                            {check.recommendation}
                          </p>
                        )}
                      </div>
                      <ValidationBadge result={check.result} />
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Step 7: Risk Assessment ──────────────────────────────────────────────────

function StepRiskAssessment() {
  const risks = [
    { label: 'Overall Risk Score', value: '6.2 / 10', level: 'medium' as RiskLevel, detail: 'Moderate risk — review warnings before proceeding' },
    { label: 'Potential Downtime', value: '~4–6 hours', level: 'high' as RiskLevel, detail: 'Full table locks required for FK constraint migration' },
    { label: 'Breaking Changes', value: '3 detected', level: 'medium' as RiskLevel, detail: 'PL/SQL procedures require rewrite; CLOB → JSONB conversion' },
    { label: 'Data Loss Risk', value: 'Low', level: 'low' as RiskLevel, detail: 'All data types have valid mappings; no truncation expected' },
    { label: 'Rollback Readiness', value: 'Ready', level: 'low' as RiskLevel, detail: 'Full snapshot taken; rollback estimated at 45 minutes' },
    { label: 'CDC Compatibility', value: 'Partial', level: 'medium' as RiskLevel, detail: 'LogMiner enabled; 2 tables lack supplemental logging' },
  ];

  const riskColor = (level: RiskLevel) => ({
    low: '#22C55E', medium: '#F59E0B', high: '#EF4444', critical: '#EF4444',
  }[level]);

  const riskBg = (level: RiskLevel) => ({
    low: 'rgba(34,197,94,0.08)', medium: 'rgba(245,158,11,0.08)', high: 'rgba(239,68,68,0.08)', critical: 'rgba(239,68,68,0.12)',
  }[level]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {risks.map(risk => (
          <div key={risk.label} className="rounded-lg p-4" style={{ background: riskBg(risk.level), border: `1px solid ${riskColor(risk.level)}22` }}>
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{risk.label}</p>
              <span className="text-xs font-bold flex-shrink-0" style={{ color: riskColor(risk.level), fontFamily: "'JetBrains Mono', monospace" }}>{risk.value}</span>
            </div>
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{risk.detail}</p>
          </div>
        ))}
      </div>

      <SectionCard>
        <CardHeader title="Recommendations" subtitle="Actions to reduce migration risk" />
        <div className="p-4 space-y-3">
          {[
            { priority: 'Critical', text: 'Resolve circular FK dependency in orders/order_items before migration.', color: '#EF4444' },
            { priority: 'High', text: 'Schedule maintenance window of at least 6 hours to accommodate full table locks.', color: '#F59E0B' },
            { priority: 'High', text: 'Enable supplemental logging on events and sessions tables before starting CDC.', color: '#F59E0B' },
            { priority: 'Medium', text: 'Rewrite 2 stored procedures that use Oracle-specific DBMS_OUTPUT package.', color: '#38BDF8' },
            { priority: 'Low', text: 'Review FLOAT(126) columns in analytics schema for precision requirements.', color: 'var(--akaal-text-muted)' },
          ].map((rec, i) => (
            <div key={i} className="flex items-start gap-3">
              <span className="flex-shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded" style={{ color: rec.color, background: `${rec.color}14`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', marginTop: '1px' }}>{rec.priority}</span>
              <p className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{rec.text}</p>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Step 8: Execution Plan ───────────────────────────────────────────────────

function StepExecutionPlan() {
  const phases = [
    { phase: 1, name: 'Pre-Migration Checks', duration: '~15 min', tasks: ['Snapshot source database', 'Verify target connectivity', 'Validate permissions', 'Enable supplemental logging'] },
    { phase: 2, name: 'Schema Migration', duration: '~30 min', tasks: ['Create target schemas', 'Create tables (DDL)', 'Create sequences', 'Defer FK constraints'] },
    { phase: 3, name: 'Data Migration', duration: '~3–4 hours', tasks: ['Parallel bulk load (8 workers)', 'Batch size: 10,000 rows', 'Progress checkpoints every 5%', 'Error row capture to staging'] },
    { phase: 4, name: 'Post-Migration', duration: '~1 hour', tasks: ['Re-enable FK constraints', 'Rebuild indexes (parallel)', 'Run row count validation', 'Execute data integrity checks'] },
    { phase: 5, name: 'Cutover', duration: '~30 min', tasks: ['Stop CDC replication', 'Final delta sync', 'Switch application connections', 'Verify application health'] },
  ];

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Est. Duration', value: '~5.5 hours', color: '#38BDF8' },
          { label: 'Strategy', value: 'Bulk + CDC', color: '#A78BFA' },
          { label: 'Parallel Workers', value: '8', color: '#22C55E' },
          { label: 'Batch Size', value: '10,000 rows', color: '#F59E0B' },
        ].map(item => (
          <div key={item.label} className="rounded-lg px-4 py-3" style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}>
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</p>
            <p className="text-sm font-bold mt-1" style={{ color: item.color, fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</p>
          </div>
        ))}
      </div>

      <SectionCard>
        <CardHeader title="Execution Timeline" subtitle="Phased migration plan with estimated durations" />
        <div className="p-4 space-y-3">
          {phases.map((phase, idx) => (
            <div key={phase.phase} className="flex gap-4">
              <div className="flex flex-col items-center flex-shrink-0">
                <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: 'rgba(37,99,235,0.15)', border: '1.5px solid #2563EB', color: '#2563EB', fontFamily: "'JetBrains Mono', monospace" }}>{phase.phase}</div>
                {idx < phases.length - 1 && <div className="w-px flex-1 mt-1" style={{ background: 'rgba(37,99,235,0.2)', minHeight: '20px' }} aria-hidden="true" />}
              </div>
              <div className="flex-1 pb-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{phase.name}</p>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>{phase.duration}</span>
                </div>
                <ul className="space-y-1">
                  {phase.tasks.map((task, i) => (
                    <li key={i} className="flex items-center gap-2 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
                      <span className="w-1 h-1 rounded-full flex-shrink-0" style={{ background: 'var(--akaal-border)' }} aria-hidden="true" />
                      {task}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard>
        <CardHeader title="Rollback Strategy" />
        <div className="p-4 space-y-2">
          {[
            { label: 'Rollback Method', value: 'Point-in-time snapshot restore' },
            { label: 'Rollback Trigger', value: 'Manual or automatic on critical failure' },
            { label: 'Estimated Rollback Time', value: '~45 minutes' },
            { label: 'Checkpoint Interval', value: 'Every 5% of data migrated' },
            { label: 'Data Retention', value: 'Source data preserved for 72 hours post-migration' },
          ].map(item => (
            <div key={item.label} className="flex items-center justify-between py-1.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
              <span className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Step 9: Review & Launch ──────────────────────────────────────────────────

function StepReviewLaunch({
  onLaunch, isLaunching,
}: {
  onLaunch: () => void;
  isLaunching: boolean;
}) {
  const [confirmed, setConfirmed] = useState(false);

  const sections = [
    {
      title: 'Source Database',
      icon: '⬡',
      items: [
        { label: 'Type', value: 'Oracle 19c Enterprise Edition' },
        { label: 'Host', value: 'oracle-prod-01.internal:1521' },
        { label: 'Database', value: 'ORCL' },
        { label: 'Connection', value: 'Verified ✓' },
      ],
    },
    {
      title: 'Target Database',
      icon: '⬡',
      items: [
        { label: 'Type', value: 'PostgreSQL 15.4' },
        { label: 'Host', value: 'postgres-prod-01.internal:5432' },
        { label: 'Database', value: 'migration_target' },
        { label: 'Connection', value: 'Verified ✓' },
      ],
    },
    {
      title: 'Selected Objects',
      icon: '⬡',
      items: [
        { label: 'Tables', value: '5 selected' },
        { label: 'Views', value: '2 selected' },
        { label: 'Functions', value: '1 selected' },
        { label: 'Total Rows', value: '~222M rows' },
      ],
    },
    {
      title: 'Validation',
      icon: '⬡',
      items: [
        { label: 'Passed', value: '8 checks' },
        { label: 'Warnings', value: '3 checks' },
        { label: 'Failed', value: '1 check (FK dependency)' },
        { label: 'Status', value: 'Proceed with caution' },
      ],
    },
    {
      title: 'Risk Assessment',
      icon: '⬡',
      items: [
        { label: 'Risk Score', value: '6.2 / 10 (Medium)' },
        { label: 'Est. Downtime', value: '~4–6 hours' },
        { label: 'Data Loss Risk', value: 'Low' },
        { label: 'Rollback', value: 'Ready (~45 min)' },
      ],
    },
    {
      title: 'Execution Plan',
      icon: '⬡',
      items: [
        { label: 'Strategy', value: 'Bulk Load + CDC' },
        { label: 'Est. Duration', value: '~5.5 hours' },
        { label: 'Workers', value: '8 parallel' },
        { label: 'Batch Size', value: '10,000 rows' },
      ],
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {sections.map(section => (
          <SectionCard key={section.title}>
            <div className="px-4 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{section.title}</p>
            </div>
            <div className="px-4 py-3 space-y-2">
              {section.items.map(item => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
                  <span className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </SectionCard>
        ))}
      </div>

      {/* Confirmation */}
      <SectionCard>
        <div className="p-4">
          <div className="flex items-start gap-3 p-3 rounded-md mb-4" style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)' }} role="alert">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: '#F59E0B' }}>
              <path d="M8 2L1.5 13h13L8 2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              <path d="M8 6v3M8 11v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
            </svg>
            <div>
              <p className="text-xs font-semibold" style={{ color: '#F59E0B', fontFamily: "'Inter', sans-serif" }}>Production Migration Warning</p>
              <p className="text-xs mt-0.5" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>
                This migration will affect production databases. Estimated downtime is 4–6 hours. Ensure all stakeholders have been notified and a rollback plan is in place before proceeding.
              </p>
            </div>
          </div>
          <label className="flex items-start gap-3 cursor-pointer mb-4">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={e => setConfirmed(e.target.checked)}
              className="w-4 h-4 rounded mt-0.5 flex-shrink-0"
              style={{ accentColor: '#2563EB' }}
              aria-label="I confirm I have reviewed all migration settings and accept the risks"
            />
            <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>
              I confirm I have reviewed all migration settings, understand the risks, and have authorization to proceed with this production migration.
            </span>
          </label>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onLaunch}
              disabled={!confirmed || isLaunching}
              className="flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{
                background: !confirmed || isLaunching ? 'rgba(37,99,235,0.4)' : 'var(--akaal-primary)',
                color: !confirmed ? 'var(--akaal-text-muted)' : '#fff',
                fontFamily: "'Inter', sans-serif",
                cursor: !confirmed || isLaunching ? 'not-allowed' : 'pointer',
              }}
              aria-disabled={!confirmed || isLaunching}
              aria-busy={isLaunching}
            >
              {isLaunching ? (
                <><svg className="animate-spin" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><circle cx="7" cy="7" r="5.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" /><path d="M7 1.5A5.5 5.5 0 0 1 12.5 7" stroke="white" strokeWidth="1.5" strokeLinecap="round" /></svg>Launching Migration…</>
              ) : (
                <><svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 2l9 5-9 5V2z" fill="currentColor" /></svg>Launch Migration</>
              )}
            </button>
            <button type="button" className="px-4 py-2.5 rounded-md text-sm font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-active-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
            >Save Draft</button>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

// ─── Right Inspector Panel ────────────────────────────────────────────────────

function InspectorPanel({
  collapsed, onToggle, currentStep, selectedObjects,
}: {
  collapsed: boolean;
  onToggle: () => void;
  currentStep: number;
  selectedObjects: DBObject[];
}) {
  const stepInfo: Record<number, { title: string; content: React.ReactNode }> = {
    1: {
      title: 'Source Database',
      content: (
        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Supported Types</p>
            {['Oracle 19c', 'SQL Server 2019', 'MySQL 8.0', 'PostgreSQL 15', 'MongoDB 7.0', 'IBM Db2'].map(db => (
              <div key={db} className="flex items-center gap-2 py-1.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: '#22C55E' }} aria-hidden="true" />
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{db}</span>
              </div>
            ))}
          </div>
          <div>
            <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>SSL Modes</p>
            {['require', 'verify-ca', 'verify-full', 'disable'].map(mode => (
              <div key={mode} className="py-1">
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>{mode}</span>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    2: {
      title: 'Compatibility',
      content: (
        <div className="space-y-3">
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Oracle → PostgreSQL compatibility matrix for common data types.</p>
          {[
            { src: 'NUMBER', tgt: 'NUMERIC / BIGINT', compat: 'passed' as ValidationResult },
            { src: 'VARCHAR2', tgt: 'VARCHAR', compat: 'passed' as ValidationResult },
            { src: 'DATE', tgt: 'TIMESTAMPTZ', compat: 'warning' as ValidationResult },
            { src: 'CLOB', tgt: 'TEXT / JSONB', compat: 'warning' as ValidationResult },
            { src: 'BLOB', tgt: 'BYTEA', compat: 'passed' as ValidationResult },
            { src: 'FLOAT(126)', tgt: 'DOUBLE PRECISION', compat: 'warning' as ValidationResult },
          ].map(row => (
            <div key={row.src} className="flex items-center justify-between py-1.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <div>
                <span className="text-xs" style={{ color: '#38BDF8', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{row.src}</span>
                <span className="text-xs mx-1" style={{ color: '#374151' }}>→</span>
                <span className="text-xs" style={{ color: '#A78BFA', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{row.tgt}</span>
              </div>
              <ValidationBadge result={row.compat} />
            </div>
          ))}
        </div>
      ),
    },
    3: {
      title: 'Selection Summary',
      content: (
        <div className="space-y-3">
          <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
            <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Selected Objects</p>
            <p className="text-2xl font-bold tabular-nums" style={{ color: 'var(--akaal-primary)', fontFamily: "'JetBrains Mono', monospace" }}>{selectedObjects.filter(o => o.selected).length}</p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>of {selectedObjects.length} total objects</p>
          </div>
          {(['table', 'view', 'function', 'procedure', 'sequence', 'index', 'trigger'] as DBObject['type'][]).map(type => {
            const count = selectedObjects.filter(o => o.type === type && o.selected).length;
            const total = selectedObjects.filter(o => o.type === type).length;
            if (total === 0) return null;
            return (
              <div key={type} className="flex items-center justify-between py-1" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                <span className="text-xs capitalize" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{type}s</span>
                <span className="text-xs tabular-nums" style={{ color: count > 0 ? 'var(--akaal-text-secondary)' : 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>{count}/{total}</span>
              </div>
            );
          })}
        </div>
      ),
    },
    4: {
      title: 'Mapping Statistics',
      content: (
        <div className="space-y-3">
          {[
            { label: 'Auto-mapped', value: '44 / 47', color: '#22C55E' },
            { label: 'Manual override', value: '3 / 47', color: '#F59E0B' },
            { label: 'Unmapped', value: '0 / 47', color: 'var(--akaal-text-muted)' },
          ].map(item => (
            <div key={item.label} className="flex items-center justify-between py-1.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
              <span className="text-xs font-semibold" style={{ color: item.color, fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</span>
            </div>
          ))}
          <p className="text-xs mt-2" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>Click any row to override the automatic mapping for that column.</p>
        </div>
      ),
    },
    5: {
      title: 'Transformation Guide',
      content: (
        <div className="space-y-3">
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Available transformation types:</p>
          {[
            { type: 'Masking', desc: 'Redact sensitive data (PII, PCI)' },
            { type: 'Transform', desc: 'Apply SQL expressions to columns' },
            { type: 'Default Value', desc: 'Set fallback for NULL values' },
            { type: 'Type Cast', desc: 'Explicit type conversion' },
            { type: 'Custom SQL', desc: 'Arbitrary SQL expression' },
          ].map(item => (
            <div key={item.type} className="py-1.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{item.type}</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.desc}</p>
            </div>
          ))}
        </div>
      ),
    },
    6: {
      title: 'Validation Guide',
      content: (
        <div className="space-y-3">
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Validation runs 12 checks across 8 categories. Failed checks must be resolved before launch.</p>
          <div className="rounded-md p-3" style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <p className="text-xs font-semibold" style={{ color: '#EF4444', fontFamily: "'Inter', sans-serif" }}>1 Critical Issue</p>
            <p className="text-xs mt-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Circular FK dependency must be resolved before migration can proceed.</p>
          </div>
        </div>
      ),
    },
    7: {
      title: 'Risk Explanation',
      content: (
        <div className="space-y-3">
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Risk score is calculated from schema complexity, data volume, type compatibility, and downtime requirements.</p>
          <div>
            {[
              { label: 'Low (0–3)', color: '#22C55E' },
              { label: 'Medium (4–6)', color: '#F59E0B' },
              { label: 'High (7–8)', color: '#EF4444' },
              { label: 'Critical (9–10)', color: '#EF4444' },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-2 py-1.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: item.color }} aria-hidden="true" />
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    8: {
      title: 'Execution Details',
      content: (
        <div className="space-y-3">
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>The execution plan is optimized for your source/target configuration and selected objects.</p>
          {[
            { label: 'Checkpoints', value: 'Every 5% progress' },
            { label: 'Error handling', value: 'Skip & log by default' },
            { label: 'Retry policy', value: '3 attempts, 30s backoff' },
            { label: 'Monitoring', value: 'Real-time via Logs panel' },
          ].map(item => (
            <div key={item.label} className="py-1.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</p>
              <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</p>
            </div>
          ))}
        </div>
      ),
    },
    9: {
      title: 'Pre-Launch Checklist',
      content: (
        <div className="space-y-2">
          {[
            { label: 'Source connection verified', done: true },
            { label: 'Target connection verified', done: true },
            { label: 'Objects selected', done: true },
            { label: 'Schema mapping complete', done: true },
            { label: 'Transformations configured', done: true },
            { label: 'Validation passed', done: false },
            { label: 'Risk reviewed', done: true },
            { label: 'Execution plan reviewed', done: true },
            { label: 'Confirmation checked', done: false },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2 py-1.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <div className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: item.done ? 'rgba(34,197,94,0.12)' : 'var(--akaal-surface-elevated)', border: `1px solid ${item.done ? '#22C55E' : 'var(--akaal-border)'}` }} aria-hidden="true">
                {item.done && <svg width="8" height="8" viewBox="0 0 8 8" fill="none"><path d="M1.5 4l1.5 1.5L6.5 2.5" stroke="#22C55E" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>}
              </div>
              <span className="text-xs" style={{ color: item.done ? 'var(--akaal-text-muted)' : 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
            </div>
          ))}
        </div>
      ),
    },
  };

  const info = stepInfo[currentStep] || stepInfo[1];

  return (
    <div
      className="flex flex-col flex-shrink-0 h-full"
      style={{
        width: collapsed ? '36px' : '260px',
        background: 'var(--akaal-nav-bg)',
        borderLeft: '1px solid var(--akaal-nav-border)',
        transition: 'width 0.2s ease',
        overflow: 'hidden',
      }}
      aria-label="Inspector panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-nav-border)', minHeight: '45px' }}>
        {!collapsed && <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{info.title}</p>}
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center justify-center w-6 h-6 rounded transition-all duration-150 focus:outline-none focus-visible:ring-2 flex-shrink-0"
          style={{ color: '#64748B', marginLeft: collapsed ? 'auto' : '0' }}
          aria-label={collapsed ? 'Expand inspector' : 'Collapse inspector'}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#64748B'; }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
            <path d="M7.5 2l-4 4 4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
      {/* Content */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3">
          {info.content}
        </div>
      )}
    </div>
  );
}

// ─── Bottom Panel ─────────────────────────────────────────────────────────────

function BottomPanel({
  collapsed, onToggle, logs,
}: {
  collapsed: boolean;
  onToggle: () => void;
  logs: LogEntry[];
}) {
  const [activeTab, setActiveTab] = useState<'logs' | 'validation' | 'preview' | 'sql' | 'warnings'>('logs');
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!collapsed && activeTab === 'logs') {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, collapsed, activeTab]);

  const tabs: { id: typeof activeTab; label: string; badge?: number }[] = [
    { id: 'logs', label: 'Logs', badge: logs.length },
    { id: 'validation', label: 'Validation', badge: MOCK_VALIDATION.filter(c => c.result === 'failed').length },
    { id: 'preview', label: 'Preview' },
    { id: 'sql', label: 'SQL Preview' },
    { id: 'warnings', label: 'Warnings', badge: MOCK_VALIDATION.filter(c => c.result === 'warning').length },
  ];

  const logLevelColor = (level: LogEntry['level']) => ({
    info: 'var(--akaal-text-muted)', warn: '#F59E0B', error: '#EF4444', debug: 'var(--akaal-text-muted)',
  }[level]);

  return (
    <div
      className="flex flex-col flex-shrink-0"
      style={{
        height: collapsed ? '36px' : '220px',
        background: 'var(--akaal-nav-bg)',
        borderTop: '1px solid var(--akaal-nav-border)',
        transition: 'height 0.2s ease',
        overflow: 'hidden',
      }}
      aria-label="Bottom panel"
    >
      {/* Tab bar */}
      <div className="flex items-center flex-shrink-0" style={{ borderBottom: collapsed ? 'none' : '1px solid var(--akaal-nav-border)', height: '36px' }}>
        <div className="flex items-center flex-1 overflow-x-auto" style={{ scrollbarWidth: 'none' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => { setActiveTab(tab.id); if (collapsed) onToggle(); }}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium flex-shrink-0 transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset"
              style={{
                color: activeTab === tab.id && !collapsed ? 'var(--akaal-text)' : 'var(--akaal-text-muted)',
                borderBottom: activeTab === tab.id && !collapsed ? '2px solid var(--akaal-primary)' : '2px solid transparent',
                fontFamily: "'Inter', sans-serif",
                background: 'transparent',
              }}
              aria-selected={activeTab === tab.id}
              role="tab"
            >
              {tab.label}
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="px-1 rounded text-xs" style={{ background: tab.id === 'validation' ? 'rgba(239,68,68,0.15)' : tab.id === 'warnings' ? 'rgba(245,158,11,0.15)' : 'rgba(255,255,255,0.08)', color: tab.id === 'validation' ? '#EF4444' : tab.id === 'warnings' ? '#F59E0B' : '#94A3B8', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{tab.badge}</span>
              )}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center justify-center w-8 h-8 flex-shrink-0 transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: '#64748B' }}
          aria-label={collapsed ? 'Expand bottom panel' : 'Collapse bottom panel'}
          aria-expanded={!collapsed}
          onMouseEnter={e => { e.currentTarget.style.color = '#94A3B8'; }}
          onMouseLeave={e => { e.currentTarget.style.color = '#64748B'; }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
            <path d="M2 4.5l4 4 4-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* Panel content */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto" role="tabpanel" aria-label={`${activeTab} panel`}>
          {activeTab === 'logs' && (
            <div className="p-2 space-y-0.5">
              {logs.map(log => (
                <div key={log.id} className="flex items-start gap-3 px-2 py-1 rounded text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  <span className="flex-shrink-0 tabular-nums" style={{ color: 'var(--akaal-text-muted)', fontSize: '10px' }}>{log.time}</span>
                  <span className="flex-shrink-0 uppercase font-bold" style={{ color: logLevelColor(log.level), fontSize: '9px', letterSpacing: '0.08em', minWidth: '32px' }}>{log.level}</span>
                  <span style={{ color: log.level === 'error' ? '#EF4444' : log.level === 'warn' ? '#F59E0B' : 'var(--akaal-text-muted)', fontSize: '11px' }}>{log.message}</span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}
          {activeTab === 'validation' && (
            <div className="p-2">
              {MOCK_VALIDATION.filter(c => c.result === 'failed').map((check, i) => (
                <div key={i} className="flex items-start gap-3 px-2 py-2 rounded mb-1" style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}>
                  <ValidationBadge result="failed" />
                  <div>
                    <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{check.name}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{check.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          {activeTab === 'preview' && (
            <div className="p-3">
              <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>Select objects in Step 3 to preview transformed data here.</p>
            </div>
          )}
          {activeTab === 'sql' && (
            <div className="p-2">
              <pre className="text-xs overflow-x-auto" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', lineHeight: '1.6', whiteSpace: 'pre' }}>
                {MOCK_SQL_PREVIEW}
              </pre>
            </div>
          )}
          {activeTab === 'warnings' && (
            <div className="p-2 space-y-1">
              {MOCK_VALIDATION.filter(c => c.result === 'warning').map((check, i) => (
                <div key={i} className="flex items-start gap-3 px-2 py-2 rounded" style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}>
                  <ValidationBadge result="warning" />
                  <div>
                    <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{check.name}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{check.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function MigrationWorkspacePage() {
  const [appSidebarCollapsed, setAppSidebarCollapsed] = useState(false);
  const [steps, setSteps] = useState<WorkflowStep[]>(INITIAL_STEPS);
  const [currentStep, setCurrentStep] = useState(1);
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);
  const [bottomCollapsed, setBottomCollapsed] = useState(false);
  const [migrationStatus] = useState<StatusType>('draft');
  const [isLaunching, setIsLaunching] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>(MOCK_LOGS);
  const [isLoading, setIsLoading] = useState(true);

  // DB configs
  const [srcConfig, setSrcConfig] = useState<DBConfig>({ type: 'oracle', host: 'oracle-prod-01.internal', port: '1521', database: 'ORCL', username: 'migration_user', password: '', ssl: true, sslMode: 'require' });
  const [tgtConfig, setTgtConfig] = useState<DBConfig>({ type: 'postgres', host: '', port: '5432', database: '', username: '', password: '', ssl: true, sslMode: 'require' });
  const [srcTestState, setSrcTestState] = useState<'idle' | 'testing' | 'success' | 'failed'>('idle');
  const [tgtTestState, setTgtTestState] = useState<'idle' | 'testing' | 'success' | 'failed'>('idle');
  const [objects, setObjects] = useState<DBObject[]>(MOCK_OBJECTS);
  const [validationRunning, setValidationRunning] = useState(false);

  // Simulate initial load
  useEffect(() => {
    const t = setTimeout(() => setIsLoading(false), 800);
    return () => clearTimeout(t);
  }, []);

  const addLog = useCallback((level: LogEntry['level'], message: string) => {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    setLogs(prev => [...prev, { id: `l${Date.now()}`, time, level, message }]);
  }, []);

  const handleStepClick = useCallback((id: number) => {
    setCurrentStep(id);
    setSteps(prev => prev.map(s => ({
      ...s,
      status: s.id < id ? 'completed' : s.id === id ? 'current' : s.status === 'completed' ? 'completed' : 'pending',
    })));
  }, []);

  const handleNext = useCallback(() => {
    if (currentStep < 9) {
      setSteps(prev => prev.map(s => ({
        ...s,
        status: s.id === currentStep ? 'completed' : s.id === currentStep + 1 ? 'current' : s.status,
      })));
      setCurrentStep(prev => prev + 1);
      addLog('info', `Step ${currentStep} completed — advancing to step ${currentStep + 1}`);
    }
  }, [currentStep, addLog]);

  const handleBack = useCallback(() => {
    if (currentStep > 1) {
      setSteps(prev => prev.map(s => ({
        ...s,
        status: s.id === currentStep ? 'pending' : s.id === currentStep - 1 ? 'current' : s.status,
      })));
      setCurrentStep(prev => prev - 1);
    }
  }, [currentStep]);

  const handleSrcTest = useCallback(() => {
    setSrcTestState('testing');
    addLog('info', `Testing source connection: ${srcConfig.host}:${srcConfig.port}`);
    setTimeout(() => {
      setSrcTestState('success');
      addLog('info', 'Source connection established — Oracle 19c Enterprise Edition');
    }, 1800);
  }, [srcConfig, addLog]);

  const handleTgtTest = useCallback(() => {
    setTgtTestState('testing');
    addLog('info', `Testing target connection: ${tgtConfig.host}:${tgtConfig.port}`);
    setTimeout(() => {
      setTgtTestState('success');
      addLog('info', 'Target connection established — PostgreSQL 15.4');
    }, 1800);
  }, [tgtConfig, addLog]);

  const handleToggleObject = useCallback((id: string) => {
    setObjects(prev => prev.map(o => o.id === id ? { ...o, selected: !o.selected } : o));
  }, []);

  const handleToggleAllObjects = useCallback((selected: boolean) => {
    setObjects(prev => prev.map(o => ({ ...o, selected })));
  }, []);

  const handleRunValidation = useCallback(() => {
    setValidationRunning(true);
    addLog('info', 'Running pre-migration validation checks…');
    setTimeout(() => {
      setValidationRunning(false);
      addLog('info', 'Validation complete — 8 passed, 3 warnings, 1 failed');
      addLog('error', 'Circular FK dependency detected: orders ↔ order_items');
      setSteps(prev => prev.map(s => s.id === 6 ? { ...s, status: 'error', errorCount: 1 } : s));
    }, 2500);
  }, [addLog]);

  const handleLaunch = useCallback(() => {
    setIsLaunching(true);
    addLog('info', 'Migration launch initiated — performing final pre-flight checks');
    setTimeout(() => {
      addLog('info', 'Pre-flight checks passed — migration queued');
      addLog('info', 'Migration job ID: MIG-2026-07-25-001');
    }, 2000);
  }, [addLog]);

  const stepLabels: Record<number, string> = {
    1: 'Source Database', 2: 'Target Database', 3: 'Object Selection',
    4: 'Schema Mapping', 5: 'Data Transformation', 6: 'Validation',
    7: 'Risk Assessment', 8: 'Execution Plan', 9: 'Review & Launch',
  };

  const renderStepContent = () => {
    if (isLoading) {
      return (
        <div className="space-y-4 p-6">
          <Skeleton style={{ height: '200px', borderRadius: '8px' }} />
          <Skeleton style={{ height: '120px', borderRadius: '8px' }} />
          <Skeleton style={{ height: '80px', borderRadius: '8px' }} />
        </div>
      );
    }
    switch (currentStep) {
      case 1: return <StepSourceDB config={srcConfig} onChange={(k, v) => setSrcConfig(prev => ({ ...prev, [k]: v }))} onTest={handleSrcTest} testState={srcTestState} />;
      case 2: return <StepTargetDB config={tgtConfig} onChange={(k, v) => setTgtConfig(prev => ({ ...prev, [k]: v }))} onTest={handleTgtTest} testState={tgtTestState} />;
      case 3: return <StepObjectSelection objects={objects} onToggle={handleToggleObject} onToggleAll={handleToggleAllObjects} />;
      case 4: return <StepSchemaMapping />;
      case 5: return <StepDataTransformation />;
      case 6: return <StepValidation checks={MOCK_VALIDATION} isRunning={validationRunning} onRun={handleRunValidation} />;
      case 7: return <StepRiskAssessment />;
      case 8: return <StepExecutionPlan />;
      case 9: return <StepReviewLaunch onLaunch={handleLaunch} isLaunching={isLaunching} />;
      default: return null;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}>
      {/* Background lighting */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0" style={{ background: 'radial-gradient(ellipse 80% 50% at 10% 0%, rgba(37,99,235,0.06) 0%, transparent 60%)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0" style={{ background: 'radial-gradient(ellipse 40% 30% at 90% 0%, rgba(56,189,248,0.03) 0%, transparent 60%)' }} />

      {/* App Sidebar */}
      <AppSidebar collapsed={appSidebarCollapsed} onToggle={() => setAppSidebarCollapsed(v => !v)} />

      {/* Main content column */}
      <div className="flex flex-col flex-1 min-w-0 relative z-10">
        {/* Top Nav */}
        <TopNav />

        {/* Page Header */}
        <div
          className="flex items-center justify-between px-5 py-3 flex-shrink-0"
          style={{ background: 'var(--akaal-nav-bg)', borderBottom: '1px solid var(--akaal-nav-border)' }}
        >
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-base font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Migration Workspace</h1>
              <StatusChip status={migrationStatus} />
            </div>
            <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Create, configure and execute enterprise migration jobs.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-active-bg)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 9V3l4-1.5L10 3v6l-4 1.5L2 9Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /></svg>
              Save Draft
            </button>
            <button
              type="button"
              onClick={handleRunValidation}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-active-bg)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 2l7 4-7 4V2z" fill="currentColor" /></svg>
              Validate
            </button>
            <button
              type="button"
              onClick={() => { setCurrentStep(9); handleStepClick(9); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.filter = 'brightness(1.1)'; }}
              onMouseLeave={e => { e.currentTarget.style.filter = 'none'; }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 2l7 4-7 4V2z" fill="currentColor" /></svg>
              Launch Migration
            </button>
          </div>
        </div>

        {/* Workspace body */}
        <div className="flex flex-1 min-h-0">
          {/* Workflow Navigator */}
          <WorkflowNav steps={steps} currentStep={currentStep} onStepClick={handleStepClick} />

          {/* Main workspace */}
          <div className="flex flex-col flex-1 min-w-0">
            {/* Step header */}
            <div className="flex items-center justify-between px-5 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)', background: 'var(--akaal-surface-elevated)' }}>
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: 'var(--akaal-primary-subtle)', border: '1.5px solid var(--akaal-primary)', color: 'var(--akaal-primary)', fontFamily: "'JetBrains Mono', monospace" }} aria-hidden="true">{currentStep}</div>
                <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{stepLabels[currentStep]}</h2>
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>Step {currentStep} of 9</span>
              </div>
              <div className="flex items-center gap-2">
                {currentStep > 1 && (
                  <button
                    type="button"
                    onClick={handleBack}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                    style={{ background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-active-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                  >
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M6.5 2l-4 3 4 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    Back
                  </button>
                )}
                {currentStep < 9 && (
                  <button
                    type="button"
                    onClick={handleNext}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2"
                    style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.filter = 'brightness(1.1)'; }}
                    onMouseLeave={e => { e.currentTarget.style.filter = 'none'; }}
                  >
                    Continue
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l4 3-4 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  </button>
                )}
              </div>
            </div>

            {/* Step content + bottom panel */}
            <div className="flex flex-col flex-1 min-h-0">
              {/* Scrollable step content */}
              <div className="flex-1 overflow-y-auto p-5" style={{ minHeight: 0 }}>
                {renderStepContent()}
              </div>
              {/* Bottom panel */}
              <BottomPanel collapsed={bottomCollapsed} onToggle={() => setBottomCollapsed(v => !v)} logs={logs} />
            </div>
          </div>

          {/* Right Inspector */}
          <InspectorPanel
            collapsed={inspectorCollapsed}
            onToggle={() => setInspectorCollapsed(v => !v)}
            currentStep={currentStep}
            selectedObjects={objects}
          />
        </div>
      </div>
    </div>
  );
}
