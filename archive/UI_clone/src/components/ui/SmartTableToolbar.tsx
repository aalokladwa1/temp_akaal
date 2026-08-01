'use client';

import React from 'react';

export function exportToCSV(filename: string, rows: Record<string, any>[]) {
  if (!rows || !rows.length) return;
  const keys = Object.keys(rows[0]);
  const csvContent = [
    keys.join(','),
    ...rows.map(row => keys.map(k => JSON.stringify(row[k] ?? '')).join(',')),
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function exportToJSON(filename: string, rows: Record<string, any>[]) {
  if (!rows) return;
  const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.json`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

interface SmartTableToolbarProps {
  filename?: string;
  data?: Record<string, any>[];
  selectedCount?: number;
  onBulkPause?: () => void;
  onBulkRetry?: () => void;
  onBulkDelete?: () => void;
  onClearSelection?: () => void;
}

export function SmartTableToolbar({
  filename = 'export-data',
  data = [],
  selectedCount = 0,
  onBulkPause,
  onBulkRetry,
  onBulkDelete,
  onClearSelection,
}: SmartTableToolbarProps) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-2 flex-shrink-0" style={{ background: 'var(--akaal-sidebar-bg, #0D1520)', borderBottom: '1px solid var(--akaal-border, #2A3647)' }}>
      {selectedCount > 0 ? (
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold" style={{ color: 'var(--akaal-primary, #38BDF8)', fontFamily: "'Inter', sans-serif" }}>
            {selectedCount} selected
          </span>
          <div className="flex items-center gap-1.5">
            {onBulkPause && (
              <button
                type="button"
                onClick={onBulkPause}
                className="px-2 py-1 rounded text-xs transition-colors"
                style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#F59E0B', border: '1px solid rgba(245, 158, 11, 0.2)' }}
              >
                Pause
              </button>
            )}
            {onBulkRetry && (
              <button
                type="button"
                onClick={onBulkRetry}
                className="px-2 py-1 rounded text-xs transition-colors"
                style={{ background: 'rgba(56, 189, 248, 0.1)', color: '#38BDF8', border: '1px solid rgba(56, 189, 248, 0.2)' }}
              >
                Retry
              </button>
            )}
            {onBulkDelete && (
              <button
                type="button"
                onClick={onBulkDelete}
                className="px-2 py-1 rounded text-xs transition-colors"
                style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444', border: '1px solid rgba(239, 68, 68, 0.2)' }}
              >
                Delete
              </button>
            )}
            {data.length > 0 && (
              <button
                type="button"
                onClick={() => exportToCSV(filename, data)}
                className="px-2 py-1 rounded text-xs transition-colors"
                style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#CBD5E1', border: '1px solid #2A3647' }}
              >
                Export CSV
              </button>
            )}
          </div>
          {onClearSelection && (
            <button type="button" onClick={onClearSelection} className="text-xs ml-2 hover:underline" style={{ color: '#64748B' }}>
              Clear Selection
            </button>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2 ml-auto">
          {data.length > 0 && (
            <>
              <button
                type="button"
                onClick={() => exportToCSV(filename, data)}
                className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-all"
                style={{ background: 'transparent', border: '1px solid #2A3647', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#CBD5E1'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1v7M3 5l3 3 3-3M2 10h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                CSV
              </button>
              <button
                type="button"
                onClick={() => exportToJSON(filename, data)}
                className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-all"
                style={{ background: 'transparent', border: '1px solid #2A3647', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#CBD5E1'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1v7M3 5l3 3 3-3M2 10h8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                JSON
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
