'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';
import { AreaChart, Area, Tooltip, ResponsiveContainer } from 'recharts';

// ─── Types ────────────────────────────────────────────────────────────────────

type SystemSection =
  | 'platform' | 'runtime' | 'services' | 'api' | 'configuration' | 'feature-flags'
  | 'security'| 'users' | 'organizations' | 'teams' | 'rbac' |'licensing' | 'integrations' | 'notifications' | 'observability'
  | 'diagnostics' | 'maintenance' | 'backup';

type ServiceStatus = 'running' | 'stopped' | 'degraded' | 'starting' | 'restarting';
type ServiceHealth = 'healthy' | 'warning' | 'critical' | 'unknown';
type InspectorTab = 'overview' | 'configuration' | 'metrics' | 'logs' | 'dependencies' | 'events' | 'history';
type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | 'SUCCESS';

interface ServiceRecord {
  id: string;
  name: string;
  version: string;
  status: ServiceStatus;
  health: ServiceHealth;
  dependencies: string[];
  cpu: number;
  memory: number;
  restartCount: number;
  uptime: string;
  description: string;
  port: number;
  host: string;
}

interface MetricPoint {
  t: string;
  v: number;
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
}

interface IntegrationRecord {
  id: string;
  name: string;
  connection: 'connected' | 'disconnected' | 'error';
  version: string;
  health: ServiceHealth;
  lastSync: string;
  category: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_SERVICES: ServiceRecord[] = [
  { id: 'svc-migration-runtime', name: 'Migration Runtime', version: '3.2.1', status: 'running', health: 'healthy', dependencies: ['Planning Engine', 'Execution Engine', 'Database'], cpu: 42, memory: 58, restartCount: 0, uptime: '14d 6h 22m', description: 'Core migration runtime orchestrating all migration workflows and lifecycle management.', port: 8080, host: 'prod-runtime-01.akaal.io' },
  { id: 'svc-planning-engine', name: 'Planning Engine', version: '2.8.4', status: 'running', health: 'healthy', dependencies: ['Configuration Service', 'Database'], cpu: 28, memory: 34, restartCount: 1, uptime: '14d 5h 44m', description: 'AI-powered migration planning engine generating optimized execution strategies.', port: 8081, host: 'prod-planning-01.akaal.io' },
  { id: 'svc-execution-engine', name: 'Execution Engine', version: '3.1.0', status: 'running', health: 'healthy', dependencies: ['Migration Runtime', 'Scheduler', 'Database'], cpu: 67, memory: 71, restartCount: 0, uptime: '14d 6h 22m', description: 'High-throughput execution engine managing parallel migration task processing.', port: 8082, host: 'prod-execution-01.akaal.io' },
  { id: 'svc-validation-engine', name: 'Validation Engine', version: '2.9.2', status: 'running', health: 'healthy', dependencies: ['Execution Engine', 'Database'], cpu: 22, memory: 29, restartCount: 0, uptime: '14d 6h 18m', description: 'Comprehensive data integrity and schema validation engine.', port: 8083, host: 'prod-validation-01.akaal.io' },
  { id: 'svc-reporting-engine', name: 'Reporting Engine', version: '2.4.1', status: 'running', health: 'healthy', dependencies: ['Database', 'Audit Service'], cpu: 14, memory: 22, restartCount: 0, uptime: '14d 6h 22m', description: 'Enterprise reporting and analytics engine for operational insights.', port: 8084, host: 'prod-reporting-01.akaal.io' },
  { id: 'svc-notification', name: 'Notification Service', version: '2.3.0', status: 'running', health: 'healthy', dependencies: ['Message Queue', 'Configuration Service'], cpu: 8, memory: 14, restartCount: 0, uptime: '14d 6h 20m', description: 'Multi-channel notification dispatch service for alerts and events.', port: 8085, host: 'prod-notification-01.akaal.io' },
  { id: 'svc-security', name: 'Security Service', version: '3.0.1', status: 'running', health: 'healthy', dependencies: ['Vault', 'Identity Federation'], cpu: 11, memory: 18, restartCount: 0, uptime: '14d 6h 22m', description: 'Zero-trust security service managing authentication, authorization, and encryption.', port: 8086, host: 'prod-security-01.akaal.io' },
  { id: 'svc-configuration', name: 'Configuration Service', version: '2.6.3', status: 'running', health: 'healthy', dependencies: ['Vault', 'Database'], cpu: 6, memory: 12, restartCount: 0, uptime: '14d 6h 22m', description: 'Centralized configuration management with hot-reload and versioning.', port: 8087, host: 'prod-config-01.akaal.io' },
  { id: 'svc-scheduler', name: 'Scheduler', version: '2.7.0', status: 'running', health: 'warning', dependencies: ['Database', 'Message Queue'], cpu: 54, memory: 48, restartCount: 2, uptime: '14d 4h 12m', description: 'Distributed job scheduler managing migration task queuing and execution timing.', port: 8088, host: 'prod-scheduler-01.akaal.io' },
  { id: 'svc-audit', name: 'Audit Service', version: '2.5.2', status: 'running', health: 'healthy', dependencies: ['Database', 'Security Service'], cpu: 9, memory: 16, restartCount: 0, uptime: '14d 6h 22m', description: 'Immutable audit trail service capturing all platform events and changes.', port: 8089, host: 'prod-audit-01.akaal.io' },
  { id: 'svc-health', name: 'Health Service', version: '3.2.1', status: 'running', health: 'healthy', dependencies: ['All Services'], cpu: 7, memory: 11, restartCount: 0, uptime: '14d 6h 22m', description: 'Platform-wide health monitoring and aggregation service.', port: 8090, host: 'prod-health-01.akaal.io' },
  { id: 'svc-api-gateway', name: 'API Gateway', version: '3.1.4', status: 'running', health: 'healthy', dependencies: ['Security Service', 'Rate Limiter'], cpu: 31, memory: 38, restartCount: 0, uptime: '14d 6h 22m', description: 'Enterprise API gateway with rate limiting, authentication, and routing.', port: 443, host: 'prod-gateway-01.akaal.io' },
];

const MOCK_INTEGRATIONS: IntegrationRecord[] = [
  { id: 'int-prometheus', name: 'Prometheus', connection: 'connected', version: '2.47.0', health: 'healthy', lastSync: '5s ago', category: 'Observability' },
  { id: 'int-grafana', name: 'Grafana', connection: 'connected', version: '10.2.0', health: 'healthy', lastSync: '30s ago', category: 'Observability' },
  { id: 'int-otel', name: 'OpenTelemetry', connection: 'connected', version: '0.88.0', health: 'healthy', lastSync: '2s ago', category: 'Observability' },
  { id: 'int-slack', name: 'Slack', connection: 'connected', version: 'API v2', health: 'healthy', lastSync: '1m ago', category: 'Notifications' },
  { id: 'int-teams', name: 'Microsoft Teams', connection: 'connected', version: 'Graph API v1', health: 'healthy', lastSync: '2m ago', category: 'Notifications' },
  { id: 'int-smtp', name: 'SMTP', connection: 'connected', version: 'RFC 5321', health: 'healthy', lastSync: '5m ago', category: 'Notifications' },
  { id: 'int-webhook', name: 'Webhook', connection: 'connected', version: 'HTTP/1.1', health: 'warning', lastSync: '12m ago', category: 'Notifications' },
  { id: 'int-vault', name: 'Vault', connection: 'connected', version: '1.15.2', health: 'healthy', lastSync: '10s ago', category: 'Security' },
  { id: 'int-siem', name: 'SIEM', connection: 'disconnected', version: 'v4.2', health: 'unknown', lastSync: '2h ago', category: 'Security' },
];

const MOCK_LOGS: LogEntry[] = [
  { id: 'lg1', timestamp: '16:17:02.441', level: 'INFO', message: 'Platform health check cycle #8821 completed — all services nominal', source: 'Health Service' },
  { id: 'lg2', timestamp: '16:16:58.112', level: 'DEBUG', message: 'Configuration hot-reload triggered — 3 keys updated', source: 'Configuration Service' },
  { id: 'lg3', timestamp: '16:16:44.009', level: 'WARN', message: 'Scheduler CPU at 54% — approaching threshold', source: 'Scheduler' },
  { id: 'lg4', timestamp: '16:16:30.882', level: 'INFO', message: 'API Gateway processed 1,240 requests in last 60s — avg latency 12ms', source: 'API Gateway' },
  { id: 'lg5', timestamp: '16:15:30.001', level: 'INFO', message: 'Secret rotation completed — 4 certificates renewed', source: 'Security Service' },
  { id: 'lg6', timestamp: '16:14:12.334', level: 'SUCCESS', message: 'Backup snapshot SYS-SNAP-20240726-1614 created successfully', source: 'Backup Service' },
  { id: 'lg7', timestamp: '16:12:55.221', level: 'INFO', message: 'License usage: 847/1000 users (84.7%) — 153 seats available', source: 'License Service' },
  { id: 'lg8', timestamp: '16:11:20.009', level: 'ERROR', message: 'SIEM integration connection timeout — retrying in 60s', source: 'Security Service' },
  { id: 'lg9', timestamp: '16:10:44.009', level: 'INFO', message: 'Prometheus metrics scraped — 2,847 time series exported', source: 'Observability' },
  { id: 'lg10', timestamp: '16:09:30.118', level: 'DEBUG', message: 'Feature flag evaluation: migration.parallel_mode=true for org-42', source: 'Configuration Service' },
  { id: 'lg11', timestamp: '16:09:00.000', level: 'INFO', message: 'Audit Service committed 1,240 events to immutable log', source: 'Audit Service' },
  { id: 'lg12', timestamp: '16:08:55.441', level: 'SUCCESS', message: 'mTLS certificate rotation completed — all services re-authenticated', source: 'Security Service' },
  { id: 'lg13', timestamp: '16:05:00.002', level: 'WARN', message: 'Webhook delivery failure rate 2.1% — above 1% threshold', source: 'Notification Service' },
  { id: 'lg14', timestamp: '16:02:18.334', level: 'INFO', message: 'Platform uptime: 14d 6h 22m — SLA compliance 99.97%', source: 'Health Service' },
  { id: 'lg15', timestamp: '16:02:22.001', level: 'INFO', message: 'Execution Engine worker pool: 8/8 active — 0 idle', source: 'Execution Engine' },
];

function generateMetricData(base: number, variance: number): MetricPoint[] {
  const now = Date.now();
  return Array.from({ length: 30 }, (_, i) => {
    const t = new Date(now - (29 - i) * 10_000);
    const h = t.getHours().toString().padStart(2, '0');
    const m = t.getMinutes().toString().padStart(2, '0');
    return { t: `${h}:${m}`, v: Math.max(0, Math.min(100, base + Math.round(Math.sin(i * 0.4) * variance + Math.random() * (variance / 2)))) };
  });
}

// ─── Status / Health Config ───────────────────────────────────────────────────

const SERVICE_STATUS_META: Record<ServiceStatus, { label: string; color: string; bg: string; border: string; animated: boolean }> = {
  running:    { label: 'Running',    color: '#22C55E', bg: 'rgba(34,197,94,0.08)',    border: 'rgba(34,197,94,0.2)',    animated: false },
  stopped:    { label: 'Stopped',    color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)', animated: false },
  degraded:   { label: 'Degraded',   color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.2)',  animated: true },
  starting:   { label: 'Starting',   color: '#38BDF8', bg: 'rgba(56,189,248,0.08)',  border: 'rgba(56,189,248,0.2)',  animated: true },
  restarting: { label: 'Restarting', color: '#A78BFA', bg: 'rgba(167,139,250,0.08)', border: 'rgba(167,139,250,0.2)', animated: true },
};

const SERVICE_HEALTH_META: Record<ServiceHealth, { label: string; color: string; bg: string; border: string }> = {
  healthy:  { label: 'Healthy',  color: '#22C55E', bg: 'rgba(34,197,94,0.08)',    border: 'rgba(34,197,94,0.2)' },
  warning:  { label: 'Warning',  color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',   border: 'rgba(245,158,11,0.2)' },
  critical: { label: 'Critical', color: '#EF4444', bg: 'rgba(239,68,68,0.08)',    border: 'rgba(239,68,68,0.2)' },
  unknown:  { label: 'Unknown',  color: '#94A3B8', bg: 'rgba(148,163,184,0.08)',  border: 'rgba(148,163,184,0.2)' },
};

const LOG_LEVEL_META: Record<LogLevel, { color: string; bg: string }> = {
  INFO:    { color: '#38BDF8', bg: 'rgba(56,189,248,0.08)' },
  WARN:    { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)' },
  ERROR:   { color: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
  DEBUG:   { color: '#64748B', bg: 'rgba(100,116,139,0.08)' },
  SUCCESS: { color: '#22C55E', bg: 'rgba(34,197,94,0.08)' },
};

const CONN_META: Record<IntegrationRecord['connection'], { label: string; color: string; bg: string; border: string }> = {
  connected:    { label: 'Connected',    color: '#22C55E', bg: 'rgba(34,197,94,0.08)',    border: 'rgba(34,197,94,0.2)' },
  disconnected: { label: 'Disconnected', color: '#64748B', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)' },
  error:        { label: 'Error',        color: '#EF4444', bg: 'rgba(239,68,68,0.08)',    border: 'rgba(239,68,68,0.2)' },
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

function ServiceStatusChip({ status }: { status: ServiceStatus }) {
  const cfg = SERVICE_STATUS_META[status];
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color, animation: cfg.animated ? 'pulse 1.5s ease-in-out infinite' : 'none' }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function HealthChip({ health }: { health: ServiceHealth }) {
  const cfg = SERVICE_HEALTH_META[health];
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color }} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}

function ConnChip({ connection }: { connection: IntegrationRecord['connection'] }) {
  const cfg = CONN_META[connection];
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

function InfoRow({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
      <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{label}</span>
      <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: mono ? "'JetBrains Mono', monospace" : "'Inter', sans-serif" }}>{value}</span>
    </div>
  );
}

function MiniChart({ data, color }: { data: MetricPoint[]; color: string }) {
  return (
    <ResponsiveContainer width="100%" height={40}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
        <defs>
          <linearGradient id={`grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} fill={`url(#grad-${color.replace('#', '')})`} dot={false} />
        <Tooltip contentStyle={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', borderRadius: '4px', fontSize: '10px', fontFamily: "'JetBrains Mono', monospace", color: 'var(--akaal-text)', padding: '4px 8px' }} formatter={(v: number) => [`${v}%`, '']} labelFormatter={() => ''} />
      </AreaChart>
    </ResponsiveContainer>
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
    { href: '/reports', label: 'Reports', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/system', label: 'System', active: true, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="3" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="4.5" r="0.8" fill="currentColor" /><circle cx="4" cy="9.5" r="0.8" fill="currentColor" /><path d="M5 13h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
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

function TopNav({ searchValue, onSearchChange }: { searchValue: string; onSearchChange: (v: string) => void }) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="flex items-center gap-4 px-4 flex-shrink-0" style={{ height: '57px', background: 'var(--akaal-nav-bg)', borderBottom: '1px solid var(--akaal-nav-border)' }} role="banner">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 flex-shrink-0">
        <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Platform</span>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>System</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
          <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <input type="search" placeholder="Search services, config, users, logs…" value={searchValue} onChange={e => onSearchChange(e.target.value)}
          className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
          style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
          aria-label="Global system search"
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

// ─── Left Section Navigation ──────────────────────────────────────────────────

const SECTION_GROUPS: { label: string; items: { id: SystemSection; label: string; icon: React.ReactNode }[] }[] = [
  {
    label: 'Infrastructure',
    items: [
      { id: 'platform', label: 'Platform', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="2" width="12" height="3" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><rect x="1" y="7" width="12" height="3" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><circle cx="11" cy="3.5" r="0.8" fill="currentColor" /><circle cx="11" cy="8.5" r="0.8" fill="currentColor" /></svg> },
      { id: 'runtime', label: 'Runtime', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.2" /><path d="M5 4.5l4 2.5-4 2.5V4.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /></svg> },
      { id: 'services', label: 'Services', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="5" height="5" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><rect x="8" y="1" width="5" height="5" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><rect x="1" y="8" width="5" height="5" rx="0.8" stroke="currentColor" strokeWidth="1.2" /><rect x="8" y="8" width="5" height="5" rx="0.8" stroke="currentColor" strokeWidth="1.2" /></svg> },
      { id: 'api', label: 'API Platform', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    ],
  },
  {
    label: 'Configuration',
    items: [
      { id: 'configuration', label: 'Configuration', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.2" /><path d="M7 1v1.5M7 11.5V13M1 7h1.5M11.5 7H13M2.9 2.9l1.1 1.1M10 10l1.1 1.1M2.9 11.1L4 10M10 4l1.1-1.1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'feature-flags', label: 'Feature Flags', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2v10M2 2l8 3-8 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    ],
  },
  {
    label: 'Security',
    items: [
      { id: 'security', label: 'Security', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1L2 3.5v4c0 2.8 2.1 5.4 5 6 2.9-.6 5-3.2 5-6v-4L7 1Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /></svg> },
      { id: 'users', label: 'Users', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="4.5" r="2.5" stroke="currentColor" strokeWidth="1.2" /><path d="M1.5 12.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'organizations', label: 'Organizations', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="5" y="1" width="4" height="3" rx="0.5" stroke="currentColor" strokeWidth="1.2" /><rect x="1" y="8" width="4" height="3" rx="0.5" stroke="currentColor" strokeWidth="1.2" /><rect x="9" y="8" width="4" height="3" rx="0.5" stroke="currentColor" strokeWidth="1.2" /><path d="M7 4v2.5M7 6.5H3.5v1.5M7 6.5h3v1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'teams', label: 'Teams', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="5" cy="4" r="2" stroke="currentColor" strokeWidth="1.2" /><circle cx="10" cy="4" r="2" stroke="currentColor" strokeWidth="1.2" /><path d="M1 12c0-2.2 1.8-4 4-4s4 1.8 4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /><path d="M10 8c1.7 0 3 1.3 3 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'rbac', label: 'RBAC', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="4" width="4" height="3" rx="0.5" stroke="currentColor" strokeWidth="1.2" /><rect x="9" y="1" width="4" height="3" rx="0.5" stroke="currentColor" strokeWidth="1.2" /><rect x="9" y="7" width="4" height="3" rx="0.5" stroke="currentColor" strokeWidth="1.2" /><path d="M5 5.5h2.5v-3H9M5 5.5h2.5v3H9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
    ],
  },
  {
    label: 'Operations',
    items: [
      { id: 'licensing', label: 'Licensing', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="2" width="12" height="10" rx="1" stroke="currentColor" strokeWidth="1.2" /><path d="M4 6h6M4 9h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'integrations', label: 'Integrations', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="3" cy="7" r="2" stroke="currentColor" strokeWidth="1.2" /><circle cx="11" cy="7" r="2" stroke="currentColor" strokeWidth="1.2" /><path d="M5 7h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'notifications', label: 'Notifications', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5a4 4 0 0 0-4 4v2.5L1.5 10h11L11 8V5.5a4 4 0 0 0-4-4Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /><path d="M5.5 11.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.2" /></svg> },
      { id: 'observability', label: 'Observability', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 9l2.5-3 2.5 2 2.5-4 2.5 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    ],
  },
  {
    label: 'Maintenance',
    items: [
      { id: 'diagnostics', label: 'Diagnostics', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /><circle cx="7" cy="7" r="3" stroke="currentColor" strokeWidth="1.2" /></svg> },
      { id: 'maintenance', label: 'Maintenance', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M9.5 2.5a3 3 0 0 1 0 4.2L4.2 12a1.5 1.5 0 0 1-2.1-2.1L7.3 4.6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /><circle cx="10" cy="4" r="1" fill="currentColor" /></svg> },
      { id: 'backup', label: 'Backup & Restore', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2a5 5 0 1 0 4.33 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /><path d="M11 1v3.5H7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /><path d="M7 6v3l2 1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    ],
  },
];

function SectionNav({ active, onSelect }: { active: SystemSection; onSelect: (s: SystemSection) => void }) {
  return (
    <div className="flex flex-col flex-shrink-0" style={{ width: '196px', background: 'var(--akaal-nav-bg)', borderRight: '1px solid var(--akaal-nav-border)', overflowY: 'auto' }}>
      <div className="px-3 py-3" style={{ borderBottom: '1px solid var(--akaal-nav-border)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.1em' }}>System Modules</p>
      </div>
      <nav aria-label="System sections" className="py-2">
        {SECTION_GROUPS.map(group => (
          <div key={group.label} className="mb-1">
            <p className="px-3 py-1.5 text-xs uppercase tracking-wider" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em', opacity: 0.7 }}>{group.label}</p>
            <ul className="space-y-0.5 px-2" role="list">
              {group.items.map(item => (
                <li key={item.id}>
                  <button type="button" onClick={() => onSelect(item.id)}
                    className="w-full flex items-center gap-2 px-2 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 text-left"
                    style={{ color: active === item.id ? 'var(--akaal-text)' : 'var(--akaal-text-muted)', background: active === item.id ? 'var(--akaal-primary-subtle)' : 'transparent', borderLeft: active === item.id ? '2px solid var(--akaal-primary)' : '2px solid transparent', fontFamily: "'Inter', sans-serif" }}
                    aria-current={active === item.id ? 'page' : undefined}
                    onMouseEnter={e => { if (active !== item.id) { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text-secondary)'; } }}
                    onMouseLeave={e => { if (active !== item.id) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; } }}
                  >
                    <span className="flex-shrink-0" aria-hidden="true">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </div>
  );
}

// ─── KPI Cards ────────────────────────────────────────────────────────────────

function KpiCards({ loading }: { loading: boolean }) {
  const cards = [
    { label: 'Platform Health', value: '99.7%', color: '#22C55E', sub: 'All systems nominal' },
    { label: 'Runtime Status', value: 'Active', color: '#22C55E', sub: 'Uptime 14d 6h 22m' },
    { label: 'Running Services', value: '12', color: 'var(--akaal-primary)', sub: '0 stopped' },
    { label: 'API Requests/sec', value: '1,240', color: 'var(--akaal-secondary)', sub: 'Avg 12ms latency' },
    { label: 'Connected Clients', value: '847', color: 'var(--akaal-primary)', sub: '23 organizations' },
    { label: 'Active Sessions', value: '312', color: '#38BDF8', sub: 'Across all users' },
    { label: 'CPU Usage', value: '42%', color: '#22C55E', sub: 'Platform average' },
    { label: 'Memory Usage', value: '58%', color: '#22C55E', sub: '23.2 GB / 40 GB' },
    { label: 'Storage Usage', value: '71%', color: '#F59E0B', sub: '2.84 TB / 4 TB' },
    { label: 'Network Throughput', value: '4.2 GB/s', color: 'var(--akaal-secondary)', sub: 'Inbound + Outbound' },
    { label: 'License Usage', value: '84.7%', color: '#F59E0B', sub: '847 / 1,000 users' },
  ];

  if (loading) {
    return (
      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
        {cards.map((_, i) => (
          <Card key={i} className="px-4 py-3">
            <Skeleton className="h-3 w-20 mb-2" />
            <Skeleton className="h-6 w-14 mb-2" />
            <Skeleton className="h-2.5 w-24" />
          </Card>
        ))}
      </div>
    );
  }

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

// ─── Platform Section ─────────────────────────────────────────────────────────

function PlatformSection() {
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Card>
        <SectionHeader title="Platform Overview" subtitle="Core platform identity and deployment" />
        <div className="px-4 py-2">
          <InfoRow label="Platform Version" value="3.2.1" mono />
          <InfoRow label="Environment" value={<span className="px-2 py-0.5 rounded text-xs" style={{ background: 'rgba(34,197,94,0.08)', color: '#22C55E', border: '1px solid rgba(34,197,94,0.2)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>Production</span>} />
          <InfoRow label="Deployment Mode" value="Cluster" mono />
          <InfoRow label="Cluster Name" value="akaal-prod-cluster-01" mono />
          <InfoRow label="Platform Uptime" value="14d 6h 22m 14s" mono />
          <InfoRow label="Runtime State" value={<span className="px-2 py-0.5 rounded text-xs" style={{ background: 'rgba(34,197,94,0.08)', color: '#22C55E', border: '1px solid rgba(34,197,94,0.2)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>● Running</span>} />
          <InfoRow label="Health Score" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>99.7 / 100</span>} />
          <InfoRow label="Build Version" value="build-20240726-0842" mono />
          <InfoRow label="Git Revision" value="a4f2c8d" mono />
          <InfoRow label="Last Deployment" value="2024-07-26 08:42 UTC" mono />
        </div>
      </Card>
      <Card>
        <SectionHeader title="System Health" subtitle="Overall platform health breakdown" />
        <div className="px-4 py-2">
          {[
            { label: 'Overall Platform', score: 99.7, color: '#22C55E' },
            { label: 'Database Health', score: 99.9, color: '#22C55E' },
            { label: 'Queue Health', score: 98.2, color: '#22C55E' },
            { label: 'Runtime Health', score: 99.7, color: '#22C55E' },
            { label: 'API Health', score: 99.8, color: '#22C55E' },
            { label: 'Storage Health', score: 97.1, color: '#F59E0B' },
            { label: 'Security Health', score: 100, color: '#22C55E' },
            { label: 'Scheduler Health', score: 96.4, color: '#F59E0B' },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-3 py-2" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <span className="text-xs flex-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
              <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-surface-elevated)' }}>
                <div className="h-full rounded-full" style={{ width: `${item.score}%`, background: item.color }} />
              </div>
              <span className="text-xs w-12 text-right" style={{ color: item.color, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{item.score}%</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Runtime Section ──────────────────────────────────────────────────────────

function RuntimeSection() {
  const components = [
    { name: 'Composition Root', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'Bootstrap complete — 142 components registered' },
    { name: 'Dependency Injection', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'IoC container active — 0 unresolved dependencies' },
    { name: 'Service Registry', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: '12 services registered — all endpoints healthy' },
    { name: 'Plugin Registry', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: '8 plugins loaded — 0 conflicts' },
    { name: 'Configuration Loader', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'Hot-reload enabled — last update 16:16:58' },
    { name: 'Environment Loader', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'Production environment — 48 variables loaded' },
    { name: 'Feature Flags', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: '24 flags active — 3 overrides in effect' },
    { name: 'Lifecycle Manager', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'All lifecycle hooks registered' },
    { name: 'Startup Sequence', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'Completed in 4.2s — all checks passed' },
    { name: 'Shutdown Sequence', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'Graceful shutdown configured — drain timeout 30s' },
    { name: 'Health Bootstrap', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'Health endpoints active — /health, /ready, /live' },
    { name: 'Runtime Diagnostics', status: 'running' as ServiceStatus, health: 'healthy' as ServiceHealth, detail: 'Profiling disabled — metrics collection active' },
  ];

  return (
    <Card>
      <SectionHeader title="Runtime Lifecycle" subtitle="Platform runtime composition and dependency injection" />
      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Component', 'Status', 'Health', 'Detail'].map(h => (
                <th key={h} style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.06em', fontWeight: 600, padding: '8px 16px', textAlign: 'left', background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {components.map((c, i) => (
              <tr key={c.name} style={{ borderBottom: '1px solid var(--akaal-table-border)', background: i % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)' }}>
                <td style={{ padding: '8px 16px' }}>
                  <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{c.name}</span>
                </td>
                <td style={{ padding: '8px 16px' }}><ServiceStatusChip status={c.status} /></td>
                <td style={{ padding: '8px 16px' }}><HealthChip health={c.health} /></td>
                <td style={{ padding: '8px 16px' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{c.detail}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Services Section ─────────────────────────────────────────────────────────

function ServicesSection({ onSelectService }: { onSelectService: (s: ServiceRecord) => void }) {
  const [search, setSearch] = useState('');
  const [healthFilter, setHealthFilter] = useState<ServiceHealth | 'all'>('all');

  const filtered = MOCK_SERVICES.filter(s =>
    (healthFilter === 'all' || s.health === healthFilter) &&
    (search === '' || s.name.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <Card>
      <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: '1px solid var(--akaal-card-border)' }}>
        <div className="flex items-center gap-2 flex-1">
          <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Enterprise Services</h2>
          <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{filtered.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <select value={healthFilter} onChange={e => setHealthFilter(e.target.value as ServiceHealth | 'all')}
            className="text-xs rounded-md px-2 py-1.5 outline-none"
            style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
            aria-label="Filter by health"
          >
            <option value="all">All Health</option>
            <option value="healthy">Healthy</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
          <div className="relative">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
              <circle cx="5.5" cy="5.5" r="3.5" stroke="currentColor" strokeWidth="1.2" />
              <path d="M8.5 8.5l2.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
            <input type="search" placeholder="Search services…" value={search} onChange={e => setSearch(e.target.value)}
              className="text-xs rounded-md pl-7 pr-3 py-1.5 outline-none"
              style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif", width: '160px' }}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; }}
            />
          </div>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: 'collapse', minWidth: '900px' }}>
          <thead>
            <tr>
              {['Service', 'Version', 'Status', 'Health', 'Dependencies', 'CPU', 'Memory', 'Restarts', 'Uptime', 'Actions'].map(h => (
                <th key={h} style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.06em', fontWeight: 600, padding: '8px 12px', textAlign: 'left', background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={10} className="text-center py-12" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '13px' }}>
                  <div className="flex flex-col items-center gap-2">
                    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-border)' }}><rect x="1" y="1" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5" /><rect x="17" y="1" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5" /><rect x="1" y="17" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5" /><rect x="17" y="17" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5" /></svg>
                    <p className="font-medium" style={{ color: 'var(--akaal-text-secondary)' }}>No services found</p>
                  </div>
                </td>
              </tr>
            ) : filtered.map((svc, idx) => (
              <tr key={svc.id}
                onClick={() => onSelectService(svc)}
                style={{ background: idx % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)', cursor: 'pointer', borderBottom: '1px solid var(--akaal-table-border)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = idx % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)'; }}
              >
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)' }}>
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><rect x="1" y="2" width="10" height="2.5" rx="0.5" stroke="currentColor" strokeWidth="1.1" /><rect x="1" y="6.5" width="10" height="2.5" rx="0.5" stroke="currentColor" strokeWidth="1.1" /></svg>
                    </div>
                    <div>
                      <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{svc.name}</p>
                      <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{svc.id}</p>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>v{svc.version}</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}><ServiceStatusChip status={svc.status} /></td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}><HealthChip health={svc.health} /></td>
                <td style={{ padding: '8px 12px', maxWidth: '160px' }}>
                  <span className="text-xs truncate block" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{svc.dependencies.slice(0, 2).join(', ')}{svc.dependencies.length > 2 ? ` +${svc.dependencies.length - 2}` : ''}</span>
                </td>
                <td style={{ padding: '8px 12px', minWidth: '80px' }}><UsageBar value={svc.cpu} color="var(--akaal-primary)" /></td>
                <td style={{ padding: '8px 12px', minWidth: '80px' }}><UsageBar value={svc.memory} color="var(--akaal-secondary)" /></td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: svc.restartCount > 0 ? 'var(--akaal-warning)' : 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{svc.restartCount}</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{svc.uptime}</span>
                </td>
                <td style={{ padding: '8px 12px', whiteSpace: 'nowrap', textAlign: 'right' }} onClick={e => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-1">
                    <button type="button" onClick={() => onSelectService(svc)} className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none"
                      style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-primary-subtle)'; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                      aria-label={`Inspect ${svc.name}`}
                    >Inspect</button>
                    <button type="button" className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none"
                      style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                      aria-label={`Restart ${svc.name}`}
                    >Restart</button>
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

// ─── API Platform Section ─────────────────────────────────────────────────────

function ApiSection() {
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Card>
        <SectionHeader title="API Platform" subtitle="REST, WebSocket, and OpenAPI status" />
        <div className="px-4 py-2">
          <InfoRow label="API Health" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● Healthy</span>} />
          <InfoRow label="OpenAPI Status" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● Active</span>} />
          <InfoRow label="API Version" value="v3.2.1" mono />
          <InfoRow label="Requests/sec" value="1,240" mono />
          <InfoRow label="Avg Latency" value="12ms" mono />
          <InfoRow label="Error Rate" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>0.08%</span>} />
          <InfoRow label="Authentication" value="JWT + mTLS" mono />
          <InfoRow label="Rate Limits" value="10,000 req/min" mono />
          <InfoRow label="WebSocket Status" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● Active (312 conns)</span>} />
          <InfoRow label="REST Status" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● Active</span>} />
        </div>
      </Card>
      <Card>
        <SectionHeader title="API Endpoints" subtitle="Registered route groups" />
        <div className="px-4 py-3">
          {[
            { group: '/api/v3/migrations', routes: 24, status: 'healthy' as ServiceHealth },
            { group: '/api/v3/agents', routes: 18, status: 'healthy' as ServiceHealth },
            { group: '/api/v3/databases', routes: 12, status: 'healthy' as ServiceHealth },
            { group: '/api/v3/reports', routes: 16, status: 'healthy' as ServiceHealth },
            { group: '/api/v3/system', routes: 32, status: 'healthy' as ServiceHealth },
            { group: '/api/v3/auth', routes: 8, status: 'healthy' as ServiceHealth },
            { group: '/ws/live', routes: 6, status: 'healthy' as ServiceHealth },
          ].map(ep => (
            <div key={ep.group} className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <span className="text-xs" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{ep.group}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{ep.routes} routes</span>
                <HealthChip health={ep.status} />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Security Section ─────────────────────────────────────────────────────────

function SecuritySection() {
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Card>
        <SectionHeader title="Security Posture" subtitle="Zero-trust and encryption status" />
        <div className="px-4 py-2">
          <InfoRow label="Zero Trust Status" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● Enforced</span>} />
          <InfoRow label="mTLS" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● Active — All Services</span>} />
          <InfoRow label="Vault" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● Connected v1.15.2</span>} />
          <InfoRow label="Secret Rotation" value="Every 24h — Last: 2h ago" mono />
          <InfoRow label="Certificates" value="12 active — 0 expiring" mono />
          <InfoRow label="Encryption" value="AES-256-GCM at rest" mono />
          <InfoRow label="Identity Federation" value="OIDC + SAML 2.0" mono />
          <InfoRow label="Service Identities" value="12 registered" mono />
          <InfoRow label="Workload Identities" value="SPIFFE/SPIRE enabled" mono />
          <InfoRow label="Security Score" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>98 / 100</span>} />
        </div>
      </Card>
      <Card>
        <SectionHeader title="Compliance Status" subtitle="Regulatory framework readiness" />
        <div className="px-4 py-3">
          {[
            { name: 'GDPR', status: 'Compliant', color: '#22C55E', lastReview: '2024-07-01' },
            { name: 'HIPAA', status: 'Compliant', color: '#22C55E', lastReview: '2024-06-15' },
            { name: 'PCI-DSS', status: 'Compliant', color: '#22C55E', lastReview: '2024-07-10' },
            { name: 'SOC 2', status: 'In Review', color: '#F59E0B', lastReview: '2024-07-20' },
            { name: 'ISO 27001', status: 'Compliant', color: '#22C55E', lastReview: '2024-05-30' },
          ].map(c => (
            <div key={c.name} className="flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <div>
                <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{c.name}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Last review: {c.lastReview}</p>
              </div>
              <span className="text-xs px-2 py-0.5 rounded" style={{ color: c.color, background: `${c.color}14`, border: `1px solid ${c.color}33`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{c.status}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Identity & Access Section ────────────────────────────────────────────────

function IdentitySection() {
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Card>
        <SectionHeader title="Identity & Access" subtitle="Organizations, teams, and user management" />
        <div className="px-4 py-2">
          <InfoRow label="Organizations" value="23" mono />
          <InfoRow label="Teams" value="87" mono />
          <InfoRow label="Users" value="847 / 1,000" mono />
          <InfoRow label="Roles" value="14 custom roles" mono />
          <InfoRow label="SSO" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● OIDC Active</span>} />
          <InfoRow label="MFA Readiness" value="94.2% enrolled" mono />
          <InfoRow label="Active Sessions" value="312" mono />
          <InfoRow label="Locked Accounts" value={<span style={{ color: '#F59E0B', fontFamily: "'JetBrains Mono', monospace" }}>3 accounts</span>} />
        </div>
      </Card>
      <Card>
        <SectionHeader title="Permission Matrix" subtitle="Role-based access control overview" />
        <div className="px-4 py-3">
          {[
            { role: 'Platform Admin', users: 4, permissions: 'Full Access' },
            { role: 'Migration Engineer', users: 124, permissions: 'Migrations, Agents, Reports' },
            { role: 'DBA', users: 67, permissions: 'Databases, Migrations (read)' },
            { role: 'Compliance Officer', users: 12, permissions: 'Reports, Audit, Compliance' },
            { role: 'Viewer', users: 640, permissions: 'Read-only across all modules' },
          ].map(r => (
            <div key={r.role} className="py-2.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{r.role}</span>
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{r.users} users</span>
              </div>
              <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{r.permissions}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Licensing Section ────────────────────────────────────────────────────────

function LicensingSection() {
  return (
    <Card>
      <SectionHeader title="License Management" subtitle="Enterprise license usage and quota" />
      <div className="grid gap-4 p-4" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
        <div>
          <InfoRow label="License Tier" value={<span style={{ color: 'var(--akaal-primary)', fontFamily: "'JetBrains Mono', monospace" }}>Enterprise</span>} />
          <InfoRow label="Expiration" value="2025-07-26" mono />
          <InfoRow label="Support Plan" value="Enterprise Premium" mono />
        </div>
        <div>
          <InfoRow label="Organizations" value="23 / 50" mono />
          <InfoRow label="Users" value="847 / 1,000" mono />
          <InfoRow label="Projects" value="142 / 500" mono />
        </div>
        <div>
          <InfoRow label="Concurrent Migrations" value="8 / 20" mono />
          <InfoRow label="Storage Quota" value="2.84 TB / 4 TB" mono />
          <InfoRow label="API Quota" value="1.2M / 10M req/day" mono />
        </div>
      </div>
      <div className="px-4 pb-4">
        <p className="text-xs mb-3 font-semibold" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Quota Utilization</p>
        <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
          {[
            { label: 'Users', used: 84.7, color: '#F59E0B' },
            { label: 'Organizations', used: 46, color: '#22C55E' },
            { label: 'Projects', used: 28.4, color: '#22C55E' },
            { label: 'Concurrent Migrations', used: 40, color: '#22C55E' },
            { label: 'Storage', used: 71, color: '#F59E0B' },
            { label: 'API Requests', used: 12, color: '#22C55E' },
          ].map(q => (
            <div key={q.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{q.label}</span>
                <span className="text-xs" style={{ color: q.color, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{q.used}%</span>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-surface-elevated)' }}>
                <div className="h-full rounded-full" style={{ width: `${q.used}%`, background: q.color }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ─── Integrations Section ─────────────────────────────────────────────────────

function IntegrationsSection() {
  return (
    <Card>
      <SectionHeader title="Platform Integrations" subtitle="External service connections and health" />
      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Integration', 'Category', 'Connection', 'Version', 'Health', 'Last Sync', 'Actions'].map(h => (
                <th key={h} style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.06em', fontWeight: 600, padding: '8px 16px', textAlign: 'left', background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_INTEGRATIONS.map((intg, idx) => (
              <tr key={intg.id} style={{ borderBottom: '1px solid var(--akaal-table-border)', background: idx % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = idx % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)'; }}
              >
                <td style={{ padding: '10px 16px' }}>
                  <span className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{intg.name}</span>
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{intg.category}</span>
                </td>
                <td style={{ padding: '10px 16px' }}><ConnChip connection={intg.connection} /></td>
                <td style={{ padding: '10px 16px' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{intg.version}</span>
                </td>
                <td style={{ padding: '10px 16px' }}><HealthChip health={intg.health} /></td>
                <td style={{ padding: '10px 16px' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{intg.lastSync}</span>
                </td>
                <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                  <button type="button" className="px-2 py-1 rounded text-xs transition-all duration-150 focus:outline-none"
                    style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-primary-subtle)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                    aria-label={`Configure ${intg.name}`}
                  >Configure</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Notifications Section ────────────────────────────────────────────────────

function NotificationsSection() {
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Card>
        <SectionHeader title="Notification Channels" subtitle="Delivery channel configuration and status" />
        <div className="px-4 py-3">
          {[
            { channel: 'Email (SMTP)', status: 'active', deliveryRate: '99.8%', color: '#22C55E' },
            { channel: 'Slack', status: 'active', deliveryRate: '99.9%', color: '#22C55E' },
            { channel: 'Microsoft Teams', status: 'active', deliveryRate: '99.7%', color: '#22C55E' },
            { channel: 'Webhook', status: 'degraded', deliveryRate: '97.9%', color: '#F59E0B' },
          ].map(ch => (
            <div key={ch.channel} className="flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <div>
                <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{ch.channel}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Delivery rate: {ch.deliveryRate}</p>
              </div>
              <span className="text-xs px-2 py-0.5 rounded" style={{ color: ch.color, background: `${ch.color}14`, border: `1px solid ${ch.color}33`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{ch.status}</span>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <SectionHeader title="Alert Rules & Escalation" subtitle="Active alert policies" />
        <div className="px-4 py-3">
          {[
            { rule: 'Platform Health < 95%', severity: 'Critical', escalation: 'PagerDuty → On-call' },
            { rule: 'Service Restart > 3', severity: 'Warning', escalation: 'Slack #ops-alerts' },
            { rule: 'CPU > 90% for 5m', severity: 'Warning', escalation: 'Slack #ops-alerts' },
            { rule: 'License Usage > 95%', severity: 'Info', escalation: 'Email → admin@akaal.io' },
            { rule: 'Certificate Expiry < 30d', severity: 'Warning', escalation: 'Email + Slack' },
          ].map(r => (
            <div key={r.rule} className="py-2.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{r.rule}</span>
                <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: r.severity === 'Critical' ? '#EF4444' : r.severity === 'Warning' ? '#F59E0B' : '#38BDF8', background: r.severity === 'Critical' ? 'rgba(239,68,68,0.08)' : r.severity === 'Warning' ? 'rgba(245,158,11,0.08)' : 'rgba(56,189,248,0.08)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{r.severity}</span>
              </div>
              <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{r.escalation}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Observability Section ────────────────────────────────────────────────────

function ObservabilitySection() {
  const [cpuData] = useState(() => generateMetricData(42, 15));
  const [memData] = useState(() => generateMetricData(58, 8));
  const [netData] = useState(() => generateMetricData(65, 20));
  const [diskData] = useState(() => generateMetricData(71, 5));
  const [apiData] = useState(() => generateMetricData(55, 25));
  const [evtData] = useState(() => generateMetricData(40, 18));

  const metrics = [
    { label: 'CPU Usage', data: cpuData, color: '#3B82F6', current: '42%' },
    { label: 'Memory Usage', data: memData, color: '#38BDF8', current: '58%' },
    { label: 'Network Throughput', data: netData, color: '#22C55E', current: '65%' },
    { label: 'Storage I/O', data: diskData, color: '#F59E0B', current: '71%' },
    { label: 'API Requests', data: apiData, color: '#A78BFA', current: '1,240/s' },
    { label: 'Event Throughput', data: evtData, color: '#F472B6', current: '4,820/s' },
  ];

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
      {metrics.map(m => (
        <Card key={m.label} className="p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.label}</p>
            <span className="text-sm font-bold" style={{ color: m.color, fontFamily: "'JetBrains Mono', monospace" }}>{m.current}</span>
          </div>
          <MiniChart data={m.data} color={m.color} />
        </Card>
      ))}
    </div>
  );
}

// ─── Diagnostics Section ──────────────────────────────────────────────────────

function DiagnosticsSection() {
  const [logSearch, setLogSearch] = useState('');
  const [logLevel, setLogLevel] = useState<LogLevel | 'ALL'>('ALL');
  const logRef = useRef<HTMLDivElement>(null);

  const filteredLogs = MOCK_LOGS.filter(l =>
    (logLevel === 'ALL' || l.level === logLevel) &&
    (logSearch === '' || l.message.toLowerCase().includes(logSearch.toLowerCase()))
  );

  const checks = [
    { name: 'Configuration Validation', result: 'Passed', color: '#22C55E', detail: '48 variables validated — 0 errors' },
    { name: 'Dependency Validation', result: 'Passed', color: '#22C55E', detail: 'All 142 dependencies resolved' },
    { name: 'Runtime Diagnostics', result: 'Passed', color: '#22C55E', detail: 'No memory leaks detected' },
    { name: 'Health Checks', result: 'Passed', color: '#22C55E', detail: '12/12 services healthy' },
    { name: 'Performance Snapshot', result: 'Warning', color: '#F59E0B', detail: 'Scheduler P99 latency 420ms' },
    { name: 'Thread Dump', result: 'Passed', color: '#22C55E', detail: '48 threads — 0 deadlocks' },
    { name: 'Memory Snapshot', result: 'Passed', color: '#22C55E', detail: 'Heap: 23.2 GB / 40 GB (58%)' },
  ];

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Card>
        <SectionHeader title="Diagnostic Checks" subtitle="Platform validation and health checks" action={
          <button type="button" className="text-xs px-3 py-1.5 rounded-md transition-all duration-150" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)', border: '1px solid rgba(59,130,246,0.2)', fontFamily: "'Inter', sans-serif" }}>Run All Checks</button>
        } />
        <div className="px-4 py-2">
          {checks.map(c => (
            <div key={c.name} className="flex items-start gap-3 py-2.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <span className="w-2 h-2 rounded-full mt-1 flex-shrink-0" style={{ background: c.color }} aria-hidden="true" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{c.name}</span>
                  <span className="text-xs" style={{ color: c.color, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{c.result}</span>
                </div>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{c.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: '1px solid var(--akaal-card-border)' }}>
          <div className="flex-1">
            <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>System Logs</h2>
          </div>
          <select value={logLevel} onChange={e => setLogLevel(e.target.value as LogLevel | 'ALL')}
            className="text-xs rounded-md px-2 py-1 outline-none"
            style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
            aria-label="Filter log level"
          >
            {(['ALL', 'INFO', 'WARN', 'ERROR', 'DEBUG', 'SUCCESS'] as const).map(l => <option key={l} value={l}>{l}</option>)}
          </select>
          <div className="relative">
            <input type="search" placeholder="Search logs…" value={logSearch} onChange={e => setLogSearch(e.target.value)}
              className="text-xs rounded-md px-2 py-1 outline-none"
              style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif", width: '120px' }}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; }}
            />
          </div>
        </div>
        <div ref={logRef} className="overflow-y-auto" style={{ height: '320px', background: 'var(--akaal-code-bg)' }}>
          {filteredLogs.map(log => {
            const meta = LOG_LEVEL_META[log.level];
            return (
              <div key={log.id} className="flex items-start gap-2 px-3 py-1.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <span className="text-xs flex-shrink-0 mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{log.timestamp}</span>
                <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0" style={{ color: meta.color, background: meta.bg, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.04em' }}>{log.level}</span>
                {log.source && <span className="text-xs flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', opacity: 0.7 }}>[{log.source}]</span>}
                <span className="text-xs" style={{ color: 'var(--akaal-code-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', lineHeight: '1.5' }}>{log.message}</span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

// ─── Maintenance Section ──────────────────────────────────────────────────────

function MaintenanceSection() {
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [confirmAction, setConfirmAction] = useState<string | null>(null);

  const actions = [
    { id: 'drain', label: 'Drain Workers', desc: 'Gracefully drain all active workers before maintenance', severity: 'warning', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2v8M5 7l3 3 3-3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /><path d="M3 13h10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { id: 'pause-scheduler', label: 'Pause Scheduler', desc: 'Pause job scheduling — running jobs continue to completion', severity: 'warning', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="4" y="3" width="3" height="10" rx="0.5" stroke="currentColor" strokeWidth="1.3" /><rect x="9" y="3" width="3" height="10" rx="0.5" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { id: 'restart-services', label: 'Restart Services', desc: 'Rolling restart of all platform services', severity: 'warning', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2a6 6 0 1 0 5.2 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><path d="M13 1v4h-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'restart-platform', label: 'Restart Platform', desc: 'Full platform restart — all active migrations will be checkpointed', severity: 'critical', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M8 5v3l2 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'graceful-shutdown', label: 'Graceful Shutdown', desc: 'Initiate graceful platform shutdown with full state persistence', severity: 'critical', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" /><path d="M8 5v3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /><circle cx="8" cy="11" r="0.8" fill="currentColor" /></svg> },
    { id: 'upgrade', label: 'Platform Upgrade', desc: 'Initiate platform upgrade to latest available version', severity: 'info', icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 12V4M5 7l3-3 3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
  ];

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Card>
        <SectionHeader title="Maintenance Controls" subtitle="Platform operational controls" />
        <div className="p-4">
          <div className="flex items-center justify-between p-3 rounded-lg mb-4" style={{ background: maintenanceMode ? 'rgba(245,158,11,0.08)' : 'var(--akaal-surface-elevated)', border: `1px solid ${maintenanceMode ? 'rgba(245,158,11,0.3)' : 'var(--akaal-border)'}` }}>
            <div>
              <p className="text-xs font-semibold" style={{ color: maintenanceMode ? '#F59E0B' : 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Maintenance Mode</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{maintenanceMode ? 'Platform is in maintenance mode — API returns 503' : 'Platform is operational'}</p>
            </div>
            <button type="button" onClick={() => setMaintenanceMode(v => !v)}
              className="relative w-10 h-5 rounded-full transition-all duration-200 focus:outline-none focus-visible:ring-2 flex-shrink-0"
              style={{ background: maintenanceMode ? '#F59E0B' : 'var(--akaal-border)' }}
              role="switch" aria-checked={maintenanceMode} aria-label="Toggle maintenance mode"
            >
              <span className="absolute top-0.5 w-4 h-4 rounded-full transition-all duration-200" style={{ background: '#fff', left: maintenanceMode ? '22px' : '2px' }} />
            </button>
          </div>
          <div className="grid gap-2" style={{ gridTemplateColumns: '1fr 1fr' }}>
            {actions.map(action => (
              <button key={action.id} type="button" onClick={() => setConfirmAction(action.id)}
                className="flex items-start gap-2 p-3 rounded-lg text-left transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ background: 'var(--akaal-surface-elevated)', border: `1px solid var(--akaal-border)`, color: action.severity === 'critical' ? '#EF4444' : action.severity === 'warning' ? '#F59E0B' : 'var(--akaal-primary)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = action.severity === 'critical' ? 'rgba(239,68,68,0.4)' : action.severity === 'warning' ? 'rgba(245,158,11,0.4)' : 'rgba(59,130,246,0.4)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--akaal-border)'; }}
                aria-label={action.label}
              >
                <span className="flex-shrink-0 mt-0.5" aria-hidden="true">{action.icon}</span>
                <div>
                  <p className="text-xs font-semibold" style={{ fontFamily: "'Inter', sans-serif" }}>{action.label}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{action.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Configuration" subtitle="Feature flags and runtime settings" />
        <div className="px-4 py-3">
          {[
            { key: 'migration.parallel_mode', value: 'true', type: 'boolean', env: 'Production' },
            { key: 'migration.max_workers', value: '8', type: 'integer', env: 'Production' },
            { key: 'cdc.lag_threshold_ms', value: '2000', type: 'integer', env: 'Production' },
            { key: 'scheduler.max_concurrent_jobs', value: '20', type: 'integer', env: 'Production' },
            { key: 'api.rate_limit_rpm', value: '10000', type: 'integer', env: 'Production' },
            { key: 'security.mfa_required', value: 'true', type: 'boolean', env: 'Production' },
            { key: 'backup.retention_days', value: '30', type: 'integer', env: 'Production' },
          ].map(cfg => (
            <div key={cfg.key} className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <span className="text-xs" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cfg.key}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: 'var(--akaal-text-muted)', background: 'var(--akaal-surface-elevated)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{cfg.type}</span>
                <span className="text-xs font-medium" style={{ color: cfg.value === 'true' ? '#22C55E' : cfg.value === 'false' ? '#EF4444' : 'var(--akaal-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cfg.value}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }} role="dialog" aria-modal="true" aria-label="Confirm action">
          <div className="rounded-xl p-6 max-w-sm w-full mx-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 24px 64px var(--akaal-shadow)' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(239,68,68,0.08)', color: '#EF4444' }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M10 3L2 17h16L10 3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /><path d="M10 9v4M10 15v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </div>
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Confirm Action</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>This action requires confirmation</p>
              </div>
            </div>
            <p className="text-xs mb-6" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>
              Are you sure you want to execute <strong style={{ color: 'var(--akaal-text)' }}>{actions.find(a => a.id === confirmAction)?.label}</strong>? This operation will affect the production platform.
            </p>
            <div className="flex items-center gap-2 justify-end">
              <button type="button" onClick={() => setConfirmAction(null)}
                className="px-4 py-2 rounded-md text-xs font-medium transition-all duration-150"
                style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface-elevated)'; }}
              >Cancel</button>
              <button type="button" onClick={() => setConfirmAction(null)}
                className="px-4 py-2 rounded-md text-xs font-medium transition-all duration-150"
                style={{ background: '#EF4444', color: '#fff', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.opacity = '0.9'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
              >Confirm</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Backup & Restore Section ─────────────────────────────────────────────────

function BackupSection() {
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Card>
        <SectionHeader title="Backup Status" subtitle="Configuration and system snapshots" action={
          <button type="button" className="text-xs px-3 py-1.5 rounded-md transition-all duration-150" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)', border: '1px solid rgba(59,130,246,0.2)', fontFamily: "'Inter', sans-serif" }}>Create Snapshot</button>
        } />
        <div className="px-4 py-2">
          <InfoRow label="Configuration Backup" value={<span style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace" }}>● Active</span>} />
          <InfoRow label="System Snapshot" value="SYS-SNAP-20240726-1614" mono />
          <InfoRow label="Last Backup" value="2024-07-26 16:14 UTC" mono />
          <InfoRow label="Restore Point" value="2024-07-26 16:14 UTC" mono />
          <InfoRow label="Backup Schedule" value="Every 2 hours" mono />
          <InfoRow label="Retention Policy" value="30 days" mono />
          <InfoRow label="Backup Size" value="4.2 GB (compressed)" mono />
          <InfoRow label="Encryption" value="AES-256-GCM" mono />
        </div>
      </Card>
      <Card>
        <SectionHeader title="Restore Points" subtitle="Available system restore points" />
        <div className="px-4 py-3">
          {[
            { id: 'SYS-SNAP-20240726-1614', time: '2024-07-26 16:14', size: '4.2 GB', status: 'verified' },
            { id: 'SYS-SNAP-20240726-1414', time: '2024-07-26 14:14', size: '4.1 GB', status: 'verified' },
            { id: 'SYS-SNAP-20240726-1214', time: '2024-07-26 12:14', size: '4.0 GB', status: 'verified' },
            { id: 'SYS-SNAP-20240726-1014', time: '2024-07-26 10:14', size: '3.9 GB', status: 'verified' },
            { id: 'SYS-SNAP-20240726-0814', time: '2024-07-26 08:14', size: '3.8 GB', status: 'verified' },
          ].map((rp, i) => (
            <div key={rp.id} className="flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <div>
                <p className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{rp.id}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{rp.time} UTC · {rp.size}</p>
              </div>
              <div className="flex items-center gap-2">
                {i === 0 && <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: '#22C55E', background: 'rgba(34,197,94,0.08)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>Latest</span>}
                <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150"
                  style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif", fontSize: '10px' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-primary-subtle)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  aria-label={`Restore from ${rp.id}`}
                >Restore</button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Feature Flags Section ────────────────────────────────────────────────────

function FeatureFlagsSection() {
  const [flags, setFlags] = useState([
    { key: 'migration.parallel_mode', enabled: true, desc: 'Enable parallel batch processing for migrations', env: 'Production' },
    { key: 'migration.ai_advisor', enabled: true, desc: 'Enable AI-powered migration strategy advisor', env: 'Production' },
    { key: 'cdc.auto_recovery', enabled: true, desc: 'Automatic CDC stream recovery on failure', env: 'Production' },
    { key: 'api.graphql_endpoint', enabled: false, desc: 'Expose GraphQL API endpoint (beta)', env: 'Production' },
    { key: 'security.zero_trust_v2', enabled: true, desc: 'Zero Trust v2 policy enforcement', env: 'Production' },
    { key: 'observability.distributed_tracing', enabled: true, desc: 'OpenTelemetry distributed tracing', env: 'Production' },
    { key: 'ui.dark_mode_default', enabled: true, desc: 'Default to dark mode for new users', env: 'Production' },
    { key: 'backup.incremental', enabled: false, desc: 'Incremental backup strategy (experimental)', env: 'Production' },
  ]);

  return (
    <Card>
      <SectionHeader title="Feature Flags" subtitle="Runtime feature toggles and experimental features" />
      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Flag Key', 'Description', 'Environment', 'State', 'Toggle'].map(h => (
                <th key={h} style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.06em', fontWeight: 600, padding: '8px 16px', textAlign: 'left', background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-table-border)', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {flags.map((flag, idx) => (
              <tr key={flag.key} style={{ borderBottom: '1px solid var(--akaal-table-border)', background: idx % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)' }}>
                <td style={{ padding: '10px 16px' }}>
                  <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{flag.key}</span>
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{flag.desc}</span>
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: 'var(--akaal-primary)', background: 'var(--akaal-primary-subtle)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{flag.env}</span>
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <span className="text-xs" style={{ color: flag.enabled ? '#22C55E' : '#64748B', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{flag.enabled ? 'Enabled' : 'Disabled'}</span>
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <button type="button"
                    onClick={() => setFlags(prev => prev.map(f => f.key === flag.key ? { ...f, enabled: !f.enabled } : f))}
                    className="relative w-9 h-4.5 rounded-full transition-all duration-200 focus:outline-none focus-visible:ring-2"
                    style={{ background: flag.enabled ? '#22C55E' : 'var(--akaal-border)', width: '36px', height: '18px', display: 'inline-flex', alignItems: 'center', position: 'relative' }}
                    role="switch" aria-checked={flag.enabled} aria-label={`Toggle ${flag.key}`}
                  >
                    <span style={{ position: 'absolute', top: '2px', width: '14px', height: '14px', borderRadius: '50%', background: '#fff', transition: 'left 0.2s', left: flag.enabled ? '20px' : '2px' }} />
                  </button>
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

function InspectorPanel({ service, onClose }: { service: ServiceRecord; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<InspectorTab>('overview');
  const [cpuData] = useState(() => generateMetricData(service.cpu, 12));
  const [memData] = useState(() => generateMetricData(service.memory, 8));

  const tabs: { id: InspectorTab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'configuration', label: 'Config' },
    { id: 'metrics', label: 'Metrics' },
    { id: 'logs', label: 'Logs' },
    { id: 'dependencies', label: 'Deps' },
    { id: 'events', label: 'Events' },
    { id: 'history', label: 'History' },
  ];

  const events = [
    { time: '16:17:02', type: 'Health Check', desc: 'Health check passed — all endpoints responding', severity: '#22C55E' },
    { time: '16:14:12', type: 'Config Reload', desc: 'Configuration hot-reload applied — 2 keys updated', severity: '#38BDF8' },
    { time: '16:09:00', type: 'Heartbeat', desc: 'Heartbeat cycle completed — nominal', severity: '#94A3B8' },
    { time: '15:58:00', type: 'Metrics', desc: 'Prometheus metrics scraped successfully', severity: '#94A3B8' },
    { time: '15:45:00', type: 'Restart', desc: `Service restarted — restart count: ${service.restartCount}`, severity: service.restartCount > 0 ? '#F59E0B' : '#22C55E' },
  ];

  const configEntries = [
    { key: 'host', value: service.host },
    { key: 'port', value: String(service.port) },
    { key: 'version', value: service.version },
    { key: 'log_level', value: 'INFO' },
    { key: 'max_connections', value: '100' },
    { key: 'timeout_ms', value: '30000' },
    { key: 'retry_attempts', value: '3' },
    { key: 'health_check_interval', value: '10s' },
  ];

  return (
    <div className="flex flex-col flex-shrink-0 h-full" style={{ width: '420px', background: 'var(--akaal-surface)', borderLeft: '1px solid var(--akaal-border)', boxShadow: '-4px 0 24px var(--akaal-shadow-sm)' }} role="complementary" aria-label={`Service inspector: ${service.name}`}>
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)' }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="2" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="7" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="3.5" r="0.8" fill="currentColor" /><circle cx="4" cy="8.5" r="0.8" fill="currentColor" /></svg>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{service.name}</p>
          <p className="text-xs truncate" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{service.id}</p>
        </div>
        <ServiceStatusChip status={service.status} />
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
        {['Restart', 'Pause', 'View Logs', 'Diagnostics'].map(action => (
          <button key={action} type="button"
            className="px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
            style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface-elevated)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
          >{action}</button>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-0 px-4 flex-shrink-0 overflow-x-auto" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        {tabs.map(tab => (
          <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)}
            className="px-3 py-2.5 text-xs font-medium transition-all duration-150 focus:outline-none flex-shrink-0"
            style={{ color: activeTab === tab.id ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)', borderBottom: activeTab === tab.id ? '2px solid var(--akaal-primary)' : '2px solid transparent', fontFamily: "'Inter', sans-serif" }}
            aria-selected={activeTab === tab.id}
          >{tab.label}</button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'overview' && (
          <div className="p-4">
            <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
              {[
                { label: 'CPU', value: `${service.cpu}%`, color: service.cpu >= 80 ? '#EF4444' : service.cpu >= 60 ? '#F59E0B' : '#22C55E' },
                { label: 'Memory', value: `${service.memory}%`, color: service.memory >= 80 ? '#EF4444' : service.memory >= 60 ? '#F59E0B' : '#22C55E' },
                { label: 'Restarts', value: String(service.restartCount), color: service.restartCount > 0 ? '#F59E0B' : '#22C55E' },
              ].map(m => (
                <div key={m.label} className="p-3 rounded-lg text-center" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                  <p className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.label}</p>
                  <p className="text-lg font-bold" style={{ color: m.color, fontFamily: "'JetBrains Mono', monospace" }}>{m.value}</p>
                </div>
              ))}
            </div>
            <div className="space-y-0">
              <InfoRow label="Version" value={`v${service.version}`} mono />
              <InfoRow label="Health" value={<HealthChip health={service.health} />} />
              <InfoRow label="Uptime" value={service.uptime} mono />
              <InfoRow label="Host" value={service.host} mono />
              <InfoRow label="Port" value={String(service.port)} mono />
            </div>
            <div className="mt-4">
              <p className="text-xs mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Description</p>
              <p className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif", lineHeight: '1.6' }}>{service.description}</p>
            </div>
          </div>
        )}

        {activeTab === 'configuration' && (
          <div className="p-4">
            <p className="text-xs mb-3 font-semibold" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.08em' }}>RUNTIME CONFIGURATION</p>
            <div className="rounded-lg overflow-hidden" style={{ border: '1px solid var(--akaal-border)' }}>
              {configEntries.map((entry, i) => (
                <div key={entry.key} className="flex items-center justify-between px-3 py-2" style={{ borderBottom: i < configEntries.length - 1 ? '1px solid var(--akaal-border-subtle)' : 'none', background: i % 2 === 0 ? 'transparent' : 'var(--akaal-table-row-hover)' }}>
                  <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{entry.key}</span>
                  <span className="text-xs font-medium" style={{ color: 'var(--akaal-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{entry.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="p-4 space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>CPU Usage</p>
                <span className="text-xs font-bold" style={{ color: '#3B82F6', fontFamily: "'JetBrains Mono', monospace" }}>{service.cpu}%</span>
              </div>
              <MiniChart data={cpuData} color="#3B82F6" />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Memory Usage</p>
                <span className="text-xs font-bold" style={{ color: '#38BDF8', fontFamily: "'JetBrains Mono', monospace" }}>{service.memory}%</span>
              </div>
              <MiniChart data={memData} color="#38BDF8" />
            </div>
            <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
              {[
                { label: 'Request Rate', value: '1,240/s' },
                { label: 'Error Rate', value: '0.08%' },
                { label: 'P50 Latency', value: '8ms' },
                { label: 'P99 Latency', value: '42ms' },
              ].map(m => (
                <div key={m.label} className="p-3 rounded-lg" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                  <p className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{m.label}</p>
                  <p className="text-sm font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace" }}>{m.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="h-full" style={{ background: 'var(--akaal-code-bg)' }}>
            {MOCK_LOGS.filter(l => l.source === service.name || !l.source).slice(0, 8).map(log => {
              const meta = LOG_LEVEL_META[log.level];
              return (
                <div key={log.id} className="flex items-start gap-2 px-3 py-1.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <span className="text-xs flex-shrink-0 mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{log.timestamp}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0" style={{ color: meta.color, background: meta.bg, fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{log.level}</span>
                  <span className="text-xs" style={{ color: 'var(--akaal-code-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', lineHeight: '1.5' }}>{log.message}</span>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'dependencies' && (
          <div className="p-4">
            <p className="text-xs mb-3 font-semibold" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.08em' }}>SERVICE DEPENDENCIES</p>
            <div className="space-y-2">
              {service.dependencies.map(dep => (
                <div key={dep} className="flex items-center gap-3 p-3 rounded-lg" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: '#22C55E' }} aria-hidden="true" />
                  <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{dep}</span>
                  <span className="ml-auto text-xs" style={{ color: '#22C55E', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>● Connected</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'events' && (
          <div className="p-4">
            <div className="space-y-3">
              {events.map((ev, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="flex flex-col items-center flex-shrink-0">
                    <span className="w-2 h-2 rounded-full mt-1" style={{ background: ev.severity }} aria-hidden="true" />
                    {i < events.length - 1 && <div className="w-px flex-1 mt-1" style={{ background: 'var(--akaal-border)', minHeight: '20px' }} aria-hidden="true" />}
                  </div>
                  <div className="flex-1 pb-3">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{ev.type}</span>
                      <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{ev.time}</span>
                    </div>
                    <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{ev.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="p-4">
            <p className="text-xs mb-3 font-semibold" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.08em' }}>DEPLOYMENT HISTORY</p>
            <div className="space-y-2">
              {[
                { version: `v${service.version}`, date: '2024-07-26 08:42', type: 'Deploy', status: 'success' },
                { version: 'v3.1.9', date: '2024-07-20 14:15', type: 'Hotfix', status: 'success' },
                { version: 'v3.1.8', date: '2024-07-15 09:30', type: 'Deploy', status: 'success' },
                { version: 'v3.1.7', date: '2024-07-10 11:00', type: 'Deploy', status: 'rollback' },
              ].map(h => (
                <div key={h.version} className="flex items-center justify-between p-3 rounded-lg" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                  <div>
                    <p className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{h.version}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{h.date} · {h.type}</p>
                  </div>
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: h.status === 'success' ? '#22C55E' : '#F59E0B', background: h.status === 'success' ? 'rgba(34,197,94,0.08)' : 'rgba(245,158,11,0.08)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{h.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Section Content Router ───────────────────────────────────────────────────

function SectionContent({ section, onSelectService }: { section: SystemSection; onSelectService: (s: ServiceRecord) => void }) {
  switch (section) {
    case 'platform': return <PlatformSection />;
    case 'runtime': return <RuntimeSection />;
    case 'services': return <ServicesSection onSelectService={onSelectService} />;
    case 'api': return <ApiSection />;
    case 'configuration': return (
      <Card>
        <SectionHeader title="Configuration Management" subtitle="Centralized platform configuration with hot-reload" />
        <div className="px-4 py-3">
          {[
            { key: 'platform.name', value: 'AKAAL Enterprise', env: 'Production' },
            { key: 'platform.version', value: '3.2.1', env: 'Production' },
            { key: 'platform.cluster', value: 'akaal-prod-cluster-01', env: 'Production' },
            { key: 'database.pool_size', value: '20', env: 'Production' },
            { key: 'database.timeout_ms', value: '30000', env: 'Production' },
            { key: 'cache.ttl_seconds', value: '300', env: 'Production' },
            { key: 'api.cors_origins', value: 'https://*.akaal.io', env: 'Production' },
            { key: 'logging.level', value: 'INFO', env: 'Production' },
            { key: 'metrics.scrape_interval', value: '15s', env: 'Production' },
            { key: 'tracing.sample_rate', value: '0.1', env: 'Production' },
          ].map((cfg, i) => (
            <div key={cfg.key} className="flex items-center justify-between py-2.5" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
              <span className="text-xs" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cfg.key}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs px-1.5 py-0.5 rounded" style={{ color: 'var(--akaal-primary)', background: 'var(--akaal-primary-subtle)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>{cfg.env}</span>
                <span className="text-xs font-medium" style={{ color: 'var(--akaal-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{cfg.value}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    );
    case 'feature-flags': return <FeatureFlagsSection />;
    case 'security': return <SecuritySection />;
    case 'users': case 'organizations': case 'teams': case 'rbac': return <IdentitySection />;
    case 'licensing': return <LicensingSection />;
    case 'integrations': return <IntegrationsSection />;
    case 'notifications': return <NotificationsSection />;
    case 'observability': return <ObservabilitySection />;
    case 'diagnostics': return <DiagnosticsSection />;
    case 'maintenance': return <MaintenanceSection />;
    case 'backup': return <BackupSection />;
    default: return null;
  }
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SystemPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeSection, setActiveSection] = useState<SystemSection>('platform');
  const [selectedService, setSelectedService] = useState<ServiceRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchValue, setSearchValue] = useState('');
  const [maintenanceBanner, setMaintenanceBanner] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 900);
    return () => clearTimeout(t);
  }, []);

  const sectionTitle: Record<SystemSection, string> = {
    platform: 'Platform Overview', runtime: 'Runtime', services: 'Services', api: 'API Platform',
    configuration: 'Configuration', 'feature-flags': 'Feature Flags', security: 'Security',
    users: 'Users', organizations: 'Organizations', teams: 'Teams', rbac: 'RBAC',
    licensing: 'Licensing', integrations: 'Integrations', notifications: 'Notifications',
    observability: 'Observability', diagnostics: 'Diagnostics', maintenance: 'Maintenance', backup: 'Backup & Restore',
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--akaal-bg)' }}>
      <style>{`
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
      `}</style>

      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopNav searchValue={searchValue} onSearchChange={setSearchValue} />

        {maintenanceBanner && (
          <div className="flex items-center gap-3 px-4 py-2 flex-shrink-0" style={{ background: 'rgba(245,158,11,0.08)', borderBottom: '1px solid rgba(245,158,11,0.2)' }} role="alert">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" style={{ color: '#F59E0B', flexShrink: 0 }}><path d="M7 1.5L1 12.5h12L7 1.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /><path d="M7 5.5v3M7 10v.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
            <span className="text-xs font-medium" style={{ color: '#F59E0B', fontFamily: "'Inter', sans-serif" }}>Maintenance Mode Active — Platform API returning 503 for non-admin requests</span>
            <button type="button" onClick={() => setMaintenanceBanner(false)} className="ml-auto text-xs" style={{ color: '#F59E0B', fontFamily: "'Inter', sans-serif" }} aria-label="Dismiss banner">Dismiss</button>
          </div>
        )}

        <div className="flex flex-1 min-h-0 overflow-hidden">
          <SectionNav active={activeSection} onSelect={s => { setActiveSection(s); setSelectedService(null); }} />

          <main className="flex-1 min-w-0 overflow-y-auto" style={{ background: 'var(--akaal-bg)' }}>
            {/* Page Header */}
            <div className="px-6 py-4 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h1 className="text-lg font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif", letterSpacing: '-0.01em' }}>System</h1>
                    <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)', border: '1px solid rgba(59,130,246,0.2)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
                      {sectionTitle[activeSection]}
                    </span>
                  </div>
                  <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Enterprise platform administration and operational control.</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
                  <button type="button" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface-elevated)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                    aria-label="Refresh platform"
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1a5 5 0 1 0 4.33 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /><path d="M10 1v3H7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    Refresh Platform
                  </button>
                  <button type="button" onClick={() => setMaintenanceBanner(v => !v)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface-elevated)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                    aria-label="Toggle maintenance mode"
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M8.5 2.5a2.5 2.5 0 0 1 0 3.5L3.5 11a1.2 1.2 0 0 1-1.7-1.7L7 4.3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                    Maintenance Mode
                  </button>
                  <button type="button" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-surface-elevated)'; (e.currentTarget as HTMLElement).style.color = 'var(--akaal-text-muted)'; }}
                    aria-label="Export diagnostics"
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 8V2M3 5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /><path d="M2 10h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                    Export Diagnostics
                  </button>
                  <button type="button" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.opacity = '0.9'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                    aria-label="Restart services"
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1a5 5 0 1 0 4.33 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /><path d="M10 1v3H7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    Restart Services
                  </button>
                </div>
              </div>
            </div>

            {/* KPI Cards */}
            <div className="px-6 py-4" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
              <KpiCards loading={loading} />
            </div>

            {/* Section Content */}
            <div className="p-6">
              {loading ? (
                <div className="space-y-4">
                  <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
                    {[0, 1].map(i => (
                      <Card key={i} className="p-4">
                        <Skeleton className="h-4 w-32 mb-4" />
                        {[0, 1, 2, 3, 4].map(j => <Skeleton key={j} className="h-3 w-full mb-2" />)}
                      </Card>
                    ))}
                  </div>
                </div>
              ) : (
                <SectionContent section={activeSection} onSelectService={setSelectedService} />
              )}
            </div>
          </main>

          {/* Inspector Panel */}
          {selectedService && (
            <div style={{ animation: 'slideIn 0.2s ease' }}>
              <InspectorPanel service={selectedService} onClose={() => setSelectedService(null)} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
