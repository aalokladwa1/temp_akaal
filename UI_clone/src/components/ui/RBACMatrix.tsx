'use client';

import React, { useState } from 'react';

export type UserRole = 'Super Admin' | 'Platform Admin' | 'Migration Architect' | 'DBA' | 'Operator' | 'Auditor' | 'Read Only';

interface PermissionScope {
  category: string;
  permissions: {
    key: string;
    label: string;
    description: string;
    roles: Record<UserRole, boolean>;
  }[];
}

const DEFAULT_SCOPES: PermissionScope[] = [
  {
    category: 'Migration Operations',
    permissions: [
      { key: 'mig_create', label: 'Create Migration Workspace', description: 'Launch new migration wizard and schema mappings', roles: { 'Super Admin': true, 'Platform Admin': true, 'Migration Architect': true, DBA: true, Operator: false, Auditor: false, 'Read Only': false } },
      { key: 'mig_execute', label: 'Execute & Control Migrations', description: 'Pause, resume, retry, rollback live executions', roles: { 'Super Admin': true, 'Platform Admin': true, 'Migration Architect': true, DBA: true, Operator: true, Auditor: false, 'Read Only': false } },
      { key: 'mig_approve', label: 'Approve Production Deployments', description: 'Sign off on pre-flight checks and production cutovers', roles: { 'Super Admin': true, 'Platform Admin': true, 'Migration Architect': true, DBA: false, Operator: false, Auditor: false, 'Read Only': false } },
    ],
  },
  {
    category: 'Database Infrastructure',
    permissions: [
      { key: 'db_add', label: 'Connect Database Engines', description: 'Configure credentials, host endpoints and SSL certificates', roles: { 'Super Admin': true, 'Platform Admin': true, 'Migration Architect': true, DBA: true, Operator: false, Auditor: false, 'Read Only': false } },
      { key: 'db_credentials', label: 'View Decrypted Passwords', description: 'Decrypt connection secrets and private keys', roles: { 'Super Admin': true, 'Platform Admin': false, 'Migration Architect': false, DBA: true, Operator: false, Auditor: false, 'Read Only': false } },
    ],
  },
  {
    category: 'Governance & Security',
    permissions: [
      { key: 'rbac_manage', label: 'Manage RBAC & Team Roles', description: 'Assign roles, create custom permissions and invite users', roles: { 'Super Admin': true, 'Platform Admin': true, 'Migration Architect': false, DBA: false, Operator: false, Auditor: false, 'Read Only': false } },
      { key: 'audit_export', label: 'Export Audit Logs & Compliance Reports', description: 'Download SOC2, GDPR and PCI-DSS audit trails', roles: { 'Super Admin': true, 'Platform Admin': true, 'Migration Architect': false, DBA: false, Operator: false, Auditor: true, 'Read Only': false } },
    ],
  },
];

export function RBACMatrix() {
  const [selectedRole, setSelectedRole] = useState<UserRole>('Migration Architect');
  const [search, setSearch] = useState('');

  const roles: UserRole[] = ['Super Admin', 'Platform Admin', 'Migration Architect', 'DBA', 'Operator', 'Auditor', 'Read Only'];

  return (
    <div className="flex flex-col gap-4 p-5 rounded-lg border" style={{ background: 'var(--akaal-surface, #141E2E)', borderColor: 'var(--akaal-border, #2A3647)' }}>
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b" style={{ borderColor: 'var(--akaal-border, #2A3647)' }}>
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--akaal-text, #F8FAFC)', fontFamily: "'Inter', sans-serif" }}>
            Role-Based Access Control (RBAC) & Permission Matrix
          </h3>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted, #64748B)', fontFamily: "'Inter', sans-serif" }}>
            Manage enterprise role definitions, inherited permissions, and security scope enforcement.
          </p>
        </div>

        {/* Role Selector Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {roles.map(r => (
            <button
              key={r}
              type="button"
              onClick={() => setSelectedRole(r)}
              className="px-2.5 py-1 rounded text-xs transition-colors font-medium"
              style={{
                background: selectedRole === r ? 'var(--akaal-primary, #2563EB)' : 'transparent',
                color: selectedRole === r ? '#fff' : 'var(--akaal-text-muted, #94A3B8)',
                fontFamily: "'Inter', sans-serif",
                fontSize: '11px',
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Permission Matrix Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--akaal-border, #2A3647)', background: 'rgba(0,0,0,0.2)' }}>
              <th className="px-3 py-2 text-left font-semibold" style={{ color: 'var(--akaal-text-muted, #64748B)' }}>Permission Capability</th>
              <th className="px-3 py-2 text-left font-semibold" style={{ color: 'var(--akaal-text-muted, #64748B)' }}>Description</th>
              <th className="px-3 py-2 text-center font-semibold" style={{ color: 'var(--akaal-text, #F8FAFC)' }}>{selectedRole} Access</th>
            </tr>
          </thead>
          <tbody>
            {DEFAULT_SCOPES.map(scope => (
              <React.Fragment key={scope.category}>
                <tr style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <td colSpan={3} className="px-3 py-1.5 font-semibold text-[10px] uppercase tracking-wider text-sky-400" style={{ borderBottom: '1px solid var(--akaal-border, #2A3647)' }}>
                    {scope.category}
                  </td>
                </tr>
                {scope.permissions.map(perm => {
                  const hasAccess = perm.roles[selectedRole];
                  return (
                    <tr key={perm.key} className="border-b hover:bg-white/5 transition-colors" style={{ borderColor: 'var(--akaal-border, #2A3647)' }}>
                      <td className="px-3 py-2.5 font-medium" style={{ color: 'var(--akaal-text, #F8FAFC)' }}>
                        {perm.label}
                      </td>
                      <td className="px-3 py-2.5 text-xs" style={{ color: 'var(--akaal-text-muted, #94A3B8)' }}>
                        {perm.description}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold"
                          style={{
                            background: hasAccess ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            color: hasAccess ? '#22C55E' : '#EF4444',
                          }}
                        >
                          {hasAccess ? 'ALLOWED' : 'DENIED'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
