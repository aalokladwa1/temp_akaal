'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { GovernancePersistenceStore } from '@/security/governance/governancePersistenceStore';

interface UserItem {
  id: string;
  fullName: string;
  email: string;
  department: string;
  role: string;
  status: 'active' | 'invited' | 'suspended' | 'archived';
  mfa: boolean;
}

const INITIAL_USERS: UserItem[] = [
  { id: 'usr_1', fullName: 'Sarah Chen', email: 'sarah.chen@acme.com', department: 'Infrastructure Architecture', role: 'Super Administrator', status: 'active', mfa: true },
  { id: 'usr_2', fullName: 'David Miller', email: 'david.miller@acme.com', department: 'Database Migration Ops', role: 'Migration Engineer', status: 'active', mfa: true },
  { id: 'usr_3', fullName: 'Alex Rivera', email: 'alex.rivera@acme.com', department: 'Security & Compliance', role: 'Security Auditor', status: 'invited', mfa: false },
];

export default function UserGovernancePage() {
  const [users, setUsers] = useState<UserItem[]>(() => {
    return GovernancePersistenceStore.getItem('users', INITIAL_USERS);
  });

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Modals
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);

  // Form State
  const [formName, setFormName] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formDept, setFormDept] = useState('Database Migration Ops');
  const [formRole, setFormRole] = useState('Migration Engineer');

  useEffect(() => {
    GovernancePersistenceStore.setItem('users', users);
  }, [users]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleInviteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newUser: UserItem = {
      id: `usr_${Date.now()}`,
      fullName: formName,
      email: formEmail,
      department: formDept,
      role: formRole,
      status: 'invited',
      mfa: false,
    };
    setUsers(prev => [newUser, ...prev]);
    setShowInviteModal(false);
    showToast(`Invitation sent to ${formEmail}.`);
    setFormName(''); setFormEmail('');
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setUsers(prev => prev.map(u => u.id === editingUser.id ? {
      ...u,
      fullName: formName,
      email: formEmail,
      department: formDept,
      role: formRole,
    } : u));
    setEditingUser(null);
    showToast(`User ${formName} updated.`);
  };

  const handleArchiveRestore = (userId: string, currentStatus: string) => {
    setUsers(prev => prev.map(u => {
      if (u.id === userId) {
        const nextStatus: 'active' | 'archived' = currentStatus === 'archived' ? 'active' : 'archived';
        return {
          ...u, // Preserves all original properties immutably
          status: nextStatus,
        };
      }
      return u;
    }));
    showToast(currentStatus === 'archived' ? 'User account restored.' : 'User account archived.');
  };

  const handleResetPassword = (email: string) => {
    showToast(`Password reset link dispatched to ${email}.`);
  };

  const handleDelete = (userId: string, name: string) => {
    if (confirm(`Remove user account for "${name}"?`)) {
      setUsers(prev => prev.filter(u => u.id !== userId));
      showToast(`User ${name} removed.`);
    }
  };

  const filteredUsers = users.filter(u => {
    const matchSearch = !search || u.fullName.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()) || u.department.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || u.status === statusFilter;
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
            <Link href="/dashboard" className="hover:underline">Platform</Link> / Enterprise Governance / Users
          </nav>
          <h1 className="text-xl font-bold">Enterprise User & Group Administration</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>Manage enterprise accounts, active sessions, group assignments, and lifecycle status.</p>
        </div>
        <button
          type="button"
          onClick={() => { setFormName(''); setFormEmail(''); setShowInviteModal(true); }}
          className="px-3 py-1.5 rounded-md text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-all"
        >
          + Invite Enterprise User
        </button>
      </header>

      <main className="max-w-6xl mx-auto space-y-4">
        {/* Controls */}
        <div className="flex items-center gap-3 p-3 rounded-lg flex-wrap" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <input
            type="search"
            placeholder="Search users by name, email or department…"
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
            <option value="active">Active</option>
            <option value="invited">Invited</option>
            <option value="suspended">Suspended</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        {/* Directory Table */}
        <div className="rounded-lg p-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <h2 className="text-sm font-semibold mb-3">Managed User Directory ({filteredUsers.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs" aria-label="User administration directory">
              <thead>
                <tr style={{ background: 'var(--akaal-table-header)', borderBottom: '1px solid var(--akaal-border)' }}>
                  <th className="p-2.5">User</th>
                  <th className="p-2.5">Department</th>
                  <th className="p-2.5">Primary Role</th>
                  <th className="p-2.5">MFA</th>
                  <th className="p-2.5">Status</th>
                  <th className="p-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(u => (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--akaal-border-subtle)' }}>
                    <td className="p-2.5">
                      <p className="font-semibold">{u.fullName}</p>
                      <p className="font-mono text-gray-400" style={{ fontSize: '10px' }}>{u.email}</p>
                    </td>
                    <td className="p-2.5">{u.department}</td>
                    <td className="p-2.5 font-medium">{u.role}</td>
                    <td className="p-2.5">
                      <span className="px-1.5 py-0.5 rounded text-xs font-mono font-semibold" style={{ background: u.mfa ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)', color: u.mfa ? '#22C55E' : '#EF4444' }}>
                        {u.mfa ? 'ENFORCED' : 'OFF'}
                      </span>
                    </td>
                    <td className="p-2.5">
                      <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold"
                        style={{
                          background: u.status === 'active' ? 'rgba(34,197,94,0.15)' : u.status === 'invited' ? 'rgba(56,189,248,0.15)' : u.status === 'suspended' ? 'rgba(239,68,68,0.15)' : 'rgba(156,163,175,0.2)',
                          color: u.status === 'active' ? '#22C55E' : u.status === 'invited' ? '#38BDF8' : u.status === 'suspended' ? '#EF4444' : '#9CA3AF',
                        }}
                      >
                        {u.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="p-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => {
                            setEditingUser(u);
                            setFormName(u.fullName);
                            setFormEmail(u.email);
                            setFormDept(u.department);
                            setFormRole(u.role);
                          }}
                          className="px-2 py-1 rounded text-xs font-medium bg-gray-700 text-gray-200 hover:bg-gray-600"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleResetPassword(u.email)}
                          className="px-2 py-1 rounded text-xs font-medium bg-gray-700 text-gray-200 hover:bg-gray-600"
                        >
                          Reset Pass
                        </button>
                        <button
                          type="button"
                          onClick={() => handleArchiveRestore(u.id, u.status)}
                          className="px-2 py-1 rounded text-xs font-medium bg-gray-700 text-gray-200 hover:bg-gray-600"
                        >
                          {u.status === 'archived' ? 'Restore' : 'Archive'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(u.id, u.fullName)}
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

      {/* Invite/Edit Modal */}
      {(showInviteModal || editingUser) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="max-w-md w-full p-5 rounded-xl space-y-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
            <h2 className="text-base font-bold">{editingUser ? 'Edit User Profile' : 'Invite Enterprise User'}</h2>
            <form onSubmit={editingUser ? handleEditSubmit : handleInviteSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block mb-1 font-semibold">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Sarah Chen"
                  value={formName}
                  onChange={e => setFormName(e.target.value)}
                  className="w-full p-2 rounded border outline-none"
                  style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                />
              </div>
              <div>
                <label className="block mb-1 font-semibold">Corporate Email</label>
                <input
                  type="email"
                  required
                  placeholder="sarah.chen@acme.com"
                  value={formEmail}
                  onChange={e => setFormEmail(e.target.value)}
                  className="w-full p-2 rounded border outline-none font-mono"
                  style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block mb-1 font-semibold">Department</label>
                  <input
                    type="text"
                    value={formDept}
                    onChange={e => setFormDept(e.target.value)}
                    className="w-full p-2 rounded border outline-none"
                    style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                  />
                </div>
                <div>
                  <label className="block mb-1 font-semibold">Assigned Role</label>
                  <select
                    value={formRole}
                    onChange={e => setFormRole(e.target.value)}
                    className="w-full p-2 rounded border outline-none"
                    style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
                  >
                    <option value="Super Administrator">Super Administrator</option>
                    <option value="Migration Engineer">Migration Engineer</option>
                    <option value="Security Auditor">Security Auditor</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowInviteModal(false); setEditingUser(null); }}
                  className="px-3 py-1.5 rounded bg-gray-700 text-gray-200 font-medium hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 rounded bg-blue-600 text-white font-semibold hover:bg-blue-700"
                >
                  {editingUser ? 'Save Profile' : 'Send Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
