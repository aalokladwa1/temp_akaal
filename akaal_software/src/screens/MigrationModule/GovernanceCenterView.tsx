import { useState, useEffect, type FC } from 'react';
import type { GovernanceApproval } from '../../types/migration';
import { approvalRepository } from '../../repositories/approvalRepository';
import { ApprovalModal } from '../../components/ApprovalModal/ApprovalModal';
import { EmptyState } from '../../components/EmptyState/EmptyState';

export interface GovernanceCenterViewProps {
  onBack: () => void;
}

export type GovernanceTabId =
  | 'pending'
  | 'my_approvals'
  | 'history'
  | 'delegated'
  | 'escalated'
  | 'expired'
  | 'policies';

export const GovernanceCenterView: FC<GovernanceCenterViewProps> = ({ onBack }) => {
  const [activeTab, setActiveTab] = useState<GovernanceTabId>('pending');
  const [approvals, setApprovals] = useState<GovernanceApproval[]>(() => approvalRepository.getApprovals());
  const [activeModalApproval, setActiveModalApproval] = useState<GovernanceApproval | null>(null);

  useEffect(() => {
    return approvalRepository.subscribe((updated) => setApprovals(updated));
  }, []);

  const pendingApprovals = approvals.filter((a) => a.status === 'pending');
  const approvalHistory = approvals.filter((a) => a.status !== 'pending');

  const handleDecision = (
    approvalId: string,
    decision: 'approved' | 'rejected' | 'changes_requested',
    reason: string
  ) => {
    approvalRepository.processDecision(approvalId, decision, 'Aalok', reason);
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--dash-bg)',
        overflow: 'hidden',
      }}
    >
      {/* Top Bar Header */}
      <div
        style={{
          padding: '14px 24px',
          background: 'var(--dash-topbar-bg)',
          borderBottom: '1px solid var(--dash-topbar-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button
            onClick={onBack}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--dash-text-secondary)',
              fontSize: 13,
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            ← Back to Migration Landing
          </button>
          <div style={{ width: 1, height: 18, background: 'var(--dash-border)' }} />
          <div>
            <h1 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--dash-text-primary)' }}>
              Governance Center & Multi-Custody Approval Matrix
            </h1>
            <div style={{ fontSize: 11, color: 'var(--dash-text-secondary)', marginTop: 2 }}>
              Four-Eyes Verification • Separation of Duties (SoD) • Audit Trail
            </div>
          </div>
        </div>

        <div style={{ fontSize: 12, fontWeight: 600, color: '#10B981', display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>🔒 Policy Enforcement Active</span>
        </div>
      </div>

      {/* Workspace Subnav Bar */}
      <div
        style={{
          padding: '0 24px',
          background: 'var(--dash-surface)',
          borderBottom: '1px solid var(--dash-border)',
          display: 'flex',
          gap: 16,
          flexShrink: 0,
        }}
      >
        {[
          { id: 'pending', label: `Pending Approvals (${pendingApprovals.length})` },
          { id: 'my_approvals', label: 'My Approvals' },
          { id: 'history', label: `Approval History (${approvalHistory.length})` },
          { id: 'delegated', label: 'Delegated Approvals' },
          { id: 'escalated', label: 'Escalated Approvals' },
          { id: 'expired', label: 'Expired Requests' },
          { id: 'policies', label: 'Governance Policies (Read-Only)' },
        ].map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as GovernanceTabId)}
              style={{
                padding: '12px 4px',
                border: 'none',
                borderBottom: isActive ? '2px solid #2563EB' : '2px solid transparent',
                background: 'none',
                color: isActive ? 'var(--dash-text-primary)' : 'var(--dash-text-secondary)',
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                transition: 'color 120ms ease, border-color 120ms ease',
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Workspace Body */}
      <div style={{ flex: 1, padding: 24, overflowY: 'auto' }}>
        {activeTab === 'pending' && (
          <div>
            {pendingApprovals.length === 0 ? (
              <EmptyState
                title="No Pending Approvals"
                description="There are currently no Four-Eyes governance approvals waiting for review. All workflow stages are executing normally."
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {pendingApprovals.map((appr) => (
                  <div
                    key={appr.id}
                    style={{
                      padding: 20,
                      background: 'var(--dash-card-bg)',
                      borderRadius: 12,
                      border: '1px solid var(--dash-border)',
                      boxShadow: 'var(--dash-card-shadow)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#F59E0B' }}>
                        {appr.gate} • Four-Eyes Verification Required
                      </span>
                      <span style={{ fontSize: 12, color: 'var(--dash-text-secondary)' }}>
                        Requested {new Date(appr.requestedAt).toLocaleTimeString()}
                      </span>
                    </div>

                    <h3 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 6px 0', color: 'var(--dash-text-primary)' }}>
                      {appr.gateTitle} — {appr.migrationName}
                    </h3>
                    <p style={{ fontSize: 13, color: 'var(--dash-text-secondary)', margin: '0 0 16px 0' }}>
                      {appr.summary}
                    </p>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--dash-border)', paddingTop: 14 }}>
                      <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)' }}>
                        Required Roles: <strong style={{ color: 'var(--dash-text-primary)' }}>{appr.requiredRoles.join(', ')}</strong>
                      </div>

                      <button
                        onClick={() => setActiveModalApproval(appr)}
                        style={{
                          padding: '8px 18px',
                          borderRadius: 8,
                          background: '#2563EB',
                          color: '#FFFFFF',
                          border: 'none',
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Review & Sign Off →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div>
            {approvalHistory.length === 0 ? (
              <EmptyState
                title="No Approval History"
                description="Past governance decisions, sign-offs, and rejection logs will be recorded here for compliance auditing."
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {approvalHistory.map((appr) => (
                  <div key={appr.id} style={{ padding: 16, background: 'var(--dash-card-bg)', borderRadius: 10, border: '1px solid var(--dash-border)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--dash-text-primary)' }}>{appr.gateTitle}</div>
                        <div style={{ fontSize: 12, color: 'var(--dash-text-secondary)', marginTop: 2 }}>
                          Decision: <strong style={{ color: appr.status === 'approved' ? '#10B981' : '#EF4444', textTransform: 'uppercase' }}>{appr.status}</strong> by {appr.approver}
                        </div>
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--dash-text-secondary)' }}>{appr.approvedAt ? new Date(appr.approvedAt).toLocaleString() : ''}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {['my_approvals', 'delegated', 'escalated', 'expired'].includes(activeTab) && (
          <EmptyState
            title={`No ${activeTab.replace('_', ' ').toUpperCase()}`}
            description={`No items in ${activeTab.replace('_', ' ')}. All governance policies are operating within nominal thresholds.`}
          />
        )}

        {activeTab === 'policies' && (
          <div style={{ padding: 20, background: 'var(--dash-card-bg)', borderRadius: 12, border: '1px solid var(--dash-border)' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px 0', color: 'var(--dash-text-primary)' }}>
              AKAAL Enterprise Governance Policy Matrix (Immutable)
            </h3>
            <ul style={{ fontSize: 13, color: 'var(--dash-text-secondary)', paddingLeft: 20, lineHeight: 1.6 }}>
              <li><strong>Four-Eyes Requirement:</strong> All schema modifications and bulk data transfers require 2 independent approvals.</li>
              <li><strong>Separation of Duties (SoD):</strong> Migration creators cannot approve their own migration requests.</li>
              <li><strong>Cryptographic Proof:</strong> All decisions generate SHA-256 digital signature hashes recorded in audit history.</li>
            </ul>
          </div>
        )}
      </div>

      {/* Reusable Approval Modal */}
      {activeModalApproval && (
        <ApprovalModal
          approval={activeModalApproval}
          isOpen={!!activeModalApproval}
          onClose={() => setActiveModalApproval(null)}
          onSubmitDecision={handleDecision}
        />
      )}
    </div>
  );
};
