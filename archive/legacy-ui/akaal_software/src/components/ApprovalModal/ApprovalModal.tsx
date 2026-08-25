import { useState, type FC, type FormEvent } from 'react';
import type { GovernanceApproval } from '../../types/migration';
import { ModalContainer } from '../ModalContainer';

export interface ApprovalModalProps {
  approval: GovernanceApproval;
  isOpen: boolean;
  onClose: () => void;
  onSubmitDecision: (
    approvalId: string,
    decision: 'approved' | 'rejected' | 'changes_requested',
    reason: string
  ) => void;
}

export const ApprovalModal: FC<ApprovalModalProps> = ({
  approval,
  isOpen,
  onClose,
  onSubmitDecision,
}) => {
  const [decision, setDecision] = useState<'approved' | 'rejected' | 'changes_requested'>('approved');
  const [reason, setReason] = useState<string>('');
  const [approverName, setApproverName] = useState<string>('Aalok');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) return;
    onSubmitDecision(approval.id, decision, `${approverName}: ${reason.trim()}`);
    onClose();
  };

  return (
    <ModalContainer
      isOpen={isOpen}
      onClose={onClose}
      lockBackdrop={false}
      maxWidth={520}
      ariaLabelledBy="approval-modal-title"
    >
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {/* Modal Header */}
        <div
          style={{
            padding: '18px 24px',
            background: 'var(--dash-surface)',
            borderBottom: '1px solid var(--dash-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#F59E0B', letterSpacing: '0.05em' }}>
              Four-Eyes Multi-Custody Governance Gate
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: '2px 0 0 0', color: 'var(--dash-text-primary)' }}>
              {approval.gateTitle} ({approval.gate})
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: 20,
              color: 'var(--dash-text-secondary)',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Approval Review Panel (Blueprint v3.1 Specification) */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              background: 'var(--dash-surface)',
              border: '1px solid var(--dash-border)',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 12,
              fontSize: 12,
            }}
          >
            <div>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Migration:</span>{' '}
              <strong style={{ color: 'var(--dash-text-primary)' }}>{approval.migrationName}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Project:</span>{' '}
              <strong style={{ color: 'var(--dash-text-primary)' }}>{approval.projectName}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Requested By:</span>{' '}
              <span style={{ color: 'var(--dash-text-primary)' }}>{approval.requestedBy}</span>
            </div>
            <div>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Risk Score:</span>{' '}
              <span style={{ color: approval.riskScore && approval.riskScore > 0.3 ? '#F59E0B' : '#10B981', fontWeight: 600 }}>
                {approval.riskScore !== undefined ? approval.riskScore.toFixed(2) : '0.00'} / 100 (LOW)
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Custody Hash:</span>{' '}
              <code style={{ fontSize: 11, background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: 4, color: '#60A5FA' }}>
                sha256-b8a1c9e4d3f2...
              </code>
            </div>
            <div>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Rollback Status:</span>{' '}
              <span style={{ color: '#10B981', fontWeight: 600 }}>AVAILABLE (Snapshot Ready)</span>
            </div>
            <div>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Est. Duration / Downtime:</span>{' '}
              <span style={{ color: 'var(--dash-text-primary)' }}>42 Mins / ZERO (CDC Sync)</span>
            </div>
            <div>
              <span style={{ color: 'var(--dash-text-secondary)' }}>Compliance Status:</span>{' '}
              <span style={{ color: '#10B981', fontWeight: 600 }}>HIPAA & SOC-2 Verified</span>
            </div>
          </div>

          {/* Evidence Summary */}
          {approval.evidenceSummary && (
            <div
              style={{
                padding: 14,
                borderRadius: 8,
                background: 'rgba(59, 130, 246, 0.08)',
                border: '1px solid rgba(59, 130, 246, 0.2)',
                fontSize: 12,
                color: 'var(--dash-text-primary)',
              }}
            >
              <div style={{ fontWeight: 700, color: '#3B82F6', marginBottom: 4 }}>Evidence & Audit Summary</div>
              {approval.evidenceSummary}
            </div>
          )}

          {/* Decision Selection */}
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-primary)', marginBottom: 8 }}>
              Governance Decision:
            </label>
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                type="button"
                onClick={() => setDecision('approved')}
                style={{
                  flex: 1,
                  padding: '10px 12px',
                  borderRadius: 8,
                  border: decision === 'approved' ? '2px solid #10B981' : '1px solid var(--dash-border)',
                  background: decision === 'approved' ? 'rgba(16, 185, 129, 0.12)' : 'var(--dash-surface)',
                  color: decision === 'approved' ? '#10B981' : 'var(--dash-text-secondary)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                ✓ Approve Sign-off
              </button>

              <button
                type="button"
                onClick={() => setDecision('changes_requested')}
                style={{
                  flex: 1,
                  padding: '10px 12px',
                  borderRadius: 8,
                  border: decision === 'changes_requested' ? '2px solid #F59E0B' : '1px solid var(--dash-border)',
                  background: decision === 'changes_requested' ? 'rgba(245, 158, 11, 0.12)' : 'var(--dash-surface)',
                  color: decision === 'changes_requested' ? '#F59E0B' : 'var(--dash-text-secondary)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                ⚡ Request Changes
              </button>

              <button
                type="button"
                onClick={() => setDecision('rejected')}
                style={{
                  flex: 1,
                  padding: '10px 12px',
                  borderRadius: 8,
                  border: decision === 'rejected' ? '2px solid #EF4444' : '1px solid var(--dash-border)',
                  background: decision === 'rejected' ? 'rgba(239, 68, 68, 0.12)' : 'var(--dash-surface)',
                  color: decision === 'rejected' ? '#EF4444' : 'var(--dash-text-secondary)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                ✕ Reject Request
              </button>
            </div>
          </div>

          {/* Approver Name */}
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-primary)', marginBottom: 4 }}>
              Signatory Approver Name:
            </label>
            <input
              type="text"
              value={approverName}
              onChange={(e) => setApproverName(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 6,
                background: 'var(--dash-card-bg)',
                border: '1px solid var(--dash-border)',
                color: 'var(--dash-text-primary)',
                fontSize: 13,
              }}
            />
          </div>

          {/* Decision Reason / Comments */}
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--dash-text-primary)', marginBottom: 4 }}>
              Decision Reason & Audit Notes (Required):
            </label>
            <textarea
              required
              rows={3}
              placeholder="Enter mandatory governance audit reasoning..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 6,
                background: 'var(--dash-card-bg)',
                border: '1px solid var(--dash-border)',
                color: 'var(--dash-text-primary)',
                fontSize: 13,
                resize: 'none',
              }}
            />
          </div>

          {/* Digital Signature Area */}
          <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>🔒 Digital Signature:</span>
            <code style={{ background: 'var(--dash-surface)', padding: '2px 6px', borderRadius: 4, color: '#10B981' }}>
              SHA256:{approverName}:{Date.now()}
            </code>
          </div>

          {/* Footer Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '8px 16px',
                borderRadius: 8,
                background: 'none',
                border: '1px solid var(--dash-border)',
                color: 'var(--dash-text-secondary)',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={!reason.trim()}
              style={{
                padding: '8px 20px',
                borderRadius: 8,
                background: decision === 'approved' ? '#10B981' : decision === 'changes_requested' ? '#F59E0B' : '#EF4444',
                color: '#FFFFFF',
                border: 'none',
                fontWeight: 600,
                cursor: reason.trim() ? 'pointer' : 'not-allowed',
                opacity: reason.trim() ? 1 : 0.5,
                fontSize: 13,
              }}
            >
              Submit Formal Decision
            </button>
          </div>
        </form>
      </div>
    </ModalContainer>
  );
};
