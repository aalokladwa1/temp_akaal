'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { AreaChart, Area, Tooltip, ResponsiveContainer } from 'recharts';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';

// ─── Types ────────────────────────────────────────────────────────────────────

type MigrationStatus = 'running' | 'paused' | 'failed' | 'completed' | 'queued' | 'retrying' | 'rolling_back';
type HealthStatus = 'healthy' | 'degraded' | 'critical' | 'offline' | 'unknown';
type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | 'SUCCESS';
type AlertSeverity = 'critical' | 'warning' | 'info' | 'resolved';
type InspectorTab = 'overview' | 'performance' | 'logs' | 'database' | 'worker' | 'timeline' | 'errors';

interface LiveMigration {
  id: string;
  name: string;
  stage: string;
  progress: number;
  rowsMigrated: number;
  totalRows: number;
  rowsPerSec: number;
  latency: number;
  worker: string;
  checkpoint: string;
  elapsed: string;
  eta: string;
  status: MigrationStatus;
  health: 'good' | 'warn' | 'critical';
  source: string;
  target: string;
  owner: string;
  startTime: string;
  cpuUsage: number;
  memUsage: number;
  retryCount: number;
}

interface SystemService {
  name: string;
  status: HealthStatus;
  latency?: number;
  uptime?: string;
}

interface LiveEvent {
  id: string;
  timestamp: string;
  type: string;
  description: string;
  migration?: string;
  severity: 'info' | 'success' | 'warning' | 'error';
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
}

interface Agent {
  id: string;
  name: string;
  version: string;
  status: 'connected' | 'disconnected' | 'degraded';
  cpu: number;
  memory: number;
  network: string;
  runningJobs: number;
  lastHeartbeat: string;
  host: string;
}

interface QueueStat {
  name: string;
  count: number;
  avgWait: string;
  color: string;
}

interface Checkpoint {
  id: string;
  migration: string;
  timestamp: string;
  rowsAt: number;
  size: string;
  interval: string;
  restoreAvailable: boolean;
  lastRestoreTest: string;
}

interface Alert {
  id: string;
  severity: AlertSeverity;
  title: string;
  detail: string;
  migration?: string;
  time: string;
  acknowledged: boolean;
  muted: boolean;
}

interface PerfDataPoint {
  t: string;
  cpu: number;
  mem: number;
  net: number;
  disk: number;
  rows: number;
  queue: number;
  cdcLag: number;
  workers: number;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_MIGRATIONS: LiveMigration[] = [
  { id: 'MIG-2847', name: 'prod-oracle-to-postgres', stage: 'Data Migration', progress: 67, rowsMigrated: 4_820_441, totalRows: 7_194_000, rowsPerSec: 12_400, latency: 2.1, worker: 'worker-01', checkpoint: 'CP-12', elapsed: '1h 55m', eta: '58m', status: 'running', health: 'good', source: 'Oracle 19c', target: 'PostgreSQL 15', owner: 'sarah.chen', startTime: '14:22', cpuUsage: 72, memUsage: 58, retryCount: 0 },
  { id: 'MIG-2851', name: 'dw-redshift-consolidation', stage: 'Schema Migration', progress: 12, rowsMigrated: 480_000, totalRows: 4_000_000, rowsPerSec: 8_200, latency: 3.4, worker: 'worker-03', checkpoint: 'CP-02', elapsed: '19m', eta: '2h 41m', status: 'running', health: 'warn', source: 'Redshift', target: 'BigQuery', owner: 'sarah.chen', startTime: '15:58', cpuUsage: 45, memUsage: 41, retryCount: 0 },
  { id: 'MIG-2854', name: 'finance-db-cdc-stream', stage: 'Data Migration', progress: 44, rowsMigrated: 3_080_000, totalRows: 7_000_000, rowsPerSec: 3_100, latency: 8.7, worker: 'worker-02', checkpoint: 'CP-08', elapsed: '1h 12m', eta: '1h 05m', status: 'retrying', health: 'critical', source: 'MySQL 5.7', target: 'PostgreSQL 15', owner: 'finance.ops', startTime: '15:05', cpuUsage: 88, memUsage: 76, retryCount: 3 },
  { id: 'MIG-2852', name: 'iot-timescale-archive', stage: 'Data Migration', progress: 51, rowsMigrated: 15_300_000, totalRows: 30_000_000, rowsPerSec: 0, latency: 0, worker: 'worker-04', checkpoint: 'CP-18', elapsed: '2h 41m', eta: 'Paused', status: 'paused', health: 'warn', source: 'TimescaleDB', target: 'ClickHouse', owner: 'dev.ops', startTime: '09:30', cpuUsage: 0, memUsage: 22, retryCount: 0 },
  { id: 'MIG-2849', name: 'legacy-mssql-migration', stage: 'Data Migration', progress: 34, rowsMigrated: 1_240_000, totalRows: 3_650_000, rowsPerSec: 0, latency: 0, worker: 'worker-02', checkpoint: 'CP-04', elapsed: '32m', eta: '—', status: 'failed', health: 'critical', source: 'SQL Server 2019', target: 'Azure SQL', owner: 'priya.nair', startTime: '13:45', cpuUsage: 0, memUsage: 0, retryCount: 2 },
  { id: 'MIG-2853', name: 'hr-oracle-schema-sync', stage: 'Schema Validation', progress: 8, rowsMigrated: 0, totalRows: 2_100_000, rowsPerSec: 0, latency: 1.2, worker: 'worker-05', checkpoint: '—', elapsed: '4m', eta: '~1h 20m', status: 'queued', health: 'good', source: 'Oracle 12c', target: 'PostgreSQL 14', owner: 'hr.admin', startTime: '16:13', cpuUsage: 12, memUsage: 18, retryCount: 0 },
];

const MOCK_SERVICES: SystemService[] = [
  { name: 'API',           status: 'healthy',  latency: 12,  uptime: '99.98%' },
  { name: 'Scheduler',     status: 'healthy',  latency: 8,   uptime: '99.95%' },
  { name: 'Workers',       status: 'degraded', latency: 142, uptime: '97.2%' },
  { name: 'Database',      status: 'healthy',  latency: 4,   uptime: '99.99%' },
  { name: 'CDC',           status: 'degraded', latency: 220, uptime: '96.8%' },
  { name: 'Message Queue', status: 'healthy',  latency: 6,   uptime: '99.97%' },
  { name: 'Storage',       status: 'healthy',  latency: 18,  uptime: '99.9%' },
  { name: 'Auth',          status: 'healthy',  latency: 9,   uptime: '100%' },
  { name: 'Notifications', status: 'healthy',  latency: 22,  uptime: '99.8%' },
];

const MOCK_EVENTS: LiveEvent[] = [
  { id: 'ev1',  timestamp: '16:17:02', type: 'checkpoint',   description: 'Checkpoint CP-12 saved — 4,820,441 rows committed',        migration: 'MIG-2847', severity: 'info' },
  { id: 'ev2',  timestamp: '16:16:44', type: 'retry',        description: 'Retry attempt #3 initiated on finance-db-cdc-stream',       migration: 'MIG-2854', severity: 'warning' },
  { id: 'ev3',  timestamp: '16:15:30', type: 'cdc_delay',    description: 'CDC lag spike detected — 4.2s replication delay on ORDERS', migration: 'MIG-2847', severity: 'warning' },
  { id: 'ev4',  timestamp: '16:14:12', type: 'validation',   description: 'Schema validation completed — 0 blocking issues',           migration: 'MIG-2853', severity: 'success' },
  { id: 'ev5',  timestamp: '16:12:55', type: 'paused',       description: 'Migration paused by operator dev.ops',                      migration: 'MIG-2852', severity: 'info' },
  { id: 'ev6',  timestamp: '16:11:20', type: 'failed',       description: 'Execution failed — constraint violation on ORDERS table',   migration: 'MIG-2849', severity: 'error' },
  { id: 'ev7',  timestamp: '16:09:00', type: 'started',      description: 'Migration started — dw-redshift-consolidation',             migration: 'MIG-2851', severity: 'info' },
  { id: 'ev8',  timestamp: '16:08:40', type: 'approval',     description: 'Production approval granted by j.okafor@akaal.io',         migration: 'MIG-2847', severity: 'success' },
  { id: 'ev9',  timestamp: '16:05:00', type: 'queue_warn',   description: 'Queue depth exceeded threshold — 847 pending jobs',         severity: 'warning' },
  { id: 'ev10', timestamp: '16:02:18', type: 'worker',       description: 'Worker worker-06 restarted after health check failure',     severity: 'warning' },
  { id: 'ev11', timestamp: '15:58:00', type: 'started',      description: 'Migration started — prod-oracle-to-postgres',               migration: 'MIG-2847', severity: 'info' },
  { id: 'ev12', timestamp: '15:45:00', type: 'recovery',     description: 'Connection recovered — finance-db-cdc-stream resumed',      migration: 'MIG-2854', severity: 'success' },
];

const MOCK_LOGS: LogEntry[] = [
  { id: 'lg1',  timestamp: '16:17:02.441', level: 'INFO',    message: 'Checkpoint CP-12 saved — offset 4,820,441 rows committed',                  source: 'MIG-2847' },
  { id: 'lg2',  timestamp: '16:16:58.112', level: 'DEBUG',   message: 'Worker pool utilization: 7/8 active threads on worker-01',                  source: 'worker-01' },
  { id: 'lg3',  timestamp: '16:16:44.009', level: 'WARN',    message: 'Retry attempt #3 initiated — CDC stream reconnection in progress',           source: 'MIG-2854' },
  { id: 'lg4',  timestamp: '16:16:30.882', level: 'INFO',    message: 'Batch 482 completed — 10,000 rows in 0.81s (12,345 rows/s)',                 source: 'MIG-2847' },
  { id: 'lg5',  timestamp: '16:15:30.001', level: 'WARN',    message: 'CDC lag spike detected — replication delay 4.2s on table ORDERS',           source: 'CDC' },
  { id: 'lg6',  timestamp: '16:14:12.334', level: 'SUCCESS', message: 'Schema validation completed — 142 tables, 28 views, 14 functions validated', source: 'MIG-2853' },
  { id: 'lg7',  timestamp: '16:12:55.221', level: 'INFO',    message: 'Migration paused by operator — iot-timescale-archive suspended',             source: 'MIG-2852' },
  { id: 'lg8',  timestamp: '16:11:20.009', level: 'ERROR',   message: 'Execution failed — ORA-02291: integrity constraint violation on ORDERS',     source: 'MIG-2849' },
  { id: 'lg9',  timestamp: '16:10:44.009', level: 'INFO',    message: 'Schema migration completed — 142 tables, 28 views, 14 functions migrated',   source: 'MIG-2851' },
  { id: 'lg10', timestamp: '16:09:30.118', level: 'DEBUG',   message: 'Connection pool established — 8 workers connected to target BigQuery',       source: 'MIG-2851' },
  { id: 'lg11', timestamp: '16:09:00.000', level: 'INFO',    message: 'Execution started — MIG-2851 dw-redshift-consolidation',                     source: 'system' },
  { id: 'lg12', timestamp: '16:08:55.441', level: 'SUCCESS', message: 'Pre-flight checks passed — all systems ready for MIG-2847',                  source: 'system' },
  { id: 'lg13', timestamp: '16:05:00.002', level: 'WARN',    message: 'Queue depth threshold exceeded — 847 pending jobs in priority queue',        source: 'scheduler' },
  { id: 'lg14', timestamp: '16:02:18.334', level: 'WARN',    message: 'Worker worker-06 health check failed — restarting process',                  source: 'worker-06' },
  { id: 'lg15', timestamp: '16:02:22.001', level: 'INFO',    message: 'Worker worker-06 restarted successfully — rejoining pool',                   source: 'worker-06' },
];

const MOCK_AGENTS: Agent[] = [
  { id: 'ag1', name: 'worker-01', version: '2.4.1', status: 'connected', cpu: 72, memory: 58, network: '1.2 GB/s', runningJobs: 2, lastHeartbeat: '2s ago', host: 'prod-worker-01.akaal.io' },
  { id: 'ag2', name: 'worker-02', version: '2.4.1', status: 'degraded',  cpu: 88, memory: 76, network: '0.4 GB/s', runningJobs: 1, lastHeartbeat: '8s ago', host: 'prod-worker-02.akaal.io' },
  { id: 'ag3', name: 'worker-03', version: '2.4.0', status: 'connected', cpu: 45, memory: 41, network: '0.8 GB/s', runningJobs: 1, lastHeartbeat: '1s ago', host: 'prod-worker-03.akaal.io' },
  { id: 'ag4', name: 'worker-04', version: '2.4.1', status: 'connected', cpu: 12, memory: 22, network: '0.1 GB/s', runningJobs: 0, lastHeartbeat: '3s ago', host: 'prod-worker-04.akaal.io' },
  { id: 'ag5', name: 'worker-05', version: '2.4.1', status: 'connected', cpu: 18, memory: 24, network: '0.2 GB/s', runningJobs: 1, lastHeartbeat: '2s ago', host: 'prod-worker-05.akaal.io' },
  { id: 'ag6', name: 'worker-06', version: '2.3.9', status: 'disconnected', cpu: 0, memory: 0, network: '—',       runningJobs: 0, lastHeartbeat: '4m ago', host: 'prod-worker-06.akaal.io' },
];

const MOCK_QUEUES: QueueStat[] = [
  { name: 'Queued Jobs',    count: 12,  avgWait: '4m 20s',  color: '#38BDF8' },
  { name: 'Retry Queue',    count: 5,   avgWait: '1m 12s',  color: '#F59E0B' },
  { name: 'Dead Letter',    count: 3,   avgWait: '—',       color: '#EF4444' },
  { name: 'CDC Queue',      count: 847, avgWait: '0.8s',    color: '#2563EB' },
  { name: 'Priority Queue', count: 2,   avgWait: '0m 30s',  color: '#22C55E' },
];

const MOCK_CHECKPOINTS: Checkpoint[] = [
  { id: 'cp1', migration: 'MIG-2847', timestamp: '16:17:02', rowsAt: 4_820_441, size: '2.4 MB', interval: '10 min', restoreAvailable: true, lastRestoreTest: '2026-07-24 08:00' },
  { id: 'cp2', migration: 'MIG-2851', timestamp: '16:09:00', rowsAt: 480_000,   size: '0.3 MB', interval: '10 min', restoreAvailable: true, lastRestoreTest: '2026-07-24 08:00' },
  { id: 'cp3', migration: 'MIG-2854', timestamp: '15:55:00', rowsAt: 3_080_000, size: '1.8 MB', interval: '10 min', restoreAvailable: true, lastRestoreTest: '2026-07-23 20:00' },
  { id: 'cp4', migration: 'MIG-2852', timestamp: '12:11:00', rowsAt: 15_300_000,size: '8.2 MB', interval: '10 min', restoreAvailable: true, lastRestoreTest: '2026-07-24 08:00' },
];

const MOCK_ALERTS: Alert[] = [
  { id: 'al1', severity: 'critical', title: 'Execution Failed',       detail: 'MIG-2849 legacy-mssql-migration failed with constraint violation', migration: 'MIG-2849', time: '7m ago',  acknowledged: false, muted: false },
  { id: 'al2', severity: 'critical', title: 'Worker Degraded',        detail: 'worker-02 CPU at 88% — performance impact on active migrations',   time: '12m ago', acknowledged: false, muted: false },
  { id: 'al3', severity: 'warning',  title: 'CDC Lag Spike',          detail: 'MIG-2847 replication delay 4.2s — threshold 2.0s',                 migration: 'MIG-2847', time: '15m ago', acknowledged: false, muted: false },
  { id: 'al4', severity: 'warning',  title: 'Queue Depth Threshold',  detail: 'CDC queue depth 847 — exceeds warning threshold of 500',           time: '27m ago', acknowledged: true,  muted: false },
  { id: 'al5', severity: 'info',     title: 'Worker Restarted',       detail: 'worker-06 restarted after health check failure — now offline',     time: '30m ago', acknowledged: true,  muted: false },
  { id: 'al6', severity: 'resolved', title: 'Connection Recovered',   detail: 'MIG-2854 CDC stream reconnected after 3 retry attempts',           migration: 'MIG-2854', time: '45m ago', acknowledged: true,  muted: false },
];

function generatePerfData(): PerfDataPoint[] {
  const now = Date.now();
  return Array.from({ length: 30 }, (_, i) => {
    const t = new Date(now - (29 - i) * 10_000);
    const h = t.getHours().toString().padStart(2, '0');
    const m = t.getMinutes().toString().padStart(2, '0');
    const s = t.getSeconds().toString().padStart(2, '0');
    return {
      t: `${h}:${m}:${s}`,
      cpu:     40 + Math.round(Math.sin(i * 0.4) * 20 + Math.random() * 10),
      mem:     55 + Math.round(Math.sin(i * 0.2) * 10 + Math.random() * 5),
      net:     60 + Math.round(Math.cos(i * 0.3) * 25 + Math.random() * 15),
      disk:    30 + Math.round(Math.sin(i * 0.5) * 15 + Math.random() * 8),
      rows:    12000 + Math.round(Math.sin(i * 0.6) * 3000 + Math.random() * 1000),
      queue:   800 + Math.round(Math.sin(i * 0.3) * 200 + Math.random() * 100),
      cdcLag:  2 + Math.round(Math.sin(i * 0.7) * 3 + Math.random() * 2),
      workers: 6 + Math.round(Math.sin(i * 0.2) * 1),
    };
  });
}

// ─── Status/Health Config ─────────────────────────────────────────────────────

const MIGRATION_STATUS_META: Record<MigrationStatus, { label: string; color: string; bg: string; border: string; animated: boolean }> = {
  running:      { label: 'Running',      color: '#38BDF8', bg: 'rgba(56,189,248,0.12)',  border: 'rgba(56,189,248,0.2)',  animated: true },
  paused:       { label: 'Paused',       color: '#F59E0B', bg: 'rgba(245,158,11,0.12)',  border: 'rgba(245,158,11,0.2)',  animated: false },
  failed:       { label: 'Failed',       color: '#EF4444', bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.2)',   animated: false },
  completed:    { label: 'Completed',    color: '#22C55E', bg: 'rgba(34,197,94,0.12)',   border: 'rgba(34,197,94,0.2)',   animated: false },
  queued:       { label: 'Queued',       color: '#94A3B8', bg: 'rgba(148,163,184,0.12)', border: 'rgba(148,163,184,0.2)', animated: false },
  retrying:     { label: 'Retrying',     color: '#F59E0B', bg: 'rgba(245,158,11,0.12)',  border: 'rgba(245,158,11,0.2)',  animated: true },
  rolling_back: { label: 'Rolling Back', color: '#F59E0B', bg: 'rgba(245,158,11,0.12)',  border: 'rgba(245,158,11,0.2)',  animated: true },
};

const HEALTH_META: Record<HealthStatus, { label: string; color: string; bg: string; border: string }> = {
  healthy:  { label: 'Healthy',  color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)' },
  degraded: { label: 'Degraded', color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)' },
  critical: { label: 'Critical', color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)' },
  offline:  { label: 'Offline',  color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)' },
  unknown:  { label: 'Unknown',  color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)' },
};

const LOG_LEVEL_META: Record<LogLevel, { color: string; bg: string }> = {
  INFO:    { color: '#38BDF8', bg: 'rgba(56,189,248,0.08)' },
  WARN:    { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)' },
  ERROR:   { color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
  DEBUG:   { color: '#64748B', bg: 'rgba(100,116,139,0.08)' },
  SUCCESS: { color: '#22C55E', bg: 'rgba(34,197,94,0.08)' },
};

const ALERT_META: Record<AlertSeverity, { color: string; bg: string; border: string; label: string }> = {
  critical: { color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)',   label: 'Critical' },
  warning:  { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  label: 'Warning' },
  info:     { color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  border: 'rgba(56,189,248,0.2)',  label: 'Info' },
  resolved: { color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)',   label: 'Resolved' },
};

const AGENT_STATUS_META: Record<Agent['status'], { color: string; bg: string; border: string; label: string }> = {
  connected:    { color: '#22C55E', bg: 'rgba(34,197,94,0.08)',   border: 'rgba(34,197,94,0.2)',   label: 'Connected' },
  degraded:     { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  label: 'Degraded' },
  disconnected: { color: '#EF4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.2)',   label: 'Offline' },
};

// ─── Utility Components ───────────────────────────────────────────────────────

function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded ${className ?? ''}`}
      style={{ background: 'linear-gradient(90deg, var(--akaal-skeleton-base) 25%, var(--akaal-skeleton-shine) 50%, var(--akaal-skeleton-base) 75%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s infinite', ...style }}
      aria-hidden="true"
    />
  );
}

function StatusChip({ status }: { status: HealthStatus }) {
  const cfg = HEALTH_META[status];
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color, animation: status === 'degraded' || status === 'critical' ? 'pulse 1.5s ease-in-out infinite' : 'none' }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function MigStatusChip({ status }: { status: MigrationStatus }) {
  const cfg = MIGRATION_STATUS_META[status];
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color, animation: cfg.animated ? 'pulse 1.5s ease-in-out infinite' : 'none' }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function HealthDot({ health }: { health: 'good' | 'warn' | 'critical' }) {
  const color = health === 'good' ? '#22C55E' : health === 'warn' ? '#F59E0B' : '#EF4444';
  return <span className="w-2 h-2 rounded-full flex-shrink-0 inline-block" style={{ background: color }} aria-label={`Health: ${health}`} />;
}

function ProgressBar({ value, status }: { value: number; status: MigrationStatus }) {
  const color = status === 'failed' ? '#EF4444' : status === 'completed' ? '#22C55E' : status === 'paused' ? '#F59E0B' : '#2563EB';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-border)', minWidth: '50px' }}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${value}%`, background: color }} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} aria-label={`${value}% complete`} />
      </div>
      <span className="text-xs tabular-nums flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{value}%</span>
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
        <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif" }}>{title}</h2>
        {subtitle && <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>{subtitle}</p>}
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

function UsageBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'var(--akaal-border)' }}>
        <div className="h-full rounded-full" style={{ width: `${value}%`, background: color }} />
      </div>
      <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', minWidth: '28px', textAlign: 'right' }}>{value}%</span>
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function AppSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const navItems = [
    { href: '/dashboard',          label: 'Dashboard',     active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/migrations', label: 'Migrations',   active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/execution-center',    label: 'Execution',    active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M6 5.5l5 2.5-5 2.5V5.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { href: '/databases',           label: 'Databases',    active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="6" ry="2" stroke="currentColor" strokeWidth="1.3" /><path d="M2 4v4c0 1.1 2.7 2 6 2s6-.9 6-2V4" stroke="currentColor" strokeWidth="1.3" /><path d="M2 8v4c0 1.1 2.7 2 6 2s6-.9 6-2V8" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/live-monitor',        label: 'Live Monitor', active: true,  icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M4 8l2-2 2 2 2-3 2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/agents',              label: 'Agents',       active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/reports',             label: 'Reports',      active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/system',              label: 'System',       active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="3" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="4.5" r="0.8" fill="currentColor" /><circle cx="4" cy="9.5" r="0.8" fill="currentColor" /><path d="M5 13h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/settings',            label: 'Settings',     active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.4 3.4l.85.85M11.75 11.75l.85.85M3.4 12.6l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
  ];

  return (
    <aside className="flex flex-col flex-shrink-0 h-full" style={{ width: collapsed ? '56px' : '220px', background: 'var(--akaal-sidebar-gradient)', borderRight: '1px solid var(--akaal-sidebar-border)', transition: 'width 0.2s ease', overflow: 'hidden' }} aria-label="Main navigation">
      <div className="flex items-center gap-3 px-3 py-4 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-sidebar-border)', minHeight: '57px' }}>
        <AppImage src="/assets/images/app_logo.png" alt="AKAAL" width={28} height={28} className="flex-shrink-0" style={{ filter: 'drop-shadow(0 1px 4px rgba(37,99,235,0.3))' }} />
        {!collapsed && <span className="font-bold tracking-widest uppercase text-sm" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono',monospace", letterSpacing: '0.15em', whiteSpace: 'nowrap' }}>AKAAL</span>}
      </div>
      <nav className="flex-1 py-3 overflow-y-auto" aria-label="Primary navigation">
        <ul className="space-y-0.5 px-2" role="list">
          {navItems.map(item => (
            <li key={item.href}>
              <Link href={item.href} className="flex items-center gap-3 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ color: item.active ? 'var(--akaal-text)' : 'var(--akaal-text-muted)', background: item.active ? 'var(--akaal-primary-subtle)' : 'transparent', borderLeft: item.active ? '2px solid var(--akaal-primary)' : '2px solid transparent', fontFamily: "'Inter',sans-serif", whiteSpace: 'nowrap' }}
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

function TopNav({ breadcrumb }: { breadcrumb: string }) {
  const [searchValue, setSearchValue] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="flex items-center gap-4 px-4 flex-shrink-0" style={{ height: '57px', background: 'var(--akaal-nav-bg)', borderBottom: '1px solid var(--akaal-nav-border)' }} role="banner">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 flex-shrink-0">
        <Link href="/dashboard" className="text-xs transition-colors" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }} onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}>Platform</Link>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif" }}>{breadcrumb}</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
          <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <input type="search" placeholder="Search migrations, agents…" value={searchValue} onChange={e => setSearchValue(e.target.value)}
          className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
          style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif" }}
          aria-label="Global search"
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
        />
        <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs px-1 rounded" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-hover-bg)', border: '1px solid var(--akaal-border)', fontFamily: "'JetBrains Mono',monospace", fontSize: '9px' }}>⌘K</kbd>
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
            <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}><p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif" }}>Notifications</p></div>
            {[
              { title: 'Execution Failed', detail: 'MIG-2849 legacy-mssql-migration — constraint violation', time: '7m ago', color: 'var(--akaal-error)' },
              { title: 'CDC Lag Warning',  detail: 'MIG-2847 prod-oracle-to-postgres — 4.2s delay',         time: '15m ago', color: 'var(--akaal-warning)' },
              { title: 'Worker Degraded',  detail: 'worker-02 CPU at 88% — performance impact',             time: '12m ago', color: 'var(--akaal-warning)' },
            ].map((n, i) => (
              <div key={i} className="px-3 py-2.5 transition-colors cursor-pointer" style={{ borderBottom: i < 2 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                <div className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: n.color }} aria-hidden="true" />
                  <div>
                    <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter',sans-serif" }}>{n.title}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>{n.detail}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{n.time}</p>
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
          <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter',sans-serif" }} aria-hidden="true">SC</div>
          <span className="text-xs font-medium hidden sm:block" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter',sans-serif" }}>sarah.chen</span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
        </button>
        {profileOpen && (
          <div className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50" style={{ width: '200px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }} role="menu" aria-label="User menu">
            <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif" }}>sarah.chen</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>Platform Administrator</p>
            </div>
            {[
              { label: 'Profile Settings', href: '/settings' },
              { label: 'API Keys', href: '/settings' },
              { label: 'Audit Log', href: '/reports' },
              { label: 'Sign Out', href: '/sign-in' },
            ].map((item, i) => (
              <Link key={i} href={item.href} onClick={() => setProfileOpen(false)} role="menuitem" className="block w-full text-left px-3 py-2 text-xs transition-colors"
                style={{ color: item.label === 'Sign Out' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", borderBottom: i < 3 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
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

// ─── Inspector Panel ──────────────────────────────────────────────────────────

function InspectorPanel({ migration, onClose }: { migration: LiveMigration; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<InspectorTab>('overview');
  const tabs: { id: InspectorTab; label: string }[] = [
    { id: 'overview', label: 'Overview' }, { id: 'performance', label: 'Performance' },
    { id: 'logs', label: 'Logs' }, { id: 'database', label: 'Database' },
    { id: 'worker', label: 'Worker' }, { id: 'timeline', label: 'Timeline' },
    { id: 'errors', label: 'Errors' },
  ];

  const inspectorLogs = MOCK_LOGS.filter(l => l.source === migration.id).slice(0, 8);
  const inspectorTimeline = MOCK_EVENTS.filter(e => e.migration === migration.id);

  return (
    <div className="flex flex-col h-full" style={{ width: '380px', background: 'var(--akaal-surface)', borderLeft: '1px solid var(--akaal-border)', flexShrink: 0 }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        <div className="min-w-0">
          <p className="text-xs font-semibold truncate" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif" }}>{migration.name}</p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{migration.id}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <MigStatusChip status={migration.status} />
          <button type="button" onClick={onClose} className="w-6 h-6 flex items-center justify-center rounded transition-all" style={{ color: 'var(--akaal-text-muted)' }} aria-label="Close inspector"
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
          </button>
        </div>
      </div>
      {/* Tabs */}
      <div className="flex overflow-x-auto flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        {tabs.map(tab => (
          <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)}
            className="px-3 py-2 text-xs font-medium flex-shrink-0 transition-all duration-150 focus:outline-none"
            style={{ color: activeTab === tab.id ? 'var(--akaal-text)' : 'var(--akaal-text-muted)', borderBottom: activeTab === tab.id ? '2px solid var(--akaal-primary)' : '2px solid transparent', fontFamily: "'Inter',sans-serif", background: 'transparent' }}
          >{tab.label}</button>
        ))}
      </div>
      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === 'overview' && (
          <>
            <div>
              <p className="text-xs font-medium mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>PROGRESS</p>
              <ProgressBar value={migration.progress} status={migration.status} />
              <div className="flex justify-between mt-1">
                <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{formatRows(migration.rowsMigrated)} / {formatRows(migration.totalRows)} rows</span>
                <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>ETA: {migration.eta}</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Source',      value: migration.source },
                { label: 'Target',      value: migration.target },
                { label: 'Stage',       value: migration.stage },
                { label: 'Worker',      value: migration.worker },
                { label: 'Checkpoint',  value: migration.checkpoint },
                { label: 'Elapsed',     value: migration.elapsed },
                { label: 'Rows/sec',    value: formatThroughput(migration.rowsPerSec) },
                { label: 'Latency',     value: migration.latency > 0 ? `${migration.latency}ms` : '—' },
                { label: 'Owner',       value: migration.owner },
                { label: 'Start Time',  value: migration.startTime },
                { label: 'Retries',     value: String(migration.retryCount) },
                { label: 'Health',      value: migration.health.toUpperCase() },
              ].map((f, i) => (
                <div key={i} className="rounded p-2" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                  <p style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '10px' }}>{f.label}</p>
                  <p className="mt-0.5 truncate" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', fontWeight: 500 }}>{f.value}</p>
                </div>
              ))}
            </div>
          </>
        )}
        {activeTab === 'performance' && (
          <div className="space-y-3">
            {[
              { label: 'CPU Usage',    value: migration.cpuUsage,  color: '#38BDF8', unit: '%' },
              { label: 'Memory Usage', value: migration.memUsage,  color: '#22C55E', unit: '%' },
              { label: 'Rows/sec',     value: Math.round(migration.rowsPerSec / 100), color: '#2563EB', unit: 'K/s' },
            ].map((m, i) => (
              <div key={i} className="rounded p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <div className="flex justify-between mb-1.5">
                  <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '11px' }}>{m.label}</span>
                  <span style={{ color: m.color, fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', fontWeight: 600 }}>{m.value}{m.unit}</span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-border)' }}>
                  <div className="h-full rounded-full" style={{ width: `${Math.min(m.value, 100)}%`, background: m.color }} />
                </div>
              </div>
            ))}
            <div className="rounded p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '11px', marginBottom: '8px' }}>Throughput</p>
              <p style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono',monospace", fontSize: '18px', fontWeight: 700 }}>{formatThroughput(migration.rowsPerSec)}</p>
              <p style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '10px', marginTop: '2px' }}>rows per second</p>
            </div>
          </div>
        )}
        {activeTab === 'logs' && (
          <div className="space-y-1">
            {inspectorLogs.length === 0 ? (
              <p className="text-xs text-center py-6" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>No logs for this migration.</p>
            ) : inspectorLogs.map(log => (
              <div key={log.id} className="rounded p-2" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="px-1.5 py-0.5 rounded text-xs font-medium" style={{ color: LOG_LEVEL_META[log.level].color, background: LOG_LEVEL_META[log.level].bg, fontFamily: "'JetBrains Mono',monospace", fontSize: '9px' }}>{log.level}</span>
                  <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '9px' }}>{log.timestamp}</span>
                </div>
                <p style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', lineHeight: '1.5', wordBreak: 'break-all' }}>{log.message}</p>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'database' && (
          <div className="space-y-3">
            {[
              { label: 'Source Database', items: [{ k: 'Type', v: migration.source }, { k: 'Status', v: 'Connected' }, { k: 'Latency', v: `${migration.latency}ms` }] },
              { label: 'Target Database', items: [{ k: 'Type', v: migration.target }, { k: 'Status', v: 'Connected' }, { k: 'Latency', v: '1.2ms' }] },
            ].map((db, i) => (
              <div key={i} className="rounded p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <p className="text-xs font-medium mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>{db.label}</p>
                {db.items.map((item, j) => (
                  <div key={j} className="flex justify-between py-1" style={{ borderBottom: j < db.items.length - 1 ? '1px solid var(--akaal-border-subtle)' : 'none' }}>
                    <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '11px' }}>{item.k}</span>
                    <span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px' }}>{item.v}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
        {activeTab === 'worker' && (
          <div className="space-y-3">
            <div className="rounded p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <p className="text-xs font-medium mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>Assigned Worker</p>
              <p style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono',monospace", fontSize: '13px', fontWeight: 600 }}>{migration.worker}</p>
            </div>
            {[
              { label: 'CPU',    value: migration.cpuUsage,  color: '#38BDF8' },
              { label: 'Memory', value: migration.memUsage,  color: '#22C55E' },
            ].map((m, i) => (
              <div key={i} className="rounded p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <div className="flex justify-between mb-1.5">
                  <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '11px' }}>{m.label}</span>
                  <span style={{ color: m.color, fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', fontWeight: 600 }}>{m.value}%</span>
                </div>
                <UsageBar value={m.value} color={m.color} />
              </div>
            ))}
          </div>
        )}
        {activeTab === 'timeline' && (
          <div className="space-y-2">
            {inspectorTimeline.length === 0 ? (
              <p className="text-xs text-center py-6" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>No timeline events.</p>
            ) : inspectorTimeline.map((ev, i) => {
              const color = ev.severity === 'error' ? '#EF4444' : ev.severity === 'warning' ? '#F59E0B' : ev.severity === 'success' ? '#22C55E' : '#38BDF8';
              return (
                <div key={ev.id} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="w-2 h-2 rounded-full flex-shrink-0 mt-1" style={{ background: color }} />
                    {i < inspectorTimeline.length - 1 && <div className="w-px flex-1 mt-1" style={{ background: 'var(--akaal-border-subtle)' }} />}
                  </div>
                  <div className="pb-3 min-w-0">
                    <p style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter',sans-serif", fontSize: '11px', lineHeight: '1.4' }}>{ev.description}</p>
                    <p style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', marginTop: '2px' }}>{ev.timestamp}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {activeTab === 'errors' && (
          <div className="space-y-2">
            {MOCK_LOGS.filter(l => l.level === 'ERROR' && l.source === migration.id).length === 0 ? (
              <div className="text-center py-8">
                <p className="text-xs" style={{ color: '#22C55E', fontFamily: "'Inter',sans-serif" }}>No errors recorded.</p>
              </div>
            ) : MOCK_LOGS.filter(l => l.level === 'ERROR').slice(0, 3).map(log => (
              <div key={log.id} className="rounded p-3" style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.15)' }}>
                <div className="flex items-center gap-2 mb-1">
                  <span style={{ color: '#EF4444', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', fontWeight: 600 }}>ERROR</span>
                  <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{log.timestamp}</span>
                </div>
                <p style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', lineHeight: '1.5' }}>{log.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function LiveMonitorPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [liveUpdates, setLiveUpdates] = useState(true);
  const [lastUpdated, setLastUpdated] = useState('');
  const [selectedMigration, setSelectedMigration] = useState<LiveMigration | null>(null);
  const [migrations, setMigrations] = useState<LiveMigration[]>([]);
  const [events, setEvents] = useState<LiveEvent[]>(MOCK_EVENTS);
  const [logs, setLogs] = useState<LogEntry[]>(MOCK_LOGS);
  const [perfData, setPerfData] = useState<PerfDataPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>(MOCK_ALERTS);
  const [logSearch, setLogSearch] = useState('');
  const [logLevel, setLogLevel] = useState<LogLevel | 'ALL'>('ALL');
  const [logAutoScroll, setLogAutoScroll] = useState(true);
  const [migSearch, setMigSearch] = useState('');
  const [migSortCol, setMigSortCol] = useState<string>('id');
  const [migSortDir, setMigSortDir] = useState<'asc' | 'desc'>('asc');
  const [alertFilter, setAlertFilter] = useState<AlertSeverity | 'all'>('all');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const eventContainerRef = useRef<HTMLDivElement>(null);
  const tickRef = useRef(0);

  useEffect(() => {
    const t = setTimeout(() => {
      setMigrations(MOCK_MIGRATIONS);
      setPerfData(generatePerfData());
      setLoading(false);
      setLastUpdated(new Date().toLocaleTimeString());
    }, 1200);
    return () => clearTimeout(t);
  }, []);

  // Live update simulation
  useEffect(() => {
    if (!liveUpdates || loading) return;
    const interval = setInterval(() => {
      tickRef.current += 1;
      setLastUpdated(new Date().toLocaleTimeString());
      setMigrations(prev => prev.map(m => {
        if (m.status !== 'running') return m;
        const newProgress = Math.min(m.progress + Math.random() * 0.3, 99);
        const newRows = m.rowsMigrated + Math.round(m.rowsPerSec * 3 + Math.random() * 500);
        return { ...m, progress: Math.round(newProgress * 10) / 10, rowsMigrated: Math.min(newRows, m.totalRows) };
      }));
      setPerfData(prev => {
        const now = new Date();
        const h = now.getHours().toString().padStart(2, '0');
        const mn = now.getMinutes().toString().padStart(2, '0');
        const s = now.getSeconds().toString().padStart(2, '0');
        const newPoint: PerfDataPoint = {
          t: `${h}:${mn}:${s}`,
          cpu:     40 + Math.round(Math.sin(tickRef.current * 0.4) * 20 + Math.random() * 10),
          mem:     55 + Math.round(Math.sin(tickRef.current * 0.2) * 10 + Math.random() * 5),
          net:     60 + Math.round(Math.cos(tickRef.current * 0.3) * 25 + Math.random() * 15),
          disk:    30 + Math.round(Math.sin(tickRef.current * 0.5) * 15 + Math.random() * 8),
          rows:    12000 + Math.round(Math.sin(tickRef.current * 0.6) * 3000 + Math.random() * 1000),
          queue:   800 + Math.round(Math.sin(tickRef.current * 0.3) * 200 + Math.random() * 100),
          cdcLag:  2 + Math.round(Math.sin(tickRef.current * 0.7) * 3 + Math.random() * 2),
          workers: 6 + Math.round(Math.sin(tickRef.current * 0.2) * 1),
        };
        return [...prev.slice(-29), newPoint];
      });
      // Occasionally add a new event
      if (tickRef.current % 5 === 0) {
        const newEvent: LiveEvent = {
          id: `ev-live-${tickRef.current}`,
          timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
          type: 'checkpoint',
          description: `Checkpoint saved — ${formatRows(4_820_441 + tickRef.current * 37200)} rows committed`,
          migration: 'MIG-2847',
          severity: 'info',
        };
        setEvents(prev => [newEvent, ...prev.slice(0, 19)]);
        const newLog: LogEntry = {
          id: `lg-live-${tickRef.current}`,
          timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }) + '.000',
          level: 'INFO',
          message: `Batch ${482 + tickRef.current} completed — 10,000 rows processed`,
          source: 'MIG-2847',
        };
        setLogs(prev => [newLog, ...prev.slice(0, 49)]);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [liveUpdates, loading]);

  // Auto-scroll logs
  useEffect(() => {
    if (logAutoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = 0;
    }
  }, [logs, logAutoScroll]);

  const filteredLogs = logs.filter(l => {
    const matchLevel = logLevel === 'ALL' || l.level === logLevel;
    const matchSearch = !logSearch || l.message.toLowerCase().includes(logSearch.toLowerCase()) || (l.source ?? '').toLowerCase().includes(logSearch.toLowerCase());
    return matchLevel && matchSearch;
  });

  const filteredMigrations = migrations.filter(m =>
    !migSearch || m.name.toLowerCase().includes(migSearch.toLowerCase()) || m.id.toLowerCase().includes(migSearch.toLowerCase())
  );

  const sortedMigrations = [...filteredMigrations].sort((a, b) => {
    let av: string | number = a[migSortCol as keyof LiveMigration] as string | number;
    let bv: string | number = b[migSortCol as keyof LiveMigration] as string | number;
    if (typeof av === 'string') av = av.toLowerCase();
    if (typeof bv === 'string') bv = bv.toLowerCase();
    if (av < bv) return migSortDir === 'asc' ? -1 : 1;
    if (av > bv) return migSortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const handleSort = (col: string) => {
    if (migSortCol === col) setMigSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setMigSortCol(col); setMigSortDir('asc'); }
  };

  const filteredAlerts = alertFilter === 'all' ? alerts : alerts.filter(a => a.severity === alertFilter);

  const activeMigrations = migrations.filter(m => m.status === 'running').length;
  const connectedAgents = MOCK_AGENTS.filter(a => a.status === 'connected').length;
  const avgRowsPerSec = migrations.filter(m => m.rowsPerSec > 0).reduce((s, m) => s + m.rowsPerSec, 0) / Math.max(1, migrations.filter(m => m.rowsPerSec > 0).length);
  const queueDepth = MOCK_QUEUES.reduce((s, q) => s + q.count, 0);
  const cdcStreams = migrations.filter(m => m.status === 'running').length;
  const avgLatency = migrations.filter(m => m.latency > 0).reduce((s, m) => s + m.latency, 0) / Math.max(1, migrations.filter(m => m.latency > 0).length);
  const avgCpu = MOCK_AGENTS.filter(a => a.status !== 'disconnected').reduce((s, a) => s + a.cpu, 0) / Math.max(1, MOCK_AGENTS.filter(a => a.status !== 'disconnected').length);
  const avgMem = MOCK_AGENTS.filter(a => a.status !== 'disconnected').reduce((s, a) => s + a.memory, 0) / Math.max(1, MOCK_AGENTS.filter(a => a.status !== 'disconnected').length);

  const topMetrics = [
    { label: 'Active Migrations', value: loading ? '—' : String(activeMigrations),              accent: '#38BDF8', sub: 'Currently running' },
    { label: 'Connected Agents',  value: loading ? '—' : `${connectedAgents}/${MOCK_AGENTS.length}`, accent: '#22C55E', sub: 'Agent pool' },
    { label: 'Rows/sec',          value: loading ? '—' : formatThroughput(Math.round(avgRowsPerSec)), accent: '#2563EB', sub: 'Aggregate throughput' },
    { label: 'Queue Depth',       value: loading ? '—' : String(queueDepth),                    accent: '#F59E0B', sub: 'Total queued items' },
    { label: 'CDC Streams',       value: loading ? '—' : String(cdcStreams),                     accent: '#38BDF8', sub: 'Active streams' },
    { label: 'Avg Latency',       value: loading ? '—' : `${avgLatency.toFixed(1)}ms`,           accent: '#94A3B8', sub: 'Source latency' },
    { label: 'CPU Usage',         value: loading ? '—' : `${Math.round(avgCpu)}%`,               accent: avgCpu > 80 ? '#EF4444' : avgCpu > 60 ? '#F59E0B' : '#22C55E', sub: 'Worker average' },
    { label: 'Memory Usage',      value: loading ? '—' : `${Math.round(avgMem)}%`,               accent: avgMem > 80 ? '#EF4444' : avgMem > 60 ? '#F59E0B' : '#22C55E', sub: 'Worker average' },
    { label: 'Disk Usage',        value: loading ? '—' : '42%',                                  accent: '#94A3B8', sub: 'Storage utilization' },
    { label: 'Net Throughput',    value: loading ? '—' : '3.2 GB/s',                             accent: '#2563EB', sub: 'Network I/O' },
  ];

  const SortIcon = ({ col }: { col: string }) => (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" style={{ opacity: migSortCol === col ? 1 : 0.3 }}>
      <path d={migSortDir === 'asc' && migSortCol === col ? 'M2 6l3-3 3 3' : 'M2 4l3 3 3-3'} stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );

  const chartTooltipStyle = { background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', borderRadius: '6px', fontSize: '10px', fontFamily: "'JetBrains Mono',monospace", color: 'var(--akaal-text)' };

  return (
    <div className={`flex h-screen overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50' : ''}`} style={{ background: 'var(--akaal-bg)' }}>
      <style>{`
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes slideIn { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }
        .live-monitor-table th { position: sticky; top: 0; z-index: 1; }
        .live-monitor-table tr:hover td { background: rgba(255,255,255,0.02); }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
      `}</style>

      <AppSidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />

      <div className="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
        <TopNav breadcrumb="Live Monitor" />

        {/* Page Header */}
        <div className="flex items-center justify-between px-6 py-3 flex-shrink-0" style={{ background: 'var(--akaal-nav-bg)', borderBottom: '1px solid var(--akaal-nav-border)' }}>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-base font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif" }}>Live Monitor</h1>
              {liveUpdates && !loading && (
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', color: '#22C55E', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#22C55E', animation: 'pulse 1.5s ease-in-out infinite' }} aria-hidden="true" />
                  LIVE
                </span>
              )}
            </div>
            <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>
              Real-time enterprise migration monitoring and observability.
              {lastUpdated && <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', marginLeft: '8px' }}>Updated {lastUpdated}</span>}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => { setLoading(true); setTimeout(() => { setMigrations(MOCK_MIGRATIONS); setPerfData(generatePerfData()); setLoading(false); setLastUpdated(new Date().toLocaleTimeString()); }, 800); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'transparent', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}
              aria-label="Refresh"
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M10 6A4 4 0 1 1 6 2M10 2v4H6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
              Refresh
            </button>
            <button type="button" onClick={() => setLiveUpdates(v => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: liveUpdates ? 'rgba(34,197,94,0.08)' : 'transparent', border: `1px solid ${liveUpdates ? 'rgba(34,197,94,0.2)' : 'var(--akaal-border)'}`, color: liveUpdates ? '#22C55E' : 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}
              aria-label={liveUpdates ? 'Pause live updates' : 'Resume live updates'}
              aria-pressed={liveUpdates}
            >
              {liveUpdates ? (
                <><svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M4 2v8M8 2v8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>Pause Live</>
              ) : (
                <><svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 2l7 4-7 4V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg>Resume Live</>
              )}
            </button>
            <button type="button"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'transparent', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}
              aria-label="Export snapshot"
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1v7M3 5l3 3 3-3M2 10h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
              Export Snapshot
            </button>
            <button type="button" onClick={() => setIsFullscreen(v => !v)}
              className="flex items-center justify-center w-8 h-8 rounded transition-all duration-150 focus:outline-none focus-visible:ring-2"
              style={{ background: 'transparent', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-muted)' }}
              aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
            >
              {isFullscreen
                ? <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M4 1v3H1M8 1v3h3M4 11v-3H1M8 11v-3h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                : <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M1 4V1h3M8 1h3v3M11 8v3H8M4 11H1V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
              }
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex flex-1 min-h-0 overflow-hidden">
          <div className="flex-1 overflow-y-auto min-w-0">
            <div className="p-4 space-y-4">

              {/* Top Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-2">
                {topMetrics.map((m, i) => (
                  <div key={i} className="rounded-lg p-3" style={{ background: 'var(--akaal-card-bg)', border: '1px solid var(--akaal-card-border)' }}>
                    {loading ? (
                      <>
                        <Skeleton style={{ width: '100%', height: '20px', marginBottom: '6px' }} />
                        <Skeleton style={{ width: '60%', height: '10px' }} />
                      </>
                    ) : (
                      <>
                        <p className="text-xs font-bold tabular-nums" style={{ color: m.accent, fontFamily: "'JetBrains Mono',monospace", fontSize: '16px', lineHeight: '1.2' }}>{m.value}</p>
                        <p className="text-xs mt-1 leading-tight" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '10px' }}>{m.label}</p>
                      </>
                    )}
                  </div>
                ))}
              </div>

              {/* System Health Strip */}
              <Card>
                <SectionHeader title="System Health" subtitle="Service status across the platform" />
                <div className="px-4 py-3">
                  {loading ? (
                    <div className="flex flex-wrap gap-3">
                      {MOCK_SERVICES.map((_, i) => <Skeleton key={i} style={{ width: '100px', height: '28px', borderRadius: '6px' }} />)}
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-3">
                      {MOCK_SERVICES.map(svc => (
                        <div key={svc.name} className="flex items-center gap-2 rounded px-3 py-1.5" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                          <StatusChip status={svc.status} />
                          <span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter',sans-serif", fontSize: '11px', fontWeight: 500 }}>{svc.name}</span>
                          {svc.latency && <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{svc.latency}ms</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>

              {/* Live Migration Grid */}
              <Card>
                <SectionHeader
                  title="Live Migration Grid"
                  subtitle={`${sortedMigrations.length} migrations`}
                  action={
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: '#64748B' }}>
                          <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
                          <path d="M8 8l2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                        </svg>
                        <input type="search" placeholder="Search…" value={migSearch} onChange={e => setMigSearch(e.target.value)}
                          className="text-xs rounded pl-6 pr-2 py-1 outline-none"
                          style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif", width: '140px' }}
                          aria-label="Search migrations"
                          onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; }}
                          onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; }}
                        />
                      </div>
                    </div>
                  }
                />
                <div className="overflow-x-auto">
                  {loading ? (
                    <div className="p-4 space-y-2">
                      {[1,2,3,4].map(i => <Skeleton key={i} style={{ width: '100%', height: '36px' }} />)}
                    </div>
                  ) : sortedMigrations.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12">
                      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-text-muted)', marginBottom: '8px' }}>
                        <rect x="4" y="4" width="24" height="24" rx="4" stroke="currentColor" strokeWidth="1.5" />
                        <path d="M10 16h12M16 10v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                      <p className="text-sm" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>No migrations match your search.</p>
                    </div>
                  ) : (
                    <table className="w-full live-monitor-table" aria-label="Live migration grid">
                      <thead>
                        <tr style={{ background: 'var(--akaal-table-header)' }}>
                          {[
                            { col: 'id', label: 'Migration' }, { col: 'stage', label: 'Stage' }, { col: 'progress', label: 'Progress' },
                            { col: 'rowsMigrated', label: 'Rows Migrated' }, { col: 'rowsPerSec', label: 'Rows/sec' },
                            { col: 'latency', label: 'Latency' }, { col: 'worker', label: 'Worker' },
                            { col: 'checkpoint', label: 'Checkpoint' }, { col: 'elapsed', label: 'Elapsed' },
                            { col: 'eta', label: 'ETA' }, { col: 'health', label: 'Health' }, { col: '_actions', label: '' },
                          ].map(h => (
                            <th key={h.col} className="px-3 py-2 text-left" style={{ background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)' }}>
                              {h.col !== '_actions' ? (
                                <button type="button" onClick={() => handleSort(h.col)} className="flex items-center gap-1 focus:outline-none" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '10px', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', background: 'none', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                                  {h.label} <SortIcon col={h.col} />
                                </button>
                              ) : null}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {sortedMigrations.map(m => (
                          <tr key={m.id} onClick={() => setSelectedMigration(m)} className="cursor-pointer transition-colors" style={{ borderBottom: '1px solid var(--akaal-table-border)' }}>
                            <td className="px-3 py-2">
                              <div>
                                <p style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', fontWeight: 500, whiteSpace: 'nowrap' }}>{m.name}</p>
                                <p style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{m.id}</p>
                              </div>
                            </td>
                            <td className="px-3 py-2">
                              <div>
                                <MigStatusChip status={m.status} />
                                <p className="mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", fontSize: '10px', whiteSpace: 'nowrap' }}>{m.stage}</p>
                              </div>
                            </td>
                            <td className="px-3 py-2" style={{ minWidth: '120px' }}>
                              <ProgressBar value={m.progress} status={m.status} />
                            </td>
                            <td className="px-3 py-2">
                              <span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', whiteSpace: 'nowrap' }}>{formatRows(m.rowsMigrated)}</span>
                              <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}> / {formatRows(m.totalRows)}</span>
                            </td>
                            <td className="px-3 py-2">
                              <span style={{ color: m.rowsPerSec > 0 ? '#38BDF8' : 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', whiteSpace: 'nowrap' }}>{formatThroughput(m.rowsPerSec)}</span>
                            </td>
                            <td className="px-3 py-2">
                              <span style={{ color: m.latency > 5 ? '#F59E0B' : m.latency > 0 ? '#22C55E' : 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', whiteSpace: 'nowrap' }}>{m.latency > 0 ? `${m.latency}ms` : '—'}</span>
                            </td>
                            <td className="px-3 py-2">
                              <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', whiteSpace: 'nowrap' }}>{m.worker}</span>
                            </td>
                            <td className="px-3 py-2">
                              <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', whiteSpace: 'nowrap' }}>{m.checkpoint}</span>
                            </td>
                            <td className="px-3 py-2">
                              <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', whiteSpace: 'nowrap' }}>{m.elapsed}</span>
                            </td>
                            <td className="px-3 py-2">
                              <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '11px', whiteSpace: 'nowrap' }}>{m.eta}</span>
                            </td>
                            <td className="px-3 py-2">
                              <HealthDot health={m.health} />
                            </td>
                            <td className="px-3 py-2">
                              <button type="button" onClick={e => { e.stopPropagation(); setSelectedMigration(m); }}
                                className="px-2 py-1 rounded text-xs transition-all focus:outline-none focus-visible:ring-2"
                                style={{ background: 'rgba(37,99,235,0.1)', border: '1px solid rgba(37,99,235,0.2)', color: '#2563EB', fontFamily: "'Inter',sans-serif", whiteSpace: 'nowrap' }}
                                aria-label={`Inspect ${m.name}`}
                                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(37,99,235,0.2)'; }}
                                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(37,99,235,0.1)'; }}
                              >Inspect</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </Card>

              {/* Event Stream + Log Viewer */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Real-Time Event Stream */}
                <Card>
                  <SectionHeader title="Real-Time Event Stream" subtitle="Live platform events" action={
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded" style={{ background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.2)', color: '#38BDF8', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#38BDF8', animation: liveUpdates ? 'pulse 1.5s ease-in-out infinite' : 'none' }} aria-hidden="true" />
                      Streaming
                    </span>
                  } />
                  <div ref={eventContainerRef} className="overflow-y-auto" style={{ maxHeight: '320px' }} aria-live="polite" aria-label="Event stream">
                    {loading ? (
                      <div className="p-3 space-y-2">
                        {[1,2,3,4,5].map(i => <Skeleton key={i} style={{ width: '100%', height: '44px' }} />)}
                      </div>
                    ) : (
                      <div className="divide-y" style={{ borderColor: 'var(--akaal-border-subtle)' }}>
                        {events.map((ev, i) => {
                          const color = ev.severity === 'error' ? '#EF4444' : ev.severity === 'warning' ? '#F59E0B' : ev.severity === 'success' ? '#22C55E' : '#38BDF8';
                          const typeLabel: Record<string, string> = { checkpoint: 'CHECKPOINT', retry: 'RETRY', cdc_delay: 'CDC DELAY', validation: 'VALIDATION', paused: 'PAUSED', failed: 'FAILED', started: 'STARTED', approval: 'APPROVAL', queue_warn: 'QUEUE WARN', worker: 'WORKER', recovery: 'RECOVERY' };
                          return (
                            <div key={ev.id} className="flex items-start gap-3 px-4 py-2.5" style={{ animation: i === 0 ? 'slideIn 0.3s ease' : 'none' }}>
                              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: color }} aria-hidden="true" />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="px-1.5 py-0.5 rounded" style={{ color, background: `${color}18`, fontFamily: "'JetBrains Mono',monospace", fontSize: '9px', fontWeight: 600, letterSpacing: '0.06em', flexShrink: 0 }}>{typeLabel[ev.type] ?? ev.type.toUpperCase()}</span>
                                  {ev.migration && <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{ev.migration}</span>}
                                </div>
                                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif", lineHeight: '1.4' }}>{ev.description}</p>
                              </div>
                              <span className="flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{ev.timestamp}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </Card>

                {/* Live Log Viewer */}
                <Card>
                  <SectionHeader title="Live Log Viewer" subtitle="Platform-wide log stream" action={
                    <div className="flex items-center gap-2">
                      <button type="button" onClick={() => setLogAutoScroll(v => !v)}
                        className="px-2 py-1 rounded text-xs transition-all focus:outline-none"
                        style={{ background: logAutoScroll ? 'rgba(37,99,235,0.1)' : 'transparent', border: `1px solid ${logAutoScroll ? 'rgba(37,99,235,0.2)' : 'var(--akaal-border)'}`, color: logAutoScroll ? '#2563EB' : '#64748B', fontFamily: "'Inter',sans-serif" }}
                        aria-pressed={logAutoScroll}
                      >{logAutoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'}</button>
                    </div>
                  } />
                  {/* Log Controls */}
                  <div className="flex items-center gap-2 px-4 py-2 flex-wrap" style={{ borderBottom: '1px solid var(--akaal-card-border)' }}>
                    <div className="relative flex-1" style={{ minWidth: '120px' }}>
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: '#64748B' }}>
                        <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
                        <path d="M8 8l2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                      </svg>
                      <input type="search" placeholder="Search logs…" value={logSearch} onChange={e => setLogSearch(e.target.value)}
                        className="w-full text-xs rounded pl-6 pr-2 py-1 outline-none"
                        style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter',sans-serif" }}
                        aria-label="Search logs"
                        onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; }}
                        onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; }}
                      />
                    </div>
                    <div className="flex items-center gap-1">
                      {(['ALL', 'INFO', 'WARN', 'ERROR', 'DEBUG', 'SUCCESS'] as const).map(lvl => (
                        <button key={lvl} type="button" onClick={() => setLogLevel(lvl)}
                          className="px-2 py-0.5 rounded text-xs transition-all focus:outline-none"
                          style={{
                            background: logLevel === lvl ? (lvl === 'ALL' ? 'rgba(37,99,235,0.15)' : `${LOG_LEVEL_META[lvl as LogLevel]?.color ?? '#2563EB'}18`) : 'transparent',
                            border: `1px solid ${logLevel === lvl ? (lvl === 'ALL' ? 'rgba(37,99,235,0.3)' : `${LOG_LEVEL_META[lvl as LogLevel]?.color ?? '#2563EB'}30`) : 'transparent'}`,
                            color: logLevel === lvl ? (lvl === 'ALL' ? '#2563EB' : LOG_LEVEL_META[lvl as LogLevel]?.color ?? '#2563EB') : '#64748B',
                            fontFamily: "'JetBrains Mono',monospace", fontSize: '9px', fontWeight: 600,
                          }}
                          aria-pressed={logLevel === lvl}
                        >{lvl}</button>
                      ))}
                    </div>
                    <button type="button"
                      className="px-2 py-1 rounded text-xs transition-all focus:outline-none"
                      style={{ background: 'transparent', border: '1px solid var(--akaal-border)', color: '#64748B', fontFamily: "'Inter',sans-serif" }}
                      aria-label="Download logs"
                      onMouseEnter={e => { e.currentTarget.style.color = '#94A3B8'; }}
                      onMouseLeave={e => { e.currentTarget.style.color = '#64748B'; }}
                    >
                      <svg width="11" height="11" viewBox="0 0 11 11" fill="none" aria-hidden="true"><path d="M5.5 1v6M3 5l2.5 2.5L8 5M2 9h7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </button>
                  </div>
                  <div ref={logContainerRef} className="overflow-y-auto font-mono" style={{ maxHeight: '260px', background: 'var(--akaal-input-bg)', borderTop: '1px solid var(--akaal-border)' }} aria-live="polite" aria-label="Log output">
                    {loading ? (
                      <div className="p-3 space-y-1.5">
                        {[85, 62, 78, 91, 67, 74].map((w, i) => <Skeleton key={i} style={{ width: `${w}%`, height: '16px' }} />)}
                      </div>
                    ) : filteredLogs.length === 0 ? (
                      <div className="flex items-center justify-center py-8">
                        <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter',sans-serif" }}>No log entries match your filter.</p>
                      </div>
                    ) : (
                      <div>
                        {filteredLogs.map(log => (
                          <div key={log.id} className="flex items-start gap-2 px-3 py-1.5 transition-colors" style={{ borderBottom: '1px solid var(--akaal-border)' }}
                            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                          >
                            <span style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', flexShrink: 0, marginTop: '1px' }}>{log.timestamp}</span>
                            <span className="px-1.5 py-0.5 rounded flex-shrink-0" style={{ color: LOG_LEVEL_META[log.level].color, background: LOG_LEVEL_META[log.level].bg, fontFamily: "'JetBrains Mono',monospace", fontSize: '9px', fontWeight: 700, minWidth: '44px', textAlign: 'center' }}>{log.level}</span>
                            {log.source && <span style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', flexShrink: 0 }}>[{log.source}]</span>}
                            <span style={{ color: log.level === 'ERROR' ? '#EF4444' : log.level === 'WARN' ? '#F59E0B' : log.level === 'SUCCESS' ? '#22C55E' : 'var(--akaal-text)', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', lineHeight: '1.5', wordBreak: 'break-all' }}>{log.message}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </Card>
              </div>

              {/* System Performance Charts */}
              <Card>
                <SectionHeader title="System Performance" subtitle="Real-time resource utilization" />
                <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {loading ? (
                    Array.from({ length: 8 }, (_, i) => (
                      <div key={i} className="rounded p-3" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                        <Skeleton style={{ width: '60px', height: '12px', marginBottom: '8px' }} />
                        <Skeleton style={{ width: '100%', height: '60px' }} />
                      </div>
                    ))
                  ) : (
                    <>
                      {[
                        { key: 'cpu' as const,     label: 'CPU',             color: '#38BDF8', unit: '%' },
                        { key: 'mem' as const,     label: 'Memory',          color: '#22C55E', unit: '%' },
                        { key: 'net' as const,     label: 'Network',         color: '#2563EB', unit: '%' },
                        { key: 'disk' as const,    label: 'Disk I/O',        color: '#F59E0B', unit: '%' },
                        { key: 'rows' as const,    label: 'Rows/sec',        color: '#38BDF8', unit: '' },
                        { key: 'queue' as const,   label: 'Queue Size',      color: '#F59E0B', unit: '' },
                        { key: 'cdcLag' as const,  label: 'CDC Lag',         color: '#EF4444', unit: 's' },
                        { key: 'workers' as const, label: 'Worker Util.',    color: '#22C55E', unit: '' },
                      ].map(chart => {
                        const latest = perfData[perfData.length - 1];
                        const val = latest ? latest[chart.key] : 0;
                        return (
                          <div key={chart.key} className="rounded p-3" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                            <div className="flex items-center justify-between mb-2">
                              <span style={{ color: '#94A3B8', fontFamily: "'Inter',sans-serif", fontSize: '11px' }}>{chart.label}</span>
                              <span style={{ color: chart.color, fontFamily: "'JetBrains Mono',monospace", fontSize: '12px', fontWeight: 700 }}>{typeof val === 'number' && val >= 1000 ? `${(val/1000).toFixed(1)}K` : val}{chart.unit}</span>
                            </div>
                            <ResponsiveContainer width="100%" height={50}>
                              <AreaChart data={perfData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                                <defs>
                                  <linearGradient id={`grad-${chart.key}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={chart.color} stopOpacity={0.3} />
                                    <stop offset="100%" stopColor={chart.color} stopOpacity={0} />
                                  </linearGradient>
                                </defs>
                                <Area type="monotone" dataKey={chart.key} stroke={chart.color} strokeWidth={1.5} fill={`url(#grad-${chart.key})`} dot={false} isAnimationActive={false} />
                                <Tooltip contentStyle={chartTooltipStyle} itemStyle={{ color: chart.color }} labelStyle={{ display: 'none' }} formatter={(v: number) => [`${v}${chart.unit}`, chart.label]} />
                              </AreaChart>
                            </ResponsiveContainer>
                          </div>
                        );
                      })}
                    </>
                  )}
                </div>
              </Card>

              {/* Active Agents + Queue Monitor */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Active Agents */}
                <Card>
                  <SectionHeader title="Active Agents" subtitle={`${MOCK_AGENTS.filter(a => a.status === 'connected').length} connected`} />
                  <div className="p-3 space-y-2">
                    {loading ? (
                      Array.from({ length: 4 }, (_, i) => <Skeleton key={i} style={{ width: '100%', height: '72px', borderRadius: '6px' }} />)
                    ) : MOCK_AGENTS.map(agent => {
                      const cfg = AGENT_STATUS_META[agent.status];
                      return (
                        <div key={agent.id} className="rounded p-3" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <div className="flex items-center gap-2">
                                <span style={{ color: '#F8FAFC', fontFamily: "'JetBrains Mono',monospace", fontSize: '12px', fontWeight: 600 }}>{agent.name}</span>
                                <span className="px-1.5 py-0.5 rounded" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono',monospace", fontSize: '9px', fontWeight: 600 }}>{cfg.label}</span>
                                <span style={{ color: '#374151', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>v{agent.version}</span>
                              </div>
                              <p style={{ color: '#64748B', fontFamily: "'Inter',sans-serif", fontSize: '10px', marginTop: '2px' }}>{agent.host}</p>
                            </div>
                            <div className="text-right">
                              <p style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{agent.runningJobs} job{agent.runningJobs !== 1 ? 's' : ''}</p>
                              <p style={{ color: '#374151', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>♥ {agent.lastHeartbeat}</p>
                            </div>
                          </div>
                          {agent.status !== 'disconnected' && (
                            <div className="grid grid-cols-3 gap-2">
                              <div>
                                <p style={{ color: '#64748B', fontFamily: "'Inter',sans-serif", fontSize: '10px', marginBottom: '3px' }}>CPU</p>
                                <UsageBar value={agent.cpu} color={agent.cpu > 80 ? '#EF4444' : agent.cpu > 60 ? '#F59E0B' : '#38BDF8'} />
                              </div>
                              <div>
                                <p style={{ color: '#64748B', fontFamily: "'Inter',sans-serif", fontSize: '10px', marginBottom: '3px' }}>Memory</p>
                                <UsageBar value={agent.memory} color={agent.memory > 80 ? '#EF4444' : agent.memory > 60 ? '#F59E0B' : '#22C55E'} />
                              </div>
                              <div>
                                <p style={{ color: '#64748B', fontFamily: "'Inter',sans-serif", fontSize: '10px', marginBottom: '3px' }}>Network</p>
                                <p style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px' }}>{agent.network}</p>
                              </div>
                            </div>
                          )}
                          {agent.status === 'disconnected' && (
                            <div className="rounded px-3 py-2" style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}>
                              <p style={{ color: '#EF4444', fontFamily: "'Inter',sans-serif", fontSize: '10px' }}>Agent offline — last heartbeat {agent.lastHeartbeat}. Check host connectivity and restart the AKAAL agent service.</p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </Card>

                {/* Queue Monitor */}
                <Card>
                  <SectionHeader title="Queue Monitor" subtitle="Job queue status" />
                  <div className="p-3 space-y-2">
                    {loading ? (
                      Array.from({ length: 5 }, (_, i) => <Skeleton key={i} style={{ width: '100%', height: '52px', borderRadius: '6px' }} />)
                    ) : MOCK_QUEUES.map(q => (
                      <div key={q.name} className="rounded p-3" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                        <div className="flex items-center justify-between mb-2">
                          <span style={{ color: '#CBD5E1', fontFamily: "'Inter',sans-serif", fontSize: '12px', fontWeight: 500 }}>{q.name}</span>
                          <div className="flex items-center gap-3">
                            <span style={{ color: '#64748B', fontFamily: "'Inter',sans-serif", fontSize: '10px' }}>Avg wait: <span style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono',monospace" }}>{q.avgWait}</span></span>
                            <span style={{ color: q.color, fontFamily: "'JetBrains Mono',monospace", fontSize: '16px', fontWeight: 700 }}>{q.count}</span>
                          </div>
                        </div>
                        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
                          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.min((q.count / 1000) * 100, 100)}%`, background: q.color }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>

              {/* Checkpoint Monitor + Alert Center */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Checkpoint Monitor */}
                <Card>
                  <SectionHeader title="Checkpoint Monitor" subtitle="Latest migration checkpoints" />
                  <div className="overflow-x-auto">
                    {loading ? (
                      <div className="p-3 space-y-2">
                        {[1,2,3].map(i => <Skeleton key={i} style={{ width: '100%', height: '36px' }} />)}
                      </div>
                    ) : (
                      <table className="w-full" aria-label="Checkpoint monitor">
                        <thead>
                          <tr style={{ background: 'var(--akaal-table-header)' }}>
                            {['Migration', 'Timestamp', 'Rows At', 'Size', 'Interval', 'Restore', 'Last Test'].map(h => (
                              <th key={h} className="px-3 py-2 text-left" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', borderBottom: '1px solid var(--akaal-card-border)', whiteSpace: 'nowrap' }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {MOCK_CHECKPOINTS.map(cp => (
                            <tr key={cp.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                              <td className="px-3 py-2" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', whiteSpace: 'nowrap' }}>{cp.migration}</td>
                              <td className="px-3 py-2" style={{ color: '#64748B', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', whiteSpace: 'nowrap' }}>{cp.timestamp}</td>
                              <td className="px-3 py-2" style={{ color: '#CBD5E1', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', whiteSpace: 'nowrap' }}>{formatRows(cp.rowsAt)}</td>
                              <td className="px-3 py-2" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', whiteSpace: 'nowrap' }}>{cp.size}</td>
                              <td className="px-3 py-2" style={{ color: '#64748B', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', whiteSpace: 'nowrap' }}>{cp.interval}</td>
                              <td className="px-3 py-2">
                                <span className="px-1.5 py-0.5 rounded" style={{ color: cp.restoreAvailable ? '#22C55E' : '#EF4444', background: cp.restoreAvailable ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)', fontFamily: "'JetBrains Mono',monospace", fontSize: '9px', fontWeight: 600 }}>{cp.restoreAvailable ? 'READY' : 'N/A'}</span>
                              </td>
                              <td className="px-3 py-2" style={{ color: '#374151', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', whiteSpace: 'nowrap' }}>{cp.lastRestoreTest}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </Card>

                {/* Alert Center */}
                <Card>
                  <SectionHeader title="Alert Center" subtitle={`${alerts.filter(a => !a.acknowledged && a.severity !== 'resolved').length} active alerts`} action={
                    <div className="flex items-center gap-1">
                      {(['all', 'critical', 'warning', 'info', 'resolved'] as const).map(f => (
                        <button key={f} type="button" onClick={() => setAlertFilter(f)}
                          className="px-2 py-0.5 rounded text-xs transition-all focus:outline-none"
                          style={{
                            background: alertFilter === f ? (f === 'all' ? 'rgba(37,99,235,0.15)' : `${ALERT_META[f as AlertSeverity]?.color ?? '#2563EB'}18`) : 'transparent',
                            border: `1px solid ${alertFilter === f ? (f === 'all' ? 'rgba(37,99,235,0.3)' : `${ALERT_META[f as AlertSeverity]?.color ?? '#2563EB'}30`) : 'transparent'}`,
                            color: alertFilter === f ? (f === 'all' ? '#2563EB' : ALERT_META[f as AlertSeverity]?.color ?? '#2563EB') : '#64748B',
                            fontFamily: "'JetBrains Mono',monospace", fontSize: '9px', fontWeight: 600, textTransform: 'uppercase',
                          }}
                          aria-pressed={alertFilter === f}
                        >{f}</button>
                      ))}
                    </div>
                  } />
                  <div className="divide-y" style={{ borderColor: 'var(--akaal-border-subtle)' }}>
                    {loading ? (
                      <div className="p-3 space-y-2">
                        {[1,2,3].map(i => <Skeleton key={i} style={{ width: '100%', height: '52px' }} />)}
                      </div>
                    ) : filteredAlerts.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-8">
                        <p className="text-xs" style={{ color: '#22C55E', fontFamily: "'Inter',sans-serif" }}>No alerts in this category.</p>
                      </div>
                    ) : filteredAlerts.map(alert => {
                      const cfg = ALERT_META[alert.severity];
                      return (
                        <div key={alert.id} className="px-4 py-3" style={{ opacity: alert.muted ? 0.5 : 1 }}>
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-start gap-2 min-w-0">
                              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: cfg.color, animation: alert.severity === 'critical' && !alert.acknowledged ? 'pulse 1.5s ease-in-out infinite' : 'none' }} aria-hidden="true" />
                              <div className="min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="px-1.5 py-0.5 rounded" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono',monospace", fontSize: '9px', fontWeight: 600 }}>{cfg.label.toUpperCase()}</span>
                                  <span style={{ color: '#CBD5E1', fontFamily: "'Inter',sans-serif", fontSize: '11px', fontWeight: 500 }}>{alert.title}</span>
                                  {alert.acknowledged && <span style={{ color: '#374151', fontFamily: "'JetBrains Mono',monospace", fontSize: '9px' }}>ACK</span>}
                                </div>
                                <p className="text-xs mt-0.5" style={{ color: '#64748B', fontFamily: "'Inter',sans-serif", lineHeight: '1.4' }}>{alert.detail}</p>
                                <p style={{ color: '#374151', fontFamily: "'JetBrains Mono',monospace", fontSize: '10px', marginTop: '2px' }}>{alert.time}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-1 flex-shrink-0">
                              {!alert.acknowledged && (
                                <button type="button" onClick={() => setAlerts(prev => prev.map(a => a.id === alert.id ? { ...a, acknowledged: true } : a))}
                                  className="px-2 py-1 rounded text-xs transition-all focus:outline-none"
                                  style={{ background: 'transparent', border: '1px solid var(--akaal-border)', color: '#64748B', fontFamily: "'Inter',sans-serif" }}
                                  aria-label={`Acknowledge alert: ${alert.title}`}
                                  onMouseEnter={e => { e.currentTarget.style.color = '#94A3B8'; e.currentTarget.style.borderColor = '#374151'; }}
                                  onMouseLeave={e => { e.currentTarget.style.color = '#64748B'; e.currentTarget.style.borderColor = 'var(--akaal-border)'; }}
                                >Ack</button>
                              )}
                              <button type="button" onClick={() => setAlerts(prev => prev.map(a => a.id === alert.id ? { ...a, muted: !a.muted } : a))}
                                className="px-2 py-1 rounded text-xs transition-all focus:outline-none"
                                style={{ background: 'transparent', border: '1px solid var(--akaal-border)', color: '#64748B', fontFamily: "'Inter',sans-serif" }}
                                aria-label={`${alert.muted ? 'Unmute' : 'Mute'} alert: ${alert.title}`}
                                onMouseEnter={e => { e.currentTarget.style.color = '#94A3B8'; }}
                                onMouseLeave={e => { e.currentTarget.style.color = '#64748B'; }}
                              >{alert.muted ? 'Unmute' : 'Mute'}</button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              </div>

            </div>
          </div>

          {/* Inspector Panel */}
          {selectedMigration && (
            <div style={{ animation: 'slideIn 0.2s ease' }}>
              <InspectorPanel migration={selectedMigration} onClose={() => setSelectedMigration(null)} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
