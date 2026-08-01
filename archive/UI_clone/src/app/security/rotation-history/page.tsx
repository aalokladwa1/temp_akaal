'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { SecretRotationEngine } from '@/security/secrets/secretRotationEngine';
import { SecretRotationRecord } from '@/security/secrets/secretTypes';

export default function RotationHistoryPage() {
  const [history, setHistory] = useState<SecretRotationRecord[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [triggerFilter, setTriggerFilter] = useState('all');

  useEffect(() => {
    setHistory(SecretRotationEngine.getHistory());
  }, []);

  const filtered = history.filter((h) => {
    const matchesSearch = h.secretName.toLowerCase().includes(search.toLowerCase()) || h.initiatedBy.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || h.status === statusFilter;
    const matchesTrigger = triggerFilter === 'all' || h.trigger === triggerFilter;
    return matchesSearch && matchesStatus && matchesTrigger;
  });

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rotation_history_${Date.now()}.json`;
    a.click();
  };

  const handleExportCSV = () => {
    const headers = 'ID,Secret Name,Trigger,Status,From Version,To Version,Initiated By,Initiated At\n';
    const rows = filtered.map((r) => `${r.id},${r.secretName},${r.trigger},${r.status},${r.fromVersionId},${r.toVersionId || ''},${r.initiatedBy},${r.initiatedAt}`).join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rotation_history_${Date.now()}.csv`;
    a.click();
  };

  return (
    <div className="min-h-screen p-6" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      <header className="max-w-7xl mx-auto mb-6 flex items-center justify-between">
        <div>
          <nav className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)' }}>
            <Link href="/dashboard" className="hover:underline">Platform</Link> / <Link href="/security/secrets" className="hover:underline">Security</Link> / Rotation History
          </nav>
          <h1 className="text-2xl font-bold tracking-tight">Secret Rotation Audit History</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>
            Chronological audit timeline of manual, scheduled, automatic, and emergency secret rotations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            className="px-3 py-1.5 text-xs font-medium rounded border hover:bg-white/10"
            style={{ borderColor: 'var(--akaal-border)' }}
          >
            Export CSV
          </button>
          <button
            onClick={handleExportJSON}
            className="px-3 py-1.5 text-xs font-medium rounded border hover:bg-white/10"
            style={{ borderColor: 'var(--akaal-border)' }}
          >
            Export JSON
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto space-y-6">
        <div className="p-4 rounded-lg border flex flex-wrap items-center gap-4" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
          <input
            type="text"
            placeholder="Search rotation log..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-1.5 text-sm rounded border bg-transparent w-64"
            style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-sm rounded border bg-transparent"
            style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          >
            <option value="all">All Statuses</option>
            <option value="success">Success</option>
            <option value="in_progress">In Progress</option>
            <option value="failed">Failed</option>
            <option value="rolled_back">Rolled Back</option>
          </select>

          <select
            value={triggerFilter}
            onChange={(e) => setTriggerFilter(e.target.value)}
            className="px-3 py-1.5 text-sm rounded border bg-transparent"
            style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          >
            <option value="all">All Triggers</option>
            <option value="manual">Manual</option>
            <option value="scheduled">Scheduled</option>
            <option value="automatic">Automatic</option>
            <option value="emergency">Emergency</option>
          </select>
        </div>

        <div className="rounded-lg border overflow-hidden" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase border-b" style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text-muted)' }}>
              <tr>
                <th className="p-4">Secret Name</th>
                <th className="p-4">Trigger</th>
                <th className="p-4">Versions</th>
                <th className="p-4">Initiated By</th>
                <th className="p-4">Timestamp</th>
                <th className="p-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--akaal-border)' }}>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center" style={{ color: 'var(--akaal-text-muted)' }}>
                    No rotation history recorded matching filters.
                  </td>
                </tr>
              ) : (
                filtered.map((rot) => (
                  <tr key={rot.id} className="hover:bg-white/5 transition-colors">
                    <td className="p-4 font-semibold">{rot.secretName}</td>
                    <td className="p-4 text-xs font-mono capitalize">
                      {rot.isEmergency ? <span className="text-rose-400 font-bold">Emergency</span> : rot.trigger}
                    </td>
                    <td className="p-4 text-xs font-mono">
                      {rot.fromVersionId} &rarr; {rot.toVersionId ?? 'N/A'}
                    </td>
                    <td className="p-4 text-xs">{rot.initiatedBy}</td>
                    <td className="p-4 text-xs text-muted">{new Date(rot.initiatedAt).toLocaleString()}</td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        rot.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' :
                        rot.status === 'in_progress' ? 'bg-amber-500/20 text-amber-400' :
                        rot.status === 'rolled_back' ? 'bg-purple-500/20 text-purple-400' : 'bg-rose-500/20 text-rose-400'
                      }`}>
                        {rot.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
