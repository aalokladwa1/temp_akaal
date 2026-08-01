'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';
import { EnterpriseEmptyState } from '@/components/ui/EnterpriseEmptyState';

// ─── Types ────────────────────────────────────────────────────────────────────

type ExecStatus =
  | 'queued' | 'validating' | 'approved' | 'running' | 'paused' |'retrying' | 'rolling_back' | 'completed' | 'cancelled' | 'failed';

type Priority = 'critical' | 'high' | 'medium' | 'low';
type MigrationType = 'full' | 'incremental' | 'cdc' | 'schema_only';
type Environment = 'production' | 'staging' | 'development' | 'testing';
type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | 'SUCCESS';
type DetailTab = 'overview' | 'stages' | 'logs' | 'performance' | 'errors' | 'timeline' | 'rollback' | 'approvals';
type StageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'warning';
type ErrorStateType = 'execution_lost' | 'worker_offline' | 'agent_disconnected' | 'checkpoint_failure' | 'rollback_failure' | 'cdc_failure' | 'permission_denied' | 'network_timeout' | null;

interface ExecutionJob {
  id: string;
  migrationName: string;
  source: string;
  target: string;
  status: ExecStatus;
  progress: number;
  currentStage: string;
  rowsMigrated: number;
  totalRows: number;
  throughput: number;
  elapsedTime: string;
  eta: string;
  priority: Priority;
  owner: string;
  environment: Environment;
  migrationType: MigrationType;
  startTime: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  batchSize: number;
  parallelWorkers: number;
  strategy: string;
  checkpoints: number;
  retryCount: number;
}

interface ExecutionStage {
  id: string;
  name: string;
  status: StageStatus;
  duration: string;
  rowsProcessed: number;
  warnings: number;
  errors: number;
  canRetry: boolean;
  startTime?: string;
  endTime?: string;
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  stage?: string;
  details?: string;
}

interface ExecutionError {
  id: string;
  stage: string;
  errorCode: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  resolution: string;
  canRetry: boolean;
  requiresRollback: boolean;
  stackTrace: string;
  timestamp: string;
}

interface TimelineEvent {
  id: string;
  timestamp: string;
  type: string;
  description: string;
  actor?: string;
  severity: 'info' | 'success' | 'warning' | 'error';
}

interface Checkpoint {
  id: string;
  name: string;
  timestamp: string;
  rowsAt: number;
  stage: string;
  size: string;
}

interface Approval {
  id: string;
  requestedBy: string;
  requestedAt: string;
  approvedBy?: string;
  approvedAt?: string;
  status: 'pending' | 'approved' | 'rejected';
  type: string;
  notes?: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_JOBS: ExecutionJob[] = [
  {
    id: 'EX-2847', migrationName: 'prod-oracle-to-postgres', source: 'Oracle 19c', target: 'PostgreSQL 15',
    status: 'running', progress: 67, currentStage: 'Data Migration', rowsMigrated: 4_820_441, totalRows: 7_194_000,
    throughput: 12_400, elapsedTime: '1h 55m', eta: '58m', priority: 'critical', owner: 'sarah.chen',
    environment: 'production', migrationType: 'full', startTime: '2026-07-25 14:22:00', riskLevel: 'high',
    batchSize: 10000, parallelWorkers: 8, strategy: 'Full Migration with CDC', checkpoints: 12, retryCount: 0,
  },
  {
    id: 'EX-2848', migrationName: 'analytics-mysql-warehouse', source: 'MySQL 8.0', target: 'Snowflake',
    status: 'completed', progress: 100, currentStage: 'Completed', rowsMigrated: 22_100_000, totalRows: 22_100_000,
    throughput: 0, elapsedTime: '3h 12m', eta: '—', priority: 'high', owner: 'james.okafor',
    environment: 'production', migrationType: 'full', startTime: '2026-07-25 11:00:00', riskLevel: 'medium',
    batchSize: 50000, parallelWorkers: 16, strategy: 'Bulk Load', checkpoints: 28, retryCount: 1,
  },
  {
    id: 'EX-2849', migrationName: 'legacy-mssql-migration', source: 'SQL Server 2019', target: 'Azure SQL',
    status: 'failed', progress: 34, currentStage: 'Data Migration', rowsMigrated: 1_240_000, totalRows: 3_650_000,
    throughput: 0, elapsedTime: '32m', eta: '—', priority: 'critical', owner: 'priya.nair',
    environment: 'production', migrationType: 'full', startTime: '2026-07-25 13:45:00', riskLevel: 'critical',
    batchSize: 5000, parallelWorkers: 4, strategy: 'Full Migration', checkpoints: 4, retryCount: 2,
  },
  {
    id: 'EX-2850', migrationName: 'crm-postgres-upgrade', source: 'PostgreSQL 12', target: 'PostgreSQL 15',
    status: 'queued', progress: 0, currentStage: 'Queued', rowsMigrated: 0, totalRows: 890_000,
    throughput: 0, elapsedTime: '—', eta: '~45m', priority: 'medium', owner: 'alex.morgan',
    environment: 'staging', migrationType: 'full', startTime: '—', riskLevel: 'low',
    batchSize: 20000, parallelWorkers: 4, strategy: 'In-Place Upgrade', checkpoints: 0, retryCount: 0,
  },
  {
    id: 'EX-2851', migrationName: 'dw-redshift-consolidation', source: 'Redshift', target: 'BigQuery',
    status: 'running', progress: 12, currentStage: 'Schema Migration', rowsMigrated: 480_000, totalRows: 4_000_000,
    throughput: 8_200, elapsedTime: '19m', eta: '2h 41m', priority: 'high', owner: 'sarah.chen',
    environment: 'production', migrationType: 'full', startTime: '2026-07-25 15:58:00', riskLevel: 'medium',
    batchSize: 25000, parallelWorkers: 6, strategy: 'Parallel Export', checkpoints: 2, retryCount: 0,
  },
  {
    id: 'EX-2852', migrationName: 'iot-timescale-archive', source: 'TimescaleDB', target: 'ClickHouse',
    status: 'paused', progress: 51, currentStage: 'Data Migration', rowsMigrated: 15_300_000, totalRows: 30_000_000,
    throughput: 0, elapsedTime: '2h 41m', eta: 'Paused', priority: 'medium', owner: 'dev.ops',
    environment: 'staging', migrationType: 'incremental', startTime: '2026-07-25 09:30:00', riskLevel: 'low',
    batchSize: 100000, parallelWorkers: 12, strategy: 'Incremental Batch', checkpoints: 18, retryCount: 0,
  },
  {
    id: 'EX-2853', migrationName: 'hr-oracle-schema-sync', source: 'Oracle 12c', target: 'PostgreSQL 14',
    status: 'validating', progress: 8, currentStage: 'Schema Validation', rowsMigrated: 0, totalRows: 2_100_000,
    throughput: 0, elapsedTime: '4m', eta: '~1h 20m', priority: 'low', owner: 'hr.admin',
    environment: 'development', migrationType: 'schema_only', startTime: '2026-07-25 16:13:00', riskLevel: 'low',
    batchSize: 10000, parallelWorkers: 2, strategy: 'Schema Only', checkpoints: 0, retryCount: 0,
  },
  {
    id: 'EX-2854', migrationName: 'finance-db-cdc-stream', source: 'MySQL 5.7', target: 'PostgreSQL 15',
    status: 'retrying', progress: 44, currentStage: 'Data Migration', rowsMigrated: 3_080_000, totalRows: 7_000_000,
    throughput: 3_100, elapsedTime: '1h 12m', eta: '1h 05m', priority: 'high', owner: 'finance.ops',
    environment: 'production', migrationType: 'cdc', startTime: '2026-07-25 15:05:00', riskLevel: 'high',
    batchSize: 15000, parallelWorkers: 6, strategy: 'CDC Streaming', checkpoints: 8, retryCount: 3,
  },
];

const MOCK_STAGES: ExecutionStage[] = [
  { id: 's1', name: 'Preparation',       status: 'completed', duration: '0m 42s', rowsProcessed: 0,         warnings: 0, errors: 0, canRetry: false, startTime: '14:22:00', endTime: '14:22:42' },
  { id: 's2', name: 'Schema Validation', status: 'completed', duration: '2m 18s', rowsProcessed: 0,         warnings: 2, errors: 0, canRetry: false, startTime: '14:22:42', endTime: '14:25:00' },
  { id: 's3', name: 'Schema Migration',  status: 'completed', duration: '8m 05s', rowsProcessed: 0,         warnings: 0, errors: 0, canRetry: false, startTime: '14:25:00', endTime: '14:33:05' },
  { id: 's4', name: 'Data Migration',    status: 'running',   duration: '1h 44m', rowsProcessed: 4_820_441, warnings: 3, errors: 0, canRetry: false, startTime: '14:33:05' },
  { id: 's5', name: 'Index Creation',    status: 'pending',   duration: '—',      rowsProcessed: 0,         warnings: 0, errors: 0, canRetry: false },
  { id: 's6', name: 'Constraints',       status: 'pending',   duration: '—',      rowsProcessed: 0,         warnings: 0, errors: 0, canRetry: false },
  { id: 's7', name: 'Verification',      status: 'pending',   duration: '—',      rowsProcessed: 0,         warnings: 0, errors: 0, canRetry: false },
  { id: 's8', name: 'Cleanup',           status: 'pending',   duration: '—',      rowsProcessed: 0,         warnings: 0, errors: 0, canRetry: false },
  { id: 's9', name: 'Completion',        status: 'pending',   duration: '—',      rowsProcessed: 0,         warnings: 0, errors: 0, canRetry: false },
];

const MOCK_LOGS: LogEntry[] = [
  { id: 'l1',  timestamp: '16:17:02.441', level: 'INFO',    message: 'Checkpoint saved — offset 4,820,441 rows committed', stage: 'Data Migration' },
  { id: 'l2',  timestamp: '16:16:58.112', level: 'DEBUG',   message: 'Worker pool utilization: 7/8 active threads', stage: 'Data Migration' },
  { id: 'l3',  timestamp: '16:16:45.009', level: 'INFO',    message: 'Batch 482 completed — 10,000 rows in 0.81s (12,345 rows/s)', stage: 'Data Migration' },
  { id: 'l4',  timestamp: '16:15:30.882', level: 'WARN',    message: 'CDC lag spike detected — replication delay 4.2s on table ORDERS', stage: 'Data Migration', details: 'Lag threshold: 2.0s. Current: 4.2s. Monitoring for recovery.' },
  { id: 'l5',  timestamp: '16:14:22.001', level: 'INFO',    message: 'Batch 470 completed — 10,000 rows in 0.79s', stage: 'Data Migration' },
  { id: 'l6',  timestamp: '16:12:10.334', level: 'SUCCESS', message: 'Schema migration completed — 142 tables, 28 views, 14 functions migrated', stage: 'Schema Migration' },
  { id: 'l7',  timestamp: '16:11:55.221', level: 'WARN',    message: 'Type coercion applied: NUMBER(38,10) → NUMERIC(38,10) on 2 columns', stage: 'Schema Validation', details: 'Columns: ORDERS.AMOUNT, ORDERS.TAX_AMOUNT' },
  { id: 'l8',  timestamp: '16:10:44.009', level: 'INFO',    message: 'Schema validation passed — 0 blocking issues, 2 warnings', stage: 'Schema Validation' },
  { id: 'l9',  timestamp: '16:09:30.118', level: 'DEBUG',   message: 'Connection pool established — 8 workers connected to target', stage: 'Preparation' },
  { id: 'l10', timestamp: '16:09:00.000', level: 'INFO',    message: 'Execution started — EX-2847 prod-oracle-to-postgres', stage: 'Preparation' },
  { id: 'l11', timestamp: '16:08:55.441', level: 'SUCCESS', message: 'Pre-flight checks passed — all systems ready', stage: 'Preparation' },
  { id: 'l12', timestamp: '16:08:40.002', level: 'INFO',    message: 'Approval granted by j.okafor@akaal.io — production cutover authorized', stage: 'Preparation' },
];

const MOCK_ERRORS: ExecutionError[] = [
  {
    id: 'err1', stage: 'Data Migration', errorCode: 'CDC-LAG-001', severity: 'medium',
    description: 'CDC replication lag exceeded threshold on table ORDERS (4.2s > 2.0s)',
    resolution: 'Monitor lag recovery. If sustained >10s, consider pausing and investigating source load.',
    canRetry: false, requiresRollback: false, timestamp: '16:15:30',
    stackTrace: 'CDCMonitor.checkLag() at CDCMonitor.java:142\n  ReplicationStream.getLag() at ReplicationStream.java:89\n  Lag threshold exceeded: 4200ms > 2000ms',
  },
  {
    id: 'err2', stage: 'Schema Validation', errorCode: 'SCHEMA-WARN-002', severity: 'low',
    description: 'Implicit type coercion required for NUMBER(38,10) → NUMERIC(38,10) on 2 columns',
    resolution: 'Coercion applied automatically. Verify precision is preserved in target after migration.',
    canRetry: false, requiresRollback: false, timestamp: '16:11:55',
    stackTrace: 'TypeMapper.mapOracleToPostgres() at TypeMapper.java:234\n  Column: ORDERS.AMOUNT (NUMBER 38,10 → NUMERIC 38,10)\n  Column: ORDERS.TAX_AMOUNT (NUMBER 38,10 → NUMERIC 38,10)',
  },
];

const MOCK_TIMELINE: TimelineEvent[] = [
  { id: 't1', timestamp: '16:17:02', type: 'checkpoint',  description: 'Checkpoint saved at 4,820,441 rows',           severity: 'info' },
  { id: 't2', timestamp: '16:15:30', type: 'warning',     description: 'CDC lag spike detected — 4.2s delay',          severity: 'warning' },
  { id: 't3', timestamp: '14:33:05', type: 'stage_start', description: 'Data Migration phase started',                  severity: 'info' },
  { id: 't4', timestamp: '14:25:00', type: 'stage_done',  description: 'Schema Migration completed successfully',       severity: 'success' },
  { id: 't5', timestamp: '14:22:42', type: 'stage_done',  description: 'Schema Validation passed — 2 warnings',        severity: 'success' },
  { id: 't6', timestamp: '14:22:00', type: 'exec_start',  description: 'Execution started — EX-2847',                  severity: 'info', actor: 'system' },
  { id: 't7', timestamp: '14:08:40', type: 'approval',    description: 'Approval granted by j.okafor@akaal.io',        severity: 'success', actor: 'j.okafor' },
  { id: 't8', timestamp: '13:55:00', type: 'created',     description: 'Migration job created by sarah.chen',          severity: 'info', actor: 'sarah.chen' },
];

const MOCK_CHECKPOINTS: Checkpoint[] = [
  { id: 'cp12', name: 'Checkpoint 12', timestamp: '16:17:02', rowsAt: 4_820_441, stage: 'Data Migration', size: '2.4 MB' },
  { id: 'cp11', name: 'Checkpoint 11', timestamp: '16:07:02', rowsAt: 4_220_441, stage: 'Data Migration', size: '2.1 MB' },
  { id: 'cp10', name: 'Checkpoint 10', timestamp: '15:57:02', rowsAt: 3_620_441, stage: 'Data Migration', size: '1.8 MB' },
  { id: 'cp9',  name: 'Checkpoint 9',  timestamp: '15:47:02', rowsAt: 3_020_441, stage: 'Data Migration', size: '1.5 MB' },
  { id: 'cp8',  name: 'Checkpoint 8',  timestamp: '15:37:02', rowsAt: 2_420_441, stage: 'Data Migration', size: '1.2 MB' },
];

const MOCK_APPROVALS: Approval[] = [
  {
    id: 'ap1', requestedBy: 'sarah.chen', requestedAt: '2026-07-25 13:50:00',
    approvedBy: 'j.okafor', approvedAt: '2026-07-25 14:08:40',
    status: 'approved', type: 'Production Execution Approval',
    notes: 'Reviewed migration plan. Risk assessment acceptable. Approved for production window.',
  },
  {
    id: 'ap2', requestedBy: 'sarah.chen', requestedAt: '2026-07-25 13:50:00',
    approvedBy: 'p.nair', approvedAt: '2026-07-25 14:05:00',
    status: 'approved', type: 'DBA Sign-off',
    notes: 'Schema changes reviewed. No breaking changes detected.',
  },
];

// ─── Status Config ────────────────────────────────────────────────────────────

const EXEC_STATUS_META: Record<ExecStatus, { label: string; color: string; bg: string; border: string; dot: string }> = {
  queued:       { label: 'Queued',       color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)', dot: '#94A3B8' },
  validating:   { label: 'Validating',   color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  border: 'rgba(56,189,248,0.2)',  dot: '#38BDF8' },
  approved:     { label: 'Approved',     color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)',   dot: '#22C55E' },
  running:      { label: 'Running',      color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  border: 'rgba(56,189,248,0.2)',  dot: '#38BDF8' },
  paused:       { label: 'Paused',       color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  dot: '#F59E0B' },
  retrying:     { label: 'Retrying',     color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  dot: '#F59E0B' },
  rolling_back: { label: 'Rolling Back', color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  dot: '#F59E0B' },
  completed:    { label: 'Completed',    color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)',   dot: '#22C55E' },
  cancelled:    { label: 'Cancelled',    color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)', dot: '#64748B' },
  failed:       { label: 'Failed',       color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)',   dot: '#EF4444' },
};

const PRIORITY_META: Record<Priority, { label: string; color: string; bg: string; border: string }> = {
  critical: { label: 'Critical', color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)' },
  high:     { label: 'High',     color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)' },
  medium:   { label: 'Medium',   color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  border: 'rgba(56,189,248,0.2)' },
  low:      { label: 'Low',      color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)' },
};

const STAGE_STATUS_META: Record<StageStatus, { color: string; bg: string; label: string }> = {
  pending:   { color: '#64748B', bg: 'rgba(100,116,139,0.08)', label: 'Pending' },
  running:   { color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  label: 'Running' },
  completed: { color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   label: 'Completed' },
  failed:    { color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   label: 'Failed' },
  skipped:   { color: '#64748B', bg: 'rgba(100,116,139,0.08)', label: 'Skipped' },
  warning:   { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  label: 'Warning' },
};

const LOG_LEVEL_META: Record<LogLevel, { color: string; bg: string }> = {
  INFO:    { color: '#38BDF8', bg: 'rgba(56,189,248,0.08)' },
  WARN:    { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)' },
  ERROR:   { color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
  DEBUG:   { color: '#64748B', bg: 'rgba(100,116,139,0.08)' },
  SUCCESS: { color: '#22C55E', bg: 'rgba(34,197,94,0.08)' },
};

const ERROR_STATE_META: Record<NonNullable<ErrorStateType>, { title: string; detail: string; color: string }> = {
  execution_lost:      { title: 'Execution Lost',       detail: 'The execution record could not be found. It may have been purged or the ID is invalid.', color: '#EF4444' },
  worker_offline:      { title: 'Worker Offline',       detail: 'The migration worker process is not responding. The execution has been suspended.', color: '#EF4444' },
  agent_disconnected:  { title: 'Agent Disconnected',   detail: 'The AKAAL agent on the source host has lost connectivity. Execution cannot proceed.', color: '#EF4444' },
  checkpoint_failure:  { title: 'Checkpoint Failure',   detail: 'Failed to write execution checkpoint. Data integrity cannot be guaranteed without checkpoints.', color: '#F59E0B' },
  rollback_failure:    { title: 'Rollback Failure',     detail: 'The rollback operation encountered an error. Manual intervention may be required.', color: '#EF4444' },
  cdc_failure:         { title: 'CDC Failure',          detail: 'Change Data Capture stream has been interrupted. Replication lag may cause data inconsistency.', color: '#F59E0B' },
  permission_denied:   { title: 'Permission Denied',    detail: 'Insufficient privileges to access execution details. Contact your platform administrator.', color: '#EF4444' },
  network_timeout:     { title: 'Network Timeout',      detail: 'The connection to the execution service timed out. Check network connectivity and retry.', color: '#EF4444' },
};

// ─── Utility Components ───────────────────────────────────────────────────────

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

function ExecStatusChip({ status }: { status: ExecStatus }) {
  const cfg = EXEC_STATUS_META[status];
  const isAnimated = status === 'running' || status === 'retrying' || status === 'rolling_back' || status === 'validating';
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: cfg.dot, animation: isAnimated ? 'pulse 1.5s ease-in-out infinite' : 'none' }}
        aria-hidden="true"
      />
      {cfg.label}
    </span>
  );
}

function PriorityChip({ priority }: { priority: Priority }) {
  const cfg = PRIORITY_META[priority];
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}
    >
      {cfg.label}
    </span>
  );
}

function ProgressBar({ value, status }: { value: number; status: ExecStatus }) {
  const color = status === 'failed' || status === 'cancelled' ? '#EF4444'
    : status === 'completed' ? '#22C55E'
    : status === 'paused'? '#F59E0B' :'#2563EB';
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

function Card({ children, className, style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  return (
    <div className={`rounded-lg ${className ?? ''}`} style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)', ...style }}>
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

function formatRows(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function formatThroughput(n: number): string {
  if (n === 0) return '—';
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K/s`;
  return `${n}/s`;
}

// ─── Confirmation Modal ───────────────────────────────────────────────────────

function ConfirmModal({
  open, title, message, confirmLabel, danger, onConfirm, onCancel,
}: {
  open: boolean; title: string; message: string; confirmLabel: string; danger?: boolean;
  onConfirm: () => void; onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
    >
      <div
        className="rounded-lg w-full max-w-sm mx-4"
        style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 16px 48px var(--akaal-shadow)' }}
      >
        <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
          <h3 id="confirm-title" className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{title}</h3>
        </div>
        <div className="px-5 py-4">
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", lineHeight: '1.6' }}>{message}</p>
        </div>
        <div className="flex items-center justify-end gap-2 px-5 py-3" style={{ borderTop: '1px solid var(--akaal-border)' }}>
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'transparent', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{
              background: danger ? '#EF4444' : 'var(--akaal-primary)',
              color: '#fff',
              border: 'none',
              fontFamily: "'Inter', sans-serif",
            }}
            onMouseEnter={e => { e.currentTarget.style.filter = 'brightness(1.1)'; }}
            onMouseLeave={e => { e.currentTarget.style.filter = 'none'; }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function AppSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const navItems = [
    {
      href: '/dashboard', label: 'Dashboard', active: false,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /></svg>,
    },
    {
      href: '/migrations', label: 'Migrations', active: false,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    },
    {
      href: '/execution-center', label: 'Execution', active: true,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M6 5.5l5 2.5-5 2.5V5.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg>,
    },
    {
      href: '/databases', label: 'Databases', active: false,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="6" ry="2" stroke="currentColor" strokeWidth="1.3" /><path d="M2 4v4c0 1.1 2.7 2 6 2s6-.9 6-2V4" stroke="currentColor" strokeWidth="1.3" /><path d="M2 8v4c0 1.1 2.7 2 6 2s6-.9 6-2V8" stroke="currentColor" strokeWidth="1.3" /></svg>,
    },
    {
      href: '/live-monitor', label: 'Live Monitor', active: false,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M4 8l2-2 2 2 2-3 2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>,
    },
    {
      href: '/agents', label: 'Agents', active: false,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>,
    },
    {
      href: '/reports', label: 'Reports', active: false,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>,
    },
    {
      href: '/system', label: 'System', active: false,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="3" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="4.5" r="0.8" fill="currentColor" /><circle cx="4" cy="9.5" r="0.8" fill="currentColor" /><path d="M5 13h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>,
    },
    {
      href: '/settings', label: 'Settings', active: false,
      icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.4 3.4l.85.85M11.75 11.75l.85.85M3.4 12.6l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>,
    },
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
    <header className="flex items-center gap-4 px-4 flex-shrink-0" style={{ height: '57px', background: 'var(--akaal-nav-bg)', borderBottom: '1px solid var(--akaal-nav-border)' }} role="banner">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 flex-shrink-0">
        <Link href="/dashboard" className="text-xs transition-colors" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }} onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}>Platform</Link>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Execution Center</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
          <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <input
          type="search" placeholder="Search executions, jobs…" value={searchValue} onChange={e => setSearchValue(e.target.value)}
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
        {notifOpen && (
          <div className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50" style={{ width: '300px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }} role="dialog" aria-label="Notifications">
            <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}><p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Notifications</p></div>
            {[
              { title: 'Execution Failed', detail: 'EX-2849 legacy-mssql-migration — constraint violation', time: '7m ago', color: 'var(--akaal-error)' },
              { title: 'CDC Lag Warning', detail: 'EX-2847 prod-oracle-to-postgres — 4.2s replication delay', time: '23m ago', color: 'var(--akaal-warning)' },
              { title: 'Approval Required', detail: 'EX-2850 crm-postgres-upgrade awaiting sign-off', time: '1h ago', color: 'var(--akaal-secondary)' },
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
            {['Profile Settings', 'API Keys', 'Audit Log', 'Sign Out'].map((item, i) => (
              <button key={i} type="button" role="menuitem"
                className="w-full text-left px-3 py-2 text-xs transition-colors"
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

// ─── Metric Cards ─────────────────────────────────────────────────────────────

function MetricCards({ jobs, loading }: { jobs: ExecutionJob[]; loading: boolean }) {
  const running   = jobs.filter(j => j.status === 'running').length;
  const queued    = jobs.filter(j => j.status === 'queued' || j.status === 'approved').length;
  const completed = jobs.filter(j => j.status === 'completed').length;
  const failed    = jobs.filter(j => j.status === 'failed').length;
  const paused    = jobs.filter(j => j.status === 'paused').length;
  const rollbacks = jobs.filter(j => j.status === 'rolling_back').length;
  const avgThroughput = jobs.filter(j => j.throughput > 0).reduce((s, j) => s + j.throughput, 0) / Math.max(1, jobs.filter(j => j.throughput > 0).length);
  const rowsToday = jobs.reduce((s, j) => s + j.rowsMigrated, 0);

  const cards = [
    { label: 'Running Jobs',        value: running,                      accent: '#38BDF8', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 4.5l5 2.5-5 2.5V4.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg>, sub: 'Active executions' },
    { label: 'Queued Jobs',         value: queued,                       accent: '#94A3B8', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 4h10M2 7h10M2 10h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>, sub: 'Awaiting execution' },
    { label: 'Completed Today',     value: completed,                    accent: '#22C55E', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" /><path d="M4 7l2.5 2.5L10 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>, sub: 'Successfully finished' },
    { label: 'Failed Jobs',         value: failed,                       accent: '#EF4444', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 5l4 4M9 5l-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>, sub: 'Require attention' },
    { label: 'Paused Jobs',         value: paused,                       accent: '#F59E0B', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5.5 4.5v5M8.5 4.5v5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>, sub: 'Suspended executions' },
    { label: 'Rollback Operations', value: rollbacks,                    accent: '#F59E0B', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7h8M3 7l3-3M3 7l3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>, sub: 'Active rollbacks' },
    { label: 'Avg Throughput',      value: `${formatThroughput(Math.round(avgThroughput))}`, accent: '#2563EB', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 10l3-4 2.5 2 2.5-5 2 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>, sub: 'Rows per second' },
    { label: 'Rows Migrated Today', value: formatRows(rowsToday),        accent: '#2563EB', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="2" y="3" width="10" height="8" rx="1" stroke="currentColor" strokeWidth="1.3" /><path d="M5 6h4M5 8.5h2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>, sub: 'Across all jobs' },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {cards.map((_, i) => (
          <div key={i} className="rounded-lg p-3" style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}>
            <Skeleton style={{ width: '28px', height: '28px', borderRadius: '6px', marginBottom: '8px' }} />
            <Skeleton style={{ width: '40px', height: '22px', marginBottom: '4px' }} />
            <Skeleton style={{ width: '80px', height: '10px' }} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
      {cards.map((card, i) => (
        <div
          key={i}
          className="rounded-lg p-3 flex flex-col"
          style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0" style={{ background: `${card.accent}18`, color: card.accent }}>
              {card.icon}
            </div>
          </div>
          <div className="text-xl font-bold tabular-nums" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.1 }}>{card.value}</div>
          <div className="text-xs mt-1 font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{card.label}</div>
          <div className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{card.sub}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Filter Panel ─────────────────────────────────────────────────────────────

function FilterPanel({
  statusFilter, onStatusFilter,
  envFilter, onEnvFilter,
  typeFilter, onTypeFilter,
  priorityFilter, onPriorityFilter,
  searchQuery, onSearch,
  onClear,
}: {
  statusFilter: string; onStatusFilter: (v: string) => void;
  envFilter: string; onEnvFilter: (v: string) => void;
  typeFilter: string; onTypeFilter: (v: string) => void;
  priorityFilter: string; onPriorityFilter: (v: string) => void;
  searchQuery: string; onSearch: (v: string) => void;
  onClear: () => void;
}) {
  const selectStyle: React.CSSProperties = {
    background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text-secondary)',
    fontFamily: "'Inter', sans-serif", fontSize: '11px', borderRadius: '6px',
    padding: '5px 8px', width: '100%', outline: 'none', appearance: 'none' as const,
  };

  const labelStyle: React.CSSProperties = {
    color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px',
    letterSpacing: '0.1em', textTransform: 'uppercase' as const, fontWeight: 600,
    display: 'block', marginBottom: '4px',
  };

  const hasFilters = statusFilter !== 'all' || envFilter !== 'all' || typeFilter !== 'all' || priorityFilter !== 'all' || searchQuery !== '';

  return (
    <aside
      className="flex flex-col flex-shrink-0 overflow-y-auto"
      style={{ width: '192px', background: 'var(--akaal-sidebar-bg)', borderRight: '1px solid var(--akaal-card-border)' }}
      aria-label="Execution filters"
    >
      <div className="px-3 py-3 flex-shrink-0 flex items-center justify-between" style={{ borderBottom: '1px solid var(--akaal-card-border)' }}>
        <p style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>Filters</p>
        {hasFilters && (
          <button type="button" onClick={onClear} className="text-xs transition-colors focus:outline-none" style={{ color: '#2563EB', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
            onMouseEnter={e => { e.currentTarget.style.color = '#38BDF8'; }} onMouseLeave={e => { e.currentTarget.style.color = '#2563EB'; }}>
            Clear
          </button>
        )}
      </div>

      <div className="p-3 space-y-4">
        {/* Search */}
        <div>
          <label style={labelStyle}>Search</label>
          <div className="relative">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: '#64748B' }}>
              <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
              <path d="M8 8l2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
            <input
              type="search" placeholder="Job ID, name…" value={searchQuery} onChange={e => onSearch(e.target.value)}
              className="w-full outline-none transition-all duration-150"
              style={{ ...selectStyle, paddingLeft: '24px' }}
              aria-label="Search executions"
              onFocus={e => { e.currentTarget.style.borderColor = '#2563EB'; e.currentTarget.style.boxShadow = '0 0 0 2px rgba(37,99,235,0.2)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = '#374151'; e.currentTarget.style.boxShadow = 'none'; }}
            />
          </div>
        </div>

        {/* Status */}
        <div>
          <label htmlFor="filter-status" style={labelStyle}>Status</label>
          <select id="filter-status" value={statusFilter} onChange={e => onStatusFilter(e.target.value)} style={selectStyle}
            onFocus={e => { e.currentTarget.style.borderColor = '#2563EB'; }} onBlur={e => { e.currentTarget.style.borderColor = '#374151'; }}>
            <option value="all">All Statuses</option>
            <option value="running">Running</option>
            <option value="queued">Queued</option>
            <option value="paused">Paused</option>
            <option value="failed">Failed</option>
            <option value="completed">Completed</option>
            <option value="retrying">Retrying</option>
            <option value="validating">Validating</option>
            <option value="rolling_back">Rolling Back</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        {/* Environment */}
        <div>
          <label htmlFor="filter-env" style={labelStyle}>Environment</label>
          <select id="filter-env" value={envFilter} onChange={e => onEnvFilter(e.target.value)} style={selectStyle}
            onFocus={e => { e.currentTarget.style.borderColor = '#2563EB'; }} onBlur={e => { e.currentTarget.style.borderColor = '#374151'; }}>
            <option value="all">All Environments</option>
            <option value="production">Production</option>
            <option value="staging">Staging</option>
            <option value="development">Development</option>
            <option value="testing">Testing</option>
          </select>
        </div>

        {/* Migration Type */}
        <div>
          <label htmlFor="filter-type" style={labelStyle}>Migration Type</label>
          <select id="filter-type" value={typeFilter} onChange={e => onTypeFilter(e.target.value)} style={selectStyle}
            onFocus={e => { e.currentTarget.style.borderColor = '#2563EB'; }} onBlur={e => { e.currentTarget.style.borderColor = '#374151'; }}>
            <option value="all">All Types</option>
            <option value="full">Full Migration</option>
            <option value="incremental">Incremental</option>
            <option value="cdc">CDC Streaming</option>
            <option value="schema_only">Schema Only</option>
          </select>
        </div>

        {/* Priority */}
        <div>
          <label htmlFor="filter-priority" style={labelStyle}>Priority</label>
          <select id="filter-priority" value={priorityFilter} onChange={e => onPriorityFilter(e.target.value)} style={selectStyle}
            onFocus={e => { e.currentTarget.style.borderColor = '#2563EB'; }} onBlur={e => { e.currentTarget.style.borderColor = '#374151'; }}>
            <option value="all">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Saved Filters */}
        <div>
          <p style={labelStyle}>Saved Filters</p>
          <div className="space-y-1">
            {['Production Running', 'Failed Today', 'High Priority'].map(f => (
              <button key={f} type="button"
                className="w-full text-left text-xs px-2 py-1.5 rounded transition-all duration-150 focus:outline-none"
                style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif", background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(37,99,235,0.08)'; e.currentTarget.style.color = '#CBD5E1'; e.currentTarget.style.borderColor = 'rgba(37,99,235,0.2)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.color = '#94A3B8'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; }}
              >{f}</button>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

// ─── Execution Table ──────────────────────────────────────────────────────────

function ExecutionTable({
  jobs, loading, selectedId, onSelect, onAction,
}: {
  jobs: ExecutionJob[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAction: (action: string, job: ExecutionJob) => void;
}) {
  const [sortKey, setSortKey] = useState<keyof ExecutionJob>('id');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [bulkMenuOpen, setBulkMenuOpen] = useState(false);

  const handleSort = (key: keyof ExecutionJob) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const sorted = [...jobs].sort((a, b) => {
    const av = a[sortKey]; const bv = b[sortKey];
    if (av === bv) return 0;
    const cmp = av < bv ? -1 : 1;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const toggleRow = (id: string) => {
    setSelectedRows(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedRows.size === sorted.length) setSelectedRows(new Set());
    else setSelectedRows(new Set(sorted.map(j => j.id)));
  };

  const SortIcon = ({ col }: { col: keyof ExecutionJob }) => (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" style={{ opacity: sortKey === col ? 1 : 0.3 }}>
      {sortKey === col && sortDir === 'asc'
        ? <path d="M5 2l3 5H2l3-5Z" fill="currentColor" />
        : <path d="M5 8L2 3h6L5 8Z" fill="currentColor" />}
    </svg>
  );

  const thStyle: React.CSSProperties = {
    padding: '8px 10px', textAlign: 'left' as const, whiteSpace: 'nowrap' as const,
    color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px',
    letterSpacing: '0.08em', textTransform: 'uppercase' as const, fontWeight: 600,
    background: '#1A2333', borderBottom: '1px solid #2A3647', cursor: 'pointer',
    userSelect: 'none' as const,
  };

  if (loading) {
    return (
      <div className="overflow-hidden rounded-lg" style={{ border: '1px solid #2A3647' }}>
        <div style={{ background: '#1A2333', borderBottom: '1px solid #2A3647', padding: '8px 10px' }}>
          <Skeleton style={{ width: '200px', height: '12px' }} />
        </div>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-3 py-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: '#1F2937' }}>
            <Skeleton style={{ width: '14px', height: '14px', borderRadius: '3px' }} />
            <Skeleton style={{ width: '80px', height: '12px' }} />
            <Skeleton style={{ width: '120px', height: '12px' }} />
            <Skeleton style={{ width: '80px', height: '12px' }} />
            <Skeleton style={{ width: '60px', height: '18px', borderRadius: '4px' }} />
            <Skeleton style={{ width: '80px', height: '8px', flex: 1 }} />
          </div>
        ))}
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <div className="p-8">
        <EnterpriseEmptyState
          title="No execution jobs found"
          description="There are currently no active, queued, or completed database migration execution jobs matching your current filter criteria."
          primaryAction={{ label: 'Launch Execution', href: '/migration-workspace' }}
        />
      </div>
    );
  }

  return (
    <div className="rounded-lg overflow-hidden" style={{ border: '1px solid #2A3647' }}>
      {/* Bulk action bar */}
      {selectedRows.size > 0 && (
        <div className="flex items-center gap-3 px-3 py-2" style={{ background: 'rgba(37,99,235,0.1)', borderBottom: '1px solid rgba(37,99,235,0.2)' }}>
          <span className="text-xs font-medium" style={{ color: '#38BDF8', fontFamily: "'Inter', sans-serif" }}>{selectedRows.size} selected</span>
          <div className="flex items-center gap-2">
            {['Pause All', 'Cancel All', 'Export'].map(action => (
              <button key={action} type="button"
                className="text-xs px-2.5 py-1 rounded transition-all duration-150 focus:outline-none"
                style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; }}
              >{action}</button>
            ))}
          </div>
          <button type="button" onClick={() => setSelectedRows(new Set())} className="ml-auto text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>Clear</button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: 'collapse', minWidth: '1100px' }} role="grid" aria-label="Execution queue">
          <thead>
            <tr>
              <th style={{ ...thStyle, width: '36px', cursor: 'default' }}>
                <input
                  type="checkbox"
                  checked={selectedRows.size === sorted.length && sorted.length > 0}
                  onChange={toggleAll}
                  className="rounded"
                  style={{ accentColor: '#2563EB' }}
                  aria-label="Select all executions"
                />
              </th>
              {([
                ['id', 'Exec ID'],
                ['migrationName', 'Migration Name'],
                ['source', 'Source'],
                ['target', 'Target'],
                ['status', 'Status'],
                ['progress', 'Progress'],
                ['currentStage', 'Current Stage'],
                ['rowsMigrated', 'Rows Migrated'],
                ['throughput', 'Throughput'],
                ['elapsedTime', 'Elapsed'],
                ['eta', 'ETA'],
                ['priority', 'Priority'],
                ['owner', 'Owner'],
              ] as [keyof ExecutionJob, string][]).map(([key, label]) => (
                <th key={key} style={thStyle} onClick={() => handleSort(key)}>
                  <div className="flex items-center gap-1.5">
                    {label}
                    <SortIcon col={key} />
                  </div>
                </th>
              ))}
              <th style={{ ...thStyle, cursor: 'default' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((job, idx) => {
              const isSelected = selectedId === job.id;
              const isChecked = selectedRows.has(job.id);
              return (
                <tr
                  key={job.id}
                  onClick={() => onSelect(job.id)}
                  className="cursor-pointer transition-colors duration-100"
                  style={{
                    background: isSelected ? 'rgba(37,99,235,0.08)' : idx % 2 === 0 ? '#1F2937' : '#1A2333',
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    borderLeft: isSelected ? '2px solid #2563EB' : '2px solid transparent',
                  }}
                  onMouseEnter={e => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
                  onMouseLeave={e => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = idx % 2 === 0 ? '#1F2937' : '#1A2333'; }}
                  aria-selected={isSelected}
                >
                  <td style={{ padding: '8px 10px' }} onClick={e => { e.stopPropagation(); toggleRow(job.id); }}>
                    <input type="checkbox" checked={isChecked} onChange={() => toggleRow(job.id)} style={{ accentColor: '#2563EB' }} aria-label={`Select ${job.id}`} />
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs font-medium tabular-nums" style={{ color: '#2563EB', fontFamily: "'JetBrains Mono', monospace" }}>{job.id}</span>
                  </td>
                  <td style={{ padding: '8px 10px', maxWidth: '160px' }}>
                    <span className="text-xs font-medium truncate block" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>{job.migrationName}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif", whiteSpace: 'nowrap' }}>{job.source}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif", whiteSpace: 'nowrap' }}>{job.target}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <ExecStatusChip status={job.status} />
                  </td>
                  <td style={{ padding: '8px 10px', minWidth: '120px' }}>
                    <ProgressBar value={job.progress} status={job.status} />
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif", whiteSpace: 'nowrap' }}>{job.currentStage}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs tabular-nums" style={{ color: '#CBD5E1', fontFamily: "'JetBrains Mono', monospace" }}>{formatRows(job.rowsMigrated)}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs tabular-nums" style={{ color: job.throughput > 0 ? '#38BDF8' : '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>{formatThroughput(job.throughput)}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs tabular-nums" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace" }}>{job.elapsedTime}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs tabular-nums" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace" }}>{job.eta}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <PriorityChip priority={job.priority} />
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className="text-xs" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>{job.owner}</span>
                  </td>
                  <td style={{ padding: '8px 10px' }} onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-1">
                      {job.status === 'running' && (
                        <button type="button" onClick={() => onAction('pause', job)}
                          className="p-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-1"
                          style={{ color: '#F59E0B' }} title="Pause"
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(245,158,11,0.1)'; }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                        >
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M4 2.5v7M8 2.5v7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                        </button>
                      )}
                      {job.status === 'paused' && (
                        <button type="button" onClick={() => onAction('resume', job)}
                          className="p-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-1"
                          style={{ color: '#22C55E' }} title="Resume"
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(34,197,94,0.1)'; }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                        >
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 2.5l7 3.5-7 3.5V2.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /></svg>
                        </button>
                      )}
                      {job.status === 'failed' && (
                        <button type="button" onClick={() => onAction('retry', job)}
                          className="p-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-1"
                          style={{ color: '#38BDF8' }} title="Retry"
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(56,189,248,0.1)'; }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                        >
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6a4 4 0 1 0 1-2.6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /><path d="M2 2v3h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                        </button>
                      )}
                      {(job.status === 'running' || job.status === 'paused' || job.status === 'queued') && (
                        <button type="button" onClick={() => onAction('cancel', job)}
                          className="p-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-1"
                          style={{ color: '#EF4444' }} title="Cancel"
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                        >
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                        </button>
                      )}
                      <button type="button" onClick={() => onSelect(job.id)}
                        className="p-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-1"
                        style={{ color: '#64748B' }} title="View details"
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = '#94A3B8'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#64748B'; }}
                      >
                        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6s2-3.5 4-3.5S10 6 10 6s-2 3.5-4 3.5S2 6 2 6Z" stroke="currentColor" strokeWidth="1.3" /><circle cx="6" cy="6" r="1.5" stroke="currentColor" strokeWidth="1.3" /></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Detail Workspace ─────────────────────────────────────────────────────────

function DetailWorkspace({
  job, onClose, onAction,
}: {
  job: ExecutionJob;
  onClose: () => void;
  onAction: (action: string, job: ExecutionJob) => void;
}) {
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [logSearch, setLogSearch] = useState('');
  const [logLevel, setLogLevel] = useState<LogLevel | 'ALL'>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [expandedErrors, setExpandedErrors] = useState<Set<string>>(new Set());
  const [expandedCheckpoint, setExpandedCheckpoint] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [autoScroll]);

  const tabs: { id: DetailTab; label: string }[] = [
    { id: 'overview',   label: 'Overview' },
    { id: 'stages',     label: 'Stages' },
    { id: 'logs',       label: 'Logs' },
    { id: 'performance',label: 'Performance' },
    { id: 'errors',     label: `Errors${MOCK_ERRORS.length > 0 ? ` (${MOCK_ERRORS.length})` : ''}` },
    { id: 'timeline',   label: 'Timeline' },
    { id: 'rollback',   label: 'Rollback' },
    { id: 'approvals',  label: 'Approvals' },
  ];

  const filteredLogs = MOCK_LOGS.filter(l => {
    const matchLevel = logLevel === 'ALL' || l.level === logLevel;
    const matchSearch = logSearch === '' || l.message.toLowerCase().includes(logSearch.toLowerCase()) || (l.stage?.toLowerCase().includes(logSearch.toLowerCase()) ?? false);
    return matchLevel && matchSearch;
  });

  const canPause    = job.status === 'running';
  const canResume   = job.status === 'paused';
  const canCancel   = ['running', 'paused', 'queued', 'approved'].includes(job.status);
  const canRetry    = job.status === 'failed';
  const canRollback = ['failed', 'paused', 'completed'].includes(job.status);
  const canDelete   = job.status === 'completed' || job.status === 'cancelled';

  return (
    <div
      className="flex flex-col flex-shrink-0"
      style={{ width: '520px', background: 'var(--akaal-card-bg)', borderLeft: '1px solid var(--akaal-card-border)', overflow: 'hidden' }}
      aria-label="Execution detail workspace"
    >
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-card-border)' }}>
        <div className="flex-1 min-w-0 mr-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold tabular-nums" style={{ color: 'var(--akaal-primary)', fontFamily: "'JetBrains Mono', monospace" }}>{job.id}</span>
            <ExecStatusChip status={job.status} />
            <PriorityChip priority={job.priority} />
          </div>
          <p className="text-sm font-semibold truncate" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{job.migrationName}</p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{job.source} → {job.target}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: 'var(--akaal-text-muted)' }}
          aria-label="Close detail panel"
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
        </button>
      </div>

      {/* Job Controls */}
      <div className="flex items-center gap-1.5 px-4 py-2.5 flex-shrink-0 flex-wrap" style={{ borderBottom: '1px solid var(--akaal-card-border)', background: 'var(--akaal-table-header)' }}>
        {canPause && (
          <button type="button" onClick={() => onAction('pause', job)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', color: '#F59E0B', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(245,158,11,0.18)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(245,158,11,0.1)'; }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3 1.5v7M7 1.5v7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            Pause
          </button>
        )}
        {canResume && (
          <button type="button" onClick={() => onAction('resume', job)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)', color: '#22C55E', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(34,197,94,0.18)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(34,197,94,0.1)'; }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2.5 1.5l6 3.5-6 3.5V1.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /></svg>
            Resume
          </button>
        )}
        {canRetry && (
          <button type="button" onClick={() => onAction('retry', job)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.2)', color: '#38BDF8', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(56,189,248,0.18)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(56,189,248,0.1)'; }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M1.5 5a3.5 3.5 0 1 0 .8-2.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /><path d="M1.5 1.5v3h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Retry Stage
          </button>
        )}
        {canRollback && (
          <button type="button" onClick={() => onAction('rollback', job)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', color: '#F59E0B', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(245,158,11,0.18)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(245,158,11,0.1)'; }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 5h7M2 5l2.5-2.5M2 5l2.5 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Rollback
          </button>
        )}
        {canCancel && (
          <button type="button" onClick={() => onAction('cancel', job)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: '#EF4444', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.18)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2.5 2.5l5 5M7.5 2.5l-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            Cancel
          </button>
        )}
        <div className="flex items-center gap-1.5 ml-auto">
          <button type="button" onClick={() => onAction('download_logs', job)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#CBD5E1'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M5 1.5v5M2.5 4.5l2.5 2.5 2.5-2.5M1.5 8.5h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Logs
          </button>
          <button type="button" onClick={() => onAction('clone', job)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
            style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#CBD5E1'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><rect x="3.5" y="3.5" width="5" height="5" rx="0.75" stroke="currentColor" strokeWidth="1.3" /><path d="M1.5 6.5V2a.5.5 0 0 1 .5-.5h4.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
            Clone
          </button>
          {canDelete && (
            <button type="button" onClick={() => onAction('delete', job)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'transparent', border: '1px solid rgba(239,68,68,0.3)', color: '#EF4444', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M1.5 3h7M4 3V2h2v1M3 3l.5 5.5h3L7 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
              Delete
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-0 flex-shrink-0 overflow-x-auto" style={{ borderBottom: '1px solid #2A3647', background: '#0F1929' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className="flex-shrink-0 px-3 py-2.5 text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset"
            style={{
              color: activeTab === tab.id ? '#F8FAFC' : '#64748B',
              borderBottom: activeTab === tab.id ? '2px solid #2563EB' : '2px solid transparent',
              fontFamily: "'Inter', sans-serif",
              background: 'transparent',
              whiteSpace: 'nowrap',
            }}
            aria-selected={activeTab === tab.id}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {/* OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="p-4 space-y-4">
            {/* Progress */}
            <div className="rounded-lg p-3" style={{ background: '#1F2937', border: '1px solid #2A3647' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>Overall Progress</span>
                <span className="text-sm font-bold tabular-nums" style={{ color: '#F8FAFC', fontFamily: "'JetBrains Mono', monospace" }}>{job.progress}%</span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${job.progress}%`, background: job.status === 'failed' ? '#EF4444' : job.status === 'completed' ? '#22C55E' : '#2563EB' }}
                  role="progressbar" aria-valuenow={job.progress} aria-valuemin={0} aria-valuemax={100}
                />
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs tabular-nums" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{formatRows(job.rowsMigrated)} / {formatRows(job.totalRows)} rows</span>
                <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>ETA: {job.eta}</span>
              </div>
            </div>

            {/* Key metrics grid */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Execution Status', value: <ExecStatusChip status={job.status} /> },
                { label: 'Migration Strategy', value: job.strategy },
                { label: 'Batch Size', value: job.batchSize.toLocaleString() },
                { label: 'Parallel Workers', value: String(job.parallelWorkers) },
                { label: 'Current Step', value: job.currentStage },
                { label: 'Throughput', value: formatThroughput(job.throughput) },
                { label: 'Start Time', value: job.startTime },
                { label: 'Est. Completion', value: job.eta === '—' ? 'N/A' : job.eta },
                { label: 'Source Database', value: job.source },
                { label: 'Target Database', value: job.target },
                { label: 'Checkpoints', value: String(job.checkpoints) },
                { label: 'Retry Count', value: String(job.retryCount) },
              ].map(({ label, value }) => (
                <div key={label} className="rounded p-2.5" style={{ background: '#1A2333', border: '1px solid #2A3647' }}>
                  <p className="text-xs mb-1" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>{label}</p>
                  {typeof value === 'string'
                    ? <p className="text-xs font-medium" style={{ color: '#CBD5E1', fontFamily: "'JetBrains Mono', monospace" }}>{value}</p>
                    : value}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STAGES */}
        {activeTab === 'stages' && (
          <div className="p-4">
            <div className="space-y-1.5">
              {MOCK_STAGES.map((stage, idx) => {
                const cfg = STAGE_STATUS_META[stage.status];
                const isRunning = stage.status === 'running';
                return (
                  <div
                    key={stage.id}
                    className="rounded-lg p-3"
                    style={{ background: '#1F2937', border: `1px solid ${isRunning ? 'rgba(56,189,248,0.3)' : '#2A3647'}` }}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                          style={{ background: cfg.bg, color: cfg.color, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}
                          aria-hidden="true"
                        >
                          {stage.status === 'completed' ? '✓' : stage.status === 'failed' ? '✗' : idx + 1}
                        </div>
                        <span className="text-xs font-medium" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>{stage.name}</span>
                        {isRunning && <span className="text-xs" style={{ color: '#38BDF8', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', animation: 'pulse 1.5s ease-in-out infinite' }}>● LIVE</span>}
                      </div>
                      <span
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-xs"
                        style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}33`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', fontWeight: 600 }}
                      >
                        {cfg.label}
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-2 mt-2">
                      <div>
                        <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Duration</p>
                        <p className="text-xs tabular-nums" style={{ color: '#CBD5E1', fontFamily: "'JetBrains Mono', monospace" }}>{stage.duration}</p>
                      </div>
                      <div>
                        <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Rows</p>
                        <p className="text-xs tabular-nums" style={{ color: '#CBD5E1', fontFamily: "'JetBrains Mono', monospace" }}>{stage.rowsProcessed > 0 ? formatRows(stage.rowsProcessed) : '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Warnings</p>
                        <p className="text-xs tabular-nums" style={{ color: stage.warnings > 0 ? '#F59E0B' : '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>{stage.warnings}</p>
                      </div>
                      <div>
                        <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Errors</p>
                        <p className="text-xs tabular-nums" style={{ color: stage.errors > 0 ? '#EF4444' : '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>{stage.errors}</p>
                      </div>
                    </div>
                    {stage.canRetry && (
                      <button type="button" className="mt-2 text-xs px-2 py-1 rounded transition-all duration-150"
                        style={{ background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.2)', color: '#38BDF8', fontFamily: "'Inter', sans-serif" }}>
                        Retry Stage
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* LOGS */}
        {activeTab === 'logs' && (
          <div className="flex flex-col h-full">
            {/* Log toolbar */}
            <div className="flex items-center gap-2 px-3 py-2 flex-shrink-0" style={{ borderBottom: '1px solid #2A3647', background: '#0F1929' }}>
              <div className="relative flex-1">
                <svg width="11" height="11" viewBox="0 0 11 11" fill="none" aria-hidden="true" className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: '#64748B' }}>
                  <circle cx="4.5" cy="4.5" r="3" stroke="currentColor" strokeWidth="1.2" />
                  <path d="M7 7l2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                </svg>
                <input
                  type="search" placeholder="Search logs…" value={logSearch} onChange={e => setLogSearch(e.target.value)}
                  className="w-full text-xs rounded pl-6 pr-2 py-1 outline-none"
                  style={{ background: '#1A2333', border: '1px solid #2A3647', color: '#F8FAFC', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}
                  onFocus={e => { e.currentTarget.style.borderColor = '#2563EB'; }}
                  onBlur={e => { e.currentTarget.style.borderColor = '#2A3647'; }}
                />
              </div>
              <select
                value={logLevel}
                onChange={e => setLogLevel(e.target.value as LogLevel | 'ALL')}
                className="text-xs rounded px-2 py-1 outline-none"
                style={{ background: '#1A2333', border: '1px solid #2A3647', color: '#CBD5E1', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}
              >
                <option value="ALL">ALL</option>
                <option value="INFO">INFO</option>
                <option value="WARN">WARN</option>
                <option value="ERROR">ERROR</option>
                <option value="DEBUG">DEBUG</option>
                <option value="SUCCESS">SUCCESS</option>
              </select>
              <button
                type="button"
                onClick={() => setAutoScroll(v => !v)}
                className="text-xs px-2 py-1 rounded transition-all duration-150"
                style={{ background: autoScroll ? 'rgba(37,99,235,0.15)' : 'rgba(255,255,255,0.04)', border: `1px solid ${autoScroll ? 'rgba(37,99,235,0.3)' : '#2A3647'}`, color: autoScroll ? '#38BDF8' : '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
              >
                {autoScroll ? 'Auto ▼' : 'Paused'}
              </button>
              <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid #2A3647', color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                onMouseEnter={e => { e.currentTarget.style.color = '#94A3B8'; }}
                onMouseLeave={e => { e.currentTarget.style.color = '#64748B'; }}
              >
                Copy
              </button>
            </div>

            {/* Log entries */}
            <div className="flex-1 overflow-y-auto p-2 space-y-0.5" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
              {filteredLogs.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>No log entries match the current filter</p>
                </div>
              ) : filteredLogs.map(log => {
                const lvl = LOG_LEVEL_META[log.level];
                return (
                  <div
                    key={log.id}
                    className="flex items-start gap-2 px-2 py-1 rounded"
                    style={{ background: log.level === 'ERROR' ? 'rgba(239,68,68,0.04)' : 'transparent' }}
                  >
                    <span className="flex-shrink-0 tabular-nums" style={{ color: '#374151', fontSize: '9px', marginTop: '1px', minWidth: '72px' }}>{log.timestamp}</span>
                    <span
                      className="flex-shrink-0 px-1 rounded"
                      style={{ color: lvl.color, background: lvl.bg, fontSize: '9px', fontWeight: 700, letterSpacing: '0.05em', minWidth: '48px', textAlign: 'center' }}
                    >
                      {log.level}
                    </span>
                    {log.stage && (
                      <span className="flex-shrink-0 text-xs" style={{ color: '#374151', fontSize: '9px' }}>[{log.stage}]</span>
                    )}
                    <span className="flex-1 break-words" style={{ color: log.level === 'ERROR' ? '#FCA5A5' : log.level === 'WARN' ? '#FCD34D' : log.level === 'SUCCESS' ? '#86EFAC' : '#CBD5E1' }}>
                      {log.message}
                    </span>
                  </div>
                );
              })}
              <div ref={logsEndRef} />
            </div>
          </div>
        )}

        {/* PERFORMANCE */}
        {activeTab === 'performance' && (
          <div className="p-4 space-y-3">
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Current Throughput', value: formatThroughput(job.throughput), color: '#38BDF8' },
                { label: 'Peak Throughput',    value: '14.2K/s',  color: '#22C55E' },
                { label: 'Rows per Second',    value: formatThroughput(job.throughput), color: '#38BDF8' },
                { label: 'Network Speed',      value: '842 MB/s', color: '#2563EB' },
                { label: 'CPU Usage',          value: '62%',      color: '#F59E0B' },
                { label: 'Memory Usage',       value: '4.2 GB',   color: '#F59E0B' },
                { label: 'Worker Utilization', value: `${job.parallelWorkers - 1}/${job.parallelWorkers}`, color: '#22C55E' },
                { label: 'Checkpoint Freq.',   value: 'Every 10m', color: '#94A3B8' },
                { label: 'Retry Count',        value: String(job.retryCount), color: job.retryCount > 0 ? '#F59E0B' : '#64748B' },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded p-2.5" style={{ background: '#1A2333', border: '1px solid #2A3647' }}>
                  <p className="text-xs mb-1" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>{label}</p>
                  <p className="text-sm font-bold tabular-nums" style={{ color, fontFamily: "'JetBrains Mono', monospace" }}>{value}</p>
                </div>
              ))}
            </div>

            {/* Throughput sparkline */}
            <div className="rounded-lg p-3" style={{ background: '#1F2937', border: '1px solid #2A3647' }}>
              <p className="text-xs font-medium mb-3" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>Throughput History</p>
              <div className="flex items-end gap-1" style={{ height: '48px' }}>
                {[8200, 9100, 11400, 12400, 10800, 13200, 12400, 11900, 12800, 12400, 13100, 12400].map((v, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-sm"
                    style={{ height: `${(v / 14000) * 100}%`, background: '#2563EB', opacity: i === 11 ? 1 : 0.4 + (i / 12) * 0.4, minHeight: '2px' }}
                    aria-hidden="true"
                  />
                ))}
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-xs" style={{ color: '#374151', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>-60m</span>
                <span className="text-xs" style={{ color: '#374151', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>now</span>
              </div>
            </div>
          </div>
        )}

        {/* ERRORS */}
        {activeTab === 'errors' && (
          <div className="p-4 space-y-3">
            {MOCK_ERRORS.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="w-8 h-8 rounded-full flex items-center justify-center mb-2" style={{ background: 'rgba(34,197,94,0.1)' }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" style={{ color: '#22C55E' }}>
                    <path d="M3 8l3.5 3.5L13 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <p className="text-xs font-medium" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>No errors recorded</p>
                <p className="text-xs mt-0.5" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>This execution is running cleanly</p>
              </div>
            ) : MOCK_ERRORS.map(err => {
              const isExpanded = expandedErrors.has(err.id);
              const sevColor = err.severity === 'critical' ? '#EF4444' : err.severity === 'high' ? '#F59E0B' : err.severity === 'medium' ? '#F59E0B' : '#94A3B8';
              return (
                <div key={err.id} className="rounded-lg overflow-hidden" style={{ border: `1px solid ${sevColor}33`, background: '#1F2937' }}>
                  <div className="p-3">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold tabular-nums" style={{ color: sevColor, fontFamily: "'JetBrains Mono', monospace" }}>{err.errorCode}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: sevColor, background: `${sevColor}18`, border: `1px solid ${sevColor}33`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', fontWeight: 600, textTransform: 'uppercase' }}>{err.severity}</span>
                      </div>
                      <span className="text-xs tabular-nums flex-shrink-0" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{err.timestamp}</span>
                    </div>
                    <p className="text-xs mb-1" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Stage: {err.stage}</p>
                    <p className="text-xs mb-2" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif", lineHeight: '1.5' }}>{err.description}</p>
                    <div className="rounded p-2 mb-2" style={{ background: '#1A2333', border: '1px solid #2A3647' }}>
                      <p className="text-xs mb-0.5" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Suggested Resolution</p>
                      <p className="text-xs" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif", lineHeight: '1.5' }}>{err.resolution}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs" style={{ color: err.canRetry ? '#22C55E' : '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>
                        {err.canRetry ? '✓ Retry available' : '✗ No retry'}
                      </span>
                      <span className="text-xs" style={{ color: err.requiresRollback ? '#EF4444' : '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>
                        {err.requiresRollback ? '⚠ Rollback required' : '✓ No rollback needed'}
                      </span>
                      <button
                        type="button"
                        onClick={() => setExpandedErrors(prev => { const n = new Set(prev); isExpanded ? n.delete(err.id) : n.add(err.id); return n; })}
                        className="ml-auto text-xs transition-colors"
                        style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                        onMouseEnter={e => { e.currentTarget.style.color = '#94A3B8'; }}
                        onMouseLeave={e => { e.currentTarget.style.color = '#64748B'; }}
                      >
                        {isExpanded ? 'Hide trace ▲' : 'Stack trace ▼'}
                      </button>
                    </div>
                    {isExpanded && (
                      <pre className="mt-2 p-2 rounded text-xs overflow-x-auto" style={{ background: '#0B1220', border: '1px solid #2A3647', color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', lineHeight: '1.6' }}>
                        {err.stackTrace}
                      </pre>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* TIMELINE */}
        {activeTab === 'timeline' && (
          <div className="p-4">
            <div className="relative">
              <div className="absolute left-3.5 top-0 bottom-0 w-px" style={{ background: '#2A3647' }} aria-hidden="true" />
              <div className="space-y-0">
                {MOCK_TIMELINE.map((event, idx) => {
                  const colorMap = { info: '#38BDF8', success: '#22C55E', warning: '#F59E0B', error: '#EF4444' };
                  const color = colorMap[event.severity];
                  return (
                    <div key={event.id} className="flex items-start gap-3 pb-4 relative">
                      <div
                        className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center z-10"
                        style={{ background: `${color}18`, border: `1px solid ${color}44` }}
                        aria-hidden="true"
                      >
                        <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                      </div>
                      <div className="flex-1 pt-1 pb-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-medium" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>{event.description}</p>
                          <span className="text-xs tabular-nums flex-shrink-0" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{event.timestamp}</span>
                        </div>
                        {event.actor && (
                          <p className="text-xs mt-0.5" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>by {event.actor}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ROLLBACK */}
        {activeTab === 'rollback' && (
          <div className="p-4 space-y-4">
            {/* Readiness */}
            <div className="rounded-lg p-3" style={{ background: '#1F2937', border: '1px solid #2A3647' }}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>Rollback Readiness</p>
                <span className="text-xs px-2 py-0.5 rounded" style={{ color: '#22C55E', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>Ready</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Checkpoints Available', value: String(job.checkpoints) },
                  { label: 'Est. Rollback Time',    value: '~12 min' },
                  { label: 'Affected Objects',      value: '142 tables' },
                  { label: 'Rollback Strategy',     value: 'Checkpoint Restore' },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded p-2" style={{ background: '#1A2333', border: '1px solid #2A3647' }}>
                    <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>{label}</p>
                    <p className="text-xs font-medium mt-0.5" style={{ color: '#CBD5E1', fontFamily: "'JetBrains Mono', monospace" }}>{value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Checkpoints */}
            <div>
              <p className="text-xs font-semibold mb-2" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>Available Checkpoints</p>
              <div className="space-y-1.5">
                {MOCK_CHECKPOINTS.map(cp => (
                  <div
                    key={cp.id}
                    className="flex items-center justify-between rounded p-2.5 cursor-pointer transition-all duration-150"
                    style={{ background: expandedCheckpoint === cp.id ? 'rgba(37,99,235,0.08)' : '#1A2333', border: `1px solid ${expandedCheckpoint === cp.id ? 'rgba(37,99,235,0.3)' : '#2A3647'}` }}
                    onClick={() => setExpandedCheckpoint(prev => prev === cp.id ? null : cp.id)}
                  >
                    <div>
                      <p className="text-xs font-medium" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>{cp.name}</p>
                      <p className="text-xs mt-0.5" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cp.timestamp} · {formatRows(cp.rowsAt)} rows · {cp.size}</p>
                    </div>
                    <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cp.stage}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Rollback button */}
            <div className="rounded-lg p-3" style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.15)' }}>
              <p className="text-xs mb-2" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif", lineHeight: '1.5' }}>
                Initiating a rollback will restore the target database to the selected checkpoint state. This action cannot be undone.
              </p>
              <button
                type="button"
                onClick={() => onAction('rollback', job)}
                className="flex items-center gap-2 px-3 py-2 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ background: '#EF4444', color: '#fff', border: 'none', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = '#DC2626'; }}
                onMouseLeave={e => { e.currentTarget.style.background = '#EF4444'; }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6h8M2 6l3-3M2 6l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                Initiate Rollback
              </button>
            </div>
          </div>
        )}

        {/* APPROVALS */}
        {activeTab === 'approvals' && (
          <div className="p-4 space-y-3">
            {MOCK_APPROVALS.map(ap => (
              <div key={ap.id} className="rounded-lg p-3" style={{ background: '#1F2937', border: '1px solid #2A3647' }}>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>{ap.type}</p>
                  <span
                    className="text-xs px-2 py-0.5 rounded"
                    style={{
                      color: ap.status === 'approved' ? '#22C55E' : ap.status === 'rejected' ? '#EF4444' : '#F59E0B',
                      background: ap.status === 'approved' ? 'rgba(34,197,94,0.08)' : ap.status === 'rejected' ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)',
                      border: `1px solid ${ap.status === 'approved' ? 'rgba(34,197,94,0.2)' : ap.status === 'rejected' ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)'}`,
                      fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: 600, textTransform: 'uppercase',
                    }}
                  >
                    {ap.status}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <div>
                    <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Requested By</p>
                    <p className="text-xs font-medium mt-0.5" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>{ap.requestedBy}</p>
                    <p className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{ap.requestedAt}</p>
                  </div>
                  {ap.approvedBy && (
                    <div>
                      <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>Approved By</p>
                      <p className="text-xs font-medium mt-0.5" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>{ap.approvedBy}</p>
                      <p className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{ap.approvedAt}</p>
                    </div>
                  )}
                </div>
                {ap.notes && (
                  <div className="rounded p-2" style={{ background: '#1A2333', border: '1px solid #2A3647' }}>
                    <p className="text-xs" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif", lineHeight: '1.5', fontSize: '11px' }}>{ap.notes}</p>
                  </div>
                )}
              </div>
            ))}

            {/* Audit history */}
            <div>
              <p className="text-xs font-semibold mb-2" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>Audit History</p>
              <div className="space-y-1">
                {[
                  { actor: 'p.nair', action: 'DBA sign-off granted', time: '14:05:00' },
                  { actor: 'j.okafor', action: 'Production approval granted', time: '14:08:40' },
                  { actor: 'sarah.chen', action: 'Approval request submitted', time: '13:50:00' },
                ].map((entry, i) => (
                  <div key={i} className="flex items-center justify-between px-2.5 py-2 rounded" style={{ background: '#1A2333', border: '1px solid #2A3647' }}>
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0" style={{ background: '#2563EB', color: '#fff', fontFamily: "'Inter', sans-serif", fontSize: '8px' }} aria-hidden="true">
                        {entry.actor.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-xs font-medium" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>{entry.action}</p>
                        <p className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>by {entry.actor}</p>
                      </div>
                    </div>
                    <span className="text-xs tabular-nums" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{entry.time}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ExecutionCenterPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [jobs, setJobs] = useState<ExecutionJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [envFilter, setEnvFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [confirm, setConfirm] = useState<{ open: boolean; title: string; message: string; confirmLabel: string; danger?: boolean; onConfirm: () => void } | null>(null);
  const [liveUpdateTick, setLiveUpdateTick] = useState(0);
  const [lastUpdated, setLastUpdated] = useState('');

  useEffect(() => {
    const t = setTimeout(() => {
      setJobs(MOCK_JOBS);
      setLoading(false);
    }, 900);
    return () => clearTimeout(t);
  }, []);

  // Deep linking: Read initial job or status from query parameters
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const jobParam = params.get('job');
      const statusParam = params.get('status');
      if (jobParam) setSelectedJobId(jobParam);
      if (statusParam) setStatusFilter(statusParam);
    }
  }, []);

  // Set initial lastUpdated time on client only
  useEffect(() => {
    setLastUpdated(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
  }, []);

  // Live update simulation
  useEffect(() => {
    const interval = setInterval(() => {
      setLiveUpdateTick(t => t + 1);
      setLastUpdated(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
      setJobs(prev => prev.map(job => {
        if (job.status === 'running' && job.progress < 99) {
          return { ...job, progress: Math.min(99, job.progress + Math.floor(Math.random() * 2)), rowsMigrated: job.rowsMigrated + Math.floor(Math.random() * 5000) };
        }
        return job;
      }));
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1200);
  }, []);

  const handleAction = useCallback((action: string, job: ExecutionJob) => {
    const destructive: Record<string, { title: string; message: string; confirmLabel: string; danger?: boolean }> = {
      cancel:   { title: 'Cancel Execution', message: `Cancel execution ${job.id} (${job.migrationName})? This will stop all workers and mark the job as cancelled. Progress will be preserved for potential restart.`, confirmLabel: 'Cancel Execution', danger: true },
      rollback: { title: 'Initiate Rollback', message: `Roll back execution ${job.id}? This will restore the target database to the last checkpoint. Estimated rollback time: ~12 minutes. This action cannot be undone.`, confirmLabel: 'Initiate Rollback', danger: true },
      delete:   { title: 'Delete Execution', message: `Permanently delete execution record ${job.id}? All logs, checkpoints, and execution history will be removed. This action cannot be undone.`, confirmLabel: 'Delete', danger: true },
      pause:    { title: 'Pause Execution', message: `Pause execution ${job.id}? Workers will complete their current batch and then suspend. The job can be resumed at any time.`, confirmLabel: 'Pause Execution' },
    };

    if (destructive[action]) {
      setConfirm({
        open: true,
        ...destructive[action],
        onConfirm: () => {
          setConfirm(null);
          if (action === 'pause') setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'paused' as ExecStatus, throughput: 0 } : j));
          if (action === 'cancel') setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'cancelled' as ExecStatus, throughput: 0 } : j));
        },
      });
    } else if (action === 'resume') {
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'running' as ExecStatus, throughput: 8200 } : j));
    } else if (action === 'retry') {
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'retrying' as ExecStatus } : j));
    } else if (action === 'clone') {
      const clonedJob: ExecutionJob = {
        ...job,
        id: `EX-${Math.floor(2860 + Math.random() * 100)}`,
        migrationName: `${job.migrationName} (Clone)`,
        status: 'queued',
        progress: 0,
        rowsMigrated: 0,
        throughput: 0,
        elapsedTime: '00:00:00',
        eta: 'Calculating…',
      };
      setJobs(prev => [clonedJob, ...prev]);
      setSelectedJobId(clonedJob.id);
    }
  }, []);

  const filteredJobs = jobs.filter(job => {
    if (statusFilter !== 'all' && job.status !== statusFilter) return false;
    if (envFilter !== 'all' && job.environment !== envFilter) return false;
    if (typeFilter !== 'all' && job.migrationType !== typeFilter) return false;
    if (priorityFilter !== 'all' && job.priority !== priorityFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!job.id.toLowerCase().includes(q) && !job.migrationName.toLowerCase().includes(q) && !job.owner.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const selectedJob = jobs.find(j => j.id === selectedJobId) ?? null;

  return (
    <>
      <style>{`
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #2A3647; border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: #374151; }
      `}</style>

      <div
        className="flex h-screen overflow-hidden"
        style={{
          background: 'var(--akaal-bg)',
          backgroundImage: 'radial-gradient(ellipse 80% 60% at 10% 0%, rgba(37,99,235,0.07) 0%, transparent 60%), radial-gradient(ellipse 50% 40% at 90% 0%, rgba(56,189,248,0.04) 0%, transparent 50%)',
        }}
      >
        <AppSidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />

        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <TopNav />

          {/* Page Header */}
          <div
            className="flex items-center justify-between px-5 py-3 flex-shrink-0"
            style={{ background: '#111827', borderBottom: '1px solid #2A3647' }}
          >
            <div>
              <h1 className="text-base font-bold" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>Execution Center</h1>
              <p className="text-xs mt-0.5" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>Monitor, control and manage all migration executions.</p>
            </div>
            <div className="flex items-center gap-2">
              {/* Live indicator */}
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded" style={{ background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.2)' }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#38BDF8', animation: 'pulse 1.5s ease-in-out infinite' }} aria-hidden="true" />
                <span className="text-xs" style={{ color: '#38BDF8', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>LIVE</span>
              </div>
              <button
                type="button"
                onClick={handleRefresh}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
                aria-label="Refresh"
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#CBD5E1'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ animation: isRefreshing ? 'spin 0.8s linear infinite' : 'none' }}>
                  <path d="M1.5 6a4.5 4.5 0 1 0 1-2.8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                  <path d="M1.5 2v3h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Refresh
              </button>
              <button
                type="button"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#CBD5E1'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M2 9h8M2 6h6M2 3h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
                Export Report
              </button>
              <Link
                href="/migration-workspace"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ background: '#2563EB', color: '#fff', border: 'none', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = '#1D4ED8'; }}
                onMouseLeave={e => { e.currentTarget.style.background = '#2563EB'; }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M6 1.5v9M1.5 6h9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                Launch Migration
              </Link>
            </div>
          </div>

          {/* Content area */}
          <div className="flex flex-1 min-h-0 overflow-hidden">
            {/* Filter Panel */}
            <FilterPanel
              statusFilter={statusFilter} onStatusFilter={setStatusFilter}
              envFilter={envFilter} onEnvFilter={setEnvFilter}
              typeFilter={typeFilter} onTypeFilter={setTypeFilter}
              priorityFilter={priorityFilter} onPriorityFilter={setPriorityFilter}
              searchQuery={searchQuery} onSearch={setSearchQuery}
              onClear={() => { setStatusFilter('all'); setEnvFilter('all'); setTypeFilter('all'); setPriorityFilter('all'); setSearchQuery(''); }}
            />

            {/* Main content */}
            <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Metric Cards */}
                <MetricCards jobs={jobs} loading={loading} />

                {/* Execution Table */}
                <Card>
                  <SectionHeader
                    title="Execution Queue"
                    subtitle={`${filteredJobs.length} execution${filteredJobs.length !== 1 ? 's' : ''} · Last updated ${lastUpdated}`}
                    action={
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
                          {jobs.filter(j => j.status === 'running').length} running · {jobs.filter(j => j.status === 'failed').length} failed
                        </span>
                      </div>
                    }
                  />
                  <div className="p-3">
                    <ExecutionTable
                      jobs={filteredJobs}
                      loading={loading}
                      selectedId={selectedJobId}
                      onSelect={id => setSelectedJobId(prev => prev === id ? null : id)}
                      onAction={handleAction}
                    />
                  </div>
                </Card>
              </div>
            </div>

            {/* Detail Workspace */}
            {selectedJob && (
              <DetailWorkspace
                job={selectedJob}
                onClose={() => setSelectedJobId(null)}
                onAction={handleAction}
              />
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirm && (
        <ConfirmModal
          open={confirm.open}
          title={confirm.title}
          message={confirm.message}
          confirmLabel={confirm.confirmLabel}
          danger={confirm.danger}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
        />
      )}
    </>
  );
}
