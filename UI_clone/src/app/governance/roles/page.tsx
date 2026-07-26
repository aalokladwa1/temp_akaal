'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { GovernancePersistenceStore } from '@/security/governance/governancePersistenceStore';

interface RoleCatalogItem {
  id: string;
  name: string;
  scope: 'Global' | 'Tenant' | 'Organization' | 'Project';
  permissionCount: number;
  assignedUsers: number;
  isTemplate: boolean;
}

const INITIAL_ROLES: RoleCatalogItem[] = [
  { id: 'super_admin', name: 'Super Administrator', scope: 'Global', permissionCount: 48, assignedUsers: 2, isTemplate: true },
  { id: 'migration_engineer', name: 'Migration Engineer', scope: 'Project', permissionCount: 16, assignedUsers: 14, isTemplate: true },
  { id: 'sec_auditor', name: 'Security Auditor', scope: 'Tenant', permissionCount: 8, assignedUsers: 5, isTemplate: true },
  { id: 'custom_sec_lead', name: 'SecOps Team Lead', scope: 'Organization', permissionCount: 12, assignedUsers: 3, isTemplate: false },
];

export default function RoleGovernancePage() {
  const [roles, setRoles] = useState<RoleCatalogItem[]>(() => {
    return GovernancePersistenceStore.getItem('roles', INITIAL_ROLES);
  });

  const [search, setSearch] = useState('');
  const [scopeFilter, setScopeFilter] = useState('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleCatalogItem | null>(null);

  // Form State
  const [formName, setFormName] = useState('');
  const [formScope, setFormScope] = useState<'Global' | 'Tenant' | 'Organization' | 'Project'>('Organization');
  const [formPerms, setFormPerms] = useState(10);

  useEffect(() => {
    GovernancePersistenceStore.setItem('roles', roles);
  }, [roles]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newRole: RoleCatalogItem = {
      id: `role_${Date.now()}`,
      name: formName,
      scope: formScope,
      permissionCount: formPerms,
      assignedUsers: 0,
      isTemplate: false,
    };
    setRoles(prev => [newRole, ...prev]);
    setShowCreateModal(false);
    showToast(`Role "${formName}" created successfully.`);
    setFormName('');
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRole) return;
    setRoles(prev => prev.map(r => r.id === editingRole.id ? {
      ...r,
      name: formName,
      scope: formScope,
      permissionCount: formPerms,
    } : r));
    setEditingRole(null);
    showToast(`Role "${formName}" updated.`);
  };

  const handleCloneRole = (role: RoleCatalogItem) => {
    const cloned: RoleCatalogItem = {
      ...role,
      id: `role_clone_${Date.now()}`,
      name: `${role.name} (Copy)`,
      isTemplate: false,
      assignedUsers: 0,
    };
    setRoles(prev => [cloned, ...prev]);
    showToast(`Role "${role.name}" cloned.`);
  };

  const handleDeleteRole = (id: string, name: string) => {
    if (confirm(`Delete role "${name}"?`)) {
      setRoles(prev => prev.filter(r => r.id !== id));
      showToast(`Role "${name}" deleted.`);
    }
  };

  const filteredRoles = roles.filter(r => {
    const matchSearch = !search || r.name.toLowerCase().includes(search.toLowerCase()) || r.scope.toLowerCase().includes(search.toLowerCase());
    const matchScope = scopeFilter === 'all' || r.scope === scopeFilter;
    return matchSearch && matchScope;
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
            <Link href="/dashboard" className="hover:underline">Platform</Link> / Enterprise Governance / Roles & Permissions
          </nav>
          <h1 className="text-xl font-bold">Role & Permission Catalog Console</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>Configure custom RBAC roles, permission scopes, role templates, and inheritance hierarchies.</p>
        </div>
        <button
          type="button"
          onClick={() => { setFormName(''); setShowCreateModal(true); }}
          className="px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-all"
        >
          + Create Custom Role
        </button>
      </header>

      <main className="max-w-6xl mx-auto space-y-4">
        {/* Controls */}
        <div className="flex items-center gap-3 p-3 rounded-lg flex-wrap" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <input
            type="search"
            placeholder="Search roles by name or scope…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="text-xs px-3 py-1.5 rounded border outline-none min-w-[240px]"
            style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          />
          <select
            value={scopeFilter}
            onChange={e => setScopeFilter(e.target.value)}
            className="text-xs px-2.5 py-1.5 rounded border outline-none"
            style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
          >
            <option value="all">All Scopes</option>
            <option value="Global">Global</option>
            <option value="Tenant">Tenant</option>
            <option value="Organization">Organization</option>
            <option value="Project">Project</option>
          </select>
        </div>

        {/* Directory Table */}
        <div className="rounded-lg p-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <h2 className="text-sm font-semibold mb-3">Enterprise Roles ({filteredRoles.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs" aria-label="Role catalog">
              <thead>
                <tr style={{ background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-border)' }}>
                  <th className="p-2.5">Role Name</th>
                  <th className="p-2.5">Scope</th>
                  <th className="p-2.5">Permissions</th>
                  <th className="p-2.5">Assigned Users</th>
                  <th className="p-2.5">Type</th>
                  <th className="p-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRoles.map(r => (
                  <tr key={r.id} style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                    <td className="p-2.5 font-semibold">{r.name}</td>
                    <td className="p-2.5 font-mono">{r.scope}</td>
                    <td className="p-2.5">{r.permissionCount} permissions</td>
                    <td className="p-2.5">{r.assignedUsers} users</td>
                    <td className="p-2.5">
                      <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold"
                        style={{
                          background: r.isTemplate ? 'rgba(56,189,248,0.15)' : 'rgba(167,139,250,0.15)',
                          color: r.isTemplate ? '#38BDF8' : '#A78BFA',
                        }}
                      >
                        {r.isTemplate ? 'TEMPLATE' : 'CUSTOM'}
                      </span>
                    </td>
                    <td className="p-2.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => {
                            setEditingRole(r);
                            setFormName(r.name);
                            setFormScope(r.scope);
                            setFormPerms(r.permissionCount);
                          }}
                          className="px-2 py-1 rounded text-xs font-medium bg-gray-700 text-gray-200 hover:bg-gray-600"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCloneRole(r)}
                          className="px-2 py-1 rounded text-xs font-medium bg-gray-700 text-gray-200 hover:bg-gray-600"
                        >
                          Clone
                        </button>
                        {!r.isTemplate && (
                          <button
                            type="button"
                            onClick={() => handleDeleteRole(r.id, r.name)}
                            className="px-2 py-1 rounded text-xs font-medium bg-red-900/40 text-red-400 hover:bg-red-900/60"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingRole) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="max-w-md w-full p-5 rounded-xl space-y-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
            <h2 className="text-base font-bold">{editingRole ? 'Edit Custom Role' : 'Create Custom Role'}</h2>
            <form onSubmit={editingRole ? handleEditSubmit : handleCreateSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block mb-1 font-semibold">Role Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. SecOps Team Lead"
                  value={formName}
                  onChange={e => setFormName(e.target.value)}
                  className="w-full p-2 rounded border outline-none"
                  style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block mb-1 font-semibold">Role Scope</label>
                  <select
                    value={formScope}
                    onChange={e => setFormScope(e.target.value as any)}
                    className="w-full p-2 rounded border outline-none"
                    style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                  >
                    <option value="Global">Global</option>
                    <option value="Tenant">Tenant</option>
                    <option value="Organization">Organization</option>
                    <option value="Project">Project</option>
                  </select>
                </div>
                <div>
                  <label className="block mb-1 font-semibold">Permissions Count</label>
                  <input
                    type="number"
                    value={formPerms}
                    onChange={e => setFormPerms(Number(e.target.value))}
                    className="w-full p-2 rounded border outline-none font-mono"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowCreateModal(false); setEditingRole(null); }}
                  className="px-3 py-1.5 rounded bg-gray-700 text-gray-200 font-medium hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 rounded bg-blue-600 text-white font-semibold hover:bg-blue-700"
                >
                  {editingRole ? 'Save Role' : 'Create Role'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
