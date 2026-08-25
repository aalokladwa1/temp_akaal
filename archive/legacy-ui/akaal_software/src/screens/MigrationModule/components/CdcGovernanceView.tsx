import React from 'react';

interface CdcGovernanceViewProps {
  migrationId: string;
  isHistorical?: boolean;
}

export const CdcGovernanceView: React.FC<CdcGovernanceViewProps> = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ background: 'var(--dash-card-bg)', padding: '16px 20px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>
          Governance, Policy & Approvals Registry
        </div>
        <div style={{ fontSize: '13px', color: 'var(--dash-text-secondary)', marginTop: '4px' }}>
          Cryptographically signed operator approvals • PolicyEngine binding • Audit trail integration
        </div>
      </div>

      <div style={{ background: 'var(--dash-card-bg)', padding: '20px', borderRadius: '8px', border: '1px solid var(--dash-border)' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Required Approval Gates</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {[
            { title: 'Final Cutover Commit Approval', status: 'GRANTED', approver: 'operator@enterprise.internal', token: 'appr-cutover-p310' },
            { title: 'Validation Exception Bypass Gate', status: 'ENFORCED', approver: 'N/A', token: 'N/A' },
            { title: 'Destructive Remediation Override Gate', status: 'ENFORCED', approver: 'N/A', token: 'N/A' },
            { title: 'Post-Cutover Failback Authorization', status: 'PENDING_REQUEST', approver: 'N/A', token: 'N/A' },
          ].map((item, idx) => (
            <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid var(--dash-border)' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--dash-text-primary)' }}>{item.title}</div>
                <div style={{ fontSize: '12px', color: 'var(--dash-text-secondary)' }}>Approver: {item.approver} • Token: {item.token}</div>
              </div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: item.status === 'GRANTED' ? '#22c55e' : '#eab308' }}>
                {item.status}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
