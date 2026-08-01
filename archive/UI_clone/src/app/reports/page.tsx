'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

// ─── Types ────────────────────────────────────────────────────────────────────

type ReportCategory =
  | 'migration-reports' |'execution-reports' |'validation-reports' |'performance-reports' |'audit-logs' |'compliance' |'custom-reports' |'saved-reports' |'scheduled-reports';

type MigStatus = 'completed' | 'failed' | 'running' | 'pending' | 'paused' | 'cancelled' | 'rollback';
type ApprovalStatus = 'approved' | 'pending' | 'rejected' | 'not-required';
type ComplianceStatus = 'compliant' | 'partial' | 'non-compliant' | 'review';
type AuditStatus = 'success' | 'failure' | 'warning';
type TimeFilter = '1h' | '24h' | '7d' | '30d' | '90d' | 'custom';
type InspectorTab = 'overview' | 'metadata' | 'history' | 'permissions' | 'downloads';

interface MigrationRecord {
  id: string;
  name: string;
  source: string;
  target: string;
  owner: string;
  status: MigStatus;
  duration: string;
  rowsMigrated: string;
  completed: string;
  approvalStatus: ApprovalStatus;
}

interface AuditRecord {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  module: string;
  resource: string;
  before: string;
  after: string;
  ip: string;
  device: string;
  status: AuditStatus;
}

interface ComplianceFramework {
  id: string;
  name: string;
  status: ComplianceStatus;
  evidence: number;
  lastReview: string;
  owner: string;
  outstanding: number;
}

interface ScheduledReport {
  id: string;
  name: string;
  frequency: string;
  recipients: string;
  lastRun: string;
  nextRun: string;
  status: 'active' | 'paused' | 'failed';
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MIGRATION_HISTORY: MigrationRecord[] = [
  { id: 'MIG-2847', name: 'prod-oracle-to-postgres', source: 'Oracle 19c', target: 'PostgreSQL 15', owner: 'sarah.chen', status: 'completed', duration: '3h 12m', rowsMigrated: '48.2M', completed: '2026-07-25 14:22', approvalStatus: 'approved' },
  { id: 'MIG-2846', name: 'analytics-mysql-warehouse', source: 'MySQL 8.0', target: 'Snowflake', owner: 'james.okafor', status: 'completed', duration: '1h 55m', rowsMigrated: '12.7M', completed: '2026-07-25 11:00', approvalStatus: 'approved' },
  { id: 'MIG-2845', name: 'legacy-mssql-migration', source: 'SQL Server 2019', target: 'Azure SQL', owner: 'priya.nair', status: 'failed', duration: '32m', rowsMigrated: '2.1M', completed: '2026-07-25 13:45', approvalStatus: 'approved' },
  { id: 'MIG-2844', name: 'crm-postgres-upgrade', source: 'PostgreSQL 12', target: 'PostgreSQL 15', owner: 'alex.morgan', status: 'completed', duration: '45m', rowsMigrated: '8.4M', completed: '2026-07-24 16:30', approvalStatus: 'approved' },
  { id: 'MIG-2843', name: 'dw-redshift-consolidation', source: 'Redshift', target: 'BigQuery', owner: 'sarah.chen', status: 'running', duration: '19m', rowsMigrated: '1.2M', completed: '—', approvalStatus: 'approved' },
  { id: 'MIG-2842', name: 'iot-timescale-archive', source: 'TimescaleDB', target: 'ClickHouse', owner: 'dev.ops', status: 'paused', duration: '2h 41m', rowsMigrated: '22.8M', completed: '—', approvalStatus: 'pending' },
  { id: 'MIG-2841', name: 'finance-oracle-audit', source: 'Oracle 12c', target: 'PostgreSQL 14', owner: 'finance.team', status: 'completed', duration: '6h 04m', rowsMigrated: '91.3M', completed: '2026-07-23 09:15', approvalStatus: 'approved' },
  { id: 'MIG-2840', name: 'hr-mysql-consolidation', source: 'MySQL 5.7', target: 'MySQL 8.0', owner: 'hr.admin', status: 'completed', duration: '22m', rowsMigrated: '3.6M', completed: '2026-07-22 14:00', approvalStatus: 'approved' },
  { id: 'MIG-2839', name: 'inventory-mongo-shard', source: 'MongoDB 4.4', target: 'MongoDB 6.0', owner: 'backend.team', status: 'cancelled', duration: '8m', rowsMigrated: '0', completed: '2026-07-22 10:30', approvalStatus: 'rejected' },
  { id: 'MIG-2838', name: 'reporting-mssql-azure', source: 'SQL Server 2016', target: 'Azure SQL', owner: 'reporting.team', status: 'completed', duration: '1h 18m', rowsMigrated: '15.9M', completed: '2026-07-21 17:45', approvalStatus: 'approved' },
];

const AUDIT_RECORDS: AuditRecord[] = [
  { id: 'AUD-9921', timestamp: '2026-07-25 16:17:02', user: 'sarah.chen', action: 'MIGRATION_STARTED', module: 'Execution Center', resource: 'MIG-2847', before: 'status: pending', after: 'status: running', ip: '10.0.1.42', device: 'Chrome / macOS', status: 'success' },
  { id: 'AUD-9920', timestamp: '2026-07-25 16:14:38', user: 'james.okafor', action: 'APPROVAL_GRANTED', module: 'Migration Workspace', resource: 'MIG-2846', before: 'approval: pending', after: 'approval: approved', ip: '10.0.1.88', device: 'Firefox / Windows', status: 'success' },
  { id: 'AUD-9919', timestamp: '2026-07-25 15:58:44', user: 'priya.nair', action: 'MIGRATION_FAILED', module: 'Execution Center', resource: 'MIG-2845', before: 'status: running', after: 'status: failed', ip: '10.0.2.15', device: 'Chrome / Linux', status: 'failure' },
  { id: 'AUD-9918', timestamp: '2026-07-25 15:47:20', user: 'admin', action: 'CONFIG_CHANGED', module: 'Database Management', resource: 'DB-prod-oracle', before: 'timeout: 30s', after: 'timeout: 60s', ip: '10.0.0.1', device: 'Safari / macOS', status: 'success' },
  { id: 'AUD-9917', timestamp: '2026-07-25 15:33:05', user: 'alex.morgan', action: 'CREDENTIAL_ROTATED', module: 'Database Management', resource: 'DB-analytics-mysql', before: 'password: [masked]', after: 'password: [masked]', ip: '10.0.1.77', device: 'Chrome / Windows', status: 'success' },
  { id: 'AUD-9916', timestamp: '2026-07-25 14:22:00', user: 'sarah.chen', action: 'MIGRATION_CREATED', module: 'Migration Workspace', resource: 'MIG-2847', before: '—', after: 'status: pending', ip: '10.0.1.42', device: 'Chrome / macOS', status: 'success' },
  { id: 'AUD-9915', timestamp: '2026-07-25 13:45:11', user: 'system', action: 'HEALTH_CHECK_FAILED', module: 'Live Monitor', resource: 'DB-legacy-mssql', before: 'health: healthy', after: 'health: critical', ip: '10.0.0.2', device: 'System Agent', status: 'warning' },
  { id: 'AUD-9914', timestamp: '2026-07-25 12:00:00', user: 'dev.ops', action: 'AGENT_RESTARTED', module: 'Live Monitor', resource: 'agent-worker-04', before: 'status: offline', after: 'status: online', ip: '10.0.3.10', device: 'CLI / Linux', status: 'success' },
];

const COMPLIANCE_FRAMEWORKS: ComplianceFramework[] = [
  { id: 'gdpr', name: 'GDPR', status: 'compliant', evidence: 47, lastReview: '2026-07-01', owner: 'compliance.team', outstanding: 0 },
  { id: 'hipaa', name: 'HIPAA', status: 'partial', evidence: 31, lastReview: '2026-06-15', owner: 'security.team', outstanding: 3 },
  { id: 'pci-dss', name: 'PCI-DSS', status: 'compliant', evidence: 52, lastReview: '2026-07-10', owner: 'finance.team', outstanding: 0 },
  { id: 'soc2', name: 'SOC 2', status: 'review', evidence: 28, lastReview: '2026-05-20', owner: 'audit.team', outstanding: 7 },
  { id: 'iso27001', name: 'ISO 27001', status: 'partial', evidence: 39, lastReview: '2026-06-30', owner: 'security.team', outstanding: 2 },
];

const SCHEDULED_REPORTS: ScheduledReport[] = [
  { id: 'SCH-001', name: 'Weekly Executive Summary', frequency: 'Weekly (Mon 08:00)', recipients: 'exec-team@akaal.io', lastRun: '2026-07-21 08:00', nextRun: '2026-07-28 08:00', status: 'active' },
  { id: 'SCH-002', name: 'Daily Migration Status', frequency: 'Daily (06:00)', recipients: 'ops-team@akaal.io', lastRun: '2026-07-25 06:00', nextRun: '2026-07-26 06:00', status: 'active' },
  { id: 'SCH-003', name: 'Monthly Compliance Report', frequency: 'Monthly (1st)', recipients: 'compliance@akaal.io', lastRun: '2026-07-01 09:00', nextRun: '2026-08-01 09:00', status: 'active' },
  { id: 'SCH-004', name: 'Audit Log Export', frequency: 'Daily (23:59)', recipients: 'security@akaal.io', lastRun: '2026-07-24 23:59', nextRun: '2026-07-25 23:59', status: 'failed' },
  { id: 'SCH-005', name: 'Performance Analytics', frequency: 'Weekly (Fri 17:00)', recipients: 'engineering@akaal.io', lastRun: '2026-07-18 17:00', nextRun: '2026-07-25 17:00', status: 'paused' },
];

// Chart data
const migrationTrendData = [
  { date: 'Jul 19', total: 8, success: 7, failed: 1 },
  { date: 'Jul 20', total: 12, success: 11, failed: 1 },
  { date: 'Jul 21', total: 9, success: 8, failed: 1 },
  { date: 'Jul 22', total: 15, success: 13, failed: 2 },
  { date: 'Jul 23', total: 11, success: 10, failed: 1 },
  { date: 'Jul 24', total: 14, success: 14, failed: 0 },
  { date: 'Jul 25', total: 10, success: 8, failed: 2 },
];

const rowsMigratedData = [
  { date: 'Jul 19', rows: 42 },
  { date: 'Jul 20', rows: 78 },
  { date: 'Jul 21', rows: 55 },
  { date: 'Jul 22', rows: 91 },
  { date: 'Jul 23', rows: 63 },
  { date: 'Jul 24', rows: 112 },
  { date: 'Jul 25', rows: 84 },
];

const durationData = [
  { name: '< 30m', count: 18 },
  { name: '30m–1h', count: 12 },
  { name: '1h–3h', count: 8 },
  { name: '3h–6h', count: 4 },
  { name: '> 6h', count: 2 },
];

const adapterData = [
  { name: 'PostgreSQL', value: 28, color: '#3B82F6' },
  { name: 'MySQL', value: 18, color: '#38BDF8' },
  { name: 'Oracle', value: 14, color: '#7DD3FC' },
  { name: 'SQL Server', value: 11, color: '#60A5FA' },
  { name: 'MongoDB', value: 8, color: '#93C5FD' },
  { name: 'Other', value: 5, color: '#475569' },
];

const successRateData = [
  { date: 'Jul 19', rate: 87.5 },
  { date: 'Jul 20', rate: 91.7 },
  { date: 'Jul 21', rate: 88.9 },
  { date: 'Jul 22', rate: 86.7 },
  { date: 'Jul 23', rate: 90.9 },
  { date: 'Jul 24', rate: 100 },
  { date: 'Jul 25', rate: 80.0 },
];

const rollbackData = [
  { date: 'Jul 19', rollbacks: 1 },
  { date: 'Jul 20', rollbacks: 0 },
  { date: 'Jul 21', rollbacks: 1 },
  { date: 'Jul 22', rollbacks: 2 },
  { date: 'Jul 23', rollbacks: 0 },
  { date: 'Jul 24', rollbacks: 0 },
  { date: 'Jul 25', rollbacks: 1 },
];

// ─── Shared Components ────────────────────────────────────────────────────────

function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded ${className ?? ''}`}
      style={{
        background: 'linear-gradient(90deg, var(--akaal-surface) 25%, var(--akaal-surface-elevated) 50%, var(--akaal-surface) 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite',
        ...style,
      }}
      aria-hidden="true"
    />
  );
}

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

function StatusChip({ status }: { status: MigStatus }) {
  const configs: Record<MigStatus, { label: string; color: string; bg: string; border: string }> = {
    completed: { label: 'Completed', color: '#22C55E', bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.2)' },
    failed:    { label: 'Failed',    color: '#EF4444', bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.2)' },
    running:   { label: 'Running',   color: '#38BDF8', bg: 'rgba(56,189,248,0.12)', border: 'rgba(56,189,248,0.2)' },
    pending:   { label: 'Pending',   color: '#94A3B8', bg: 'rgba(148,163,184,0.12)', border: 'rgba(148,163,184,0.2)' },
    paused:    { label: 'Paused',    color: '#FACC15', bg: 'rgba(250,204,21,0.12)', border: 'rgba(250,204,21,0.2)' },
    cancelled: { label: 'Cancelled', color: '#64748B', bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.2)' },
    rollback:  { label: 'Rollback',  color: '#F97316', bg: 'rgba(249,115,22,0.12)', border: 'rgba(249,115,22,0.2)' },
  };
  const cfg = configs[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.04em', fontSize: '10px' }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function ApprovalChip({ status }: { status: ApprovalStatus }) {
  const configs: Record<ApprovalStatus, { label: string; color: string; bg: string }> = {
    approved:     { label: 'Approved',     color: '#22C55E', bg: 'rgba(34,197,94,0.08)' },
    pending:      { label: 'Pending',      color: '#FACC15', bg: 'rgba(250,204,21,0.08)' },
    rejected:     { label: 'Rejected',     color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
    'not-required': { label: 'N/A',        color: '#64748B', bg: 'rgba(100,116,139,0.08)' },
  };
  const cfg = configs[status];
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs" style={{ color: cfg.color, background: cfg.bg, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
      {cfg.label}
    </span>
  );
}

function ComplianceChip({ status }: { status: ComplianceStatus }) {
  const configs: Record<ComplianceStatus, { label: string; color: string; bg: string; border: string }> = {
    compliant:     { label: 'Compliant',     color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)' },
    partial:       { label: 'Partial',       color: '#FACC15', bg: 'rgba(250,204,21,0.08)',  border: 'rgba(250,204,21,0.2)' },
    'non-compliant': { label: 'Non-Compliant', color: '#EF4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)' },
    review:        { label: 'Under Review',  color: '#60A5FA', bg: 'rgba(96,165,250,0.08)',  border: 'rgba(96,165,250,0.2)' },
  };
  const cfg = configs[status];
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: cfg.color }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function AuditStatusChip({ status }: { status: AuditStatus }) {
  const configs: Record<AuditStatus, { label: string; color: string; bg: string }> = {
    success: { label: 'Success', color: '#22C55E', bg: 'rgba(34,197,94,0.08)' },
    failure: { label: 'Failure', color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
    warning: { label: 'Warning', color: '#FACC15', bg: 'rgba(250,204,21,0.08)' },
  };
  const cfg = configs[status];
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs" style={{ color: cfg.color, background: cfg.bg, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
      {cfg.label}
    </span>
  );
}

function ScheduledStatusChip({ status }: { status: ScheduledReport['status'] }) {
  const configs = {
    active: { label: 'Active', color: '#22C55E', bg: 'rgba(34,197,94,0.08)' },
    paused: { label: 'Paused', color: '#FACC15', bg: 'rgba(250,204,21,0.08)' },
    failed: { label: 'Failed', color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
  };
  const cfg = configs[status];
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs" style={{ color: cfg.color, background: cfg.bg, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
      {cfg.label}
    </span>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const navItems = [
    { href: '/dashboard', label: 'Dashboard', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/migrations', label: 'Migrations', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/execution-center', label: 'Execution', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M6 5.5l5 2.5-5 2.5V5.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { href: '/databases', label: 'Databases', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="6" ry="2" stroke="currentColor" strokeWidth="1.3" /><path d="M2 4v4c0 1.1 2.7 2 6 2s6-.9 6-2V4" stroke="currentColor" strokeWidth="1.3" /><path d="M2 8v4c0 1.1 2.7 2 6 2s6-.9 6-2V8" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/live-monitor', label: 'Live Monitor', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M4 8l2-2 2 2 2-3 2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/agents', label: 'Agents', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/reports', label: 'Reports', active: true, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/system', label: 'System', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="3" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="4.5" r="0.8" fill="currentColor" /><circle cx="4" cy="9.5" r="0.8" fill="currentColor" /><path d="M5 13h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/settings', label: 'Settings', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.4 3.4l.85.85M11.75 11.75l.85.85M3.4 12.4l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
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
                className="flex items-center gap-3 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 group"
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

// ─── Top Navigation ───────────────────────────────────────────────────────────

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
        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Platform</span>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Reports & Audit</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
          <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          placeholder="Search reports, audit events…"
          value={searchValue}
          onChange={e => setSearchValue(e.target.value)}
          className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
          style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
          aria-label="Global search"
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
        />
      </div>
      <div className="flex-1" />
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
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >{item.label}</Link>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

// ─── Left Category Navigation ─────────────────────────────────────────────────

function CategoryNav({ active, onSelect }: { active: ReportCategory; onSelect: (c: ReportCategory) => void }) {
  const categories: { id: ReportCategory; label: string; count?: number; icon: React.ReactNode }[] = [
    { id: 'migration-reports', label: 'Migration Reports', count: 79, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'execution-reports', label: 'Execution Reports', count: 34, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M5.5 4.5l4 2.5-4 2.5V4.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { id: 'validation-reports', label: 'Validation Reports', count: 22, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2.5 7l3 3L11.5 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'performance-reports', label: 'Performance Reports', count: 18, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 10l3-4 3 2 3-5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'audit-logs', label: 'Audit Logs', count: 9921, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2h7l3 3v7H2V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M9 2v3h3M4 6h6M4 8.5h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { id: 'compliance', label: 'Compliance', count: 5, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5L2 4v4c0 2.8 2.1 5.4 5 6 2.9-.6 5-3.2 5-6V4L7 1.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { id: 'custom-reports', label: 'Custom Reports', count: 7, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { id: 'saved-reports', label: 'Saved Reports', count: 12, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2h8l2 2v8H2V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M4 2v4h6V2" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { id: 'scheduled-reports', label: 'Scheduled Reports', count: 5, icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M7 4v3l2 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
  ];

  return (
    <div className="flex flex-col flex-shrink-0" style={{ width: '200px', background: 'var(--akaal-nav-bg)', borderRight: '1px solid var(--akaal-nav-border)', overflowY: 'auto' }}>
      <div className="px-3 py-3" style={{ borderBottom: '1px solid var(--akaal-nav-border)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.1em' }}>Report Categories</p>
      </div>
      <nav aria-label="Report categories" className="py-2">
        <ul className="space-y-0.5 px-2" role="list">
          {categories.map(cat => (
            <li key={cat.id}>
              <button
                type="button"
                onClick={() => onSelect(cat.id)}
                className="w-full flex items-center justify-between gap-2 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 text-left"
                style={{
                  color: active === cat.id ? 'var(--akaal-text)' : 'var(--akaal-text-muted)',
                  background: active === cat.id ? 'var(--akaal-primary-subtle)' : 'transparent',
                  borderLeft: active === cat.id ? '2px solid var(--akaal-primary)' : '2px solid transparent',
                  fontFamily: "'Inter', sans-serif",
                }}
                aria-current={active === cat.id ? 'page' : undefined}
                onMouseEnter={e => { if (active !== cat.id) { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; } }}
                onMouseLeave={e => { if (active !== cat.id) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; } }}
              >
                <span className="flex items-center gap-2">
                  <span className="flex-shrink-0" aria-hidden="true">{cat.icon}</span>
                  <span>{cat.label}</span>
                </span>
                {cat.count !== undefined && (
                  <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>
                    {cat.count > 999 ? `${(cat.count / 1000).toFixed(1)}k` : cat.count}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}

// ─── KPI Cards ────────────────────────────────────────────────────────────────

function KPICards({ loading }: { loading: boolean }) {
  const kpis = [
    { label: 'Total Migrations', value: '1,284', sub: 'All time', color: '#3B82F6', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { label: 'Successful', value: '1,197', sub: '93.2% success rate', color: '#22C55E', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2.5 7l3 3L11.5 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { label: 'Failed', value: '87', sub: '6.8% failure rate', color: '#EF4444', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M4 4l6 6M10 4l-6 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { label: 'Rollback Rate', value: '2.1%', sub: '27 rollbacks total', color: '#F97316', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7h8M3 7l3-3M3 7l3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { label: 'Success %', value: '93.2%', sub: '+1.4% vs last month', color: '#22C55E', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 9l3-4 3 2 3-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { label: 'Avg Duration', value: '1h 47m', sub: '-12m vs last month', color: '#38BDF8', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M7 4v3l2 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { label: 'Rows Migrated', value: '4.8B', sub: 'Total across all jobs', color: '#7DD3FC', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><ellipse cx="7" cy="4" rx="4" ry="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M3 4v6c0 .8 1.8 1.5 4 1.5s4-.7 4-1.5V4" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { label: 'Data Volume', value: '18.4 TB', sub: 'Total data transferred', color: '#A78BFA', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2h10v10H2V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M5 2v10M9 2v10M2 5h10M2 9h10" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { label: 'Downtime Avoided', value: '99.7%', sub: 'Zero-downtime migrations', color: '#22C55E', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5L2 4v4c0 2.8 2.1 5.4 5 6 2.9-.6 5-3.2 5-6V4L7 1.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { label: 'Approval SLA', value: '98.4%', sub: 'Within 4h SLA target', color: '#60A5FA', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2h8l2 2v8H2V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M4 6h6M4 8.5h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3 mb-5">
        {Array(10).fill(0).map((_, i) => (
          <div key={i} className="rounded-lg p-3" style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}>
            <Skeleton style={{ width: '28px', height: '28px', borderRadius: '6px', marginBottom: '8px' }} />
            <Skeleton style={{ width: '60px', height: '22px', marginBottom: '4px' }} />
            <Skeleton style={{ width: '90px', height: '10px' }} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3 mb-5">
      {kpis.map((kpi, i) => (
        <Card key={i} className="p-3">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0" style={{ background: `${kpi.color}14`, color: kpi.color }} aria-hidden="true">{kpi.icon}</div>
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", lineHeight: 1.3 }}>{kpi.label}</p>
          </div>
          <p className="text-lg font-bold tabular-nums" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{kpi.value}</p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{kpi.sub}</p>
        </Card>
      ))}
    </div>
  );
}

// ─── Analytics Charts ─────────────────────────────────────────────────────────

function AnalyticsSection({ loading, timeFilter, onTimeFilter }: { loading: boolean; timeFilter: TimeFilter; onTimeFilter: (t: TimeFilter) => void }) {
  const timeFilters: TimeFilter[] = ['1h', '24h', '7d', '30d', '90d'];
  const tooltipStyle = { background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', borderRadius: '6px', fontSize: '11px', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" };

  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Analytics</h2>
        <div className="flex items-center gap-1">
          {timeFilters.map(tf => (
            <button
              key={tf}
              type="button"
              onClick={() => onTimeFilter(tf)}
              className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{
                background: timeFilter === tf ? 'var(--akaal-primary)' : 'var(--akaal-surface)',
                color: timeFilter === tf ? '#fff' : 'var(--akaal-text-muted)',
                border: `1px solid ${timeFilter === tf ? 'var(--akaal-primary)' : 'var(--akaal-border)'}`,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px',
              }}
            >{tf}</button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {Array(6).fill(0).map((_, i) => (
            <div key={i} className="rounded-lg" style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)', height: '180px' }}>
              <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--akaal-card-border)' }}>
                <Skeleton style={{ width: '120px', height: '12px' }} />
              </div>
              <div className="p-4"><Skeleton style={{ width: '100%', height: '110px' }} /></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {/* Migration Trend */}
          <Card>
            <SectionHeader title="Migration Trend" subtitle="Daily totals — success vs failed" action={
              <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }} aria-label="Export migration trend chart">Export</button>
            } />
            <div className="p-3" style={{ height: '160px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={migrationTrendData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--akaal-border)" strokeOpacity={0.4} />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Area type="monotone" dataKey="success" stackId="1" stroke="#22C55E" fill="rgba(34,197,94,0.15)" strokeWidth={1.5} name="Success" />
                  <Area type="monotone" dataKey="failed" stackId="1" stroke="#EF4444" fill="rgba(239,68,68,0.15)" strokeWidth={1.5} name="Failed" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Daily Success Rate */}
          <Card>
            <SectionHeader title="Daily Success Rate" subtitle="% of migrations completed successfully" action={
              <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }} aria-label="Export success rate chart">Export</button>
            } />
            <div className="p-3" style={{ height: '160px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={successRateData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--akaal-border)" strokeOpacity={0.4} />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <YAxis domain={[70, 100]} tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`${v}%`, 'Success Rate']} />
                  <Line type="monotone" dataKey="rate" stroke="#3B82F6" strokeWidth={2} dot={{ r: 3, fill: '#3B82F6' }} name="Success Rate" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Rows Migrated */}
          <Card>
            <SectionHeader title="Rows Migrated" subtitle="Millions of rows per day" action={
              <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }} aria-label="Export rows migrated chart">Export</button>
            } />
            <div className="p-3" style={{ height: '160px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rowsMigratedData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--akaal-border)" strokeOpacity={0.4} />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`${v}M`, 'Rows']} />
                  <Bar dataKey="rows" fill="#38BDF8" radius={[2, 2, 0, 0]} name="Rows (M)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Migration Duration */}
          <Card>
            <SectionHeader title="Migration Duration" subtitle="Distribution by duration bucket" action={
              <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }} aria-label="Export duration chart">Export</button>
            } />
            <div className="p-3" style={{ height: '160px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={durationData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--akaal-border)" strokeOpacity={0.4} />
                  <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="count" fill="#7DD3FC" radius={[2, 2, 0, 0]} name="Migrations" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Adapter Distribution */}
          <Card>
            <SectionHeader title="Adapter Distribution" subtitle="Migrations by database vendor" action={
              <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }} aria-label="Export adapter chart">Export</button>
            } />
            <div className="p-3 flex items-center gap-4" style={{ height: '160px' }}>
              <ResponsiveContainer width="50%" height="100%">
                <PieChart>
                  <Pie data={adapterData} cx="50%" cy="50%" innerRadius={35} outerRadius={60} dataKey="value" strokeWidth={0}>
                    {adapterData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-1">
                {adapterData.map((d, i) => (
                  <div key={i} className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: d.color }} aria-hidden="true" />
                      <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{d.name}</span>
                    </div>
                    <span className="text-xs tabular-nums" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {/* Rollback Trends */}
          <Card>
            <SectionHeader title="Rollback Trends" subtitle="Daily rollback operations" action={
              <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }} aria-label="Export rollback chart">Export</button>
            } />
            <div className="p-3" style={{ height: '160px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rollbackData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--akaal-border)" strokeOpacity={0.4} />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: 'var(--akaal-text-muted)', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="rollbacks" fill="#F97316" radius={[2, 2, 0, 0]} name="Rollbacks" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

// ─── Migration History Grid ───────────────────────────────────────────────────

function MigrationHistoryGrid({ loading, onSelect }: { loading: boolean; onSelect: (id: string) => void }) {
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState<keyof MigrationRecord>('completed');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<MigStatus | 'all'>('all');
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const filtered = MIGRATION_HISTORY
    .filter(m => {
      const q = search.toLowerCase();
      const matchSearch = !q || m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q) || m.owner.toLowerCase().includes(q);
      const matchStatus = statusFilter === 'all' || m.status === statusFilter;
      return matchSearch && matchStatus;
    })
    .sort((a, b) => {
      const av = String(a[sortField]);
      const bv = String(b[sortField]);
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });

  const handleSort = (field: keyof MigrationRecord) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const SortIcon = ({ field }: { field: keyof MigrationRecord }) => (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" style={{ opacity: sortField === field ? 1 : 0.3 }}>
      {sortField === field && sortDir === 'asc'
        ? <path d="M2 7l3-4 3 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        : <path d="M2 3l3 4 3-4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />}
    </svg>
  );

  const cols: { key: keyof MigrationRecord; label: string; sortable: boolean; width?: string }[] = [
    { key: 'id', label: 'Migration ID', sortable: true, width: '100px' },
    { key: 'name', label: 'Migration Name', sortable: true },
    { key: 'source', label: 'Source', sortable: true, width: '120px' },
    { key: 'target', label: 'Target', sortable: true, width: '120px' },
    { key: 'owner', label: 'Owner', sortable: true, width: '110px' },
    { key: 'status', label: 'Status', sortable: true, width: '100px' },
    { key: 'duration', label: 'Duration', sortable: false, width: '80px' },
    { key: 'rowsMigrated', label: 'Rows', sortable: false, width: '80px' },
    { key: 'completed', label: 'Completed', sortable: true, width: '140px' },
    { key: 'approvalStatus', label: 'Approval', sortable: true, width: '90px' },
  ];

  return (
    <Card className="mb-5">
      <SectionHeader
        title="Migration History"
        subtitle={`${filtered.length} records`}
        action={
          <div className="flex items-center gap-2">
            {selected.size > 0 && (
              <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>
                Export {selected.size} selected
              </button>
            )}
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value as MigStatus | 'all')}
              className="text-xs rounded px-2 py-1 outline-none"
              style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
              aria-label="Filter by status"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="running">Running</option>
              <option value="paused">Paused</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <div className="relative">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
                <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
                <path d="M8 8l2.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
              </svg>
              <input
                type="search"
                placeholder="Search…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="text-xs rounded pl-7 pr-2 py-1 outline-none w-32"
                style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
                aria-label="Search migration history"
              />
            </div>
          </div>
        }
      />
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse', minWidth: '900px' }} role="grid" aria-label="Migration history">
          <thead>
            <tr style={{ background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)' }}>
              <th className="px-3 py-2.5 text-left w-8">
                <input
                  type="checkbox"
                  checked={selected.size === filtered.length && filtered.length > 0}
                  onChange={e => setSelected(e.target.checked ? new Set(filtered.map(m => m.id)) : new Set())}
                  className="rounded"
                  aria-label="Select all migrations"
                  style={{ accentColor: 'var(--akaal-primary)' }}
                />
              </th>
              {cols.map(col => (
                <th
                  key={col.key}
                  className="px-3 py-2.5 text-left font-medium"
                  style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px', letterSpacing: '0.05em', textTransform: 'uppercase', width: col.width, cursor: col.sortable ? 'pointer' : 'default', userSelect: 'none', whiteSpace: 'nowrap' }}
                  onClick={() => col.sortable && handleSort(col.key)}
                  aria-sort={sortField === col.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined}
                >
                  <span className="flex items-center gap-1">
                    {col.label}
                    {col.sortable && <SortIcon field={col.key} />}
                  </span>
                </th>
              ))}
              <th className="px-3 py-2.5 text-left font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array(6).fill(0).map((_, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--akaal-table-border)' }}>
                  <td className="px-3 py-2.5"><Skeleton style={{ width: '14px', height: '14px' }} /></td>
                  {cols.map((_, j) => (
                    <td key={j} className="px-3 py-2.5"><Skeleton style={{ width: j === 1 ? '140px' : '70px', height: '12px' }} /></td>
                  ))}
                  <td className="px-3 py-2.5"><Skeleton style={{ width: '60px', height: '12px' }} /></td>
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={cols.length + 2} className="px-4 py-12 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)', opacity: 0.4 }}>
                      <path d="M4 16h24M12 8l8 8-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <p className="text-sm font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>No migration records found</p>
                    <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", opacity: 0.7 }}>Adjust your search or filter criteria to find records.</p>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map(m => (
                <tr
                  key={m.id}
                  style={{ borderBottom: '1px solid var(--akaal-table-border)', background: selected.has(m.id) ? 'var(--akaal-primary-subtle)' : 'transparent', cursor: 'pointer' }}
                  onMouseEnter={e => { if (!selected.has(m.id)) (e.currentTarget as HTMLElement).style.background = 'var(--akaal-table-row-hover)'; }}
                  onMouseLeave={e => { if (!selected.has(m.id)) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  onClick={() => onSelect(m.id)}
                  role="row"
                >
                  <td className="px-3 py-2.5" onClick={e => e.stopPropagation()}>
                    <input type="checkbox" checked={selected.has(m.id)} onChange={() => toggleSelect(m.id)} className="rounded" aria-label={`Select ${m.name}`} style={{ accentColor: 'var(--akaal-primary)' }} />
                  </td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.id}</span></td>
                  <td className="px-3 py-2.5"><span className="font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{m.name}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{m.source}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{m.target}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.owner}</span></td>
                  <td className="px-3 py-2.5"><StatusChip status={m.status} /></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace', fontSize: '10px" }}>{m.duration}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.rowsMigrated}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{m.completed}</span></td>
                  <td className="px-3 py-2.5"><ApprovalChip status={m.approvalStatus} /></td>
                  <td className="px-3 py-2.5" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-1">
                      <button type="button" className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none focus-visible:ring-2" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }}
                        onClick={() => onSelect(m.id)} aria-label={`View ${m.name}`}
                        onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                        onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                      >View</button>
                      <button type="button" className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none focus-visible:ring-2" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }}
                        aria-label={`Export ${m.name}`}
                        onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                        onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                      >Export</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Executive Summary ────────────────────────────────────────────────────────

function ExecutiveSummary({ loading }: { loading: boolean }) {
  const insights = [
    { label: 'Platform Health', value: 'Operational', detail: 'All 9 platform services are online and responding within SLA thresholds.', color: '#22C55E', icon: '●' },
    { label: 'Migration Efficiency', value: '93.2%', detail: 'Success rate is 1.4% above last month. Zero-downtime migrations account for 99.7% of all jobs.', color: '#3B82F6', icon: '▲' },
    { label: 'Current Risks', value: '2 Active', detail: 'HIPAA compliance has 3 outstanding tasks. SOC 2 audit review is overdue by 14 days.', color: '#FACC15', icon: '⚠' },
    { label: 'Recent Improvements', value: '+1.4% Success', detail: 'Rollback rate decreased from 3.2% to 2.1% following agent stability improvements deployed Jul 20.', color: '#22C55E', icon: '↑' },
    { label: 'Operational Insights', value: '4.8B Rows', detail: 'Total rows migrated this quarter. Peak throughput of 248M rows/day recorded on Jul 24.', color: '#38BDF8', icon: '◆' },
  ];

  return (
    <Card className="mb-5">
      <SectionHeader title="Executive Summary" subtitle="Platform-wide operational overview" action={
        <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>Generate PDF</button>
      } />
      {loading ? (
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {Array(5).fill(0).map((_, i) => (
            <div key={i} className="p-3 rounded-md" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <Skeleton style={{ width: '80px', height: '10px', marginBottom: '6px' }} />
              <Skeleton style={{ width: '60px', height: '18px', marginBottom: '6px' }} />
              <Skeleton style={{ width: '100%', height: '10px' }} />
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {insights.map((ins, i) => (
            <div key={i} className="p-3 rounded-md" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-bold" style={{ color: ins.color, fontFamily: "'JetBrains Mono', monospace" }}>{ins.icon}</span>
                <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{ins.label}</p>
              </div>
              <p className="text-sm font-bold mb-1" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{ins.value}</p>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{ins.detail}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ─── Audit Logs ───────────────────────────────────────────────────────────────

function AuditLogsPanel({ loading }: { loading: boolean }) {
  const [search, setSearch] = useState('');
  const [moduleFilter, setModuleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState<AuditStatus | 'all'>('all');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const filtered = AUDIT_RECORDS.filter(r => {
    const q = search.toLowerCase();
    const matchSearch = !q || r.user.toLowerCase().includes(q) || r.action.toLowerCase().includes(q) || r.resource.toLowerCase().includes(q);
    const matchModule = moduleFilter === 'all' || r.module === moduleFilter;
    const matchStatus = statusFilter === 'all' || r.status === statusFilter;
    return matchSearch && matchModule && matchStatus;
  });

  const modules = Array.from(new Set(AUDIT_RECORDS.map(r => r.module)));

  return (
    <Card className="mb-5">
      <SectionHeader
        title="Audit Logs"
        subtitle="Immutable platform audit trail"
        action={
          <div className="flex items-center gap-2">
            <select value={moduleFilter} onChange={e => setModuleFilter(e.target.value)} className="text-xs rounded px-2 py-1 outline-none" style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }} aria-label="Filter by module">
              <option value="all">All Modules</option>
              {modules.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as AuditStatus | 'all')} className="text-xs rounded px-2 py-1 outline-none" style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }} aria-label="Filter by status">
              <option value="all">All Status</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
              <option value="warning">Warning</option>
            </select>
            <div className="relative">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
                <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
                <path d="M8 8l2.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
              </svg>
              <input type="search" placeholder="Search audit…" value={search} onChange={e => setSearch(e.target.value)} className="text-xs rounded pl-7 pr-2 py-1 outline-none w-32" style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }} aria-label="Search audit logs" />
            </div>
            <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>Export</button>
          </div>
        }
      />
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse', minWidth: '900px' }} role="grid" aria-label="Audit logs">
          <thead>
            <tr style={{ background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)' }}>
              {['Timestamp', 'User', 'Action', 'Module', 'Resource', 'Before', 'After', 'IP Address', 'Device', 'Status'].map(col => (
                <th key={col} className="px-3 py-2.5 text-left font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px', letterSpacing: '0.05em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array(5).fill(0).map((_, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--akaal-table-border)' }}>
                  {Array(10).fill(0).map((_, j) => (
                    <td key={j} className="px-3 py-2.5"><Skeleton style={{ width: j === 2 ? '120px' : '70px', height: '12px' }} /></td>
                  ))}
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-4 py-12 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)', opacity: 0.4 }}>
                      <path d="M6 4h14l6 6v18H6V4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /><path d="M20 4v6h6M10 14h12M10 19h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                    <p className="text-sm font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>No audit events found</p>
                    <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", opacity: 0.7 }}>Adjust your filters to find audit records.</p>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map(r => (
                <React.Fragment key={r.id}>
                  <tr
                    style={{ borderBottom: expandedRow === r.id ? 'none' : '1px solid var(--akaal-table-border)', cursor: 'pointer' }}
                    onClick={() => setExpandedRow(expandedRow === r.id ? null : r.id)}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-table-row-hover)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                    role="row"
                    aria-expanded={expandedRow === r.id}
                  >
                    <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', whiteSpace: 'nowrap' }}>{r.timestamp}</span></td>
                    <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{r.user}</span></td>
                    <td className="px-3 py-2.5"><span className="font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{r.action}</span></td>
                    <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{r.module}</span></td>
                    <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{r.resource}</span></td>
                    <td className="px-3 py-2.5 max-w-xs"><span className="truncate block" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', maxWidth: '100px' }}>{r.before}</span></td>
                    <td className="px-3 py-2.5 max-w-xs"><span className="truncate block" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', maxWidth: '100px' }}>{r.after}</span></td>
                    <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{r.ip}</span></td>
                    <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", whiteSpace: 'nowrap' }}>{r.device}</span></td>
                    <td className="px-3 py-2.5"><AuditStatusChip status={r.status} /></td>
                  </tr>
                  {expandedRow === r.id && (
                    <tr style={{ borderBottom: '1px solid var(--akaal-table-border)' }}>
                      <td colSpan={10} className="px-4 py-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                          <div><p className="font-medium mb-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Audit ID</p><p style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{r.id}</p></div>
                          <div><p className="font-medium mb-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Before State</p><p style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{r.before}</p></div>
                          <div><p className="font-medium mb-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>After State</p><p style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{r.after}</p></div>
                          <div><p className="font-medium mb-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Device</p><p style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{r.device}</p></div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Compliance Panel ─────────────────────────────────────────────────────────

function CompliancePanel({ loading }: { loading: boolean }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <Card className="mb-5">
      <SectionHeader title="Compliance Readiness" subtitle="Framework compliance status and evidence" action={
        <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>Export Evidence</button>
      } />
      {loading ? (
        <div className="p-4 space-y-3">
          {Array(5).fill(0).map((_, i) => (
            <div key={i} className="p-3 rounded-md" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <div className="flex items-center justify-between">
                <Skeleton style={{ width: '80px', height: '14px' }} />
                <Skeleton style={{ width: '70px', height: '20px', borderRadius: '4px' }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 space-y-2">
          {COMPLIANCE_FRAMEWORKS.map(fw => (
            <div key={fw.id}>
              <button
                type="button"
                className="w-full text-left p-3 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ background: expanded === fw.id ? 'var(--akaal-surface-elevated)' : 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}
                onClick={() => setExpanded(expanded === fw.id ? null : fw.id)}
                aria-expanded={expanded === fw.id}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", minWidth: '80px' }}>{fw.name}</span>
                    <ComplianceChip status={fw.status} />
                    <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{fw.evidence} evidence items</span>
                    {fw.outstanding > 0 && (
                      <span className="text-xs px-2 py-0.5 rounded" style={{ color: '#FACC15', background: 'rgba(250,204,21,0.08)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{fw.outstanding} outstanding</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Owner: {fw.owner}</span>
                    <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>Reviewed: {fw.lastReview}</span>
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)', transform: expanded === fw.id ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                      <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                    </svg>
                  </div>
                </div>
              </button>
              {expanded === fw.id && (
                <div className="mx-0.5 p-4 rounded-b-md" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)', borderTop: 'none' }}>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                    <div>
                      <p className="font-medium mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Status</p>
                      <ComplianceChip status={fw.status} />
                    </div>
                    <div>
                      <p className="font-medium mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Evidence Items</p>
                      <p style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{fw.evidence} collected</p>
                    </div>
                    <div>
                      <p className="font-medium mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Last Review</p>
                      <p style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{fw.lastReview}</p>
                    </div>
                    <div>
                      <p className="font-medium mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Outstanding Tasks</p>
                      <p style={{ color: fw.outstanding > 0 ? '#FACC15' : '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>{fw.outstanding > 0 ? `${fw.outstanding} tasks pending` : 'All tasks complete'}</p>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center gap-2">
                    <button type="button" className="text-xs px-3 py-1.5 rounded transition-all duration-150" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}>View Evidence</button>
                    <button type="button" className="text-xs px-3 py-1.5 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>Export Report</button>
                    {fw.outstanding > 0 && (
                      <button type="button" className="text-xs px-3 py-1.5 rounded transition-all duration-150" style={{ color: '#FACC15', background: 'rgba(250,204,21,0.08)', border: '1px solid rgba(250,204,21,0.2)', fontFamily: "'Inter', sans-serif" }}>Review Tasks</button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ─── Scheduled Reports ────────────────────────────────────────────────────────

function ScheduledReportsPanel({ loading }: { loading: boolean }) {
  return (
    <Card className="mb-5">
      <SectionHeader title="Scheduled Reports" subtitle="Automated report delivery" action={
        <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}>+ Schedule Report</button>
      } />
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse', minWidth: '700px' }} role="grid" aria-label="Scheduled reports">
          <thead>
            <tr style={{ background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)' }}>
              {['Report Name', 'Frequency', 'Recipients', 'Last Run', 'Next Run', 'Status', 'Actions'].map(col => (
                <th key={col} className="px-3 py-2.5 text-left font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px', letterSpacing: '0.05em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array(4).fill(0).map((_, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--akaal-table-border)' }}>
                  {Array(7).fill(0).map((_, j) => (
                    <td key={j} className="px-3 py-2.5"><Skeleton style={{ width: j === 0 ? '140px' : '80px', height: '12px' }} /></td>
                  ))}
                </tr>
              ))
            ) : SCHEDULED_REPORTS.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)', opacity: 0.4 }}>
                      <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="1.5" /><path d="M16 9v7l4 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                    <p className="text-sm font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>No scheduled reports configured</p>
                    <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", opacity: 0.7 }}>Schedule a report to automate delivery to your team.</p>
                  </div>
                </td>
              </tr>
            ) : (
              SCHEDULED_REPORTS.map(r => (
                <tr key={r.id} style={{ borderBottom: '1px solid var(--akaal-table-border)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-table-row-hover)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <td className="px-3 py-2.5"><span className="font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{r.name}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{r.frequency}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{r.recipients}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{r.lastRun}</span></td>
                  <td className="px-3 py-2.5"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{r.nextRun}</span></td>
                  <td className="px-3 py-2.5"><ScheduledStatusChip status={r.status} /></td>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-1">
                      <button type="button" className="px-2 py-1 rounded text-xs transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }}
                        onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                        onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                      >{r.status === 'paused' ? 'Resume' : 'Pause'}</button>
                      <button type="button" className="px-2 py-1 rounded text-xs transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', fontFamily: "'Inter', sans-serif" }}
                        onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                        onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                      >Edit</button>
                      <button type="button" className="px-2 py-1 rounded text-xs transition-all duration-150" style={{ color: 'var(--akaal-error)', background: 'var(--akaal-error-bg)', fontFamily: "'Inter', sans-serif" }}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Report Builder ───────────────────────────────────────────────────────────

function ReportBuilder({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(1);
  const [reportName, setReportName] = useState('');
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [dateRange, setDateRange] = useState('7d');
  const [chartType, setChartType] = useState('bar');
  const [groupBy, setGroupBy] = useState('day');

  const metrics = ['Total Migrations', 'Success Rate', 'Failure Rate', 'Rows Migrated', 'Avg Duration', 'Rollback Rate', 'Throughput', 'Downtime', 'Approval SLA'];

  const toggleMetric = (m: string) => {
    setSelectedMetrics(prev => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }} role="dialog" aria-modal="true" aria-label="Report Builder">
      <div className="rounded-xl overflow-hidden flex flex-col" style={{ width: '600px', maxHeight: '80vh', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 24px 64px rgba(0,0,0,0.5)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
          <div>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Report Builder</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Step {step} of 3 — {step === 1 ? 'Configure' : step === 2 ? 'Customize' : 'Preview & Save'}</p>
          </div>
          <button type="button" onClick={onClose} className="w-7 h-7 rounded-md flex items-center justify-center transition-all duration-150" style={{ color: 'var(--akaal-text-muted)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            aria-label="Close report builder"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
          </button>
        </div>

        {/* Progress */}
        <div className="px-5 py-3" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
          <div className="flex items-center gap-2">
            {[1, 2, 3].map(s => (
              <React.Fragment key={s}>
                <div className="flex items-center gap-1.5">
                  <div className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: step >= s ? 'var(--akaal-primary)' : 'var(--akaal-surface-elevated)', color: step >= s ? '#fff' : 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>{s}</div>
                  <span className="text-xs" style={{ color: step >= s ? 'var(--akaal-text)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{s === 1 ? 'Configure' : s === 2 ? 'Customize' : 'Preview'}</span>
                </div>
                {s < 3 && <div className="flex-1 h-px" style={{ background: step > s ? 'var(--akaal-primary)' : 'var(--akaal-border)' }} />}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Report Name</label>
                <input type="text" value={reportName} onChange={e => setReportName(e.target.value)} placeholder="e.g. Weekly Migration Summary" className="w-full text-xs rounded-md px-3 py-2 outline-none" style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
                  onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; }}
                  onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Date Range</label>
                <select value={dateRange} onChange={e => setDateRange(e.target.value)} className="w-full text-xs rounded-md px-3 py-2 outline-none" style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
                  <option value="1d">Last 24 hours</option>
                  <option value="7d">Last 7 days</option>
                  <option value="30d">Last 30 days</option>
                  <option value="90d">Last 90 days</option>
                  <option value="custom">Custom range</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Metrics</label>
                <div className="grid grid-cols-3 gap-2">
                  {metrics.map(m => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => toggleMetric(m)}
                      className="text-left px-2 py-1.5 rounded text-xs transition-all duration-150 focus:outline-none focus-visible:ring-2"
                      style={{
                        background: selectedMetrics.includes(m) ? 'var(--akaal-primary-subtle)' : 'var(--akaal-surface-elevated)',
                        border: `1px solid ${selectedMetrics.includes(m) ? 'var(--akaal-primary)' : 'var(--akaal-border)'}`,
                        color: selectedMetrics.includes(m) ? 'var(--akaal-text)' : 'var(--akaal-text-muted)',
                        fontFamily: "'Inter', sans-serif",
                      }}
                    >{m}</button>
                  ))}
                </div>
              </div>
            </div>
          )}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Chart Type</label>
                <div className="flex items-center gap-2">
                  {['bar', 'line', 'area', 'pie'].map(ct => (
                    <button key={ct} type="button" onClick={() => setChartType(ct)} className="px-3 py-1.5 rounded text-xs transition-all duration-150 capitalize" style={{ background: chartType === ct ? 'var(--akaal-primary)' : 'var(--akaal-surface-elevated)', color: chartType === ct ? '#fff' : 'var(--akaal-text-muted)', border: `1px solid ${chartType === ct ? 'var(--akaal-primary)' : 'var(--akaal-border)'}`, fontFamily: "'Inter', sans-serif" }}>{ct}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Group By</label>
                <select value={groupBy} onChange={e => setGroupBy(e.target.value)} className="w-full text-xs rounded-md px-3 py-2 outline-none" style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
                  <option value="hour">Hour</option>
                  <option value="day">Day</option>
                  <option value="week">Week</option>
                  <option value="month">Month</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Columns to Include</label>
                <div className="grid grid-cols-2 gap-2">
                  {['Migration ID', 'Migration Name', 'Source', 'Target', 'Owner', 'Status', 'Duration', 'Rows Migrated', 'Completed', 'Approval Status'].map(col => (
                    <label key={col} className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
                      <input type="checkbox" defaultChecked className="rounded" style={{ accentColor: 'var(--akaal-primary)' }} />
                      {col}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
          {step === 3 && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <p className="text-xs font-semibold mb-3" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Report Preview</p>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Name</span><span style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{reportName || 'Untitled Report'}</span></div>
                  <div className="flex justify-between"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Date Range</span><span style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{dateRange}</span></div>
                  <div className="flex justify-between"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Metrics</span><span style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{selectedMetrics.length > 0 ? selectedMetrics.join(', ') : 'None selected'}</span></div>
                  <div className="flex justify-between"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Chart Type</span><span style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{chartType}</span></div>
                  <div className="flex justify-between"><span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Group By</span><span style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{groupBy}</span></div>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Schedule (optional)</label>
                <select className="w-full text-xs rounded-md px-3 py-2 outline-none" style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
                  <option value="">No schedule — run manually</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4" style={{ borderTop: '1px solid var(--akaal-border)' }}>
          <button type="button" onClick={() => step > 1 ? setStep(s => s - 1) : onClose()} className="text-xs px-3 py-1.5 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>
            {step > 1 ? 'Back' : 'Cancel'}
          </button>
          <button type="button" onClick={() => step < 3 ? setStep(s => s + 1) : onClose()} className="text-xs px-4 py-1.5 rounded transition-all duration-150" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}>
            {step < 3 ? 'Next' : 'Generate Report'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Inspector Panel ──────────────────────────────────────────────────────────

function InspectorPanel({ migrationId, onClose }: { migrationId: string; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<InspectorTab>('overview');
  const migration = MIGRATION_HISTORY.find(m => m.id === migrationId);
  if (!migration) return null;

  const tabs: { id: InspectorTab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'metadata', label: 'Metadata' },
    { id: 'history', label: 'History' },
    { id: 'permissions', label: 'Permissions' },
    { id: 'downloads', label: 'Downloads' },
  ];

  return (
    <div
      className="flex flex-col flex-shrink-0"
      style={{ width: '360px', background: 'var(--akaal-surface)', borderLeft: '1px solid var(--akaal-border)', height: '100%', overflow: 'hidden' }}
      role="complementary"
      aria-label="Migration inspector"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        <div>
          <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{migration.id}</p>
          <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", maxWidth: '260px' }}>{migration.name}</p>
        </div>
        <button type="button" onClick={onClose} className="w-7 h-7 rounded-md flex items-center justify-center transition-all duration-150" style={{ color: 'var(--akaal-text-muted)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          aria-label="Close inspector"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex flex-shrink-0 overflow-x-auto" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className="px-3 py-2.5 text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 flex-shrink-0"
            style={{
              color: activeTab === tab.id ? 'var(--akaal-text)' : 'var(--akaal-text-muted)',
              borderBottom: activeTab === tab.id ? '2px solid var(--akaal-primary)' : '2px solid transparent',
              fontFamily: "'Inter', sans-serif",
            }}
            aria-selected={activeTab === tab.id}
          >{tab.label}</button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-3">
            <div className="p-3 rounded-md" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Status</p>
                <StatusChip status={migration.status} />
              </div>
              <div className="space-y-2 text-xs">
                {[
                  { label: 'Source', value: migration.source },
                  { label: 'Target', value: migration.target },
                  { label: 'Owner', value: migration.owner },
                  { label: 'Duration', value: migration.duration },
                  { label: 'Rows Migrated', value: migration.rowsMigrated },
                  { label: 'Completed', value: migration.completed },
                ].map(item => (
                  <div key={item.label} className="flex justify-between gap-2">
                    <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
                    <span style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', textAlign: 'right' }}>{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="p-3 rounded-md" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Approval</p>
              <ApprovalChip status={migration.approvalStatus} />
            </div>
          </div>
        )}
        {activeTab === 'metadata' && (
          <div className="space-y-2 text-xs">
            {[
              { label: 'Migration ID', value: migration.id },
              { label: 'Created By', value: migration.owner },
              { label: 'Strategy', value: 'Full Load + CDC' },
              { label: 'Batch Size', value: '10,000 rows' },
              { label: 'Parallel Workers', value: '4' },
              { label: 'Checkpoints', value: '12 saved' },
              { label: 'Retry Count', value: '0' },
              { label: 'Tags', value: 'production, critical' },
            ].map(item => (
              <div key={item.label} className="flex justify-between gap-2 py-1.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
                <span style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{item.value}</span>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'history' && (
          <div className="space-y-2">
            {[
              { time: '14:22:00', event: 'Migration Created', color: '#3B82F6' },
              { time: '14:22:15', event: 'Pre-flight Checks Passed', color: '#22C55E' },
              { time: '14:23:00', event: 'Approval Requested', color: '#FACC15' },
              { time: '14:45:00', event: 'Approval Granted', color: '#22C55E' },
              { time: '14:45:30', event: 'Execution Started', color: '#3B82F6' },
              { time: '16:17:02', event: 'Completed Successfully', color: '#22C55E' },
            ].map((ev, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <div className="flex flex-col items-center flex-shrink-0">
                  <div className="w-2 h-2 rounded-full mt-0.5" style={{ background: ev.color }} aria-hidden="true" />
                  {i < 5 && <div className="w-px flex-1 mt-1" style={{ background: 'var(--akaal-border)', minHeight: '16px' }} aria-hidden="true" />}
                </div>
                <div className="pb-2">
                  <p className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{ev.event}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{ev.time}</p>
                </div>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'permissions' && (
          <div className="space-y-2 text-xs">
            {[
              { role: 'Platform Admin', access: 'Full Access', user: 'sarah.chen' },
              { role: 'Migration Owner', access: 'Read / Write', user: migration.owner },
              { role: 'Approver', access: 'Approve / Reject', user: 'james.okafor' },
              { role: 'Viewer', access: 'Read Only', user: 'reporting.team' },
            ].map((p, i) => (
              <div key={i} className="p-2.5 rounded-md" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{p.role}</span>
                  <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{p.access}</span>
                </div>
                <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{p.user}</span>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'downloads' && (
          <div className="space-y-2">
            {[
              { format: 'PDF Report', size: '2.4 MB', icon: '📄' },
              { format: 'Excel Export', size: '1.8 MB', icon: '📊' },
              { format: 'CSV Data', size: '0.9 MB', icon: '📋' },
              { format: 'JSON Export', size: '3.1 MB', icon: '{ }' },
              { format: 'Execution Logs', size: '0.4 MB', icon: '📝' },
            ].map((d, i) => (
              <button key={i} type="button" className="w-full flex items-center justify-between p-2.5 rounded-md transition-all duration-150 text-left" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--akaal-primary)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--akaal-border)'; }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm" aria-hidden="true">{d.icon}</span>
                  <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{d.format}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{d.size}</span>
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)' }}>
                    <path d="M6 1v7M3 5l3 3 3-3M1 9v1a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Export Panel ─────────────────────────────────────────────────────────────

function ExportPanel({ onClose }: { onClose: () => void }) {
  const [format, setFormat] = useState('pdf');
  const [scope, setScope] = useState('current');
  const [exporting, setExporting] = useState(false);

  const handleExport = () => {
    setExporting(true);
    setTimeout(() => { setExporting(false); onClose(); }, 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }} role="dialog" aria-modal="true" aria-label="Export options">
      <div className="rounded-xl overflow-hidden" style={{ width: '420px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 24px 64px rgba(0,0,0,0.5)' }}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
          <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Export Report</h2>
          <button type="button" onClick={onClose} className="w-7 h-7 rounded-md flex items-center justify-center transition-all duration-150" style={{ color: 'var(--akaal-text-muted)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            aria-label="Close export panel"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Export Format</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'pdf', label: 'PDF', icon: '📄' },
                { id: 'excel', label: 'Excel', icon: '📊' },
                { id: 'csv', label: 'CSV', icon: '📋' },
                { id: 'json', label: 'JSON', icon: '{ }' },
                { id: 'print', label: 'Print', icon: '🖨' },
                { id: 'email', label: 'Email', icon: '✉' },
              ].map(f => (
                <button key={f.id} type="button" onClick={() => setFormat(f.id)} className="flex flex-col items-center gap-1 p-2.5 rounded-md transition-all duration-150 text-xs" style={{ background: format === f.id ? 'var(--akaal-primary-subtle)' : 'var(--akaal-surface-elevated)', border: `1px solid ${format === f.id ? 'var(--akaal-primary)' : 'var(--akaal-border)'}`, color: format === f.id ? 'var(--akaal-text)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
                  <span className="text-base" aria-hidden="true">{f.icon}</span>
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Scope</label>
            <select value={scope} onChange={e => setScope(e.target.value)} className="w-full text-xs rounded-md px-3 py-2 outline-none" style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
              <option value="current">Current view</option>
              <option value="all">All records</option>
              <option value="selected">Selected records</option>
              <option value="date-range">Custom date range</option>
            </select>
          </div>
          {exporting && (
            <div className="p-3 rounded-md" style={{ background: 'var(--akaal-info-bg)', border: '1px solid rgba(96,165,250,0.2)' }}>
              <div className="flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="animate-spin" style={{ color: 'var(--akaal-info)' }}>
                  <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="20 15" />
                </svg>
                <p className="text-xs" style={{ color: 'var(--akaal-info)', fontFamily: "'Inter', sans-serif" }}>Generating {format.toUpperCase()} export…</p>
              </div>
            </div>
          )}
        </div>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderTop: '1px solid var(--akaal-border)' }}>
          <button type="button" onClick={onClose} className="text-xs px-3 py-1.5 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>Cancel</button>
          <button type="button" onClick={handleExport} disabled={exporting} className="text-xs px-4 py-1.5 rounded transition-all duration-150 disabled:opacity-50" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}>
            {exporting ? 'Exporting…' : `Export as ${format.toUpperCase()}`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeCategory, setActiveCategory] = useState<ReportCategory>('migration-reports');
  const [isLoading, setIsLoading] = useState(true);
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('7d');
  const [inspectorId, setInspectorId] = useState<string | null>(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setIsLoading(false), 1200);
    return () => clearTimeout(t);
  }, []);

  const handleGenerate = useCallback(() => {
    setIsGenerating(true);
    setTimeout(() => setIsGenerating(false), 2000);
  }, []);

  const renderContent = () => {
    switch (activeCategory) {
      case 'audit-logs':
        return <AuditLogsPanel loading={isLoading} />;
      case 'compliance':
        return <CompliancePanel loading={isLoading} />;
      case 'scheduled-reports':
        return <ScheduledReportsPanel loading={isLoading} />;
      case 'custom-reports':
        return (
          <div className="mb-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Custom Reports</h2>
              <button type="button" onClick={() => setShowBuilder(true)} className="text-xs px-3 py-1.5 rounded transition-all duration-150" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}>+ New Report</button>
            </div>
            <Card className="py-16">
              <div className="flex flex-col items-center gap-3">
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)', opacity: 0.4 }}>
                  <path d="M8 6h16l8 8v20H8V6Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /><path d="M24 6v8h8M14 18h12M14 24h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <p className="text-sm font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>No custom reports yet</p>
                <p className="text-xs text-center max-w-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", opacity: 0.7 }}>Use the Report Builder to create custom reports tailored to your operational needs.</p>
                <button type="button" onClick={() => setShowBuilder(true)} className="text-xs px-4 py-2 rounded transition-all duration-150 mt-1" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}>Open Report Builder</button>
              </div>
            </Card>
          </div>
        );
      case 'saved-reports':
        return (
          <Card className="mb-5 py-16">
            <div className="flex flex-col items-center gap-3">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)', opacity: 0.4 }}>
                <path d="M8 6h20l6 6v22H8V6Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /><path d="M12 6v10h16V6" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
              </svg>
              <p className="text-sm font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>No saved reports</p>
              <p className="text-xs text-center max-w-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", opacity: 0.7 }}>Generate and save reports to access them quickly from this panel.</p>
            </div>
          </Card>
        );
      default:
        return (
          <>
            <KPICards loading={isLoading} />
            <AnalyticsSection loading={isLoading} timeFilter={timeFilter} onTimeFilter={setTimeFilter} />
            <ExecutiveSummary loading={isLoading} />
            <MigrationHistoryGrid loading={isLoading} onSelect={id => setInspectorId(id)} />
          </>
        );
    }
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}>
      {/* Background lighting */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0" style={{ background: 'radial-gradient(ellipse 80% 50% at 10% 0%, rgba(37,99,235,0.06) 0%, transparent 60%)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0" style={{ background: 'radial-gradient(ellipse 40% 30% at 90% 0%, rgba(56,189,248,0.03) 0%, transparent 60%)' }} />

      {/* Sidebar */}
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />

      {/* Main content */}
      <div className="flex flex-col flex-1 min-w-0 relative z-10">
        {/* Top Nav */}
        <TopNav />

        {/* Content area */}
        <div className="flex flex-1 min-h-0">
          {/* Category Nav */}
          <CategoryNav active={activeCategory} onSelect={setActiveCategory} />

          {/* Main scrollable area */}
          <main
            className="flex-1 overflow-y-auto overflow-x-hidden"
            id="main-content"
            aria-label="Reports and audit main content"
          >
            <div className="px-5 py-5 max-w-screen-2xl mx-auto">
              {/* Page Header */}
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-5">
                <div>
                  <h1 className="text-xl font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Reports & Audit</h1>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Enterprise reporting, analytics and compliance.</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Generate Report */}
                  <button
                    type="button"
                    onClick={handleGenerate}
                    disabled={isGenerating}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2 disabled:opacity-60"
                    style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
                    aria-label={isGenerating ? 'Generating report' : 'Generate report'}
                    onMouseEnter={e => { if (!isGenerating) (e.currentTarget as HTMLElement).style.opacity = '0.9'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                  >
                    {isGenerating ? (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="animate-spin"><circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="15 10" /></svg>
                    ) : (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 2v8M2 6h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                    )}
                    {isGenerating ? 'Generating…' : 'Generate Report'}
                  </button>
                  {/* Schedule Report */}
                  <button
                    type="button"
                    onClick={() => setActiveCategory('scheduled-reports')}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                    style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.3" /><path d="M6 3.5v2.5l1.5 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
                    Schedule Report
                  </button>
                  {/* Export */}
                  <button
                    type="button"
                    onClick={() => setShowExport(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                    style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1v7M3 5l3 3 3-3M1 9v1a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    Export
                  </button>
                  {/* Share */}
                  <button
                    type="button"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                    style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="9.5" cy="2.5" r="1.5" stroke="currentColor" strokeWidth="1.2" /><circle cx="2.5" cy="6" r="1.5" stroke="currentColor" strokeWidth="1.2" /><circle cx="9.5" cy="9.5" r="1.5" stroke="currentColor" strokeWidth="1.2" /><path d="M4 6.5l4 2.5M4 5.5l4-2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                    Share
                  </button>
                </div>
              </div>

              {/* Main content */}
              {renderContent()}
            </div>
          </main>

          {/* Inspector Panel */}
          {inspectorId && (
            <InspectorPanel migrationId={inspectorId} onClose={() => setInspectorId(null)} />
          )}
        </div>
      </div>

      {/* Report Builder Modal */}
      {showBuilder && <ReportBuilder onClose={() => setShowBuilder(false)} />}

      {/* Export Modal */}
      {showExport && <ExportPanel onClose={() => setShowExport(false)} />}
    </div>
  );
}
