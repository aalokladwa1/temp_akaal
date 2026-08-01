'use client';

import React, { useState } from 'react';

export interface ValidationItem {
  id: string;
  category: 'Connectivity' | 'Schema' | 'Compatibility' | 'Permissions' | 'Resources';
  name: string;
  status: 'passed' | 'warning' | 'failed' | 'checking';
  message: string;
  recommendation?: string;
}

export function ValidationCenter({
  validations,
  onRunAll,
  riskScore = 'LOW',
  estimatedTime = '14m 20s',
  estimatedDowntime = '0s (Zero-Downtime CDC)',
}: {
  validations: ValidationItem[];
  onRunAll: () => void;
  riskScore?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  estimatedTime?: string;
  estimatedDowntime?: string;
}) {
  const [filter, setFilter] = useState<'all' | 'passed' | 'warning' | 'failed'>('all');

  const filtered = validations.filter(v => filter === 'all' || v.status === filter);
  const passedCount = validations.filter(v => v.status === 'passed').length;
  const warningCount = validations.filter(v => v.status === 'warning').length;
  const failedCount = validations.filter(v => v.status === 'failed').length;

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'LOW': return { bg: 'rgba(34, 197, 94, 0.15)', text: '#22C55E' };
      case 'MEDIUM': return { bg: 'rgba(245, 158, 11, 0.15)', text: '#F59E0B' };
      case 'HIGH':
      case 'CRITICAL': return { bg: 'rgba(239, 68, 68, 0.15)', text: '#EF4444' };
      default: return { bg: 'rgba(100, 116, 139, 0.15)', text: '#94A3B8' };
    }
  };

  const riskBadge = getRiskColor(riskScore);

  return (
    <div className="flex flex-col gap-4 p-5 rounded-lg border" style={{ background: 'var(--akaal-surface, #141E2E)', borderColor: 'var(--akaal-border, #2A3647)' }}>
      {/* Header & Metrics */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b" style={{ borderColor: 'var(--akaal-border, #2A3647)' }}>
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
            Pre-Flight Validation & Compatibility Center
          </h3>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
            Verifies network connectivity, user permissions, table constraints, CDC replication slot availability, and schema compatibility.
          </p>
        </div>

        <button
          type="button"
          onClick={onRunAll}
          className="px-3 py-1.5 rounded text-xs font-semibold transition-colors shadow-sm flex items-center gap-1.5"
          style={{ background: 'var(--akaal-primary, #2563EB)', color: '#fff', fontFamily: "'Inter', sans-serif" }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2.5 6A3.5 3.5 0 1 1 6 9.5a3.5 3.5 0 0 1-3.5-3.5Z" stroke="currentColor" strokeWidth="1.3" /><path d="M6 3.5v2.5l1.5 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
          Re-run Pre-Flight Checks
        </button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'var(--akaal-border, #2A3647)' }}>
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>Migration Risk Score</p>
          <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded mt-1 font-mono" style={{ background: riskBadge.bg, color: riskBadge.text }}>
            {riskScore} RISK
          </span>
        </div>
        <div className="p-3 rounded border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'var(--akaal-border, #2A3647)' }}>
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>Est. Duration</p>
          <p className="text-xs font-semibold font-mono mt-1" style={{ color: 'var(--akaal-text, #F8FAFC)' }}>{estimatedTime}</p>
        </div>
        <div className="p-3 rounded border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'var(--akaal-border, #2A3647)' }}>
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>Est. Downtime</p>
          <p className="text-xs font-semibold font-mono mt-1 text-emerald-400">{estimatedDowntime}</p>
        </div>
        <div className="p-3 rounded border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'var(--akaal-border, #2A3647)' }}>
          <p className="text-xs" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>Validation Checks</p>
          <p className="text-xs font-mono mt-1">
            <span className="text-emerald-400 font-semibold">{passedCount} Passed</span> • <span className="text-amber-400 font-semibold">{warningCount} Warnings</span> • <span className="text-red-400 font-semibold">{failedCount} Failed</span>
          </p>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-1">
        {(['all', 'passed', 'warning', 'failed'] as const).map(tab => (
          <button
            key={tab}
            type="button"
            onClick={() => setFilter(tab)}
            className="px-2.5 py-1 rounded text-xs capitalize transition-colors font-medium"
            style={{
              background: filter === tab ? 'var(--akaal-hover-bg, rgba(255,255,255,0.08))' : 'transparent',
              color: filter === tab ? 'var(--akaal-text, #F8FAFC)' : 'var(--akaal-text-muted, #64748B)',
              fontFamily: "'Inter', sans-serif",
            }}
          >
            {tab} ({tab === 'all' ? validations.length : validations.filter(v => v.status === tab).length})
          </button>
        ))}
      </div>

      {/* Validation items list */}
      <div className="space-y-2 max-h-72 overflow-y-auto custom-scrollbar">
        {filtered.map(item => (
          <div key={item.id} className="p-3 rounded border flex items-start gap-3" style={{ background: 'rgba(0,0,0,0.15)', borderColor: 'var(--akaal-border, #2A3647)' }}>
            <div className="mt-0.5 flex-shrink-0">
              {item.status === 'passed' && <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" fill="rgba(34,197,94,0.15)" stroke="#22C55E" strokeWidth="1.2" /><path d="M5 8l2 2 4-4" stroke="#22C55E" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>}
              {item.status === 'warning' && <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" fill="rgba(245,158,11,0.15)" stroke="#F59E0B" strokeWidth="1.2" /><path d="M8 5v3.5M8 10.5v.5" stroke="#F59E0B" strokeWidth="1.4" strokeLinecap="round" /></svg>}
              {item.status === 'failed' && <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" fill="rgba(239,68,68,0.15)" stroke="#EF4444" strokeWidth="1.2" /><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#EF4444" strokeWidth="1.4" strokeLinecap="round" /></svg>}
              {item.status === 'checking' && <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="animate-spin"><circle cx="8" cy="8" r="6" stroke="#38BDF8" strokeWidth="1.4" strokeDasharray="14 8" /></svg>}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-xs font-semibold" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
                  {item.name}
                </h4>
                <span className="text-xs px-1.5 py-0.2 rounded font-mono" style={{ background: 'rgba(255,255,255,0.04)', color: 'var(--akaal-text-muted, #64748B)', fontSize: '10px' }}>
                  {item.category}
                </span>
              </div>
              <p className="text-xs mt-0.5 leading-relaxed" style={{ color: 'var(--akaal-text-muted, #94A3B8)', fontFamily: "'Inter', sans-serif" }}>
                {item.message}
              </p>
              {item.recommendation && (
                <p className="text-xs mt-1 font-mono text-amber-300/80 bg-amber-500/10 p-1.5 rounded border border-amber-500/20">
                  💡 Recommendation: {item.recommendation}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
