'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { GovernancePersistenceStore } from '@/security/governance/governancePersistenceStore';

interface TenantRecord {
  id: string;
  name: string;
  code: string;
  region: string;
  status: 'active' | 'suspended' | 'archived';
  orgCount: number;
  usersCount: number;
  maxUsers: number;
  securityPolicy: string;
}

const INITIAL_TENANTS: TenantRecord[] = [
  { id: 'tenant_prod_us_east', name: 'Acme Financial Systems', code: 'ACME-FIN', region: 'us-east-1', status: 'active', orgCount: 4, usersCount: 1420, maxUsers: 5000, securityPolicy: 'SOC2-Strict' },
  { id: 'tenant_prod_eu_west', name: 'Global Logistics GmbH', code: 'LOG-EU', region: 'eu-west-1', status: 'active', orgCount: 2, usersCount: 680, maxUsers: 2000, securityPolicy: 'GDPR-Enforced' },
  { id: 'tenant_stg_us_west', name: 'HealthCare Direct', code: 'HCD-US', region: 'us-west-2', status: 'suspended', orgCount: 1, usersCount: 95, maxUsers: 500, securityPolicy: 'HIPAA-Compliant' },
];

export default function TenantGovernancePage() {
  const [tenants, setTenants] = useState<TenantRecord[]>(() => {
    return GovernancePersistenceStore.getItem('tenants', INITIAL_TENANTS);
  });

  const [search, setSearch] = useState('');
  const [regionFilter, setRegionFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTenant, setEditingTenant] = useState<TenantRecord | null>(null);

  // Form State
  const [formName, setFormName] = useState('');
  const [formCode, setFormCode] = useState('');
  const [formRegion, setFormRegion] = useState('us-east-1');
  const [formPolicy, setFormPolicy] = useState('SOC2-Strict');
  const [formMaxUsers, setFormMaxUsers] = useState(1000);

  useEffect(() => {
    GovernancePersistenceStore.setItem('tenants', tenants);
  }, [tenants]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newTenant: TenantRecord = {
      id: `tenant_${Date.now()}`,
      name: formName,
      code: formCode.toUpperCase(),
      region: formRegion,
      status: 'active',
      orgCount: 1,
      usersCount: 1,
      maxUsers: formMaxUsers,
      securityPolicy: formPolicy,
    };
    setTenants(prev => [newTenant, ...prev]);
    setShowCreateModal(false);
    showToast(`Tenant "${formName}" provisioned successfully.`);
    setFormName(''); setFormCode('');
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTenant) return;
    setTenants(prev => prev.map(t => t.id === editingTenant.id ? {
      ...t,
      name: formName,
      code: formCode.toUpperCase(),
      region: formRegion,
      securityPolicy: formPolicy,
      maxUsers: formMaxUsers,
    } : t));
    setEditingTenant(null);
    showToast(`Tenant "${formName}" updated successfully.`);
  };

  const handleArchiveRestore = (id: string, currentStatus: 'active' | 'suspended' | 'archived') => {
    setTenants(prev => prev.map(t => {
      if (t.id === id) {
        const nextStatus: 'active' | 'archived' = currentStatus === 'archived' ? 'active' : 'archived';
        return {
          ...t, // Immutable copy preserving all original fields
          status: nextStatus,
        };
      }
      return t;
    }));
    showToast(currentStatus === 'archived' ? 'Tenant restored to active state.' : 'Tenant archived.');
  };

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Are you sure you want to delete tenant "${name}"? This action cannot be undone.`)) {
      setTenants(prev => prev.filter(t => t.id !== id));
      showToast(`Tenant "${name}" deleted.`);
    }
  };

  const filteredTenants = tenants.filter(t => {
    const matchSearch = !search || t.name.toLowerCase().includes(search.toLowerCase()) || t.code.toLowerCase().includes(search.toLowerCase());
    const matchRegion = regionFilter === 'all' || t.region === regionFilter;
    const matchStatus = statusFilter === 'all' || t.status === statusFilter;
    return matchSearch && matchRegion && matchStatus;
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
            <Link href="/dashboard" className="hover:underline">Platform</Link> / Enterprise Governance / Tenants
          </nav>
          <h1 className="text-xl font-bold">Multi-Tenant Governance Console</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>Manage tenant isolation, regions, security policies, and user quotas.</p>
        </div>
        <button
          type="button"
          onClick={() => { setFormName(''); setFormCode(''); setShowCreateModal(true); }}
          className="px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-all"
        >
          + Provision Tenant
        </button>
      </header>

      <main className="max-w-6xl mx-auto space-y-4">
        {/* Controls */}
        <div className="flex items-center gap-3 p-3 rounded-lg flex-wrap" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <input
            type="search"
            placeholder="Search tenants by name or code…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="text-xs px-3 py-1.5 rounded border outline-none min-w-[240px]"
            style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          />
          <select
            value={regionFilter}
            onChange={e => setRegionFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded border outline-none"
            style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          >
            <option value="all">All Regions</option>
            <option value="us-east-1">us-east-1</option>
            <option value="us-west-2">us-west-2</option>
            <option value="eu-west-1">eu-west-1</option>
          </select>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded border outline-none"
            style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        {/* Directory Table */}
        <div className="rounded-lg p-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <h2 className="text-sm font-semibold mb-3">Provisioned Enterprise Tenants ({filteredTenants.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs" aria-label="Tenant directory">
              <thead>
                <tr style={{ background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-border)' }}>
                  <th className="p-2.5">Tenant Name</th>
                  <th className="p-2.5">Code</th>
                  <th className="p-2.5">Region</th>
                  <th className="p-2.5">Organizations</th>
                  <th className="p-2.5">User Quota</th>
                  <th className="p-2.5">Security Policy</th>
                  <th className="p-2.5">Status</th>
                  <th className="p-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredTenants.map(t => (
                  <tr key={t.id} style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                    <td className="p-2.5 font-semibold">{t.name}</td>
                    <td className="p-2.5 font-mono" style={{ color: 'var(--akaal-primary)' }}>{t.code}</td>
                    <td className="p-2.5 font-mono">{t.region}</td>
                    <td className="p-2.5">{t.orgCount} orgs</td>
                    <td className="p-2.5 font-mono">{t.usersCount.toLocaleString()} / {t.maxUsers.toLocaleString()}</td>
                    <td className="p-2.5 font-mono text-gray-400">{t.securityPolicy}</td>
                    <td className="p-2.5">
                      <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold"
                        style={{
                          background: t.status === 'active' ? 'rgba(34,197,94,0.15)' : t.status === 'suspended' ? 'rgba(239,68,68,0.15)' : 'rgba(156,163,175,0.2)',
                          color: t.status === 'active' ? '#22C55E' : t.status === 'suspended' ? '#EF4444' : '#9CA3AF',
                        }}
                      >
                        {t.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="p-2.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => {
                            setEditingTenant(t);
                            setFormName(t.name);
                            setFormCode(t.code);
                            setFormRegion(t.region);
                            setFormPolicy(t.securityPolicy);
                            setFormMaxUsers(t.maxUsers);
                          }}
                          className="px-2 py-1 rounded text-xs font-medium bg-gray-700 text-gray-200 hover:bg-gray-600"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleArchiveRestore(t.id, t.status)}
                          className="px-2 py-1 rounded text-xs font-medium bg-gray-700 text-gray-200 hover:bg-gray-600"
                        >
                          {t.status === 'archived' ? 'Restore' : 'Archive'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(t.id, t.name)}
                          className="px-2 py-1 rounded text-xs font-medium bg-red-900/40 text-red-400 hover:bg-red-900/60"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Provision / Edit Tenant Modal */}
      {(showCreateModal || editingTenant) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="max-w-md w-full p-5 rounded-xl space-y-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
            <h2 className="text-base font-bold">{editingTenant ? 'Edit Tenant' : 'Provision Enterprise Tenant'}</h2>
            <form onSubmit={editingTenant ? handleEditSubmit : handleCreateSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block mb-1 font-semibold">Tenant Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Financial Systems"
                  value={formName}
                  onChange={e => setFormName(e.target.value)}
                  className="w-full p-2 rounded border outline-none"
                  style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                />
              </div>
              <div>
                <label className="block mb-1 font-semibold">Tenant Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ACME-FIN"
                  value={formCode}
                  onChange={e => setFormCode(e.target.value)}
                  className="w-full p-2 rounded border outline-none font-mono"
                  style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block mb-1 font-semibold">Primary Region</label>
                  <select
                    value={formRegion}
                    onChange={e => setFormRegion(e.target.value)}
                    className="w-full p-2 rounded border outline-none"
                    style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                  >
                    <option value="us-east-1">us-east-1</option>
                    <option value="us-west-2">us-west-2</option>
                    <option value="eu-west-1">eu-west-1</option>
                  </select>
                </div>
                <div>
                  <label className="block mb-1 font-semibold">User Quota</label>
                  <input
                    type="number"
                    value={formMaxUsers}
                    onChange={e => setFormMaxUsers(Number(e.target.value))}
                    className="w-full p-2 rounded border outline-none font-mono"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowCreateModal(false); setEditingTenant(null); }}
                  className="px-3 py-1.5 rounded bg-gray-700 text-gray-200 font-medium hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 rounded bg-blue-600 text-white font-semibold hover:bg-blue-700"
                >
                  {editingTenant ? 'Save Changes' : 'Provision Tenant'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
