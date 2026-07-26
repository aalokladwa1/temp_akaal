'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import AppImage from '@/components/ui/AppImage';
import { ThemeSwitcher } from '@/components/ui/ThemeSwitcher';

// ─── Types ────────────────────────────────────────────────────────────────────

type SettingsSection =
  | 'profile' | 'appearance' | 'notifications' | 'accessibility' | 'localization'
  | 'security'| 'sessions' | 'api-tokens' | 'migration-defaults' | 'ai-config' |'developer' | 'feature-flags' | 'keyboard-shortcuts' | 'branding' | 'about';

type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

interface SessionRecord {
  id: string;
  browser: string;
  os: string;
  ip: string;
  location: string;
  lastActivity: string;
  current: boolean;
  device: string;
}

interface ApiToken {
  id: string;
  name: string;
  type: 'personal' | 'service';
  scopes: string[];
  lastUsed: string;
  expires: string;
  status: 'active' | 'expired' | 'revoked';
  created: string;
}

interface FeatureFlag {
  id: string;
  feature: string;
  status: 'enabled' | 'disabled' | 'partial';
  rollout: number;
  environment: string;
  description: string;
  lastModified: string;
}

interface KeyboardShortcut {
  id: string;
  action: string;
  category: string;
  keys: string[];
  customKeys?: string[];
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_SESSIONS: SessionRecord[] = [
  { id: 'sess-1', browser: 'Chrome 120', os: 'macOS 14.2', ip: '192.168.1.42', location: 'San Francisco, CA', lastActivity: 'Now', current: true, device: 'MacBook Pro 16"' },
  { id: 'sess-2', browser: 'Firefox 121', os: 'Ubuntu 22.04', ip: '10.0.0.15', location: 'New York, NY', lastActivity: '2h ago', current: false, device: 'Dell XPS 15' },
  { id: 'sess-3', browser: 'Safari 17', os: 'iOS 17.2', ip: '172.16.0.8', location: 'Chicago, IL', lastActivity: '1d ago', current: false, device: 'iPhone 15 Pro' },
  { id: 'sess-4', browser: 'Edge 120', os: 'Windows 11', ip: '192.168.2.100', location: 'Austin, TX', lastActivity: '3d ago', current: false, device: 'Surface Pro 9' },
];

const MOCK_TOKENS: ApiToken[] = [
  { id: 'tok-1', name: 'CI/CD Pipeline Token', type: 'service', scopes: ['migrations:read', 'migrations:write', 'executions:read'], lastUsed: '5m ago', expires: '2025-12-31', status: 'active', created: '2024-01-15' },
  { id: 'tok-2', name: 'Personal Dev Token', type: 'personal', scopes: ['migrations:read', 'reports:read'], lastUsed: '2h ago', expires: '2025-06-30', status: 'active', created: '2024-03-01' },
  { id: 'tok-3', name: 'Monitoring Integration', type: 'service', scopes: ['metrics:read', 'health:read'], lastUsed: '1m ago', expires: '2025-09-15', status: 'active', created: '2024-02-20' },
  { id: 'tok-4', name: 'Legacy API Key', type: 'personal', scopes: ['migrations:read'], lastUsed: '45d ago', expires: '2024-01-01', status: 'expired', created: '2023-01-01' },
];

const MOCK_FEATURE_FLAGS: FeatureFlag[] = [
  { id: 'ff-1', feature: 'migration.parallel_mode', status: 'enabled', rollout: 100, environment: 'production', description: 'Enable parallel execution for multi-table migrations', lastModified: '2024-07-20' },
  { id: 'ff-2', feature: 'ai.planning_assistant', status: 'partial', rollout: 25, environment: 'production', description: 'AI-powered migration planning suggestions', lastModified: '2024-07-18' },
  { id: 'ff-3', feature: 'ui.new_dashboard', status: 'enabled', rollout: 100, environment: 'staging', description: 'Redesigned dashboard with enhanced metrics', lastModified: '2024-07-15' },
  { id: 'ff-4', feature: 'cdc.enhanced_streaming', status: 'disabled', rollout: 0, environment: 'production', description: 'Enhanced CDC streaming with sub-second latency', lastModified: '2024-07-10' },
  { id: 'ff-5', feature: 'reports.executive_summary', status: 'enabled', rollout: 100, environment: 'production', description: 'Executive summary report generation', lastModified: '2024-07-08' },
  { id: 'ff-6', feature: 'security.zero_trust_v2', status: 'partial', rollout: 50, environment: 'staging', description: 'Zero Trust v2 with enhanced workload identities', lastModified: '2024-07-05' },
];

const MOCK_SHORTCUTS: KeyboardShortcut[] = [
  { id: 'ks-1', action: 'Global Search', category: 'Global', keys: ['⌘', 'K'] },
  { id: 'ks-2', action: 'Command Palette', category: 'Global', keys: ['⌘', 'Shift', 'P'] },
  { id: 'ks-3', action: 'Navigate to Dashboard', category: 'Navigation', keys: ['G', 'D'] },
  { id: 'ks-4', action: 'Navigate to Migrations', category: 'Navigation', keys: ['G', 'M'] },
  { id: 'ks-5', action: 'Navigate to Reports', category: 'Navigation', keys: ['G', 'R'] },
  { id: 'ks-6', action: 'Refresh Page', category: 'Actions', keys: ['⌘', 'R'] },
  { id: 'ks-7', action: 'Save Changes', category: 'Actions', keys: ['⌘', 'S'] },
  { id: 'ks-8', action: 'Cancel / Discard', category: 'Actions', keys: ['Esc'] },
  { id: 'ks-9', action: 'New Migration', category: 'Quick Actions', keys: ['⌘', 'N'] },
  { id: 'ks-10', action: 'Export Data', category: 'Quick Actions', keys: ['⌘', 'E'] },
];

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

function FormField({ label, hint, children, required }: { label: string; hint?: string; children: React.ReactNode; required?: boolean }) {
  return (
    <div className="space-y-1.5">
      <label className="flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>
        {label}
        {required && <span style={{ color: 'var(--akaal-error)' }}>*</span>}
      </label>
      {children}
      {hint && <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{hint}</p>}
    </div>
  );
}

function Input({ value, onChange, placeholder, type = 'text', disabled }: { value: string; onChange?: (v: string) => void; placeholder?: string; type?: string; disabled?: boolean }) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange?.(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full text-xs rounded-md px-3 py-2 outline-none transition-all duration-150"
      style={{ background: disabled ? 'var(--akaal-surface-elevated)' : 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: disabled ? 'var(--akaal-text-muted)' : 'var(--akaal-text)', fontFamily: "'Inter', sans-serif", cursor: disabled ? 'not-allowed' : 'text' }}
      onFocus={e => { if (!disabled) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; } }}
      onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
    />
  );
}

function Select({ value, onChange, options, disabled }: { value: string; onChange?: (v: string) => void; options: { value: string; label: string }[]; disabled?: boolean }) {
  return (
    <select
      value={value}
      onChange={e => onChange?.(e.target.value)}
      disabled={disabled}
      className="w-full text-xs rounded-md px-3 py-2 outline-none transition-all duration-150 appearance-none"
      style={{ background: disabled ? 'var(--akaal-surface-elevated)' : 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: disabled ? 'var(--akaal-text-muted)' : 'var(--akaal-text)', fontFamily: "'Inter', sans-serif", cursor: disabled ? 'not-allowed' : 'pointer' }}
      onFocus={e => { if (!disabled) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; } }}
      onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
    >
      {options.map(o => <option key={o.value} value={o.value} style={{ background: 'var(--akaal-surface)', color: 'var(--akaal-text)' }}>{o.label}</option>)}
    </select>
  );
}

function Toggle({ checked, onChange, label, description }: { checked: boolean; onChange: (v: boolean) => void; label: string; description?: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-3" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{label}</p>
        {description && <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{description}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className="flex-shrink-0 relative w-9 h-5 rounded-full transition-all duration-200 focus:outline-none focus-visible:ring-2"
        style={{ background: checked ? 'var(--akaal-primary)' : 'var(--akaal-surface-elevated)', border: '1px solid ' + (checked ? 'var(--akaal-primary)' : 'var(--akaal-border)') }}
      >
        <span className="absolute top-0.5 w-4 h-4 rounded-full transition-all duration-200" style={{ background: '#fff', left: checked ? 'calc(100% - 18px)' : '1px', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }} />
      </button>
    </div>
  );
}

function StatusChip({ status, label }: { status: 'active' | 'expired' | 'revoked' | 'enabled' | 'disabled' | 'partial'; label?: string }) {
  const cfg: Record<string, { color: string; bg: string; border: string }> = {
    active:   { color: '#22C55E', bg: 'rgba(34,197,94,0.08)',    border: 'rgba(34,197,94,0.2)' },
    enabled:  { color: '#22C55E', bg: 'rgba(34,197,94,0.08)',    border: 'rgba(34,197,94,0.2)' },
    expired:  { color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)' },
    revoked:  { color: '#EF4444', bg: 'rgba(239,68,68,0.08)',    border: 'rgba(239,68,68,0.2)' },
    disabled: { color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)' },
    partial:  { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)',   border: 'rgba(245,158,11,0.2)' },
  };
  const c = cfg[status] ?? cfg.disabled;
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded" style={{ color: c.color, background: c.bg, border: `1px solid ${c.border}`, fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.04em', fontWeight: 500 }}>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: c.color }} aria-hidden="true" />
      {label ?? status.charAt(0).toUpperCase() + status.slice(1)}
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

function InfoRow({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
      <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{label}</span>
      <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: mono ? "'JetBrains Mono', monospace" : "'Inter', sans-serif" }}>{value}</span>
    </div>
  );
}

// ─── Toast Notifications ──────────────────────────────────────────────────────

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
  const cfg: Record<ToastType, { color: string; bg: string; border: string; icon: React.ReactNode }> = {
    success: { color: 'var(--akaal-success)', bg: 'var(--akaal-success-bg)', border: 'rgba(34,197,94,0.3)', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" /><path d="M4.5 7l2 2 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    error:   { color: 'var(--akaal-error)',   bg: 'var(--akaal-error-bg)',   border: 'rgba(239,68,68,0.3)',  icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" /><path d="M5 5l4 4M9 5l-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
    info:    { color: 'var(--akaal-info)',    bg: 'var(--akaal-info-bg)',    border: 'rgba(96,165,250,0.3)', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" /><path d="M7 6.5v3M7 4.5v.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg> },
  };
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2" aria-live="polite" aria-label="Notifications">
      {toasts.map(t => {
        const c = cfg[t.type];
        return (
          <div key={t.id} className="flex items-center gap-3 px-4 py-3 rounded-lg" style={{ background: 'var(--akaal-surface)', border: `1px solid ${c.border}`, boxShadow: '0 8px 32px var(--akaal-shadow)', minWidth: '280px', animation: 'slideIn 0.2s ease', color: c.color }}>
            {c.icon}
            <span className="flex-1 text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{t.message}</span>
            <button type="button" onClick={() => onRemove(t.id)} className="flex-shrink-0" style={{ color: 'var(--akaal-text-muted)' }} aria-label="Dismiss notification">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
            </button>
          </div>
        );
      })}
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
    { href: '/agents', label: 'Agents', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/reports', label: 'Reports', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 2h7l3 3v9H3V2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /><path d="M10 2v3h3M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/system', label: 'System', active: false, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="3" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="14" height="3" rx="1" stroke="currentColor" strokeWidth="1.3" /><circle cx="4" cy="4.5" r="0.8" fill="currentColor" /><circle cx="4" cy="9.5" r="0.8" fill="currentColor" /><path d="M5 13h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { href: '/settings', label: 'Settings', active: true, icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M8 1.5v1.2M8 13.3v1.2M1.5 8h1.2M13.3 8h1.2M3.4 3.4l.85.85M11.75 11.75l.85.85M3.4 12.6l.85-.85M11.75 4.25l.85-.85" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
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
        <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Settings</span>
      </nav>
      <div className="flex-1 max-w-xs relative">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
          <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        <input type="search" placeholder="Search settings…" value={searchValue} onChange={e => onSearchChange(e.target.value)}
          className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
          style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
          aria-label="Search settings"
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

// ─── Settings Left Navigation ─────────────────────────────────────────────────

const SETTINGS_SECTIONS: { group: string; items: { id: SettingsSection; label: string; icon: React.ReactNode }[] }[] = [
  {
    group: 'Personal',
    items: [
      { id: 'profile', label: 'Profile', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="4.5" r="2.5" stroke="currentColor" strokeWidth="1.2" /><path d="M1.5 12.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'appearance', label: 'Appearance', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" /><path d="M7 1.5v1M7 11.5v1M1.5 7h1M11.5 7h1M3.3 3.3l.7.7M10 10l.7.7M3.3 10.7l.7-.7M10 4l.7-.7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'notifications', label: 'Notifications', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1.5a4 4 0 0 0-4 4v2.5L1.5 10h11L11 8V5.5a4 4 0 0 0-4-4Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /><path d="M5.5 11.5a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.2" /></svg> },
      { id: 'accessibility', label: 'Accessibility', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="2.5" r="1.2" stroke="currentColor" strokeWidth="1.2" /><path d="M3 5h8M7 5v4M5 13l2-4 2 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
      { id: 'localization', label: 'Localization', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" /><path d="M7 1.5C5.5 3 4.5 5 4.5 7s1 4 2.5 5.5M7 1.5C8.5 3 9.5 5 9.5 7s-1 4-2.5 5.5M1.5 7h11" stroke="currentColor" strokeWidth="1.2" /></svg> },
    ],
  },
  {
    group: 'Security',
    items: [
      { id: 'security', label: 'Security', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1L2 3.5v4c0 2.8 2.1 5.4 5 6 2.9-.6 5-3.2 5-6v-4L7 1Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /></svg> },
      { id: 'sessions', label: 'Sessions', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="2" width="12" height="9" rx="1" stroke="currentColor" strokeWidth="1.2" /><path d="M4 12h6M7 11v1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'api-tokens', label: 'API Tokens', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    ],
  },
  {
    group: 'Platform',
    items: [
      { id: 'migration-defaults', label: 'Migration Defaults', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 8h10M8 4l4 4-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /><path d="M2 4h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'ai-config', label: 'AI Configuration', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.2" /><path d="M7 1v2M7 11v2M1 7h2M11 7h2M3.2 3.2l1.4 1.4M9.4 9.4l1.4 1.4M3.2 10.8l1.4-1.4M9.4 4.6l1.4-1.4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
    ],
  },
  {
    group: 'Advanced',
    items: [
      { id: 'developer', label: 'Developer', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M4 4l-3 3 3 3M10 4l3 3-3 3M7.5 2l-1 10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
      { id: 'feature-flags', label: 'Feature Flags', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2v10M2 2l8 3-8 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
      { id: 'keyboard-shortcuts', label: 'Keyboard Shortcuts', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="3" width="12" height="8" rx="1" stroke="currentColor" strokeWidth="1.2" /><path d="M4 7h1M7 7h1M10 7h1M5.5 9h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg> },
      { id: 'branding', label: 'Branding', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" /><path d="M4.5 9.5l1.5-5 2 3.5 1.5-2 1 3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg> },
      { id: 'about', label: 'About', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" /><path d="M7 6.5v3M7 4.5v.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg> },
    ],
  },
];

function SettingsNav({ active, onSelect, search }: { active: SettingsSection; onSelect: (s: SettingsSection) => void; search: string }) {
  const filtered = search
    ? SETTINGS_SECTIONS.map(g => ({ ...g, items: g.items.filter(i => i.label.toLowerCase().includes(search.toLowerCase())) })).filter(g => g.items.length > 0)
    : SETTINGS_SECTIONS;

  return (
    <div className="flex flex-col flex-shrink-0" style={{ width: '200px', background: 'var(--akaal-nav-bg)', borderRight: '1px solid var(--akaal-nav-border)', overflowY: 'auto' }}>
      <div className="px-3 py-3" style={{ borderBottom: '1px solid var(--akaal-nav-border)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', letterSpacing: '0.1em' }}>Settings</p>
      </div>
      <nav aria-label="Settings sections" className="py-2 flex-1">
        {filtered.map(group => (
          <div key={group.group} className="mb-1">
            <p className="px-3 py-1.5 text-xs uppercase tracking-wider" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', letterSpacing: '0.12em', opacity: 0.7 }}>{group.group}</p>
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
        {filtered.length === 0 && (
          <div className="px-3 py-6 text-center">
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>No settings found</p>
          </div>
        )}
      </nav>
    </div>
  );
}

// ─── Section: Profile ─────────────────────────────────────────────────────────

function ProfileSection({ loading }: { loading: boolean }) {
  const [form, setForm] = useState({ fullName: 'Sarah Chen', email: 'sarah.chen@akaal.io', phone: '+1 (415) 555-0192', department: 'Platform Engineering', role: 'Platform Administrator', organization: 'AKAAL Enterprise', jobTitle: 'Senior Platform Engineer', timezone: 'America/Los_Angeles', language: 'en-US' });

  if (loading) return <div className="space-y-4">{[0,1,2].map(i => <Card key={i} className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2].map(j => <Skeleton key={j} className="h-8 w-full mb-3" />)}</Card>)}</div>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Avatar & Identity" subtitle="Your public profile information" />
        <div className="p-4 flex items-start gap-6">
          <div className="flex flex-col items-center gap-3">
            <div className="w-20 h-20 rounded-full flex items-center justify-center text-2xl font-bold flex-shrink-0" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }} aria-label="Profile avatar: SC">SC</div>
            <button type="button" className="text-xs px-3 py-1.5 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
            >Upload Photo</button>
          </div>
          <div className="flex-1 grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <FormField label="Full Name" required>
              <Input value={form.fullName} onChange={v => setForm(f => ({ ...f, fullName: v }))} />
            </FormField>
            <FormField label="Email Address" required>
              <Input value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} type="email" />
            </FormField>
            <FormField label="Phone">
              <Input value={form.phone} onChange={v => setForm(f => ({ ...f, phone: v }))} type="tel" />
            </FormField>
            <FormField label="Job Title">
              <Input value={form.jobTitle} onChange={v => setForm(f => ({ ...f, jobTitle: v }))} />
            </FormField>
          </div>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Organization & Role" subtitle="Your organizational context" />
        <div className="p-4 grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <FormField label="Department">
            <Input value={form.department} onChange={v => setForm(f => ({ ...f, department: v }))} />
          </FormField>
          <FormField label="Role" hint="Managed by your administrator">
            <Input value={form.role} disabled />
          </FormField>
          <FormField label="Organization" hint="Managed by your administrator">
            <Input value={form.organization} disabled />
          </FormField>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Regional Preferences" />
        <div className="p-4 grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <FormField label="Timezone">
            <Select value={form.timezone} onChange={v => setForm(f => ({ ...f, timezone: v }))} options={[{ value: 'America/Los_Angeles', label: 'Pacific Time (PT)' }, { value: 'America/New_York', label: 'Eastern Time (ET)' }, { value: 'Europe/London', label: 'GMT / BST' }, { value: 'Europe/Berlin', label: 'Central European Time' }, { value: 'Asia/Tokyo', label: 'Japan Standard Time' }, { value: 'UTC', label: 'UTC' }]} />
          </FormField>
          <FormField label="Language">
            <Select value={form.language} onChange={v => setForm(f => ({ ...f, language: v }))} options={[{ value: 'en-US', label: 'English (US)' }, { value: 'en-GB', label: 'English (UK)' }, { value: 'de-DE', label: 'Deutsch' }, { value: 'fr-FR', label: 'Français' }, { value: 'ja-JP', label: '日本語' }]} />
          </FormField>
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Appearance ──────────────────────────────────────────────────────

function AppearanceSection({ loading }: { loading: boolean }) {
  const [density, setDensity] = useState<'compact' | 'comfortable'>('comfortable');
  const [uiScale, setUiScale] = useState('100');
  const [fontSize, setFontSize] = useState('14');
  const [sidebarBehavior, setSidebarBehavior] = useState('auto-collapse');
  const [tableDensity, setTableDensity] = useState('default');
  const [animations, setAnimations] = useState(true);
  const [systemTheme, setSystemTheme] = useState(false);

  if (loading) return <div className="space-y-4">{[0,1].map(i => <Card key={i} className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2].map(j => <Skeleton key={j} className="h-10 w-full mb-3" />)}</Card>)}</div>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Theme" subtitle="Choose your preferred visual theme" />
        <div className="p-4 space-y-3">
          <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
            {[
              { id: 'dark', label: 'Midnight Glass', icon: '🌙', desc: 'Dark mode — deep navy surfaces with blue accents' },
              { id: 'light', label: 'Enterprise Blue', icon: '☀', desc: 'Light mode — clean white surfaces with blue accents' },
            ].map(t => (
              <button key={t.id} type="button" className="flex items-start gap-3 p-3 rounded-lg text-left transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ border: `2px solid var(--akaal-primary)`, background: 'var(--akaal-primary-subtle)' }}
                aria-label={`Select ${t.label} theme`}
              >
                <span className="text-xl flex-shrink-0">{t.icon}</span>
                <div>
                  <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{t.label}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{t.desc}</p>
                </div>
              </button>
            ))}
          </div>
          <Toggle checked={systemTheme} onChange={setSystemTheme} label="Follow System Theme" description="Automatically switch between themes based on your OS preference" />
        </div>
      </Card>
      <Card>
        <SectionHeader title="Layout & Density" />
        <div className="p-4 space-y-4">
          <div>
            <p className="text-xs font-medium mb-2" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>UI Density</p>
            <div className="flex gap-2">
              {(['compact', 'comfortable'] as const).map(d => (
                <button key={d} type="button" onClick={() => setDensity(d)}
                  className="flex-1 py-2 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none capitalize"
                  style={{ background: density === d ? 'var(--akaal-primary)' : 'var(--akaal-surface-elevated)', color: density === d ? '#fff' : 'var(--akaal-text-muted)', border: `1px solid ${density === d ? 'var(--akaal-primary)' : 'var(--akaal-border)'}`, fontFamily: "'Inter', sans-serif" }}
                  aria-pressed={density === d}
                >{d}</button>
              ))}
            </div>
          </div>
          <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <FormField label="UI Scale" hint="Percentage of base size">
              <Select value={uiScale} onChange={setUiScale} options={[{ value: '90', label: '90%' }, { value: '100', label: '100% (Default)' }, { value: '110', label: '110%' }, { value: '125', label: '125%' }]} />
            </FormField>
            <FormField label="Font Size" hint="Base font size in pixels">
              <Select value={fontSize} onChange={setFontSize} options={[{ value: '12', label: '12px (Small)' }, { value: '13', label: '13px' }, { value: '14', label: '14px (Default)' }, { value: '16', label: '16px (Large)' }]} />
            </FormField>
            <FormField label="Sidebar Behavior">
              <Select value={sidebarBehavior} onChange={setSidebarBehavior} options={[{ value: 'auto-collapse', label: 'Auto Collapse' }, { value: 'always-open', label: 'Always Open' }, { value: 'always-collapsed', label: 'Always Collapsed' }]} />
            </FormField>
            <FormField label="Table Density">
              <Select value={tableDensity} onChange={setTableDensity} options={[{ value: 'compact', label: 'Compact' }, { value: 'default', label: 'Default' }, { value: 'relaxed', label: 'Relaxed' }]} />
            </FormField>
          </div>
          <Toggle checked={animations} onChange={setAnimations} label="Enable Animations" description="Smooth transitions and micro-interactions throughout the UI" />
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Notifications ───────────────────────────────────────────────────

function NotificationsSection({ loading }: { loading: boolean }) {
  const [email, setEmail] = useState(true);
  const [slack, setSlack] = useState(true);
  const [teams, setTeams] = useState(false);
  const [desktop, setDesktop] = useState(true);
  const [sound, setSound] = useState(false);
  const [digest, setDigest] = useState('daily');
  const [critical, setCritical] = useState(true);
  const [completion, setCompletion] = useState(true);
  const [failures, setFailures] = useState(true);
  const [warnings, setWarnings] = useState(true);
  const [maintenance, setMaintenance] = useState(false);

  if (loading) return <div className="space-y-4">{[0,1].map(i => <Card key={i} className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3].map(j => <Skeleton key={j} className="h-10 w-full mb-2" />)}</Card>)}</div>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Delivery Channels" subtitle="Configure how you receive notifications" />
        <div className="px-4 pb-2">
          <Toggle checked={email} onChange={setEmail} label="Email Notifications" description="Receive notifications via email at sarah.chen@akaal.io" />
          <Toggle checked={slack} onChange={setSlack} label="Slack" description="Send notifications to your connected Slack workspace" />
          <Toggle checked={teams} onChange={setTeams} label="Microsoft Teams" description="Send notifications to your Microsoft Teams channel" />
          <Toggle checked={desktop} onChange={setDesktop} label="Desktop Notifications" description="Browser push notifications when the app is in the background" />
          <Toggle checked={sound} onChange={setSound} label="Notification Sound" description="Play a sound for critical alerts and completions" />
        </div>
        <div className="px-4 pb-4 pt-2">
          <FormField label="Digest Frequency" hint="Receive a summary digest at this interval">
            <Select value={digest} onChange={setDigest} options={[{ value: 'realtime', label: 'Real-time' }, { value: 'hourly', label: 'Hourly' }, { value: 'daily', label: 'Daily' }, { value: 'weekly', label: 'Weekly' }]} />
          </FormField>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Alert Types" subtitle="Choose which events trigger notifications" />
        <div className="px-4 pb-2">
          <Toggle checked={critical} onChange={setCritical} label="Critical Alerts" description="Platform failures, security incidents, and data loss risks" />
          <Toggle checked={completion} onChange={setCompletion} label="Migration Completion" description="Notify when a migration finishes successfully" />
          <Toggle checked={failures} onChange={setFailures} label="Failures & Errors" description="Migration failures, worker crashes, and service errors" />
          <Toggle checked={warnings} onChange={setWarnings} label="Warnings" description="Performance degradation, quota thresholds, and anomalies" />
          <Toggle checked={maintenance} onChange={setMaintenance} label="Maintenance Windows" description="Scheduled maintenance and platform upgrade notifications" />
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Accessibility ───────────────────────────────────────────────────

function AccessibilitySection({ loading }: { loading: boolean }) {
  const [highContrast, setHighContrast] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [keyboardNav, setKeyboardNav] = useState(true);
  const [focusIndicators, setFocusIndicators] = useState(true);
  const [screenReader, setScreenReader] = useState(false);
  const [fontScaling, setFontScaling] = useState(true);
  const [colorBlind, setColorBlind] = useState(false);

  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-10 w-full mb-2" />)}</Card>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Accessibility Options" subtitle="WCAG AA compliant configuration" />
        <div className="px-4 pb-2">
          <Toggle checked={highContrast} onChange={setHighContrast} label="High Contrast Mode" description="Increase contrast ratios for improved readability" />
          <Toggle checked={reducedMotion} onChange={setReducedMotion} label="Reduced Motion" description="Minimize animations and transitions throughout the UI" />
          <Toggle checked={keyboardNav} onChange={setKeyboardNav} label="Enhanced Keyboard Navigation" description="Full keyboard navigation support with visible focus indicators" />
          <Toggle checked={focusIndicators} onChange={setFocusIndicators} label="Visible Focus Indicators" description="Always show focus rings on interactive elements" />
          <Toggle checked={screenReader} onChange={setScreenReader} label="Screen Reader Optimizations" description="Enhanced ARIA labels and live region announcements" />
          <Toggle checked={fontScaling} onChange={setFontScaling} label="Respect Browser Font Scaling" description="Honor the user's browser font size preferences" />
          <Toggle checked={colorBlind} onChange={setColorBlind} label="Color Blind Friendly Indicators" description="Use patterns and icons in addition to color for status indicators" />
        </div>
      </Card>
      <Card className="p-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0" style={{ background: 'var(--akaal-info-bg)' }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><circle cx="7" cy="7" r="5.5" stroke="var(--akaal-info)" strokeWidth="1.2" /><path d="M7 6.5v3M7 4.5v.5" stroke="var(--akaal-info)" strokeWidth="1.4" strokeLinecap="round" /></svg>
          </div>
          <div>
            <p className="text-xs font-semibold mb-1" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>WCAG AA Compliance</p>
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>AKAAL maintains WCAG 2.1 Level AA compliance across all themes. All interactive elements meet minimum contrast ratios and are fully keyboard accessible.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Localization ────────────────────────────────────────────────────

function LocalizationSection({ loading }: { loading: boolean }) {
  const [lang, setLang] = useState('en-US');
  const [tz, setTz] = useState('America/Los_Angeles');
  const [dateFormat, setDateFormat] = useState('MM/DD/YYYY');
  const [timeFormat, setTimeFormat] = useState('12h');
  const [numberFormat, setNumberFormat] = useState('en-US');
  const [currency, setCurrency] = useState('USD');

  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3].map(i => <Skeleton key={i} className="h-8 w-full mb-3" />)}</Card>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Language & Region" />
        <div className="p-4 grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <FormField label="Language">
            <Select value={lang} onChange={setLang} options={[{ value: 'en-US', label: 'English (US)' }, { value: 'en-GB', label: 'English (UK)' }, { value: 'de-DE', label: 'Deutsch' }, { value: 'fr-FR', label: 'Français' }, { value: 'es-ES', label: 'Español' }, { value: 'ja-JP', label: '日本語' }, { value: 'zh-CN', label: '中文 (简体)' }]} />
          </FormField>
          <FormField label="Timezone">
            <Select value={tz} onChange={setTz} options={[{ value: 'America/Los_Angeles', label: 'Pacific Time (PT)' }, { value: 'America/New_York', label: 'Eastern Time (ET)' }, { value: 'America/Chicago', label: 'Central Time (CT)' }, { value: 'Europe/London', label: 'GMT / BST' }, { value: 'Europe/Berlin', label: 'Central European Time' }, { value: 'Asia/Tokyo', label: 'Japan Standard Time' }, { value: 'UTC', label: 'UTC' }]} />
          </FormField>
          <FormField label="Date Format">
            <Select value={dateFormat} onChange={setDateFormat} options={[{ value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' }, { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' }, { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (ISO 8601)' }, { value: 'DD MMM YYYY', label: 'DD MMM YYYY' }]} />
          </FormField>
          <FormField label="Time Format">
            <Select value={timeFormat} onChange={setTimeFormat} options={[{ value: '12h', label: '12-hour (AM/PM)' }, { value: '24h', label: '24-hour' }]} />
          </FormField>
          <FormField label="Number Format">
            <Select value={numberFormat} onChange={setNumberFormat} options={[{ value: 'en-US', label: '1,234,567.89 (US)' }, { value: 'de-DE', label: '1.234.567,89 (EU)' }, { value: 'fr-FR', label: '1 234 567,89 (FR)' }]} />
          </FormField>
          <FormField label="Currency">
            <Select value={currency} onChange={setCurrency} options={[{ value: 'USD', label: 'USD — US Dollar' }, { value: 'EUR', label: 'EUR — Euro' }, { value: 'GBP', label: 'GBP — British Pound' }, { value: 'JPY', label: 'JPY — Japanese Yen' }]} />
          </FormField>
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Security ────────────────────────────────────────────────────────

function SecuritySection({ loading }: { loading: boolean }) {
  const [sessionTimeout, setSessionTimeout] = useState('8h');
  const [mfaEnabled] = useState(true);

  if (loading) return <div className="space-y-4">{[0,1,2].map(i => <Card key={i} className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2].map(j => <Skeleton key={j} className="h-8 w-full mb-3" />)}</Card>)}</div>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Password" subtitle="Manage your account password" action={
          <button type="button" className="text-xs px-3 py-1.5 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
          >Change Password</button>
        } />
        <div className="p-4 space-y-3">
          <InfoRow label="Last Changed" value="45 days ago" />
          <InfoRow label="Password Strength" value={<span style={{ color: 'var(--akaal-success)' }}>Strong</span>} />
          <InfoRow label="Password Policy" value="Min 12 chars, uppercase, number, symbol" />
          <InfoRow label="Password Expiry" value="90 days" />
        </div>
      </Card>
      <Card>
        <SectionHeader title="Multi-Factor Authentication" action={
          <StatusChip status={mfaEnabled ? 'enabled' : 'disabled'} label={mfaEnabled ? 'Enabled' : 'Disabled'} />
        } />
        <div className="p-4 space-y-3">
          <InfoRow label="MFA Status" value={<StatusChip status="enabled" label="Active" />} />
          <InfoRow label="Method" value="Authenticator App (TOTP)" />
          <InfoRow label="Backup Codes" value="8 remaining" />
          <InfoRow label="Recovery Email" value="s.chen.recovery@akaal.io" />
          <div className="flex gap-2 pt-2">
            <button type="button" className="text-xs px-3 py-1.5 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
            >Manage MFA</button>
            <button type="button" className="text-xs px-3 py-1.5 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
            >View Backup Codes</button>
          </div>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Session & Access" />
        <div className="p-4 space-y-3">
          <FormField label="Session Timeout">
            <Select value={sessionTimeout} onChange={setSessionTimeout} options={[{ value: '1h', label: '1 hour' }, { value: '4h', label: '4 hours' }, { value: '8h', label: '8 hours (Default)' }, { value: '24h', label: '24 hours' }, { value: 'never', label: 'Never (Not recommended)' }]} />
          </FormField>
          <InfoRow label="Trusted Devices" value="3 devices" />
          <InfoRow label="Active Sessions" value="4 sessions" />
        </div>
      </Card>
      <Card>
        <SectionHeader title="Recent Security Events" />
        <div className="p-4 space-y-2">
          {[
            { event: 'Successful login', time: '5 minutes ago', ip: '192.168.1.42', ok: true },
            { event: 'Password changed', time: '45 days ago', ip: '192.168.1.42', ok: true },
            { event: 'MFA verified', time: '5 minutes ago', ip: '192.168.1.42', ok: true },
            { event: 'Failed login attempt', time: '12 days ago', ip: '203.0.113.42', ok: false },
          ].map((ev, i) => (
            <div key={i} className="flex items-center justify-between py-2" style={{ borderBottom: i < 3 ? '1px solid var(--akaal-border-subtle)' : 'none' }}>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: ev.ok ? 'var(--akaal-success)' : 'var(--akaal-error)' }} aria-hidden="true" />
                <span className="text-xs" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{ev.event}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{ev.ip}</span>
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{ev.time}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Sessions ────────────────────────────────────────────────────────

function SessionsSection({ loading, onSelectSession }: { loading: boolean; onSelectSession: (s: SessionRecord) => void }) {
  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3].map(i => <Skeleton key={i} className="h-12 w-full mb-2" />)}</Card>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>4 active sessions across your account</p>
        <button type="button" className="text-xs px-3 py-1.5 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-error-bg)', color: 'var(--akaal-error)', border: '1px solid rgba(239,68,68,0.2)', fontFamily: "'Inter', sans-serif" }}
          onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
          onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
        >Terminate All Others</button>
      </div>
      <Card>
        <SectionHeader title="Active Sessions" />
        <div className="overflow-x-auto">
          <table className="w-full" aria-label="Active sessions">
            <thead>
              <tr style={{ background: 'var(--akaal-table-header)' }}>
                {['Browser', 'OS', 'IP Address', 'Location', 'Last Activity', 'Actions'].map(h => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", borderBottom: '1px solid var(--akaal-table-border)', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_SESSIONS.map((sess, i) => (
                <tr key={sess.id} className="transition-colors cursor-pointer" style={{ borderBottom: i < MOCK_SESSIONS.length - 1 ? '1px solid var(--akaal-table-border)' : 'none' }}
                  onClick={() => onSelectSession(sess)}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-table-row-hover)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{sess.browser}</span>
                      {sess.current && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--akaal-primary-subtle)', color: 'var(--akaal-primary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '9px' }}>Current</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{sess.os}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{sess.ip}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{sess.location}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{sess.lastActivity}</td>
                  <td className="px-4 py-3">
                    {!sess.current && (
                      <button type="button" className="text-xs px-2 py-1 rounded transition-all duration-150 focus:outline-none" style={{ color: 'var(--akaal-error)', background: 'var(--akaal-error-bg)', border: '1px solid rgba(239,68,68,0.2)', fontFamily: "'Inter', sans-serif" }}
                        onClick={e => { e.stopPropagation(); }}
                        aria-label={`Terminate session from ${sess.browser}`}
                      >Terminate</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ─── Section: API Tokens ──────────────────────────────────────────────────────

function ApiTokensSection({ loading, onSelectToken }: { loading: boolean; onSelectToken: (t: ApiToken) => void }) {
  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3].map(i => <Skeleton key={i} className="h-12 w-full mb-2" />)}</Card>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Manage personal and service API tokens</p>
        <button type="button" className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
          onMouseEnter={e => { e.currentTarget.style.opacity = '0.9'; }}
          onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M5 1v8M1 5h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
          Create Token
        </button>
      </div>
      <Card>
        <SectionHeader title="API Tokens" subtitle="Personal and service tokens for API access" />
        <div className="overflow-x-auto">
          <table className="w-full" aria-label="API tokens">
            <thead>
              <tr style={{ background: 'var(--akaal-table-header)' }}>
                {['Name', 'Type', 'Scopes', 'Last Used', 'Expires', 'Status', 'Actions'].map(h => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", borderBottom: '1px solid var(--akaal-table-border)', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_TOKENS.map((tok, i) => (
                <tr key={tok.id} className="transition-colors cursor-pointer" style={{ borderBottom: i < MOCK_TOKENS.length - 1 ? '1px solid var(--akaal-table-border)' : 'none' }}
                  onClick={() => onSelectToken(tok)}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-table-row-hover)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <td className="px-4 py-3 text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{tok.name}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 rounded" style={{ background: tok.type === 'service' ? 'var(--akaal-info-bg)' : 'var(--akaal-primary-subtle)', color: tok.type === 'service' ? 'var(--akaal-info)' : 'var(--akaal-primary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{tok.type}</span>
                  </td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{tok.scopes.length} scopes</td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{tok.lastUsed}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{tok.expires}</td>
                  <td className="px-4 py-3"><StatusChip status={tok.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {['Copy', 'Rotate', 'Revoke'].map(action => (
                        <button key={action} type="button" onClick={e => e.stopPropagation()} className="text-xs px-2 py-1 rounded transition-all duration-150 focus:outline-none" style={{ color: action === 'Revoke' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)', background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                          onMouseEnter={e => { e.currentTarget.style.color = action === 'Revoke' ? 'var(--akaal-error)' : 'var(--akaal-text)'; }}
                          onMouseLeave={e => { e.currentTarget.style.color = action === 'Revoke' ? 'var(--akaal-error)' : 'var(--akaal-text-muted)'; }}
                          aria-label={`${action} token ${tok.name}`}
                          disabled={tok.status !== 'active'}
                        >{action}</button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Migration Defaults ──────────────────────────────────────────────

function MigrationDefaultsSection({ loading }: { loading: boolean }) {
  const [batchSize, setBatchSize] = useState('10000');
  const [retryCount, setRetryCount] = useState('3');
  const [checkpointFreq, setCheckpointFreq] = useState('5000');
  const [validationLevel, setValidationLevel] = useState('standard');
  const [conflictStrategy, setConflictStrategy] = useState('skip');
  const [rollbackStrategy, setRollbackStrategy] = useState('checkpoint');
  const [loggingLevel, setLoggingLevel] = useState('INFO');
  const [notifyOnComplete, setNotifyOnComplete] = useState(true);
  const [notifyOnFailure, setNotifyOnFailure] = useState(true);

  if (loading) return <div className="space-y-4">{[0,1].map(i => <Card key={i} className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3].map(j => <Skeleton key={j} className="h-8 w-full mb-3" />)}</Card>)}</div>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Execution Defaults" subtitle="Default parameters applied to new migrations" />
        <div className="p-4 grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <FormField label="Default Batch Size" hint="Rows processed per batch">
            <Select value={batchSize} onChange={setBatchSize} options={[{ value: '1000', label: '1,000 rows' }, { value: '5000', label: '5,000 rows' }, { value: '10000', label: '10,000 rows (Default)' }, { value: '50000', label: '50,000 rows' }, { value: '100000', label: '100,000 rows' }]} />
          </FormField>
          <FormField label="Retry Count" hint="Automatic retries on failure">
            <Select value={retryCount} onChange={setRetryCount} options={[{ value: '0', label: 'No retries' }, { value: '1', label: '1 retry' }, { value: '3', label: '3 retries (Default)' }, { value: '5', label: '5 retries' }, { value: '10', label: '10 retries' }]} />
          </FormField>
          <FormField label="Checkpoint Frequency" hint="Save checkpoint every N rows">
            <Select value={checkpointFreq} onChange={setCheckpointFreq} options={[{ value: '1000', label: 'Every 1,000 rows' }, { value: '5000', label: 'Every 5,000 rows (Default)' }, { value: '10000', label: 'Every 10,000 rows' }, { value: '50000', label: 'Every 50,000 rows' }]} />
          </FormField>
          <FormField label="Validation Level">
            <Select value={validationLevel} onChange={setValidationLevel} options={[{ value: 'none', label: 'None' }, { value: 'basic', label: 'Basic (Row count)' }, { value: 'standard', label: 'Standard (Default)' }, { value: 'strict', label: 'Strict (Full checksum)' }]} />
          </FormField>
          <FormField label="Conflict Strategy" hint="How to handle duplicate records">
            <Select value={conflictStrategy} onChange={setConflictStrategy} options={[{ value: 'skip', label: 'Skip (Default)' }, { value: 'overwrite', label: 'Overwrite' }, { value: 'error', label: 'Raise Error' }, { value: 'merge', label: 'Merge' }]} />
          </FormField>
          <FormField label="Rollback Strategy">
            <Select value={rollbackStrategy} onChange={setRollbackStrategy} options={[{ value: 'checkpoint', label: 'Restore to Checkpoint (Default)' }, { value: 'full', label: 'Full Rollback' }, { value: 'none', label: 'No Rollback' }]} />
          </FormField>
          <FormField label="Logging Level">
            <Select value={loggingLevel} onChange={setLoggingLevel} options={[{ value: 'ERROR', label: 'ERROR only' }, { value: 'WARN', label: 'WARN and above' }, { value: 'INFO', label: 'INFO (Default)' }, { value: 'DEBUG', label: 'DEBUG (Verbose)' }]} />
          </FormField>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Notification Defaults" />
        <div className="px-4 pb-2">
          <Toggle checked={notifyOnComplete} onChange={setNotifyOnComplete} label="Notify on Completion" description="Send notification when migration completes successfully" />
          <Toggle checked={notifyOnFailure} onChange={setNotifyOnFailure} label="Notify on Failure" description="Send notification when migration fails or is rolled back" />
        </div>
      </Card>
    </div>
  );
}

// ─── Section: AI Configuration ────────────────────────────────────────────────

function AiConfigSection({ loading }: { loading: boolean }) {
  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('gpt-4o');
  const [temperature, setTemperature] = useState('0.3');
  const [maxTokens, setMaxTokens] = useState('4096');
  const [timeout, setTimeout] = useState('30');
  const [streaming, setStreaming] = useState(true);

  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3,4].map(i => <Skeleton key={i} className="h-8 w-full mb-3" />)}</Card>;

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0" style={{ background: 'var(--akaal-warning-bg)' }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M7 1.5L1.5 12h11L7 1.5Z" stroke="var(--akaal-warning)" strokeWidth="1.2" strokeLinejoin="round" /><path d="M7 5.5v3M7 10v.5" stroke="var(--akaal-warning)" strokeWidth="1.4" strokeLinecap="round" /></svg>
          </div>
          <div>
            <p className="text-xs font-semibold mb-1" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Placeholder Configuration</p>
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>AI configuration is a mock interface pending backend integration. Settings saved here will not affect live AI behavior until the integration is complete.</p>
          </div>
        </div>
      </Card>
      <Card>
        <SectionHeader title="AI Provider" subtitle="Configure the AI provider for AKAAL intelligence features" />
        <div className="p-4 space-y-4">
          <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
            {[
              { id: 'openai', label: 'OpenAI', desc: 'GPT-4o, GPT-4' },
              { id: 'anthropic', label: 'Anthropic', desc: 'Claude 3.5' },
              { id: 'google', label: 'Google', desc: 'Gemini 1.5' },
              { id: 'azure', label: 'Azure OpenAI', desc: 'Enterprise' },
              { id: 'local', label: 'Local Models', desc: 'Ollama, LM Studio' },
            ].map(p => (
              <button key={p.id} type="button" onClick={() => setProvider(p.id)}
                className="flex flex-col items-start p-3 rounded-lg text-left transition-all duration-150 focus:outline-none focus-visible:ring-2"
                style={{ border: `1px solid ${provider === p.id ? 'var(--akaal-primary)' : 'var(--akaal-border)'}`, background: provider === p.id ? 'var(--akaal-primary-subtle)' : 'var(--akaal-surface-elevated)' }}
                aria-pressed={provider === p.id}
              >
                <p className="text-xs font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{p.label}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{p.desc}</p>
              </button>
            ))}
          </div>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Model Configuration" />
        <div className="p-4 grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <FormField label="API Key" hint="Stored securely in Vault">
            <Input value="sk-••••••••••••••••••••••••••••••" type="password" disabled />
          </FormField>
          <FormField label="Default Model">
            <Select value={model} onChange={setModel} options={[{ value: 'gpt-4o', label: 'GPT-4o' }, { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' }, { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' }]} />
          </FormField>
          <FormField label="Temperature" hint="0 = deterministic, 1 = creative">
            <Select value={temperature} onChange={setTemperature} options={[{ value: '0', label: '0.0 (Deterministic)' }, { value: '0.1', label: '0.1' }, { value: '0.3', label: '0.3 (Default)' }, { value: '0.7', label: '0.7' }, { value: '1', label: '1.0 (Creative)' }]} />
          </FormField>
          <FormField label="Max Tokens">
            <Select value={maxTokens} onChange={setMaxTokens} options={[{ value: '1024', label: '1,024' }, { value: '2048', label: '2,048' }, { value: '4096', label: '4,096 (Default)' }, { value: '8192', label: '8,192' }]} />
          </FormField>
          <FormField label="Timeout (seconds)">
            <Select value={timeout} onChange={setTimeout} options={[{ value: '10', label: '10s' }, { value: '30', label: '30s (Default)' }, { value: '60', label: '60s' }, { value: '120', label: '120s' }]} />
          </FormField>
        </div>
        <div className="px-4 pb-4">
          <Toggle checked={streaming} onChange={setStreaming} label="Enable Streaming" description="Stream AI responses token-by-token for faster perceived performance" />
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Developer ───────────────────────────────────────────────────────

function DeveloperSection({ loading }: { loading: boolean }) {
  const [devMode, setDevMode] = useState(false);
  const [debugLogs, setDebugLogs] = useState(false);
  const [verboseLogging, setVerboseLogging] = useState(false);
  const [experimentalUI, setExperimentalUI] = useState(false);
  const [runtimeDiag, setRuntimeDiag] = useState(false);
  const [mockServices, setMockServices] = useState(false);

  if (loading) return <div className="space-y-4">{[0,1].map(i => <Card key={i} className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2].map(j => <Skeleton key={j} className="h-10 w-full mb-2" />)}</Card>)}</div>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="Developer Options" subtitle="Advanced options for platform engineers" />
        <div className="px-4 pb-2">
          <Toggle checked={devMode} onChange={setDevMode} label="Developer Mode" description="Enable developer tools, verbose error messages, and debug overlays" />
          <Toggle checked={debugLogs} onChange={setDebugLogs} label="Debug Logs" description="Output DEBUG level logs to the browser console" />
          <Toggle checked={verboseLogging} onChange={setVerboseLogging} label="Verbose Logging" description="Include request/response payloads in all log entries" />
          <Toggle checked={experimentalUI} onChange={setExperimentalUI} label="Experimental UI" description="Enable unreleased UI features currently in development" />
          <Toggle checked={runtimeDiag} onChange={setRuntimeDiag} label="Runtime Diagnostics" description="Show real-time performance metrics overlay in the UI" />
          <Toggle checked={mockServices} onChange={setMockServices} label="Mock Services" description="Use mock data instead of live API calls (for testing)" />
        </div>
      </Card>
      <Card>
        <SectionHeader title="Environment Information" />
        <div className="p-4 space-y-1">
          <InfoRow label="Environment" value={<StatusChip status="enabled" label="Production" />} />
          <InfoRow label="Node.js Version" value="v20.11.0" mono />
          <InfoRow label="Next.js Version" value="15.0.0" mono />
          <InfoRow label="React Version" value="19.0.3" mono />
          <InfoRow label="Build Target" value="server" mono />
          <InfoRow label="API Base URL" value="https://api.akaal.io/v3" mono />
          <InfoRow label="WebSocket URL" value="wss://ws.akaal.io" mono />
          <InfoRow label="CDN" value="https://cdn.akaal.io" mono />
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Feature Flags ───────────────────────────────────────────────────

function FeatureFlagsSection({ loading, onSelectFlag }: { loading: boolean; onSelectFlag: (f: FeatureFlag) => void }) {
  const [search, setSearch] = useState('');
  const filtered = MOCK_FEATURE_FLAGS.filter(f => f.feature.toLowerCase().includes(search.toLowerCase()) || f.description.toLowerCase().includes(search.toLowerCase()));

  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3,4,5].map(i => <Skeleton key={i} className="h-10 w-full mb-2" />)}</Card>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
            <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
            <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
          <input type="search" placeholder="Search feature flags…" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
            style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
            aria-label="Search feature flags"
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
          />
        </div>
        <p className="text-xs flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{filtered.length} flags</p>
      </div>
      <Card>
        <SectionHeader title="Feature Flags" subtitle="Enterprise feature flag management" />
        <div className="overflow-x-auto">
          <table className="w-full" aria-label="Feature flags">
            <thead>
              <tr style={{ background: 'var(--akaal-table-header)' }}>
                {['Feature', 'Status', 'Rollout', 'Environment', 'Description', 'Last Modified'].map(h => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", borderBottom: '1px solid var(--akaal-table-border)', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((flag, i) => (
                <tr key={flag.id} className="transition-colors cursor-pointer" style={{ borderBottom: i < filtered.length - 1 ? '1px solid var(--akaal-table-border)' : 'none' }}
                  onClick={() => onSelectFlag(flag)}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-table-row-hover)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <td className="px-4 py-3 text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{flag.feature}</td>
                  <td className="px-4 py-3"><StatusChip status={flag.status} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 min-w-[80px]">
                      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--akaal-surface-elevated)' }}>
                        <div className="h-full rounded-full" style={{ width: `${flag.rollout}%`, background: flag.status === 'enabled' ? 'var(--akaal-success)' : flag.status === 'partial' ? 'var(--akaal-warning)' : 'var(--akaal-border)' }} />
                      </div>
                      <span className="text-xs flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{flag.rollout}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{flag.environment}</span>
                  </td>
                  <td className="px-4 py-3 text-xs max-w-xs truncate" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{flag.description}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>{flag.lastModified}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ─── Section: Keyboard Shortcuts ──────────────────────────────────────────────

function KeyboardShortcutsSection({ loading }: { loading: boolean }) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const categories = [...new Set(MOCK_SHORTCUTS.map(s => s.category))];

  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3,4].map(i => <Skeleton key={i} className="h-10 w-full mb-2" />)}</Card>;

  return (
    <div className="space-y-4">
      {categories.map(cat => (
        <Card key={cat}>
          <SectionHeader title={cat} />
          <div className="p-2">
            {MOCK_SHORTCUTS.filter(s => s.category === cat).map((shortcut, i, arr) => (
              <div key={shortcut.id} className="flex items-center justify-between px-3 py-2.5 rounded-md transition-colors"
                style={{ borderBottom: i < arr.length - 1 ? '1px solid var(--akaal-border-subtle)' : 'none' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--akaal-hover-bg)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                <span className="text-xs" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{shortcut.action}</span>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1">
                    {shortcut.keys.map((key, ki) => (
                      <React.Fragment key={ki}>
                        <kbd className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)', color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', boxShadow: '0 1px 0 var(--akaal-border)' }}>{key}</kbd>
                        {ki < shortcut.keys.length - 1 && <span className="text-xs" style={{ color: 'var(--akaal-text-muted)' }}>+</span>}
                      </React.Fragment>
                    ))}
                  </div>
                  <button type="button" onClick={() => setEditingId(editingId === shortcut.id ? null : shortcut.id)}
                    className="text-xs px-2 py-1 rounded transition-all duration-150 focus:outline-none"
                    style={{ color: editingId === shortcut.id ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)', background: editingId === shortcut.id ? 'var(--akaal-primary-subtle)' : 'transparent', border: `1px solid ${editingId === shortcut.id ? 'var(--akaal-primary)' : 'transparent'}`, fontFamily: "'Inter', sans-serif" }}
                    aria-label={`Customize shortcut for ${shortcut.action}`}
                  >{editingId === shortcut.id ? 'Press keys…' : 'Customize'}</button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}

// ─── Section: Branding ────────────────────────────────────────────────────────

function BrandingSection({ loading }: { loading: boolean }) {
  const [orgName, setOrgName] = useState('AKAAL Enterprise');
  const [supportContact, setSupportContact] = useState('support@akaal.io');
  const [footerText, setFooterText] = useState('© 2024 AKAAL Enterprise. All rights reserved.');
  const [loginMessage, setLoginMessage] = useState('Welcome to AKAAL — Enterprise Migration Platform');

  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3].map(i => <Skeleton key={i} className="h-8 w-full mb-3" />)}</Card>;

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0" style={{ background: 'var(--akaal-info-bg)' }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><circle cx="7" cy="7" r="5.5" stroke="var(--akaal-info)" strokeWidth="1.2" /><path d="M7 6.5v3M7 4.5v.5" stroke="var(--akaal-info)" strokeWidth="1.4" strokeLinecap="round" /></svg>
          </div>
          <div>
            <p className="text-xs font-semibold mb-1" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Mock Configuration</p>
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Branding configuration is a placeholder pending backend integration. Changes here are for preview purposes only.</p>
          </div>
        </div>
      </Card>
      <Card>
        <SectionHeader title="Organization Branding" subtitle="Customize the platform appearance for your organization" />
        <div className="p-4 space-y-3">
          <FormField label="Organization Name">
            <Input value={orgName} onChange={setOrgName} />
          </FormField>
          <FormField label="Logo" hint="Recommended: 200×48px PNG or SVG">
            <div className="flex items-center gap-3">
              <div className="w-32 h-10 rounded-md flex items-center justify-center" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>AKAAL</span>
              </div>
              <button type="button" className="text-xs px-3 py-1.5 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
              >Upload Logo</button>
            </div>
          </FormField>
          <FormField label="Accent Color" hint="Uses official AKAAL theme — cannot be overridden">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-md flex-shrink-0" style={{ background: 'var(--akaal-primary)', border: '1px solid var(--akaal-border)' }} aria-label="Current accent color" />
              <Input value="var(--akaal-primary) — Theme Controlled" disabled />
            </div>
          </FormField>
          <FormField label="Support Contact">
            <Input value={supportContact} onChange={setSupportContact} type="email" />
          </FormField>
          <FormField label="Footer Text">
            <Input value={footerText} onChange={setFooterText} />
          </FormField>
          <FormField label="Custom Login Message">
            <Input value={loginMessage} onChange={setLoginMessage} />
          </FormField>
        </div>
      </Card>
    </div>
  );
}

// ─── Section: About ───────────────────────────────────────────────────────────

function AboutSection({ loading }: { loading: boolean }) {
  if (loading) return <Card className="p-4"><Skeleton className="h-4 w-32 mb-4" />{[0,1,2,3,4,5,6,7].map(i => <Skeleton key={i} className="h-8 w-full mb-2" />)}</Card>;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHeader title="AKAAL Platform" subtitle="Version and build information" />
        <div className="p-4 space-y-1">
          <InfoRow label="AKAAL Version" value="3.2.1" mono />
          <InfoRow label="Build Number" value="20240726.1" mono />
          <InfoRow label="Frontend Version" value="3.2.1-fe" mono />
          <InfoRow label="Backend Version" value="3.2.1-be (placeholder)" mono />
          <InfoRow label="License" value={<StatusChip status="enabled" label="Enterprise" />} />
          <InfoRow label="Environment" value={<StatusChip status="enabled" label="Production" />} />
          <InfoRow label="Git Commit" value="a3f8c2d (placeholder)" mono />
          <InfoRow label="Deployed" value="2024-07-26 at 03:47 UTC" mono />
          <InfoRow label="Platform Uptime" value="14d 6h 22m" mono />
        </div>
      </Card>
      <Card>
        <SectionHeader title="Release Notes" />
        <div className="p-4 space-y-3">
          {[
            { version: '3.2.1', date: '2024-07-26', notes: 'Settings module, performance improvements, bug fixes' },
            { version: '3.2.0', date: '2024-07-15', notes: 'System module, enhanced observability, RBAC improvements' },
            { version: '3.1.0', date: '2024-07-01', notes: 'Agents module, AI planning assistant, CDC enhancements' },
          ].map((r, i) => (
            <div key={i} className="flex items-start gap-3 py-2" style={{ borderBottom: i < 2 ? '1px solid var(--akaal-border-subtle)' : 'none' }}>
              <span className="text-xs font-semibold flex-shrink-0" style={{ color: 'var(--akaal-primary)', fontFamily: "'JetBrains Mono', monospace" }}>v{r.version}</span>
              <div className="flex-1">
                <p className="text-xs" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{r.notes}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{r.date}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <SectionHeader title="Documentation & Support" />
        <div className="p-4 space-y-2">
          {[
            { label: 'Documentation', href: '#', desc: 'Full platform documentation and API reference' },
            { label: 'Release Notes', href: '#', desc: 'Detailed changelog for all versions' },
            { label: 'Support Portal', href: '#', desc: 'Submit tickets and track issues' },
            { label: 'Status Page', href: '#', desc: 'Real-time platform status and incident history' },
          ].map((link, i) => (
            <div key={i} className="flex items-center justify-between py-2" style={{ borderBottom: i < 3 ? '1px solid var(--akaal-border-subtle)' : 'none' }}>
              <div>
                <p className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{link.label}</p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{link.desc}</p>
              </div>
              <a href={link.href} className="text-xs px-2 py-1 rounded transition-all duration-150 focus:outline-none focus-visible:ring-2" style={{ color: 'var(--akaal-primary)', background: 'var(--akaal-primary-subtle)', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
                onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                aria-label={`Open ${link.label}`}
              >Open →</a>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── Section Content Router ───────────────────────────────────────────────────

function SectionContent({
  section, loading, onSelectSession, onSelectToken, onSelectFlag,
}: {
  section: SettingsSection;
  loading: boolean;
  onSelectSession: (s: SessionRecord) => void;
  onSelectToken: (t: ApiToken) => void;
  onSelectFlag: (f: FeatureFlag) => void;
}) {
  switch (section) {
    case 'profile':           return <ProfileSection loading={loading} />;
    case 'appearance':        return <AppearanceSection loading={loading} />;
    case 'notifications':     return <NotificationsSection loading={loading} />;
    case 'accessibility':     return <AccessibilitySection loading={loading} />;
    case 'localization':      return <LocalizationSection loading={loading} />;
    case 'security':          return <SecuritySection loading={loading} />;
    case 'sessions':          return <SessionsSection loading={loading} onSelectSession={onSelectSession} />;
    case 'api-tokens':        return <ApiTokensSection loading={loading} onSelectToken={onSelectToken} />;
    case 'migration-defaults':return <MigrationDefaultsSection loading={loading} />;
    case 'ai-config':         return <AiConfigSection loading={loading} />;
    case 'developer':         return <DeveloperSection loading={loading} />;
    case 'feature-flags':     return <FeatureFlagsSection loading={loading} onSelectFlag={onSelectFlag} />;
    case 'keyboard-shortcuts':return <KeyboardShortcutsSection loading={loading} />;
    case 'branding':          return <BrandingSection loading={loading} />;
    case 'about':             return <AboutSection loading={loading} />;
    default:                  return null;
  }
}

// ─── Inspector Panel ──────────────────────────────────────────────────────────

type InspectorItem = SessionRecord | ApiToken | FeatureFlag;
type InspectorType = 'session' | 'token' | 'flag';

function InspectorPanel({ item, type, onClose }: { item: InspectorItem; type: InspectorType; onClose: () => void }) {
  const [tab, setTab] = useState<'overview' | 'details' | 'history'>('overview');

  const title = type === 'session' ? (item as SessionRecord).browser
    : type === 'token' ? (item as ApiToken).name
    : (item as FeatureFlag).feature;

  return (
    <div className="flex flex-col flex-shrink-0 h-full" style={{ width: '360px', background: 'var(--akaal-surface)', borderLeft: '1px solid var(--akaal-border)', animation: 'slideIn 0.2s ease' }} role="complementary" aria-label="Detail inspector">
      <div className="flex items-center justify-between px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold truncate" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{title}</p>
          <p className="text-xs mt-0.5 capitalize" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{type} details</p>
        </div>
        <button type="button" onClick={onClose} className="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-md transition-all duration-150 focus:outline-none focus-visible:ring-2" style={{ color: 'var(--akaal-text-muted)' }} aria-label="Close inspector"
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.color = 'var(--akaal-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
        </button>
      </div>
      <div className="flex border-b flex-shrink-0" style={{ borderColor: 'var(--akaal-border)' }}>
        {(['overview', 'details', 'history'] as const).map(t => (
          <button key={t} type="button" onClick={() => setTab(t)}
            className="flex-1 py-2.5 text-xs font-medium capitalize transition-all duration-150 focus:outline-none"
            style={{ color: tab === t ? 'var(--akaal-primary)' : 'var(--akaal-text-muted)', borderBottom: tab === t ? '2px solid var(--akaal-primary)' : '2px solid transparent', fontFamily: "'Inter', sans-serif" }}
            aria-selected={tab === t}
          >{t}</button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {type === 'session' && tab === 'overview' && (
          <div className="space-y-1">
            <InfoRow label="Browser" value={(item as SessionRecord).browser} />
            <InfoRow label="Operating System" value={(item as SessionRecord).os} />
            <InfoRow label="Device" value={(item as SessionRecord).device} />
            <InfoRow label="IP Address" value={(item as SessionRecord).ip} mono />
            <InfoRow label="Location" value={(item as SessionRecord).location} />
            <InfoRow label="Last Activity" value={(item as SessionRecord).lastActivity} />
            <InfoRow label="Status" value={(item as SessionRecord).current ? <StatusChip status="active" label="Current" /> : <StatusChip status="active" />} />
          </div>
        )}
        {type === 'token' && tab === 'overview' && (
          <div className="space-y-1">
            <InfoRow label="Name" value={(item as ApiToken).name} />
            <InfoRow label="Type" value={(item as ApiToken).type} />
            <InfoRow label="Status" value={<StatusChip status={(item as ApiToken).status} />} />
            <InfoRow label="Created" value={(item as ApiToken).created} mono />
            <InfoRow label="Expires" value={(item as ApiToken).expires} mono />
            <InfoRow label="Last Used" value={(item as ApiToken).lastUsed} />
            <div className="pt-2">
              <p className="text-xs mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Scopes</p>
              <div className="flex flex-wrap gap-1">
                {(item as ApiToken).scopes.map(scope => (
                  <span key={scope} className="text-xs px-2 py-0.5 rounded" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-secondary)', border: '1px solid var(--akaal-border)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{scope}</span>
                ))}
              </div>
            </div>
          </div>
        )}
        {type === 'flag' && tab === 'overview' && (
          <div className="space-y-1">
            <InfoRow label="Feature" value={(item as FeatureFlag).feature} mono />
            <InfoRow label="Status" value={<StatusChip status={(item as FeatureFlag).status} />} />
            <InfoRow label="Rollout" value={`${(item as FeatureFlag).rollout}%`} mono />
            <InfoRow label="Environment" value={(item as FeatureFlag).environment} />
            <InfoRow label="Last Modified" value={(item as FeatureFlag).lastModified} mono />
            <div className="pt-2">
              <p className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Description</p>
              <p className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>{(item as FeatureFlag).description}</p>
            </div>
            <div className="pt-3">
              <p className="text-xs mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Rollout Progress</p>
              <UsageBar value={(item as FeatureFlag).rollout} color="var(--akaal-success)" />
            </div>
          </div>
        )}
        {tab === 'details' && (
          <div className="space-y-2">
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Extended configuration details will be available after backend integration.</p>
          </div>
        )}
        {tab === 'history' && (
          <div className="space-y-2">
            {[
              { action: 'Created', time: '2024-01-15', user: 'sarah.chen' },
              { action: 'Modified', time: '2024-04-20', user: 'admin' },
              { action: 'Accessed', time: '2024-07-26', user: 'sarah.chen' },
            ].map((ev, i) => (
              <div key={i} className="flex items-center gap-3 py-2" style={{ borderBottom: i < 2 ? '1px solid var(--akaal-border-subtle)' : 'none' }}>
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: 'var(--akaal-primary)' }} aria-hidden="true" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{ev.action}</p>
                  <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>by {ev.user}</p>
                </div>
                <span className="text-xs flex-shrink-0" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>{ev.time}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {type !== 'session' || !(item as SessionRecord).current ? (
        <div className="px-4 py-3 flex-shrink-0" style={{ borderTop: '1px solid var(--akaal-border)' }}>
          <button type="button" className="w-full text-xs py-2 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-error-bg)', color: 'var(--akaal-error)', border: '1px solid rgba(239,68,68,0.2)', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => { e.currentTarget.style.opacity = '0.8'; }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
          >
            {type === 'session' ? 'Terminate Session' : type === 'token' ? 'Revoke Token' : 'Disable Flag'}
          </button>
        </div>
      ) : null}
    </div>
  );
}

// ─── Import/Export Modal ──────────────────────────────────────────────────────

function ImportModal({ onClose, onImport }: { onClose: () => void; onImport: () => void }) {
  const [dragging, setDragging] = useState(false);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }} role="dialog" aria-modal="true" aria-label="Import configuration">
      <div className="rounded-xl w-full max-w-md mx-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 24px 64px var(--akaal-shadow)' }}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid var(--akaal-border)' }}>
          <div>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Import Configuration</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Upload a previously exported settings file</p>
          </div>
          <button type="button" onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded-md transition-all duration-150 focus:outline-none" style={{ color: 'var(--akaal-text-muted)' }} aria-label="Close import dialog"
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
          </button>
        </div>
        <div className="p-5">
          <div
            className="rounded-lg flex flex-col items-center justify-center py-10 transition-all duration-150"
            style={{ border: `2px dashed ${dragging ? 'var(--akaal-primary)' : 'var(--akaal-border)'}`, background: dragging ? 'var(--akaal-primary-subtle)' : 'var(--akaal-surface-elevated)', cursor: 'pointer' }}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); onImport(); onClose(); }}
            role="button"
            aria-label="Drop configuration file here"
            tabIndex={0}
          >
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true" className="mb-3" style={{ color: 'var(--akaal-text-muted)' }}>
              <path d="M16 20V8M10 14l6-6 6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M6 24h20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <p className="text-xs font-medium mb-1" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Drop configuration file here</p>
            <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>or click to browse — JSON format only</p>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-5 py-4" style={{ borderTop: '1px solid var(--akaal-border)' }}>
          <button type="button" onClick={onClose} className="text-xs px-4 py-2 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}>Cancel</button>
          <button type="button" onClick={() => { onImport(); onClose(); }} className="text-xs px-4 py-2 rounded-md transition-all duration-150 focus:outline-none" style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}>Import</button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeSection, setActiveSection] = useState<SettingsSection>('profile');
  const [loading, setLoading] = useState(true);
  const [globalSearch, setGlobalSearch] = useState('');
  const [settingsSearch, setSettingsSearch] = useState('');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [inspectorItem, setInspectorItem] = useState<InspectorItem | null>(null);
  const [inspectorType, setInspectorType] = useState<InspectorType>('session');
  const [showImport, setShowImport] = useState(false);
  const [hasChanges, setHasChanges] = useState(true);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = `toast-${Date.now()}`;
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 900);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => setLoading(false), 400);
    return () => clearTimeout(t);
  }, [activeSection]);

  const handleSave = () => {
    addToast('success', 'Settings saved successfully');
    setHasChanges(false);
  };

  const handleDiscard = () => {
    addToast('info', 'Changes discarded');
    setHasChanges(false);
  };

  const handleReset = () => {
    addToast('info', 'Settings reset to defaults');
    setHasChanges(false);
  };

  const handleExport = () => {
    addToast('success', 'Configuration exported successfully');
  };

  const handleImport = () => {
    addToast('success', 'Configuration imported successfully');
    setHasChanges(true);
  };

  const sectionLabel = SETTINGS_SECTIONS.flatMap(g => g.items).find(i => i.id === activeSection)?.label ?? 'Settings';

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--akaal-bg)' }}>
      <style>{`
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
      `}</style>

      {/* Main Sidebar */}
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(v => !v)} />

      {/* Content Area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopNav searchValue={globalSearch} onSearchChange={setGlobalSearch} />

        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Settings Left Nav */}
          <SettingsNav active={activeSection} onSelect={s => { setActiveSection(s); setInspectorItem(null); }} search={settingsSearch} />

          {/* Main Content */}
          <main className="flex-1 flex flex-col min-w-0 overflow-hidden" style={{ background: 'var(--akaal-bg)' }}>
            {/* Page Header */}
            <div className="flex-shrink-0 px-6 py-4" style={{ borderBottom: '1px solid var(--akaal-border)', background: 'var(--akaal-surface)' }}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h1 className="text-lg font-bold" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Settings</h1>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Configure your workspace, preferences and platform defaults.</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
                  {hasChanges && (
                    <>
                      <button type="button" onClick={handleDiscard} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                        style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                        onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                        onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                        aria-label="Discard changes"
                      >
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                        Discard
                      </button>
                      <button type="button" onClick={handleSave} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                        style={{ background: 'var(--akaal-primary)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
                        onMouseEnter={e => { e.currentTarget.style.opacity = '0.9'; }}
                        onMouseLeave={e => { e.currentTarget.style.opacity = '1'; }}
                        aria-label="Save changes"
                      >
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M1.5 5.5l2.5 2.5 4.5-5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                        Save Changes
                      </button>
                    </>
                  )}
                  <button type="button" onClick={handleReset} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                    aria-label="Reset to defaults"
                  >
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M5 1a4 4 0 1 0 3.46 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /><path d="M8 1v2.5H5.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    Reset
                  </button>
                  <button type="button" onClick={handleExport} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                    aria-label="Export configuration"
                  >
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M5 7V1M2 4l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /><path d="M1 9h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                    Export
                  </button>
                  <button type="button" onClick={() => setShowImport(true)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 focus:outline-none"
                    style={{ background: 'var(--akaal-surface-elevated)', color: 'var(--akaal-text-muted)', border: '1px solid var(--akaal-border)', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { e.currentTarget.style.color = 'var(--akaal-text)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--akaal-text-muted)'; }}
                    aria-label="Import configuration"
                  >
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M5 3v6M2 6l3-3 3 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /><path d="M1 9h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
                    Import
                  </button>
                </div>
              </div>
              {/* Settings Search */}
              <div className="mt-3 relative max-w-sm">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--akaal-text-muted)' }}>
                  <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.3" />
                  <path d="M9.5 9.5l2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
                <input type="search" placeholder="Search all settings…" value={settingsSearch} onChange={e => setSettingsSearch(e.target.value)}
                  className="w-full text-xs rounded-md pl-8 pr-3 py-1.5 outline-none transition-all duration-150"
                  style={{ background: 'var(--akaal-input-bg)', border: '1px solid var(--akaal-input-border)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}
                  aria-label="Search all settings"
                  onFocus={e => { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 2px var(--akaal-focus-ring)'; }}
                  onBlur={e => { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; }}
                />
              </div>
            </div>

            {/* Section Title Bar */}
            <div className="flex-shrink-0 px-6 py-3 flex items-center gap-2" style={{ borderBottom: '1px solid var(--akaal-border)', background: 'var(--akaal-surface)' }}>
              <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Settings</span>
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true"><path d="M3.5 2l3 3-3 3" stroke="var(--akaal-border)" strokeWidth="1.2" strokeLinecap="round" /></svg>
              <span className="text-xs font-medium" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>{sectionLabel}</span>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <SectionContent
                section={activeSection}
                loading={loading}
                onSelectSession={s => { setInspectorItem(s); setInspectorType('session'); }}
                onSelectToken={t => { setInspectorItem(t); setInspectorType('token'); }}
                onSelectFlag={f => { setInspectorItem(f); setInspectorType('flag'); }}
              />
            </div>
          </main>

          {/* Inspector Panel */}
          {inspectorItem && (
            <InspectorPanel
              item={inspectorItem}
              type={inspectorType}
              onClose={() => setInspectorItem(null)}
            />
          )}
        </div>
      </div>

      {/* Import Modal */}
      {showImport && <ImportModal onClose={() => setShowImport(false)} onImport={handleImport} />}

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
