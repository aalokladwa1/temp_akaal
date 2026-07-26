'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { GovernancePersistenceStore } from '@/security/governance/governancePersistenceStore';

interface ApprovalQueueItem {
  id: string;
  type: 'Migration Cutover' | 'JIT Elevation' | 'Credential Rotation' | 'Role Grant';
  requester: string;
  target: string;
  requestedAt: string;
  status: 'pending' | 'approved' | 'rejected';
  comment?: string;
}

const INITIAL_APPROVALS: ApprovalQueueItem[] = [
  { id: 'appr_9482', type: 'Migration Cutover', requester: 'david.miller@acme.com', target: 'Oracle 19c -> PostgreSQL 16 (PROD)', requestedAt: '10 minutes ago', status: 'pending' },
  { id: 'appr_8491', type: 'JIT Elevation', requester: 'sarah.chen@acme.com', target: 'Super Admin (60 min break-glass)', requestedAt: '25 minutes ago', status: 'pending' },
  { id: 'appr_7391', type: 'Credential Rotation', requester: 'secops-automation@acme.com', target: 'Prod Vault DB Passwords', requestedAt: '2 hours ago', status: 'approved', comment: 'Rotated automatically by Vault Agent' },
];

export default function ApprovalWorkflowsPage() {
  const [approvals, setApprovals] = useState<ApprovalQueueItem[]>(() => {
    return GovernancePersistenceStore.getItem('approvals', INITIAL_APPROVALS);
  });

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modals
  const [showJITModal, setShowJITModal] = useState(false);
  const [activeApproval, setActiveApproval] = useState<ApprovalQueueItem | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'reject' | null>(null);
  const [commentText, setCommentText] = useState('');

  // JIT Form State
  const [jitTarget, setJitTarget] = useState('Super Admin (60 min break-glass)');

  useEffect(() => {
    GovernancePersistenceStore.setItem('approvals', approvals);
  }, [approvals]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleJITSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newReq: ApprovalQueueItem = {
      id: `appr_${Date.now()}`,
      type: 'JIT Elevation',
      requester: 'sarah.chen@acme.com',
      target: jitTarget,
      requestedAt: 'Just now',
      status: 'pending',
    };
    setApprovals(prev => [newReq, ...prev]);
    setShowJITModal(false);
    showToast('JIT Elevation Request submitted to approval chain.');
  };

  const handleActionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeApproval || !actionType) return;
    setApprovals(prev => prev.map(a => a.id === activeApproval.id ? {
      ...a,
      status: actionType === 'approve' ? 'approved' : 'rejected',
      comment: commentText || (actionType === 'approve' ? 'Approved by Admin' : 'Rejected by Admin'),
    } : a));
    showToast(`Request ${actionType === 'approve' ? 'approved' : 'rejected'} successfully.`);
    setActiveApproval(null);
    setActionType(null);
    setCommentText('');
  };

  const filteredApprovals = approvals.filter(a => {
    const matchSearch = !search || a.target.toLowerCase().includes(search.toLowerCase()) || a.requester.toLowerCase().includes(search.toLowerCase()) || a.type.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || a.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="min-h-screen p-6" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      {toastMessage && (
        <div className="fixed top-4 right-4 z-50 px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 text-white shadow-lg">
          ✓ {toastMessage}
        </div>
      )}

      <header className="max-w-6xl mx-auto mb-6 flex items-center justify-between">
        <div>
          <nav className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)' }}>
            <Link href="/dashboard" className="hover:underline">Platform</Link> / Enterprise Governance / Approvals
          </nav>
          <h1 className="text-xl font-bold">Enterprise Access Requests & Approval Workflows</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>Review multi-step approval chains, JIT elevation requests, cutover sign-offs, and Four-Eyes dual approvals.</p>
        </div>
        <button
          type="button"
          onClick={() => setShowJITModal(true)}
          className="px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-all"
        >
          + Request JIT Elevation
        </button>
      </header>

      <main className="max-w-6xl mx-auto space-y-4">
        {/* Controls */}
        <div className="flex items-center gap-3 p-3 rounded-lg flex-wrap" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <input
            type="search"
            placeholder="Search approvals by target or requester…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="text-xs px-3 py-1.5 rounded border outline-none min-w-[260px]"
            style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded border outline-none"
            style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        {/* Directory */}
        <div className="rounded-lg p-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <h2 className="text-sm font-semibold mb-3">Approval Queue ({filteredApprovals.filter(a => a.status === 'pending').length} pending)</h2>
          <div className="space-y-3">
            {filteredApprovals.map(item => (
              <div key={item.id} className="flex items-center justify-between p-3 rounded-md" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold">{item.type}</span>
                    <span className="px-1.5 py-0.5 rounded text-xs font-mono font-semibold"
                      style={{
                        background: item.status === 'pending' ? 'rgba(245,158,11,0.15)' : item.status === 'approved' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                        color: item.status === 'pending' ? '#F59E0B' : item.status === 'approved' ? '#22C55E' : '#EF4444',
                        fontSize: '9px',
                      }}
                    >
                      {item.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs font-medium mt-1">{item.target}</p>
                  <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontSize: '10px' }}>
                    Requested by {item.requester} • {item.requestedAt}
                  </p>
                  {item.comment && (
                    <p className="text-xs italic mt-1 text-gray-400" style={{ fontSize: '10px' }}>
                      Comment: "{item.comment}"
                    </p>
                  )}
                </div>
                {item.status === 'pending' && (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => { setActiveApproval(item); setActionType('approve'); setCommentText(''); }}
                      className="px-3 py-1 rounded text-xs font-semibold bg-green-600 text-white hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => { setActiveApproval(item); setActionType('reject'); setCommentText(''); }}
                      className="px-3 py-1 rounded text-xs font-semibold bg-red-600 text-white hover:bg-red-700"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* JIT Elevation Request Modal */}
      {showJITModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="max-w-md w-full p-5 rounded-xl space-y-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
            <h2 className="text-base font-bold">Request JIT Privilege Elevation</h2>
            <form onSubmit={handleJITSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block mb-1 font-semibold">Target Privilege</label>
                <select
                  value={jitTarget}
                  onChange={e => setJitTarget(e.target.value)}
                  className="w-full p-2 rounded border outline-none"
                  style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                >
                  <option value="Super Admin (60 min break-glass)">Super Admin (60 min break-glass)</option>
                  <option value="Cutover Operator (120 min)">Cutover Operator (120 min)</option>
                  <option value="Credential Master (30 min)">Credential Master (30 min)</option>
                </select>
              </div>
              <div>
                <label className="block mb-1 font-semibold">Business Justification</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Provide explicit reason for break-glass emergency elevation…"
                  className="w-full p-2 rounded border outline-none"
                  style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowJITModal(false)} className="px-3 py-1.5 rounded bg-gray-700 text-gray-200 font-medium hover:bg-gray-600">
                  Cancel
                </button>
                <button type="submit" className="px-3 py-1.5 rounded bg-blue-600 text-white font-semibold hover:bg-blue-700">
                  Submit JIT Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Approve/Reject Action Modal */}
      {activeApproval && actionType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="max-w-md w-full p-5 rounded-xl space-y-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
            <h2 className="text-base font-bold capitalize">{actionType} Request: {activeApproval.type}</h2>
            <form onSubmit={handleActionSubmit} className="space-y-3 text-xs">
              <p className="text-gray-300">Target: <span className="font-semibold text-white">{activeApproval.target}</span></p>
              <div>
                <label className="block mb-1 font-semibold">Approval Comment / Reason</label>
                <textarea
                  rows={2}
                  placeholder={`Enter ${actionType} note or compliance audit comment…`}
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                  className="w-full p-2 rounded border outline-none"
                  style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => { setActiveApproval(null); setActionType(null); }} className="px-3 py-1.5 rounded bg-gray-700 text-gray-200 font-medium hover:bg-gray-600">
                  Cancel
                </button>
                <button type="submit" className={`px-3 py-1.5 rounded font-semibold text-white ${actionType === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`}>
                  Confirm {actionType.toUpperCase()}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
