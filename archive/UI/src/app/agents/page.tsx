'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';
import { AreaChart, Area, Bar, Tooltip, ResponsiveContainer,  } from 'recharts';

// ─── Types ────────────────────────────────────────────────────────────────────

type AgentStatus = 'online' | 'offline' | 'degraded' | 'starting' | 'draining' | 'paused';
type AgentHealth = 'healthy' | 'warning' | 'critical' | 'unknown';
type AgentCategory = 'all' | 'core' | 'migration' | 'validation' | 'recovery' | 'monitoring' | 'notification' | 'infrastructure';
type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | 'SUCCESS';
type InspectorTab = 'overview' | 'runtime' | 'tasks' | 'performance' | 'logs' | 'events' | 'configuration' | 'dependencies' | 'history';
type AlertSeverity = 'critical' | 'warning' | 'info' | 'resolved';

interface AgentRecord {
  id: string;
  name: string;
  type: string;
  role: string;
  version: string;
  status: AgentStatus;
  health: AgentHealth;
  currentTask: string;
  cpu: number;
  memory: number;
  network: string;
  heartbeat: string;
  uptime: string;
  latency: number;
  category: AgentCategory;
  description: string;
  capabilities: string[];
  dependencies: string[];
  runningJobs: number;
  queuedTasks: number;
  restartCount: number;
  failureCount: number;
  lastActivity: string;
  host: string;
  port: number;
  successRate: number;
  tasksPerMin: number;
  avgProcessingTime: string;
}

interface AgentTask {
  id: string;
  migration: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  state: 'running' | 'queued' | 'completed' | 'failed' | 'paused';
  progress: number;
  started: string;
  duration: string;
}

interface AgentEvent {
  id: string;
  timestamp: string;
  type: string;
  description: string;
  severity: 'info' | 'success' | 'warning' | 'error';
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
}

interface AgentAlert {
  id: string;
  agentId: string;
  severity: AlertSeverity;
  title: string;
  detail: string;
  time: string;
  acknowledged: boolean;
}

interface PerfPoint {
  t: string;
  cpu: number;
  mem: number;
  latency: number;
  net: number;
  tpm: number;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_AGENTS: AgentRecord[] = [
  {
    id: 'ag-manager-01', name: 'Manager', type: 'Manager', role: 'Orchestration Controller',
    version: '3.2.1', status: 'online', health: 'healthy', currentTask: 'Orchestrating MIG-2847',
    cpu: 34, memory: 42, network: '0.8 GB/s', heartbeat: '1s ago', uptime: '14d 6h 22m', latency: 4,
    category: 'core', description: 'Central orchestration controller managing all migration workflows, agent coordination, and execution scheduling.',
    capabilities: ['Workflow Orchestration', 'Agent Coordination', 'Execution Scheduling', 'Resource Allocation', 'Priority Management'],
    dependencies: ['Scheduler', 'Database', 'Message Queue'],
    runningJobs: 3, queuedTasks: 12, restartCount: 0, failureCount: 0,
    lastActivity: '1s ago', host: 'prod-manager-01.akaal.io', port: 8080,
    successRate: 99.8, tasksPerMin: 24, avgProcessingTime: '2.1s',
  },
  {
    id: 'ag-scout-01', name: 'Scout', type: 'Scout', role: 'Schema Discovery Agent',
    version: '2.8.4', status: 'online', health: 'healthy', currentTask: 'Scanning prod-oracle schema',
    cpu: 22, memory: 31, network: '0.3 GB/s', heartbeat: '2s ago', uptime: '14d 6h 18m', latency: 8,
    category: 'migration', description: 'Performs deep schema discovery, dependency mapping, and pre-migration analysis across source databases.',
    capabilities: ['Schema Discovery', 'Dependency Mapping', 'Object Cataloging', 'Compatibility Analysis', 'Risk Assessment'],
    dependencies: ['Manager', 'Database Adapters'],
    runningJobs: 1, queuedTasks: 3, restartCount: 1, failureCount: 0,
    lastActivity: '4s ago', host: 'prod-scout-01.akaal.io', port: 8081,
    successRate: 98.2, tasksPerMin: 8, avgProcessingTime: '12.4s',
  },
  {
    id: 'ag-advisor-01', name: 'Advisor', type: 'Advisor', role: 'Migration Strategy Advisor',
    version: '2.5.0', status: 'online', health: 'healthy', currentTask: 'Analyzing MIG-2853 strategy',
    cpu: 18, memory: 28, network: '0.1 GB/s', heartbeat: '3s ago', uptime: '14d 6h 10m', latency: 6,
    category: 'migration', description: 'AI-powered migration strategy advisor providing recommendations, risk analysis, and optimization suggestions.',
    capabilities: ['Strategy Recommendation', 'Risk Analysis', 'Performance Optimization', 'Compatibility Checks', 'Rollback Planning'],
    dependencies: ['Manager', 'Scout'],
    runningJobs: 1, queuedTasks: 2, restartCount: 0, failureCount: 0,
    lastActivity: '12s ago', host: 'prod-advisor-01.akaal.io', port: 8082,
    successRate: 97.5, tasksPerMin: 4, avgProcessingTime: '8.2s',
  },
  {
    id: 'ag-liveintel-01', name: 'Live Intel', type: 'Live Intel', role: 'Real-Time Intelligence Agent',
    version: '3.0.2', status: 'online', health: 'warning', currentTask: 'Monitoring CDC lag on MIG-2847',
    cpu: 61, memory: 55, network: '1.4 GB/s', heartbeat: '1s ago', uptime: '14d 5h 44m', latency: 12,
    category: 'monitoring', description: 'Provides real-time intelligence, live metrics streaming, and anomaly detection across all active migrations.',
    capabilities: ['Real-Time Metrics', 'Anomaly Detection', 'CDC Monitoring', 'Alert Generation', 'Trend Analysis'],
    dependencies: ['Manager', 'CDC Agent', 'Message Queue'],
    runningJobs: 4, queuedTasks: 0, restartCount: 2, failureCount: 1,
    lastActivity: '1s ago', host: 'prod-liveintel-01.akaal.io', port: 8083,
    successRate: 94.1, tasksPerMin: 42, avgProcessingTime: '0.4s',
  },
  {
    id: 'ag-gb-01', name: 'GB', type: 'GB', role: 'Bulk Data Transfer Agent',
    version: '2.9.1', status: 'online', health: 'healthy', currentTask: 'Bulk transfer MIG-2847 batch 482',
    cpu: 78, memory: 64, network: '2.1 GB/s', heartbeat: '1s ago', uptime: '14d 6h 22m', latency: 3,
    category: 'migration', description: 'High-throughput bulk data transfer agent optimized for large-scale row migration with parallel batch processing.',
    capabilities: ['Bulk Data Transfer', 'Parallel Batch Processing', 'Compression', 'Checkpointing', 'Retry Logic'],
    dependencies: ['Manager', 'Checkpoint Agent', 'Database Adapters'],
    runningJobs: 2, queuedTasks: 5, restartCount: 0, failureCount: 0,
    lastActivity: '1s ago', host: 'prod-gb-01.akaal.io', port: 8084,
    successRate: 99.4, tasksPerMin: 18, avgProcessingTime: '0.8s',
  },
  {
    id: 'ag-cdc-01', name: 'CDC', type: 'CDC', role: 'Change Data Capture Agent',
    version: '2.7.3', status: 'degraded', health: 'warning', currentTask: 'Streaming changes — lag 4.2s',
    cpu: 82, memory: 71, network: '0.9 GB/s', heartbeat: '8s ago', uptime: '14d 4h 12m', latency: 42,
    category: 'migration', description: 'Captures and streams real-time database changes using log-based CDC for zero-downtime migrations.',
    capabilities: ['Log-Based CDC', 'Change Streaming', 'Lag Monitoring', 'Schema Evolution', 'Conflict Resolution'],
    dependencies: ['Manager', 'Live Intel', 'Message Queue'],
    runningJobs: 1, queuedTasks: 847, restartCount: 3, failureCount: 2,
    lastActivity: '8s ago', host: 'prod-cdc-01.akaal.io', port: 8085,
    successRate: 91.2, tasksPerMin: 12, avgProcessingTime: '4.2s',
  },
  {
    id: 'ag-checkpoint-01', name: 'Checkpoint', type: 'Checkpoint', role: 'State Persistence Agent',
    version: '2.6.0', status: 'online', health: 'healthy', currentTask: 'Saving CP-12 for MIG-2847',
    cpu: 15, memory: 22, network: '0.4 GB/s', heartbeat: '2s ago', uptime: '14d 6h 22m', latency: 5,
    category: 'infrastructure', description: 'Manages migration state persistence, checkpoint creation, and point-in-time recovery capabilities.',
    capabilities: ['Checkpoint Creation', 'State Persistence', 'Point-in-Time Recovery', 'Restore Testing', 'Integrity Verification'],
    dependencies: ['Manager', 'Storage', 'GB Agent'],
    runningJobs: 1, queuedTasks: 0, restartCount: 0, failureCount: 0,
    lastActivity: '2s ago', host: 'prod-checkpoint-01.akaal.io', port: 8086,
    successRate: 100, tasksPerMin: 6, avgProcessingTime: '1.2s',
  },
  {
    id: 'ag-validator-01', name: 'Validator', type: 'Validator', role: 'Data Integrity Validator',
    version: '3.1.0', status: 'online', health: 'healthy', currentTask: 'Validating schema MIG-2853',
    cpu: 28, memory: 35, network: '0.5 GB/s', heartbeat: '2s ago', uptime: '14d 6h 15m', latency: 7,
    category: 'validation', description: 'Performs comprehensive data integrity validation, schema verification, and post-migration consistency checks.',
    capabilities: ['Schema Validation', 'Data Integrity Checks', 'Row Count Verification', 'Constraint Validation', 'Checksum Comparison'],
    dependencies: ['Manager', 'Scout', 'Database Adapters'],
    runningJobs: 1, queuedTasks: 2, restartCount: 0, failureCount: 0,
    lastActivity: '5s ago', host: 'prod-validator-01.akaal.io', port: 8087,
    successRate: 99.1, tasksPerMin: 10, avgProcessingTime: '3.8s',
  },
  {
    id: 'ag-healing-01', name: 'Healing', type: 'Healing', role: 'Autonomous Recovery Agent',
    version: '2.4.2', status: 'online', health: 'healthy', currentTask: 'Monitoring recovery readiness',
    cpu: 12, memory: 18, network: '0.2 GB/s', heartbeat: '3s ago', uptime: '14d 6h 22m', latency: 9,
    category: 'recovery', description: 'Autonomous self-healing agent that detects failures, initiates recovery procedures, and restores migration state.',
    capabilities: ['Failure Detection', 'Auto Recovery', 'Rollback Initiation', 'State Restoration', 'Dependency Healing'],
    dependencies: ['Manager', 'Checkpoint Agent', 'Live Intel'],
    runningJobs: 0, queuedTasks: 1, restartCount: 0, failureCount: 0,
    lastActivity: '1m ago', host: 'prod-healing-01.akaal.io', port: 8088,
    successRate: 98.7, tasksPerMin: 2, avgProcessingTime: '15.0s',
  },
  {
    id: 'ag-noticer-01', name: 'Noticer', type: 'Noticer', role: 'Notification Dispatch Agent',
    version: '2.3.1', status: 'online', health: 'healthy', currentTask: 'Dispatching alert batch #44',
    cpu: 8, memory: 14, network: '0.1 GB/s', heartbeat: '4s ago', uptime: '14d 6h 20m', latency: 11,
    category: 'notification', description: 'Manages all platform notifications, alert dispatching, and stakeholder communication across channels.',
    capabilities: ['Email Notifications', 'Slack Integration', 'PagerDuty Alerts', 'Webhook Dispatch', 'Escalation Management'],
    dependencies: ['Manager', 'Live Intel'],
    runningJobs: 1, queuedTasks: 3, restartCount: 0, failureCount: 0,
    lastActivity: '4s ago', host: 'prod-noticer-01.akaal.io', port: 8089,
    successRate: 99.6, tasksPerMin: 14, avgProcessingTime: '0.6s',
  },
  {
    id: 'ag-system-01', name: 'System', type: 'System', role: 'Platform Infrastructure Agent',
    version: '3.2.1', status: 'online', health: 'healthy', currentTask: 'Health monitoring cycle #8821',
    cpu: 9, memory: 16, network: '0.2 GB/s', heartbeat: '1s ago', uptime: '14d 6h 22m', latency: 2,
    category: 'infrastructure', description: 'Core platform infrastructure agent managing system health, resource allocation, and platform-wide operations.',
    capabilities: ['System Health Monitoring', 'Resource Management', 'Agent Lifecycle', 'Configuration Management', 'Platform Diagnostics'],
    dependencies: ['All Agents'],
    runningJobs: 1, queuedTasks: 0, restartCount: 0, failureCount: 0,
    lastActivity: '1s ago', host: 'prod-system-01.akaal.io', port: 8090,
    successRate: 100, tasksPerMin: 60, avgProcessingTime: '0.1s',
  },
];

const MOCK_TASKS: AgentTask[] = [
  { id: 'TSK-4421', migration: 'MIG-2847', priority: 'critical', state: 'running', progress: 67, started: '14:22:00', duration: '1h 55m' },
  { id: 'TSK-4422', migration: 'MIG-2851', priority: 'high', state: 'running', progress: 12, started: '15:58:00', duration: '19m' },
  { id: 'TSK-4423', migration: 'MIG-2854', priority: 'high', state: 'running', progress: 44, started: '15:05:00', duration: '1h 12m' },
  { id: 'TSK-4424', migration: 'MIG-2852', priority: 'medium', state: 'paused', progress: 51, started: '09:30:00', duration: '2h 41m' },
  { id: 'TSK-4425', migration: 'MIG-2853', priority: 'medium', state: 'queued', progress: 0, started: '—', duration: '—' },
  { id: 'TSK-4426', migration: 'MIG-2849', priority: 'high', state: 'failed', progress: 34, started: '13:45:00', duration: '32m' },
];

const MOCK_EVENTS: AgentEvent[] = [
  { id: 'ev1', timestamp: '16:17:02', type: 'checkpoint', description: 'Checkpoint CP-12 saved — 4,820,441 rows committed', severity: 'info' },
  { id: 'ev2', timestamp: '16:16:44', type: 'retry', description: 'CDC retry attempt #3 initiated — reconnecting stream', severity: 'warning' },
  { id: 'ev3', timestamp: '16:15:30', type: 'warning', description: 'CDC lag spike detected — 4.2s replication delay', severity: 'warning' },
  { id: 'ev4', timestamp: '16:14:12', type: 'task_completed', description: 'Schema validation completed — 0 blocking issues', severity: 'success' },
  { id: 'ev5', timestamp: '16:12:55', type: 'heartbeat', description: 'Heartbeat received — all core agents nominal', severity: 'info' },
  { id: 'ev6', timestamp: '16:11:20', type: 'failure', description: 'Task failed — constraint violation on ORDERS table', severity: 'error' },
  { id: 'ev7', timestamp: '16:09:00', type: 'task_assigned', description: 'Task TSK-4422 assigned to GB agent', severity: 'info' },
  { id: 'ev8', timestamp: '16:08:40', type: 'started', description: 'Agent CDC restarted after connection recovery', severity: 'success' },
  { id: 'ev9', timestamp: '16:05:00', type: 'upgrade', description: 'Manager agent upgraded to v3.2.1', severity: 'info' },
  { id: 'ev10', timestamp: '16:02:18', type: 'restart', description: 'CDC agent restarted — health check failure resolved', severity: 'warning' },
];

const MOCK_LOGS: LogEntry[] = [
  { id: 'lg1', timestamp: '16:17:02.441', level: 'INFO', message: 'Checkpoint CP-12 saved — offset 4,820,441 rows committed', source: 'Checkpoint' },
  { id: 'lg2', timestamp: '16:16:58.112', level: 'DEBUG', message: 'Worker pool utilization: 7/8 active threads', source: 'Manager' },
  { id: 'lg3', timestamp: '16:16:44.009', level: 'WARN', message: 'CDC retry attempt #3 — stream reconnection in progress', source: 'CDC' },
  { id: 'lg4', timestamp: '16:16:30.882', level: 'INFO', message: 'Batch 482 completed — 10,000 rows in 0.81s (12,345 rows/s)', source: 'GB' },
  { id: 'lg5', timestamp: '16:15:30.001', level: 'WARN', message: 'CDC lag spike detected — replication delay 4.2s on ORDERS', source: 'CDC' },
  { id: 'lg6', timestamp: '16:14:12.334', level: 'SUCCESS', message: 'Schema validation completed — 142 tables, 28 views validated', source: 'Validator' },
  { id: 'lg7', timestamp: '16:12:55.221', level: 'INFO', message: 'Heartbeat cycle #8821 — all 11 agents nominal', source: 'System' },
  { id: 'lg8', timestamp: '16:11:20.009', level: 'ERROR', message: 'Task failed — ORA-02291: integrity constraint violation on ORDERS', source: 'GB' },
  { id: 'lg9', timestamp: '16:10:44.009', level: 'INFO', message: 'Schema migration completed — 142 tables, 28 views, 14 functions', source: 'Scout' },
  { id: 'lg10', timestamp: '16:09:30.118', level: 'DEBUG', message: 'Connection pool established — 8 workers connected to target', source: 'Manager' },
  { id: 'lg11', timestamp: '16:09:00.000', level: 'INFO', message: 'Task TSK-4422 assigned to GB agent — priority: high', source: 'Manager' },
  { id: 'lg12', timestamp: '16:08:55.441', level: 'SUCCESS', message: 'Pre-flight checks passed — all systems ready', source: 'System' },
  { id: 'lg13', timestamp: '16:05:00.002', level: 'WARN', message: 'Queue depth threshold exceeded — 847 pending CDC events', source: 'CDC' },
  { id: 'lg14', timestamp: '16:02:18.334', level: 'WARN', message: 'CDC agent health check failed — initiating restart', source: 'Healing' },
  { id: 'lg15', timestamp: '16:02:22.001', level: 'INFO', message: 'CDC agent restarted successfully — rejoining pool', source: 'System' },
];

const MOCK_ALERTS: AgentAlert[] = [
  { id: 'al1', agentId: 'ag-cdc-01', severity: 'critical', title: 'CDC Lag Spike', detail: 'CDC agent replication delay 4.2s — threshold 2.0s', time: '15m ago', acknowledged: false },
  { id: 'al2', agentId: 'ag-cdc-01', severity: 'warning', title: 'CDC Agent Degraded', detail: 'CDC agent CPU at 82% — performance impact on active streams', time: '18m ago', acknowledged: false },
  { id: 'al3', agentId: 'ag-liveintel-01', severity: 'warning', title: 'Live Intel High CPU', detail: 'Live Intel agent CPU at 61% — monitoring 4 concurrent migrations', time: '22m ago', acknowledged: true },
  { id: 'al4', agentId: 'ag-gb-01', severity: 'info', title: 'GB High Throughput', detail: 'GB agent processing at 2.1 GB/s — within normal range', time: '30m ago', acknowledged: true },
  { id: 'al5', agentId: 'ag-cdc-01', severity: 'resolved', title: 'CDC Connection Restored', detail: 'CDC stream reconnected after 3 retry attempts', time: '45m ago', acknowledged: true },
];

function generatePerfData(): PerfPoint[] {
  const now = Date.now();
  return Array.from({ length: 30 }, (_, i) => {
    const t = new Date(now - (29 - i) * 10_000);
    const h = t.getHours().toString().padStart(2, '0');
    const m = t.getMinutes().toString().padStart(2, '0');
    const s = t.getSeconds().toString().padStart(2, '0');
    return {
      t: `${h}:${m}:${s}`,
      cpu: 30 + Math.round(Math.sin(i * 0.4) * 20 + Math.random() * 10),
      mem: 45 + Math.round(Math.sin(i * 0.2) * 10 + Math.random() * 5),
      latency: 5 + Math.round(Math.sin(i * 0.6) * 8 + Math.random() * 4),
      net: 50 + Math.round(Math.cos(i * 0.3) * 20 + Math.random() * 10),
      tpm: 20 + Math.round(Math.sin(i * 0.5) * 8 + Math.random() * 4),
    };
  });
}

// ─── Status / Health Config ───────────────────────────────────────────────────

const AGENT_STATUS_META: Record<AgentStatus, { label: string; color: string; bg: string; border: string; animated: boolean }> = {
  online:    { label: 'Online',    color: '#22C55E', bg: 'rgba(34,197,94,0.08)',    border: 'rgba(34,197,94,0.2)',    animated: false },
  offline:   { label: 'Offline',   color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)', animated: false },
  degraded:  { label: 'Degraded',  color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  animated: true },
  starting:  { label: 'Starting',  color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  border: 'rgba(56,189,248,0.2)',  animated: true },
  draining:  { label: 'Draining',  color: '#A78BFA', bg: 'rgba(167,139,250,0.08)', border: 'rgba(167,139,250,0.2)', animated: true },
  paused:    { label: 'Paused',    color: '#FACC15', bg: 'rgba(250,204,21,0.08)',  border: 'rgba(250,204,21,0.2)',  animated: false },
};

const AGENT_HEALTH_META: Record<AgentHealth, { label: string; color: string; bg: string; border: string }> = {
  healthy:  { label: 'Healthy',  color: '#22C55E', bg: 'rgba(34,197,94,0.08)',    border: 'rgba(34,197,94,0.2)' },
  warning:  { label: 'Warning',  color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',   border: 'rgba(245,158,11,0.2)' },
  critical: { label: 'Critical', color: '#EF4444', bg: 'rgba(239,68,68,0.08)',    border: 'rgba(239,68,68,0.2)' },
  unknown:  { label: 'Unknown',  color: '#94A3B8', bg: 'rgba(148,163,184,0.08)',  border: 'rgba(148,163,184,0.2)' },
};

const TASK_STATE_META: Record<AgentTask['state'], { label: string; color: string; bg: string }> = {
  running:   { label: 'Running',   color: '#38BDF8', bg: 'rgba(56,189,248,0.08)' },
  queued:    { label: 'Queued',    color: '#94A3B8', bg: 'rgba(148,163,184,0.08)' },
  completed: { label: 'Completed', color: '#22C55E', bg: 'rgba(34,197,94,0.08)' },
  failed:    { label: 'Failed',    color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
  paused:    { label: 'Paused',    color: '#FACC15', bg: 'rgba(250,204,21,0.08)' },
};

const PRIORITY_META: Record<AgentTask['priority'], { label: string; color: string; bg: string }> = {
  critical: { label: 'Critical', color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
  high:     { label: 'High',     color: '#F59E0B', bg: 'rgba(245,158,11,0.08)' },
  medium:   { label: 'Medium',   color: '#38BDF8', bg: 'rgba(56,189,248,0.08)' },
  low:      { label: 'Low',      color: '#94A3B8', bg: 'rgba(148,163,184,0.08)' },
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

const EVENT_TYPE_META: Record<string, { color: string; label: string }> = {
  checkpoint:     { color: '#38BDF8', label: 'Checkpoint' },
  retry:          { color: '#F59E0B', label: 'Retry' },
  warning:        { color: '#F59E0B', label: 'Warning' },
  task_completed: { color: '#22C55E', label: 'Completed' },
  heartbeat:      { color: '#94A3B8', label: 'Heartbeat' },
  failure:        { color: '#EF4444', label: 'Failure' },
  task_assigned:  { color: '#38BDF8', label: 'Assigned' },
  started:        { color: '#22C55E', label: 'Started' },
  upgrade:        { color: '#A78BFA', label: 'Upgrade' },
  restart:        { color: '#F59E0B', label: 'Restart' },
};

// ─── Utility Components ───────────────────────────────────────────────────────

function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded ${className ?? ''}`}
      style={{ background: 'linear-gradient(90deg, var(--akaal-surface) 25%, var(--akaal-surface-elevated) 50%, var(--akaal-surface) 75%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s infinite', ...style }}
      aria-hidden="true"
    />
  );
}

function AgentStatusChip({ status }: { status: AgentStatus }) {
  const cfg = AGENT_STATUS_META[status];
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color, animation: cfg.animated ? 'pulse 1.5s ease-in-out infinite' : 'none' }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function HealthChip({ health }: { health: AgentHealth }) {
  const cfg = AGENT_HEALTH_META[health];
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function UsageBar({ value, color }: { value: number; color: string }) {
  const barColor = value >= 85 ? '#EF4444' : value >= 65 ? '#F59E0B' : color;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-surface-elevated)' }}>
        <div className="h-full rounded-full transition-all duration-300" style={{ width: `${Math.min(value, 100)}%`, background: barColor }} />
      </div>
      <span className="text-xs w-8 text-right flex-shrink-0" style={{ color: barColor, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{value}%</span>
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

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const navItems = [
    { href: '/dashboard', label: 'Dashboard', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/migrations', label: 'Migrations', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/execution-center', label: 'Execution', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M6 5.5l5 2.5-5 2.5V5.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { href: '/databases', label: 'Databases', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><ellipse cx="8" cy="4" rx="6" ry="2" stroke="currentColor" strokeWidth="1.3" /><path d="M2 4v4c0 1.1 2.7 2 6 2s6-.9 6-2V4" stroke="currentColor" strokeWidth="1.3" /><path d="M2 8v4c0 1.1 2.7 2 6 2s6-.9 6-2V8" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { href: '/live-monitor', label: 'Live Monitor', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M4 8l2-2 2 2 2-3 2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { href: '/agents', label: 'Agents', active: true, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/reports', label: 'Reports', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/settings', label: 'Settings', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.4 3.4l.85.85M11.75 11.75l.85.85M3.4 12.4l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
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

// ─── Top Navigation ───────────────────────────────────────────────────────────

function TopNav() {
  const [searchValue, setSearchValue] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="flex items-center gap-4 px-4 flex-shrink-0" style={{ height: '57px', background: 'var(--akaal-nav-bg)', borderBottom: '1px solid var(--akaal-nav-border)' }} role="banner">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 flex-shrink-0">
        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Platform</span>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Agents</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
          <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <input type="search" placeholder="Search agents, tasks, logs…" value={searchValue} onChange={e => setSearchValue(e.target.value)}
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
        <button type="button" onClick={() => { setNotifOpen(v => !v); setProfileOpen(false); }}
          className="relative flex items-center justify-center w-8 h-8 rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2"
          style={{ color: 'var(--akaal-text-muted)' }} aria-label="Notifications" aria-expanded={notifOpen}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1.5a5 5 0 0 0-5 5v3l-1.5 2h13L13 9.5v-3a5 5 0 0 0-5-5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M6.5 13.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.3" /></svg>
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full" style={{ background: 'var(--akaal-error)', border: '1.5px solid var(--akaal-nav-bg)' }} aria-hidden="true" />
        </button>
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
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >{item}</button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

// ─── Category Filter Sidebar ──────────────────────────────────────────────────

function CategoryFilter({ active, onSelect, counts }: { active: AgentCategory; onSelect: (c: AgentCategory) => void; counts: Record<AgentCategory, number> }) {
  const categories: { id: AgentCategory; label: string; icon: React.ReactNode }[] = [
    { id: 'all', label: 'All Agents', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="5" height="5" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><rect x="8" y="1" width="5" height="5" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><rect x="1" y="8" width="5" height="5" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><rect x="8" y="8" width="5" height="5" rx="0.8" stroke="currentColor" strokeWidth="1.2" /></svg> },
    { id: 'core', label: 'Core Agents', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.2" /><circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.2" /></svg> },
    { id: 'migration', label: 'Migration Agents', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'validation', label: 'Validation Agents', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2.5 7l3 3L11.5 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'recovery', label: 'Recovery Agents', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2a5 5 0 1 0 4.33 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /><path d="M11 1v3.5H7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'monitoring', label: 'Monitoring Agents', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 9l2.5-3 2.5 2 2.5-4 2.5 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'notification', label: 'Notification Agents', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5a4 4 0 0 0-4 4v2.5L1.5 10h11L11 8V5.5a4 4 0 0 0-4-4Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /><path d="M5.5 11.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.2" /></svg> },
    { id: 'infrastructure', label: 'Infrastructure Agents', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="2" width="12" height="3" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><rect x="1" y="7" width="12" height="3" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><circle cx="11" cy="3.5" r="0.8" fill="currentColor" /><circle cx="11" cy="8.5" r="0.8" fill="currentColor" /></svg> },
  ];

  return (
    <div className="flex flex-col flex-shrink-0" style={{ width: '196px', background: 'var(--akaal-nav-bg)', borderRight: '1px solid var(--akaal-nav-border)', overflowY: 'auto' }}>
      <div className="px-3 py-3" style={{ borderBottom: '1px solid var(--akaal-nav-border)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.1em' }}>Agent Categories</p>
      </div>
      <nav aria-label="Agent categories" className="py-2">
        <ul className="space-y-0.5 px-2" role="list">
          {categories.map(cat => (
            <li key={cat.id}>
              <button type="button" onClick={() => onSelect(cat.id)}
                className="w-full flex items-center justify-between gap-2 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 text-left"
                style={{ color: active === cat.id ? 'var(--akaal-text)' : 'var(--akaal-text-muted)', background: active === cat.id ? 'var(--akaal-primary-subtle)' : 'transparent', borderLeft: active === cat.id ? '2px solid var(--akaal-primary)' : '2px solid transparent', fontFamily: "'Inter', sans-serif" }}
                aria-current={active === cat.id ? 'page' : undefined}
                onMouseEnter={e => { if (active !== cat.id) { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; } }}
                onMouseLeave={e => { if (active !== cat.id) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; } }}
              >
                <span className="flex items-center gap-2">
                  <span className="flex-shrink-0" aria-hidden="true">{cat.icon}</span>
                  <span>{cat.label}</span>
                </span>
                <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>
                  {counts[cat.id] ?? 0}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}

// ─── KPI Cards ────────────────────────────────────────────────────────────────

function KpiCards({ agents }: { agents: AgentRecord[] }) {
  const total = agents.length;
  const online = agents.filter(a => a.status === 'online').length;
  const offline = agents.filter(a => a.status === 'offline').length;
  const healthy = agents.filter(a => a.health === 'healthy').length;
  const warning = agents.filter(a => a.health === 'warning').length;
  const critical = agents.filter(a => a.health === 'critical').length;
  const runningTasks = agents.reduce((s, a) => s + a.runningJobs, 0);
  const queuedTasks = agents.reduce((s, a) => s + a.queuedTasks, 0);
  const avgCpu = Math.round(agents.reduce((s, a) => s + a.cpu, 0) / total);
  const avgMem = Math.round(agents.reduce((s, a) => s + a.memory, 0) / total);
  const avgLatency = Math.round(agents.reduce((s, a) => s + a.latency, 0) / total);

  const cards = [
    { label: 'Total Agents', value: total, color: 'var(--akaal-primary)', sub: `${online} online` },
    { label: 'Online', value: online, color: '#22C55E', sub: `${((online / total) * 100).toFixed(0)}% availability` },
    { label: 'Offline', value: offline, color: '#64748B', sub: offline === 0 ? 'All agents up' : `${offline} unreachable` },
    { label: 'Healthy', value: healthy, color: '#22C55E', sub: `${((healthy / total) * 100).toFixed(0)}% health rate` },
    { label: 'Warning', value: warning, color: '#F59E0B', sub: warning === 0 ? 'No warnings' : 'Needs attention' },
    { label: 'Critical', value: critical, color: '#EF4444', sub: critical === 0 ? 'No critical' : 'Immediate action' },
    { label: 'Running Tasks', value: runningTasks, color: '#38BDF8', sub: 'Active executions' },
    { label: 'Queued Tasks', value: queuedTasks, color: '#A78BFA', sub: 'Pending dispatch' },
    { label: 'Avg CPU', value: `${avgCpu}%`, color: avgCpu >= 80 ? '#EF4444' : avgCpu >= 60 ? '#F59E0B' : '#22C55E', sub: 'Across all agents' },
    { label: 'Avg Memory', value: `${avgMem}%`, color: avgMem >= 80 ? '#EF4444' : avgMem >= 60 ? '#F59E0B' : '#22C55E', sub: 'Across all agents' },
    { label: 'Avg Response', value: `${avgLatency}ms`, color: avgLatency >= 30 ? '#EF4444' : avgLatency >= 15 ? '#F59E0B' : '#22C55E', sub: 'Average latency' },
  ];

  return (
    <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
      {cards.map(card => (
        <Card key={card.label} className="px-4 py-3">
          <p className="text-xs mb-1.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{card.label}</p>
          <p className="text-xl font-bold mb-1" style={{ color: card.color, fontFamily: "'JetBrains Mono', monospace" }}>{card.value}</p>
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{card.sub}</p>
        </Card>
      ))}
    </div>
  );
}

// ─── Agent Directory Table ────────────────────────────────────────────────────

function AgentDirectory({
  agents, selectedId, onSelect, searchQuery, onSearchChange,
}: {
  agents: AgentRecord[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}) {
  const [sortCol, setSortCol] = useState<keyof AgentRecord>('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkMenuOpen, setBulkMenuOpen] = useState(false);

  const filtered = agents.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.role.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortCol] as string | number;
    const bv = b[sortCol] as string | number;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  function toggleSort(col: keyof AgentRecord) {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
  }

  function toggleAll() {
    if (selectedIds.size === sorted.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(sorted.map(a => a.id)));
  }

  function toggleOne(id: string) {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  const SortIcon = ({ col }: { col: keyof AgentRecord }) => (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" style={{ opacity: sortCol === col ? 1 : 0.3 }}>
      <path d={sortCol === col && sortDir === 'desc' ? 'M2 3.5l3 3 3-3' : 'M2 6.5l3-3 3 3'} stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );

  const thStyle: React.CSSProperties = { color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.06em', fontWeight: 600, padding: '8px 12px', textAlign: 'left', whiteSpace: 'nowrap', background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)', userSelect: 'none' };

  return (
    <Card>
      <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: '1px solid var(--akaal-card-border)' }}>
        <div className="flex items-center gap-2 flex-1">
          <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Agent Directory</h2>
          <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{filtered.length}</span>
        </div>
        <div className="relative">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
            <circle cx="5.5" cy="5.5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
            <path d="M8.5 8.5l2.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
          <input type="search" placeholder="Search agents…" value={searchQuery} onChange={e => onSearchChange(e.target.value)}
            className="text-xs rounded-md pl-7 pr-3 py-1.5 outline-none"
            style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif", width: '180px' }}
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; }}
          />
        </div>
        {selectedIds.size > 0 && (
          <div className="relative">
            <button type="button" onClick={() => setBulkMenuOpen(v => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150"
              style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)', border: '1px solid rgba(59,130,246,0.2)', fontFamily: "'Inter', sans-serif" }}
            >
              <span>{selectedIds.size} selected</span>
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
            </button>
            {bulkMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setBulkMenuOpen(false)} aria-hidden="true" />
                <div className="absolute right-0 top-full mt-1 rounded-lg overflow-hidden z-50" style={{ width: '160px', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 24px var(--akaal-shadow)' }}>
                  {['Restart Selected', 'Pause Selected', 'Resume Selected', 'Export Diagnostics'].map((action, i) => (
                    <button key={i} type="button" onClick={() => setBulkMenuOpen(false)}
                      className="w-full text-left px-3 py-2 text-xs transition-colors"
                      style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", borderBottom: i < 3 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                    >{action}</button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: 'collapse', minWidth: '1100px' }}>
          <thead>
            <tr>
              <th style={{ ...thStyle, width: '36px' }}>
                <input type="checkbox" checked={selectedIds.size === sorted.length && sorted.length > 0} onChange={toggleAll}
                  className="rounded" style={{ accentColor: 'var(--akaal-primary)', cursor: 'pointer' }} aria-label="Select all agents" />
              </th>
              {([['name', 'Agent'], ['role', 'Role'], ['version', 'Version'], ['status', 'Status'], ['health', 'Health'], ['currentTask', 'Current Task'], ['cpu', 'CPU'], ['memory', 'Memory'], ['network', 'Network'], ['heartbeat', 'Heartbeat'], ['uptime', 'Uptime'], ['latency', 'Latency']] as [keyof AgentRecord, string][]).map(([col, label]) => (
                <th key={col} style={thStyle}>
                  <button type="button" onClick={() => toggleSort(col)} className="flex items-center gap-1 focus:outline-none" style={{ color: 'inherit', fontFamily: 'inherit', fontSize: 'inherit', letterSpacing: 'inherit', fontWeight: 'inherit' }}>
                    {label} <SortIcon col={col} />
                  </button>
                </th>
              ))}
              <th style={{ ...thStyle, textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={14} className="text-center py-16" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '13px' }}>
                  <div className="flex flex-col items-center gap-2">
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-border)' }}>
                      <circle cx="16" cy="16" r="6" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M16 2v4M16 26v4M2 16h4M26 16h4M6.4 6.4l2.8 2.8M22.8 22.8l2.8 2.8M6.4 25.6l2.8-2.8M22.8 9.2l2.8-2.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                    <p className="font-medium" style={{ color: 'var(--akaal-text-secondary)' }}>No agents found</p>
                    <p className="text-xs">Try adjusting your search or category filter</p>
                  </div>
                </td>
              </tr>
            ) : sorted.map((agent, idx) => (
              <tr key={agent.id}
                onClick={() => onSelect(agent.id)}
                style={{ background: selectedId === agent.id ? 'var(--akaal-primary-subtle)' : idx % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)', cursor: 'pointer', borderBottom: '1px solid var(--akaal-table-border)' }}
                onMouseEnter={e => { if (selectedId !== agent.id) (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { if (selectedId !== agent.id) (e.currentTarget as HTMLElement).style.background = idx % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)'; }}
              >
                <td style={{ padding: '8px 12px' }} onClick={e => e.stopPropagation()}>
                  <input type="checkbox" checked={selectedIds.has(agent.id)} onChange={() => toggleOne(agent.id)}
                    className="rounded" style={{ accentColor: 'var(--akaal-primary)', cursor: 'pointer' }} aria-label={`Select ${agent.name}`} />
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)' }}>
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="6" cy="6" r="2.5" stroke="currentColor" strokeWidth="1.2" /><path d="M6 1v1.5M6 9.5V11M1 6h1.5M9.5 6H11" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                    </div>
                    <div>
                      <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{agent.name}</p>
                      <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{agent.id}</p>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{agent.role}</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>v{agent.version}</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}><AgentStatusChip status={agent.status} /></td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}><HealthChip health={agent.health} /></td>
                <td style={{ padding: '8px 12px', maxWidth: '180px' }}>
                  <span className="text-xs truncate block" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{agent.currentTask}</span>
                </td>
                <td style={{ padding: '8px 12px', minWidth: '80px' }}><UsageBar value={agent.cpu} color="var(--akaal-primary)" /></td>
                <td style={{ padding: '8px 12px', minWidth: '80px' }}><UsageBar value={agent.memory} color="var(--akaal-secondary)" /></td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{agent.network}</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: agent.status === 'offline' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{agent.heartbeat}</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{agent.uptime}</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: agent.latency >= 30 ? 'var(--akaal-error)' : agent.latency >= 15 ? 'var(--akaal-warning)' : 'var(--akaal-success)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{agent.latency}ms</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap', textAlign: 'right' }} onClick={e => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-1">
                    <button type="button" onClick={() => onSelect(agent.id)} className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none"
                      style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-primary-subtle)'; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                      aria-label={`Inspect ${agent.name}`}
                    >Inspect</button>
                    <button type="button" className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none"
                      style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                      aria-label={`View logs for ${agent.name}`}
                    >Logs</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Inspector Panel ──────────────────────────────────────────────────────────

function InspectorPanel({
  agent, onClose, perfData,
}: {
  agent: AgentRecord;
  onClose: () => void;
  perfData: PerfPoint[];
}) {
  const [activeTab, setActiveTab] = useState<InspectorTab>('overview');
  const [logSearch, setLogSearch] = useState('');
  const [logLevel, setLogLevel] = useState<LogLevel | 'ALL'>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [alertFilter, setAlertFilter] = useState<AlertSeverity | 'all'>('all');
  const logRef = useRef<HTMLDivElement>(null);

  const agentAlerts = MOCK_ALERTS.filter(a => a.agentId === agent.id);
  const filteredAlerts = alertFilter === 'all' ? agentAlerts : agentAlerts.filter(a => a.severity === alertFilter);

  const filteredLogs = MOCK_LOGS.filter(l =>
    (logLevel === 'ALL' || l.level === logLevel) &&
    (logSearch === '' || l.message.toLowerCase().includes(logSearch.toLowerCase()))
  );

  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const tabs: { id: InspectorTab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'runtime', label: 'Runtime' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'performance', label: 'Performance' },
    { id: 'logs', label: 'Logs' },
    { id: 'events', label: 'Events' },
    { id: 'configuration', label: 'Config' },
    { id: 'dependencies', label: 'Deps' },
    { id: 'history', label: 'History' },
  ];

  const chartTooltipStyle = { background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', borderRadius: '6px', fontSize: '10px', fontFamily: "'JetBrains Mono', monospace", color: 'var(--akaal-text)' };

  return (
    <div
      className="flex flex-col flex-shrink-0 h-full"
      style={{ width: '480px', background: 'var(--akaal-surface)', borderLeft: '1px solid var(--akaal-border)', boxShadow: '-4px 0 24px var(--akaal-shadow-sm)' }}
      role="complementary"
      aria-label={`Agent inspector: ${agent.name}`}
    >
      {/* Inspector Header */}
      <div className="flex items-center gap-3 px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)' }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{agent.name}</p>
          <p className="text-xs truncate" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{agent.role}</p>
        </div>
        <AgentStatusChip status={agent.status} />
        <button type="button" onClick={onClose} className="flex items-center justify-center w-7 h-7 rounded-md transition-all duration-150 focus:outline-none flex-shrink-0"
          style={{ color: 'var(--akaal-text-muted)' }} aria-label="Close inspector"
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
        </button>
      </div>

      {/* Action Bar */}
      <div className="flex items-center gap-1.5 px-4 py-2 flex-shrink-0 flex-wrap" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        {[
          { label: 'Restart', color: 'var(--akaal-warning)' },
          { label: 'Pause', color: 'var(--akaal-text-muted)' },
          { label: 'Resume', color: 'var(--akaal-success)' },
          { label: 'Drain', color: 'var(--akaal-text-muted)' },
          { label: 'Logs', color: 'var(--akaal-primary)' },
          { label: 'Deps', color: 'var(--akaal-text-muted)' },
        ].map(action => (
          <button key={action.label} type="button"
            className="px-2.5 py-1 rounded text-xs font-medium transition-all duration-150 focus:outline-none"
            style={{ color: action.color, background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface-elevated)'; }}
          >{action.label}</button>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-0 px-4 flex-shrink-0 overflow-x-auto" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        {tabs.map(tab => (
          <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)}
            className="px-3 py-2.5 text-xs font-medium transition-all duration-150 focus:outline-none flex-shrink-0"
            style={{
              color: activeTab === tab.id ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)',
              borderBottom: activeTab === tab.id ? '2px solid var(--akaal-primary)' : '2px solid transparent',
              fontFamily: "'Inter', sans-serif",
              marginBottom: '-1px',
            }}
          >{tab.label}</button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Agent ID', value: agent.id },
                { label: 'Version', value: `v${agent.version}` },
                { label: 'Host', value: agent.host },
                { label: 'Port', value: agent.port.toString() },
                { label: 'Uptime', value: agent.uptime },
                { label: 'Last Activity', value: agent.lastActivity },
                { label: 'Success Rate', value: `${agent.successRate}%` },
                { label: 'Tasks/min', value: agent.tasksPerMin.toString() },
                { label: 'Avg Processing', value: agent.avgProcessingTime },
                { label: 'Restart Count', value: agent.restartCount.toString() },
                { label: 'Failure Count', value: agent.failureCount.toString() },
                { label: 'Heartbeat', value: agent.heartbeat },
              ].map(item => (
                <div key={item.label} className="rounded-md px-3 py-2" style={{ background: 'var(--akaal-surface-elevated)' }}>
                  <p className="text-xs mb-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</p>
                  <p className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</p>
                </div>
              ))}
            </div>
            <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Description</p>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{agent.description}</p>
            </div>
            <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Capabilities</p>
              <div className="flex flex-wrap gap-1.5">
                {agent.capabilities.map(cap => (
                  <span key={cap} className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}>{cap}</span>
                ))}
              </div>
            </div>
            {/* Health Score */}
            <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Health Score</p>
              <div className="space-y-2">
                {[
                  { label: 'CPU Pressure', value: agent.cpu, threshold: 80 },
                  { label: 'Memory Pressure', value: agent.memory, threshold: 80 },
                  { label: 'Task Health', value: agent.successRate, threshold: 90, invert: true },
                  { label: 'Queue Health', value: Math.min(agent.queuedTasks * 2, 100), threshold: 60 },
                ].map(item => (
                  <div key={item.label}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
                      <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{item.value}%</span>
                    </div>
                    <UsageBar value={item.value} color="var(--akaal-primary)" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Runtime Tab */}
        {activeTab === 'runtime' && (
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Running Jobs', value: agent.runningJobs.toString(), color: '#38BDF8' },
                { label: 'Queued Tasks', value: agent.queuedTasks.toString(), color: '#A78BFA' },
                { label: 'Restart Count', value: agent.restartCount.toString(), color: agent.restartCount > 0 ? '#F59E0B' : '#22C55E' },
                { label: 'Failure Count', value: agent.failureCount.toString(), color: agent.failureCount > 0 ? '#EF4444' : '#22C55E' },
                { label: 'Recovery Status', value: agent.health === 'healthy' ? 'Nominal' : 'Monitoring', color: agent.health === 'healthy' ? '#22C55E' : '#F59E0B' },
                { label: 'Last Activity', value: agent.lastActivity, color: 'var(--akaal-text-secondary)' },
              ].map(item => (
                <div key={item.label} className="rounded-md px-3 py-2.5" style={{ background: 'var(--akaal-surface-elevated)' }}>
                  <p className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</p>
                  <p className="text-lg font-bold" style={{ color: item.color, fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</p>
                </div>
              ))}
            </div>
            {/* Execution Timeline */}
            <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Execution Timeline</p>
              <div className="space-y-2">
                {MOCK_EVENTS.slice(0, 6).map(ev => {
                  const meta = EVENT_TYPE_META[ev.type] ?? { color: '#94A3B8', label: ev.type };
                  return (
                    <div key={ev.id} className="flex items-start gap-2.5">
                      <span className="text-xs flex-shrink-0 mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', minWidth: '52px' }}>{ev.timestamp}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0" style={{ color: meta.color, background: `${meta.color}18`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{meta.label}</span>
                      <span className="text-xs leading-relaxed" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{ev.description}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Tasks Tab */}
        {activeTab === 'tasks' && (
          <div className="p-4">
            {MOCK_TASKS.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 gap-2">
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-border)' }}><rect x="2" y="2" width="24" height="24" rx="3" stroke="currentColor" strokeWidth="1.5" /><path d="M8 14h12M8 9h8M8 19h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                <p className="text-sm font-medium" style={{ color: 'var(--akaal-text-secondary)' }}>No Active Tasks</p>
                <p className="text-xs" style={{ color: 'var(--akaal-text-muted)' }}>This agent has no tasks assigned</p>
              </div>
            ) : (
              <div className="space-y-2">
                {MOCK_TASKS.map(task => {
                  const stateMeta = TASK_STATE_META[task.state];
                  const priMeta = PRIORITY_META[task.priority];
                  return (
                    <div key={task.id} className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{task.id}</span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: priMeta.color, background: priMeta.bg, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{priMeta.label}</span>
                          <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: stateMeta.color, background: stateMeta.bg, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{stateMeta.label}</span>
                        </div>
                      </div>
                      <p className="text-xs mb-2" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{task.migration}</p>
                      {task.state === 'running' && (
                        <div className="mb-2">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Progress</span>
                            <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{task.progress}%</span>
                          </div>
                          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-surface)' }}>
                            <div className="h-full rounded-full" style={{ width: `${task.progress}%`, background: 'var(--akaal-primary)' }} />
                          </div>
                        </div>
                      )}
                      <div className="flex items-center gap-4">
                        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>Started: {task.started}</span>
                        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>Duration: {task.duration}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Performance Tab */}
        {activeTab === 'performance' && (
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'CPU', value: `${agent.cpu}%`, color: agent.cpu >= 80 ? '#EF4444' : agent.cpu >= 60 ? '#F59E0B' : '#22C55E' },
                { label: 'Memory', value: `${agent.memory}%`, color: agent.memory >= 80 ? '#EF4444' : agent.memory >= 60 ? '#F59E0B' : '#22C55E' },
                { label: 'Latency', value: `${agent.latency}ms`, color: agent.latency >= 30 ? '#EF4444' : agent.latency >= 15 ? '#F59E0B' : '#22C55E' },
                { label: 'Network', value: agent.network, color: 'var(--akaal-primary)' },
                { label: 'Tasks/min', value: agent.tasksPerMin.toString(), color: 'var(--akaal-secondary)' },
                { label: 'Success Rate', value: `${agent.successRate}%`, color: '#22C55E' },
              ].map(m => (
                <div key={m.label} className="rounded-md px-3 py-2.5 text-center" style={{ background: 'var(--akaal-surface-elevated)' }}>
                  <p className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.label}</p>
                  <p className="text-base font-bold" style={{ color: m.color, fontFamily: "'JetBrains Mono', monospace" }}>{m.value}</p>
                </div>
              ))}
            </div>
            {[
              { key: 'cpu' as keyof PerfPoint, label: 'CPU Usage', color: '#3B82F6', unit: '%' },
              { key: 'mem' as keyof PerfPoint, label: 'Memory Usage', color: '#38BDF8', unit: '%' },
              { key: 'latency' as keyof PerfPoint, label: 'Latency', color: '#F59E0B', unit: 'ms' },
              { key: 'tpm' as keyof PerfPoint, label: 'Tasks per Minute', color: '#22C55E', unit: '' },
            ].map(chart => (
              <div key={chart.key} className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
                <p className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{chart.label}</p>
                <ResponsiveContainer width="100%" height={60}>
                  <AreaChart data={perfData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
                    <defs>
                      <linearGradient id={`grad-${chart.key}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chart.color} stopOpacity={0.25} />
                        <stop offset="95%" stopColor={chart.color} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => [`${v}${chart.unit}`, chart.label]} labelFormatter={() => ''} />
                    <Area type="monotone" dataKey={chart.key} stroke={chart.color} strokeWidth={1.5} fill={`url(#grad-${chart.key})`} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>
        )}

        {/* Logs Tab */}
        {activeTab === 'logs' && (
          <div className="flex flex-col h-full">
            <div className="flex items-center gap-2 px-4 py-2.5 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <div className="relative flex-1">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
                  <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.2" /><path d="M8 8l2.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                </svg>
                <input type="search" placeholder="Search logs…" value={logSearch} onChange={e => setLogSearch(e.target.value)}
                  className="w-full text-xs rounded pl-6 pr-2 py-1 outline-none"
                  style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}
                />
              </div>
              <select value={logLevel} onChange={e => setLogLevel(e.target.value as LogLevel | 'ALL')}
                className="text-xs rounded px-2 py-1 outline-none"
                style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}
              >
                {(['ALL', 'INFO', 'WARN', 'ERROR', 'DEBUG', 'SUCCESS'] as const).map(l => <option key={l} value={l}>{l}</option>)}
              </select>
              <button type="button" onClick={() => setAutoScroll(v => !v)}
                className="px-2 py-1 rounded text-xs transition-all duration-150"
                style={{ background: autoScroll ? 'var(--akaal-primary-subtle)' : 'var(--akaal-surface-elevated)', color: autoScroll ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px', border: '1px solid var(--akaal-border)' }}
              >Auto</button>
            </div>
            <div ref={logRef} className="flex-1 overflow-y-auto p-3 space-y-1" style={{ background: 'var(--akaal-code-bg)', fontFamily: "'JetBrains Mono', monospace" }}>
              {filteredLogs.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-xs" style={{ color: 'var(--akaal-text-muted)' }}>No log entries match your filter</p>
                </div>
              ) : filteredLogs.map(log => {
                const meta = LOG_LEVEL_META[log.level];
                return (
                  <div key={log.id} className="flex items-start gap-2 text-xs leading-relaxed">
                    <span className="flex-shrink-0 text-xs" style={{ color: 'var(--akaal-text-muted)', fontSize: '9px', minWidth: '72px' }}>{log.timestamp}</span>
                    <span className="flex-shrink-0 px-1.5 py-0.5 rounded text-xs" style={{ color: meta.color, background: meta.bg, fontSize: '9px', minWidth: '52px', textAlign: 'center' }}>{log.level}</span>
                    {log.source && <span className="flex-shrink-0 text-xs" style={{ color: 'var(--akaal-text-muted)', fontSize: '9px', minWidth: '64px' }}>[{log.source}]</span>}
                    <span className="text-xs" style={{ color: 'var(--akaal-code-text)', fontSize: '10px' }}>{log.message}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-between px-4 py-2 flex-shrink-0" style={{ borderTop: '1px solid var(--akaal-border)' }}>
              <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{filteredLogs.length} entries</span>
              <div className="flex items-center gap-2">
                <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >Copy</button>
                <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >Download</button>
              </div>
            </div>
          </div>
        )}

        {/* Events Tab */}
        {activeTab === 'events' && (
          <div className="p-4">
            <div className="space-y-0">
              {MOCK_EVENTS.map((ev, idx) => {
                const meta = EVENT_TYPE_META[ev.type] ?? { color: '#94A3B8', label: ev.type };
                const severityColors = { info: '#38BDF8', success: '#22C55E', warning: '#F59E0B', error: '#EF4444' };
                const dotColor = severityColors[ev.severity];
                return (
                  <div key={ev.id} className="flex items-start gap-3 relative">
                    <div className="flex flex-col items-center flex-shrink-0">
                      <div className="w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0" style={{ background: dotColor, boxShadow: `0 0 6px ${dotColor}60` }} aria-hidden="true" />
                      {idx < MOCK_EVENTS.length - 1 && <div className="w-px flex-1 mt-1" style={{ background: 'var(--akaal-border)', minHeight: '24px' }} aria-hidden="true" />}
                    </div>
                    <div className="pb-4 flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: meta.color, background: `${meta.color}18`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{meta.label}</span>
                        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{ev.timestamp}</span>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{ev.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Configuration Tab */}
        {activeTab === 'configuration' && (
          <div className="p-4 space-y-4">
            <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Agent Configuration</p>
              <div className="space-y-2">
                {[
                  { key: 'agent.id', value: agent.id },
                  { key: 'agent.version', value: agent.version },
                  { key: 'agent.host', value: agent.host },
                  { key: 'agent.port', value: agent.port.toString() },
                  { key: 'agent.heartbeat_interval', value: '5s' },
                  { key: 'agent.max_concurrent_tasks', value: '8' },
                  { key: 'agent.retry_limit', value: '3' },
                  { key: 'agent.timeout', value: '30s' },
                  { key: 'agent.log_level', value: 'INFO' },
                  { key: 'agent.metrics_enabled', value: 'true' },
                ].map(cfg => (
                  <div key={cfg.key} className="flex items-center justify-between py-1.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                    <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cfg.key}</span>
                    <span className="text-xs" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cfg.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Dependencies Tab */}
        {activeTab === 'dependencies' && (
          <div className="p-4 space-y-4">
            <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Dependencies</p>
              <div className="space-y-2">
                {agent.dependencies.map(dep => (
                  <div key={dep} className="flex items-center justify-between px-3 py-2 rounded" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ background: '#22C55E' }} aria-hidden="true" />
                      <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{dep}</span>
                    </div>
                    <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: '#22C55E', background: 'rgba(34,197,94,0.08)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>Connected</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-md p-3" style={{ background: 'var(--akaal-surface-elevated)' }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>Communication</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Incoming Msgs', value: '1,284/min' },
                  { label: 'Outgoing Msgs', value: '847/min' },
                  { label: 'Message Queue', value: agent.queuedTasks.toString() },
                  { label: 'Retries', value: agent.restartCount.toString() },
                ].map(item => (
                  <div key={item.label} className="rounded px-3 py-2" style={{ background: 'var(--akaal-surface)' }}>
                    <p className="text-xs mb-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</p>
                    <p className="text-sm font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="p-4">
            <div className="space-y-2">
              {[
                { date: '2026-07-25', event: 'Agent upgraded to v' + agent.version, type: 'upgrade' },
                { date: '2026-07-24', event: 'Completed 1,284 tasks — 99.8% success rate', type: 'completed' },
                { date: '2026-07-23', event: 'Health check passed — all metrics nominal', type: 'heartbeat' },
                { date: '2026-07-22', event: 'Configuration updated — timeout increased to 30s', type: 'checkpoint' },
                { date: '2026-07-21', event: 'Agent restarted after scheduled maintenance', type: 'restart' },
                { date: '2026-07-20', event: 'Completed 1,102 tasks — 98.4% success rate', type: 'completed' },
                { date: '2026-07-19', event: 'Warning: elevated latency detected (28ms)', type: 'warning' },
                { date: '2026-07-18', event: 'Agent started — joined agent pool', type: 'started' },
              ].map((item, idx) => {
                const meta = EVENT_TYPE_META[item.type] ?? { color: '#94A3B8', label: item.type };
                return (
                  <div key={idx} className="flex items-start gap-3 py-2" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                    <span className="text-xs flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', minWidth: '72px' }}>{item.date}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0" style={{ color: meta.color, background: `${meta.color}18`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{meta.label}</span>
                    <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{item.event}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

// ─── Alert Center ─────────────────────────────────────────────────────────────

function AlertCenter({ alerts }: { alerts: AgentAlert[] }) {
  const [filter, setFilter] = useState<AlertSeverity | 'all'>('all');
  const [acknowledged, setAcknowledged] = useState<Set<string>>(new Set());

  const filtered = filter === 'all' ? alerts : alerts.filter(a => a.severity === filter);

  return (
    <Card>
      <SectionHeader
        title="Alert Center"
        subtitle={`${alerts.filter(a => !a.acknowledged).length} unacknowledged`}
        action={
          <div className="flex items-center gap-1">
            {(['all', 'critical', 'warning', 'info', 'resolved'] as const).map(f => (
              <button key={f} type="button" onClick={() => setFilter(f)}
                className="px-2 py-1 rounded text-xs transition-all duration-150 capitalize"
                style={{ background: filter === f ? 'var(--akaal-primary-subtle)' : 'transparent', color: filter === f ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
              >{f}</button>
            ))}
          </div>
        }
      />
      <div className="divide-y" style={{ borderColor: 'var(--akaal-card-border)' }}>
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-border)' }}><path d="M14 3l11 19H3L14 3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /><path d="M14 11v5M14 19v1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            <p className="text-sm font-medium" style={{ color: 'var(--akaal-text-secondary)' }}>No Alerts</p>
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)' }}>All agents are operating normally</p>
          </div>
        ) : filtered.map(alert => {
          const meta = ALERT_META[alert.severity];
          const isAck = acknowledged.has(alert.id) || alert.acknowledged;
          return (
            <div key={alert.id} className="flex items-start gap-3 px-4 py-3" style={{ opacity: isAck ? 0.6 : 1 }}>
              <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" style={{ background: meta.color }} aria-hidden="true" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{alert.title}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: meta.color, background: meta.bg, border: `1px solid ${meta.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{meta.label}</span>
                </div>
                <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{alert.detail}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{alert.time}</p>
              </div>
              {!isAck && (
                <button type="button" onClick={() => setAcknowledged(prev => new Set([...prev, alert.id]))}
                  className="text-xs px-2 py-1 rounded flex-shrink-0 transition-all duration-150"
                  style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-surface-elevated)', fontFamily: "'Inter', sans-serif", fontSize: '10px', border: '1px solid var(--akaal-border)' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface-elevated)'; }}
                >Ack</button>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeCategory, setActiveCategory] = useState<AgentCategory>('all');
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [perfData, setPerfData] = useState<PerfPoint[]>([]);
  const [liveTime, setLiveTime] = useState('');
  const [confirmAction, setConfirmAction] = useState<{ label: string; agentId: string } | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 900);
    setPerfData(generatePerfData());
    setLiveTime(new Date().toLocaleTimeString());
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setPerfData(generatePerfData());
      setLiveTime(new Date().toLocaleTimeString());
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const filteredAgents = activeCategory === 'all'
    ? MOCK_AGENTS
    : MOCK_AGENTS.filter(a => a.category === activeCategory);

  const categoryCounts = Object.fromEntries(
    (['all', 'core', 'migration', 'validation', 'recovery', 'monitoring', 'notification', 'infrastructure'] as AgentCategory[]).map(cat => [
      cat,
      cat === 'all' ? MOCK_AGENTS.length : MOCK_AGENTS.filter(a => a.category === cat).length,
    ])
  ) as Record<AgentCategory, number>;

  const selectedAgent = selectedAgentId ? MOCK_AGENTS.find(a => a.id === selectedAgentId) ?? null : null;

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--akaal-bg)' }}>
      <style>{`
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
      `}</style>

      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopNav />

        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Category Filter */}
          <CategoryFilter active={activeCategory} onSelect={setActiveCategory} counts={categoryCounts} />

          {/* Main Content */}
          <main className="flex-1 overflow-y-auto min-w-0" style={{ background: 'var(--akaal-bg)' }}>
            {/* Page Header */}
            <div className="px-6 py-4 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h1 className="text-lg font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Agents</h1>
                    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)' }}>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#22C55E', animation: 'pulse 1.5s ease-in-out infinite' }} aria-hidden="true" />
                      <span className="text-xs font-medium" style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>LIVE</span>
                    </div>
                  </div>
                  <p className="text-sm" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
                    Monitor and manage the AKAAL intelligent agent network.
                    {liveTime && <span className="ml-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>Updated {liveTime}</span>}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button type="button" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-surface)'; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M10 6A4 4 0 1 1 6 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M10 2v3H7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    Refresh
                  </button>
                  <button type="button" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-surface)'; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 6a4 4 0 1 0 8 0 4 4 0 0 0-8 0Z" stroke="currentColor" strokeWidth="1.2" /><path d="M6 4v2l1.5 1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                    Restart Selected
                  </button>
                  <button type="button" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'var(--akaal-surface)'; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 9V3l8 3-8 3Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /></svg>
                    Export Diagnostics
                  </button>
                  <button type="button" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ color: '#fff', background: 'var(--akaal-primary)', border: '1px solid var(--akaal-primary)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.opacity = '0.9'; }}
                    onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 2v8M2 6h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                    Register Agent
                  </button>
                </div>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* KPI Cards */}
              {loading ? (
                <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
                  {Array.from({ length: 11 }).map((_, i) => <Skeleton key={i} style={{ height: '80px' }} />)}
                </div>
              ) : (
                <KpiCards agents={MOCK_AGENTS} />
              )}

              {/* Agent Directory */}
              {loading ? (
                <Card>
                  <div className="p-4 space-y-3">
                    <Skeleton style={{ height: '36px', width: '200px' }} />
                    {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} style={{ height: '44px' }} />)}
                  </div>
                </Card>
              ) : (
                <AgentDirectory
                  agents={filteredAgents}
                  selectedId={selectedAgentId}
                  onSelect={id => setSelectedAgentId(prev => prev === id ? null : id)}
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                />
              )}

              {/* Alert Center */}
              {!loading && <AlertCenter alerts={MOCK_ALERTS} />}

              {/* Event Timeline */}
              {!loading && (
                <Card>
                  <SectionHeader title="Event Timeline" subtitle="Live agent activity stream" />
                  <div className="p-4 space-y-0">
                    {MOCK_EVENTS.map((ev, idx) => {
                      const meta = EVENT_TYPE_META[ev.type] ?? { color: '#94A3B8', label: ev.type };
                      const severityColors = { info: '#38BDF8', success: '#22C55E', warning: '#F59E0B', error: '#EF4444' };
                      const dotColor = severityColors[ev.severity];
                      return (
                        <div key={ev.id} className="flex items-start gap-3 relative">
                          <div className="flex flex-col items-center flex-shrink-0">
                            <div className="w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0" style={{ background: dotColor, boxShadow: `0 0 6px ${dotColor}60` }} aria-hidden="true" />
                            {idx < MOCK_EVENTS.length - 1 && <div className="w-px flex-1 mt-1" style={{ background: 'var(--akaal-border)', minHeight: '24px' }} aria-hidden="true" />}
                          </div>
                          <div className="pb-3 flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: meta.color, background: `${meta.color}18`, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{meta.label}</span>
                              <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{ev.timestamp}</span>
                            </div>
                            <p className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{ev.description}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              )}
            </div>
          </main>

          {/* Inspector Panel */}
          {selectedAgent && (
            <div style={{ animation: 'slideIn 0.2s ease' }}>
              <InspectorPanel
                agent={selectedAgent}
                onClose={() => setSelectedAgentId(null)}
                perfData={perfData}
              />
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmAction && (
        <>
          <div className="fixed inset-0 z-50" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => setConfirmAction(null)} aria-hidden="true" />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="rounded-xl p-6 w-full max-w-sm" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 24px 64px var(--akaal-shadow)' }} role="dialog" aria-modal="true" aria-labelledby="confirm-title">
              <h3 id="confirm-title" className="text-sm font-semibold mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Confirm {confirmAction.label}</h3>
              <p className="text-xs mb-4" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Are you sure you want to {confirmAction.label.toLowerCase()} this agent? This action may affect active migrations.</p>
              <div className="flex items-center justify-end gap-2">
                <button type="button" onClick={() => setConfirmAction(null)} className="px-3 py-1.5 rounded-md text-xs font-medium" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>Cancel</button>
                <button type="button" onClick={() => setConfirmAction(null)} className="px-3 py-1.5 rounded-md text-xs font-medium" style={{ color: '#fff', background: 'var(--akaal-error)', fontFamily: "'Inter', sans-serif" }}>Confirm {confirmAction.label}</button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
