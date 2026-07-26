'use client';

import React, { useState } from 'react';
import { EntityDrawer } from './EntityDrawer';

export interface ApprovalRecord {
  id: string;
  migrationTitle: string;
  environment: string;
  requestedBy: string;
  requestedAt: string;
  status: 'pending' | 'approved' | 'rejected' | 'changes_requested';
  approvers: { name: string; role: string; status: 'approved' | 'rejected' | 'pending' }[];
  comments: { user: string; text: string; time: string }[];
}

export function ApprovalWorkflowDrawer({
  approval,
  isOpen,
  onClose,
  onApprove,
  onReject,
  onRequestChanges,
}: {
  approval: ApprovalRecord | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove?: (id: string, comment: string) => void;
  onReject?: (id: string, comment: string) => void;
  onRequestChanges?: (id: string, comment: string) => void;
}) {
  const [newComment, setNewComment] = useState('');

  if (!approval) return null;

  return (
    <EntityDrawer
      isOpen={isOpen}
      onClose={onClose}
      title={`Approval Request: ${approval.migrationTitle}`}
      subtitle={`Environment: ${approval.environment} • Requested by ${approval.requestedBy}`}
      size="lg"
      badge={
        <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold"
          style={{
            background: approval.status === 'approved' ? 'rgba(34,197,94,0.15)' : approval.status === 'rejected' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
            color: approval.status === 'approved' ? '#22C55E' : approval.status === 'rejected' ? '#EF4444' : '#F59E0B',
          }}
        >
          {approval.status.toUpperCase().replace('_', ' ')}
        </span>
      }
      footerActions={
        approval.status === 'pending' ? (
          <div className="flex items-center gap-2 w-full justify-end">
            <button
              type="button"
              onClick={() => {
                onRequestChanges?.(approval.id, newComment);
                onClose();
              }}
              className="px-3 py-1.5 rounded text-xs font-semibold transition-colors"
              style={{ background: 'rgba(245,158,11,0.15)', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.3)' }}
            >
              Request Changes
            </button>
            <button
              type="button"
              onClick={() => {
                onReject?.(approval.id, newComment);
                onClose();
              }}
              className="px-3 py-1.5 rounded text-xs font-semibold transition-colors"
              style={{ background: 'rgba(239,68,68,0.15)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.3)' }}
            >
              Reject
            </button>
            <button
              type="button"
              onClick={() => {
                onApprove?.(approval.id, newComment);
                onClose();
              }}
              className="px-4 py-1.5 rounded text-xs font-semibold transition-colors"
              style={{ background: 'var(--akaal-primary, #2563EB)', color: '#fff' }}
            >
              Approve Migration Crossover
            </button>
          </div>
        ) : undefined
      }
    >
      <div className="space-y-6">
        {/* Approvers list */}
        <div>
          <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
            Required Sign-off Matrix ({approval.approvers.filter(a => a.status === 'approved').length}/{approval.approvers.length})
          </h4>
          <div className="space-y-2">
            {approval.approvers.map((app, idx) => (
              <div key={idx} className="flex items-center justify-between p-2.5 rounded border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'var(--akaal-border, #2A3647)' }}>
                <div>
                  <p className="text-xs font-medium" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>{app.name}</p>
                  <p className="text-[10px]" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>{app.role}</p>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded"
                  style={{
                    background: app.status === 'approved' ? 'rgba(34,197,94,0.15)' : 'rgba(245,158,11,0.15)',
                    color: app.status === 'approved' ? '#22C55E' : '#F59E0B',
                  }}
                >
                  {app.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Comments & Discussion */}
        <div>
          <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
            Approval Comments & Decision Notes
          </h4>

          <div className="space-y-3 mb-4 max-h-48 overflow-y-auto custom-scrollbar">
            {approval.comments.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No comments submitted yet.</p>
            ) : (
              approval.comments.map((c, i) => (
                <div key={i} className="p-2.5 rounded border" style={{ background: 'rgba(0,0,0,0.2)', borderColor: 'var(--akaal-border, #2A3647)' }}>
                  <div className="flex justify-between items-center text-[10px] font-mono mb-1" style={{ color: 'var(--akaal-text-muted, #64748B)' }}>
                    <span className="font-semibold text-slate-300">{c.user}</span>
                    <span>{c.time}</span>
                  </div>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--akaal-text-secondary, #CBD5E1)', fontFamily: "'Inter', sans-serif" }}>
                    {c.text}
                  </p>
                </div>
              ))
            )}
          </div>

          <textarea
            rows={3}
            placeholder="Add decision commentary or review notes for team history…"
            value={newComment}
            onChange={e => setNewComment(e.target.value)}
            className="w-full text-xs p-2.5 rounded outline-none"
            style={{ background: 'var(--akaal-input-bg, #111827)', border: '1px solid var(--akaal-border, #2A3647)', color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}
          />
        </div>
      </div>
    </EntityDrawer>
  );
}
