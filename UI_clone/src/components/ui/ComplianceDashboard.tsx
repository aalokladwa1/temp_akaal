'use client';

import React from 'react';

export interface ComplianceFramework {
  name: string;
  code: 'SOC2' | 'GDPR' | 'HIPAA' | 'PCI-DSS' | 'ISO27001';
  score: number;
  status: 'Compliant' | 'Action Required' | 'Auditing';
  controlsPassed: number;
  totalControls: number;
  lastAudit: string;
}

const FRAMEWORKS: ComplianceFramework[] = [
  { name: 'SOC 2 Type II Security & Confidentiality', code: 'SOC2', score: 98, status: 'Compliant', controlsPassed: 49, totalControls: 50, lastAudit: '2026-06-15' },
  { name: 'General Data Protection Regulation', code: 'GDPR', score: 95, status: 'Compliant', controlsPassed: 38, totalControls: 40, lastAudit: '2026-07-01' },
  { name: 'Health Insurance Portability and Accountability Act', code: 'HIPAA', score: 100, status: 'Compliant', controlsPassed: 32, totalControls: 32, lastAudit: '2026-05-20' },
  { name: 'Payment Card Industry Data Security Standard', code: 'PCI-DSS', score: 92, status: 'Action Required', controlsPassed: 23, totalControls: 25, lastAudit: '2026-07-10' },
  { name: 'ISO/IEC 27001 Information Security', code: 'ISO27001', score: 96, status: 'Compliant', controlsPassed: 114, totalControls: 118, lastAudit: '2026-04-12' },
];

export function ComplianceDashboard() {
  return (
    <div className="flex flex-col gap-4 p-5 rounded-lg border" style={{ background: 'var(--akaal-surface, #141E2E)', borderColor: 'var(--akaal-border, #2A3647)' }}>
      <div className="flex items-center justify-between pb-4 border-b" style={{ borderColor: 'var(--akaal-border, #2A3647)' }}>
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
            Enterprise Governance & Compliance Security Suite
          </h3>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
            Automated compliance auditing for database encryption, audit trails, and data masking controls.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold px-2.5 py-1 rounded font-mono" style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#22C55E' }}>
            OVERALL COMPLIANCE SCORE: 96.2%
          </span>
        </div>
      </div>

      {/* Grid of Frameworks */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {FRAMEWORKS.map(fw => (
          <div key={fw.code} className="p-3.5 rounded border space-y-2.5" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'var(--akaal-border, #2A3647)' }}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(37,99,235,0.15)', color: '#38BDF8' }}>
                {fw.code}
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded"
                style={{
                  background: fw.status === 'Compliant' ? 'rgba(34,197,94,0.15)' : 'rgba(245,158,11,0.15)',
                  color: fw.status === 'Compliant' ? '#22C55E' : '#F59E0B',
                }}
              >
                {fw.status}
              </span>
            </div>

            <h4 className="text-xs font-semibold" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
              {fw.name}
            </h4>

            {/* Score Bar */}
            <div>
              <div className="flex justify-between text-[11px] font-mono mb-1" style={{ color: 'var(--akaal-text-muted, #94A3B8)' }}>
                <span>{fw.controlsPassed}/{fw.totalControls} Controls</span>
                <span className="text-emerald-400 font-bold">{fw.score}%</span>
              </div>
              <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)' }}>
                <div className="h-full rounded-full bg-emerald-400 transition-all duration-300" style={{ width: `${fw.score}%` }} />
              </div>
            </div>

            <p className="text-[10px] font-mono text-right" style={{ color: 'var(--akaal-text-muted, #64748B)' }}>
              Last Audited: {fw.lastAudit}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
