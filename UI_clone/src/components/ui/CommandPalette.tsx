'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

interface CommandItem {
  id: string;
  category: 'Navigation' | 'Migrations' | 'Databases' | 'Executions' | 'Agents' | 'Actions';
  title: string;
  description: string;
  href?: string;
  action?: () => void;
  shortcut?: string;
  icon: React.ReactNode;
}

export function CommandPalette({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const commandItems: CommandItem[] = [
    // Navigation
    { id: 'nav-dash', category: 'Navigation', title: 'Go to Dashboard', description: 'Enterprise Migration Operations Overview', href: '/dashboard', shortcut: 'G D', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="8" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="1" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" /><rect x="8" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { id: 'nav-migs', category: 'Navigation', title: 'Go to Migrations', description: 'Active and scheduled pipeline management', href: '/migrations', shortcut: 'G M', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'nav-exec', category: 'Navigation', title: 'Go to Execution Center', description: 'Job queue, execution inspect, live workers', href: '/execution-center', shortcut: 'G E', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 4.5l4 2.5-4 2.5V4.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" /></svg> },
    { id: 'nav-live', category: 'Navigation', title: 'Go to Live Monitor', description: 'Real-time telemetry and streaming logs', href: '/live-monitor', shortcut: 'G L', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 10l3-4 2.5 2 2.5-5 2 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg> },
    { id: 'nav-dbs', category: 'Navigation', title: 'Go to Databases', description: 'Enterprise database connectivity & schemas', href: '/databases', shortcut: 'G B', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><ellipse cx="7" cy="3.5" rx="5" ry="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M2 3.5v3c0 .8 2.2 1.5 5 1.5s5-.7 5-1.5v-3" stroke="currentColor" strokeWidth="1.3" /></svg> },
    { id: 'nav-reps', category: 'Navigation', title: 'Go to Reports', description: 'Pre-flight, validation & audit reports', href: '/reports', shortcut: 'G R', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="2.5" y="1.5" width="9" height="11" rx="1" stroke="currentColor" strokeWidth="1.3" /><path d="M5 4.5h4M5 7h4M5 9.5h2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { id: 'nav-agents', category: 'Navigation', title: 'Go to Agents', description: 'Worker agents and node cluster status', href: '/agents', shortcut: 'G A', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.3" /><path d="M7 1.5v1.5M7 11v1.5M1.5 7H3M11 7h1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { id: 'nav-sys', category: 'Navigation', title: 'Go to System & Settings', description: 'Platform health, API tokens and configuration', href: '/settings', shortcut: 'G S', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="2.5" stroke="currentColor" strokeWidth="1.3" /><path d="M7 1.5v1.5M7 11v1.5M1.5 7H3M11 7h1.5M3.2 3.2l1.1 1.1M9.7 9.7l1.1 1.1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },

    // Actions
    { id: 'act-new-mig', category: 'Actions', title: 'Create New Migration Workspace', description: 'Launch schema mapping wizard', href: '/migration-workspace', shortcut: 'C M', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg> },
    { id: 'act-new-db', category: 'Actions', title: 'Connect New Database Engine', description: 'Configure PostgreSQL, Oracle, MySQL or MSSQL', href: '/databases/connect', shortcut: 'C B', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><ellipse cx="7" cy="3.5" rx="5" ry="1.5" stroke="currentColor" strokeWidth="1.3" /><path d="M7 7.5v4.5M4.5 10h5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },
    { id: 'act-failed-migs', category: 'Actions', title: 'Inspect Failed Execution Jobs', description: 'Review constraint errors and error backtraces', href: '/execution-center?status=failed', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" /><path d="M5 5l4 4M9 5l-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg> },

    // Entities
    { id: 'ent-mig-1', category: 'Migrations', title: 'prod-oracle-to-postgres (EX-2847)', description: 'Running • Oracle 19c → PostgreSQL 15 • 67% complete', href: '/live-monitor?migration=r1', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="#38BDF8" strokeWidth="1.3" /></svg> },
    { id: 'ent-mig-2', category: 'Migrations', title: 'legacy-mssql-migration (EX-2849)', description: 'Failed • MSSQL 2017 → PostgreSQL 15 • Constraint Error', href: '/execution-center?job=EX-2849', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5" stroke="#EF4444" strokeWidth="1.3" /></svg> },
    { id: 'ent-db-1', category: 'Databases', title: 'prod-oracle-primary', description: 'Oracle 19c • db-prod-01.corp.internal:1521 • Healthy (4.2ms)', href: '/databases?search=prod-oracle', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><ellipse cx="7" cy="3.5" rx="5" ry="1.5" stroke="#22C55E" strokeWidth="1.3" /></svg> },
    { id: 'ent-db-2', category: 'Databases', title: 'target-pg-cluster', description: 'PostgreSQL 15 • pg-cluster.aws.rds:5432 • Healthy (2.1ms)', href: '/databases?search=target-pg', icon: <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><ellipse cx="7" cy="3.5" rx="5" ry="1.5" stroke="#22C55E" strokeWidth="1.3" /></svg> },
  ];

  const filteredItems = commandItems.filter(item =>
    search === '' ||
    item.title.toLowerCase().includes(search.toLowerCase()) ||
    item.description.toLowerCase().includes(search.toLowerCase()) ||
    item.category.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Open handled by parent state
        }
      }
      if (!isOpen) return;

      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(i => (i + 1) % Math.max(1, filteredItems.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(i => (i - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selected = filteredItems[selectedIndex];
        if (selected) {
          if (selected.href) {
            router.push(selected.href);
          } else if (selected.action) {
            selected.action();
          }
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, filteredItems, selectedIndex, router]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex items-start justify-center pt-20 px-4" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div
        className="fixed inset-0 transition-opacity"
        style={{ background: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(6px)' }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Command Palette Modal */}
      <div
        className="relative w-full max-w-2xl rounded-xl shadow-2xl overflow-hidden flex flex-col transition-all duration-150 transform translate-y-0"
        style={{
          background: 'var(--akaal-surface, #141E2E)',
          border: '1px solid var(--akaal-border, #2A3647)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
        }}
      >
        {/* Search Header */}
        <div className="flex items-center gap-3 px-4 py-3.5 flex-shrink-0" style={{ borderBottom: '1px solid var(--akaal-border, #2A3647)' }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-primary, #38BDF8)' }}>
            <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.4" />
            <path d="M10.5 10.5l3.5 3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command or search migrations, databases, agents…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full text-sm outline-none bg-transparent"
            style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}
            aria-label="Command search input"
          />
          <kbd
            className="text-xs px-1.5 py-0.5 rounded font-mono flex-shrink-0"
            style={{ background: 'var(--akaal-hover-bg, rgba(255,255,255,0.06))', border: '1px solid var(--akaal-border, #2A3647)', color: 'var(--akaal-text-muted, #64748B)' }}
          >
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1 custom-scrollbar">
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-xs font-medium" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
                No commands or entities matching "{search}"
              </p>
            </div>
          ) : (
            filteredItems.map((item, index) => {
              const isSelected = index === selectedIndex;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    if (item.href) router.push(item.href);
                    else if (item.action) item.action();
                    onClose();
                  }}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left transition-all duration-100 cursor-pointer"
                  style={{
                    background: isSelected ? 'var(--akaal-primary-subtle, rgba(37,99,235,0.15))' : 'transparent',
                    borderLeft: isSelected ? '3px solid var(--akaal-primary, #2563EB)' : '3px solid transparent',
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0"
                      style={{ background: 'var(--akaal-hover-bg, rgba(255,255,255,0.04))', color: isSelected ? 'var(--akaal-primary, #38BDF8)' : 'var(--akaal-text-muted, #64748B)' }}
                    >
                      {item.icon}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-semibold truncate" style={{ color: isSelected ? 'var(--akaal-text, #F8FAFC)' : 'var(--akaal-text-secondary, #CBD5E1)', fontFamily: "'Inter', sans-serif" }}>
                          {item.title}
                        </p>
                        <span className="text-xs px-1.5 py-0.2 rounded font-mono" style={{ background: 'rgba(255,255,255,0.04)', color: 'var(--akaal-text-muted, #64748B)', fontSize: '9px' }}>
                          {item.category}
                        </span>
                      </div>
                      <p className="text-xs truncate mt-0.5" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
                        {item.description}
                      </p>
                    </div>
                  </div>

                  {item.shortcut && (
                    <kbd
                      className="text-xs px-1.5 py-0.5 rounded font-mono flex-shrink-0 ml-2"
                      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--akaal-border, #2A3647)', color: 'var(--akaal-text-muted, #64748B)', fontSize: '10px' }}
                    >
                      {item.shortcut}
                    </kbd>
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 flex items-center justify-between flex-shrink-0" style={{ borderTop: '1px solid var(--akaal-border, #2A3647)', background: 'var(--akaal-sidebar-bg, #0D1520)' }}>
          <div className="flex items-center gap-3 text-xs" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif", fontSize: '11px' }}>
            <span><kbd className="px-1 py-0.2 rounded bg-white/5 border border-white/10 font-mono">↑↓</kbd> Navigate</span>
            <span><kbd className="px-1 py-0.2 rounded bg-white/5 border border-white/10 font-mono">↵</kbd> Select</span>
            <span><kbd className="px-1 py-0.2 rounded bg-white/5 border border-white/10 font-mono">ESC</kbd> Close</span>
          </div>
          <span className="text-xs font-mono" style={{ color: 'var(--akaal-text-muted, #64748B)', fontSize: '10px' }}>
            AKAAL Control Plane v2.4
          </span>
        </div>
      </div>
    </div>
  );
}
