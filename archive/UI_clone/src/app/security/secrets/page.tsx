'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { SecretManager } from '@/security/secrets/secretManager';
import { SecretRotationEngine } from '@/security/secrets/secretRotationEngine';
import { SecretRecord, SecretType, SecretProviderType, SecretVersion } from '@/security/secrets/secretTypes';

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretRecord[]>([]);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [providerFilter, setProviderFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'updated' | 'name' | 'versions'>('updated');
  const [toast, setToast] = useState<string | null>(null);

  // Modals & Drawers
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRotateModal, setShowRotateModal] = useState<SecretRecord | null>(null);
  const [editingSecret, setEditingSecret] = useState<SecretRecord | null>(null);
  const [viewingSecret, setViewingSecret] = useState<SecretRecord | null>(null);

  // Create Form State
  const [name, setName] = useState('');
  const [type, setType] = useState<SecretType>('database_credential');
  const [provider, setProvider] = useState<SecretProviderType>('env');
  const [path, setPath] = useState('');
  const [value, setValue] = useState('');
  const [description, setDescription] = useState('');

  // Edit Form State
  const [editDesc, setEditDesc] = useState('');
  const [editExpiresAt, setEditExpiresAt] = useState('');

  // Rotate Form State
  const [newValue, setNewValue] = useState('');
  const [isEmergency, setIsEmergency] = useState(false);

  const reloadSecrets = () => {
    let list = SecretManager.list({
      search: search || undefined,
      type: typeFilter !== 'all' ? (typeFilter as SecretType) : undefined,
      provider: providerFilter !== 'all' ? (providerFilter as SecretProviderType) : undefined,
    });

    if (sortBy === 'name') {
      list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === 'versions') {
      list = [...list].sort((a, b) => b.versions.length - a.versions.length);
    } // default is 'updated'

    setSecrets(list);
  };

  useEffect(() => {
    reloadSecrets();
  }, [search, typeFilter, providerFilter, sortBy]);

  const showToastMsg = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await SecretManager.create({
        name,
        type,
        provider,
        providerPath: path || name.toUpperCase(),
        value,
        description,
      }, 'admin');
      showToastMsg(`Secret "${name}" created successfully.`);
      setShowCreateModal(false);
      setName(''); setValue(''); setPath(''); setDescription('');
      reloadSecrets();
    } catch (err: any) {
      showToastMsg(`Error: ${err.message}`);
    }
  };

  const handleEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSecret) return;
    try {
      SecretManager.update({
        id: editingSecret.id,
        description: editDesc,
        expiresAt: editExpiresAt || undefined,
      }, 'admin');
      showToastMsg(`Metadata for "${editingSecret.name}" updated.`);
      setEditingSecret(null);
      reloadSecrets();
    } catch (err: any) {
      showToastMsg(`Update failed: ${err.message}`);
    }
  };

  const handleRotate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showRotateModal) return;
    try {
      if (isEmergency) {
        await SecretRotationEngine.rotateEmergency(showRotateModal.id, newValue, 'admin');
        showToastMsg(`Emergency rotation completed for "${showRotateModal.name}".`);
      } else {
        await SecretRotationEngine.rotateManual(showRotateModal.id, newValue, 'admin');
        showToastMsg(`Secret "${showRotateModal.name}" rotated successfully.`);
      }
      setShowRotateModal(null);
      setNewValue('');
      reloadSecrets();
    } catch (err: any) {
      showToastMsg(`Rotation failed: ${err.message}`);
    }
  };

  const handleToggleStatus = (sec: SecretRecord) => {
    const newStatus = sec.status === 'active' ? 'inactive' : 'active';
    SecretManager.setStatus(sec.id, newStatus, 'admin');
    showToastMsg(`Secret "${sec.name}" is now ${newStatus}.`);
    reloadSecrets();
  };

  const handleRollback = async (secretId: string, versionId: string) => {
    if (confirm(`Are you sure you want to rollback to version ${versionId}?`)) {
      try {
        await SecretRotationEngine.rollback(secretId, versionId, 'admin');
        showToastMsg(`Rollback to version ${versionId} complete.`);
        if (viewingSecret) setViewingSecret(SecretManager.get(secretId));
        reloadSecrets();
      } catch (err: any) {
        showToastMsg(`Rollback failed: ${err.message}`);
      }
    }
  };

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Are you sure you want to delete secret "${name}"?`)) {
      SecretManager.delete(id, 'admin');
      showToastMsg(`Secret "${name}" deleted.`);
      reloadSecrets();
    }
  };

  return (
    <div className="min-h-screen p-6" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-6 flex items-center justify-between">
        <div>
          <nav className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)' }}>
            <Link href="/dashboard" className="hover:underline">Platform</Link> / <Link href="/security/secrets" className="hover:underline">Security</Link> / Secret Inventory
          </nav>
          <h1 className="text-2xl font-bold tracking-tight">Secrets Inventory</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>
            Enterprise multi-provider secret management, versioning, metadata editing, and zero-downtime rotation.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 text-sm font-medium rounded-md transition-opacity hover:opacity-90"
          style={{ background: 'var(--akaal-primary)', color: '#fff' }}
        >
          + Create Secret
        </button>
      </header>

      {toast && (
        <div className="max-w-7xl mx-auto mb-4 p-3 rounded text-sm bg-emerald-900/40 text-emerald-300 border border-emerald-700/50">
          {toast}
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto space-y-6">
        {/* Filters & Sorting */}
        <div className="p-4 rounded-lg flex flex-wrap items-center justify-between gap-4 border" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              placeholder="Search secrets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="px-3 py-1.5 text-sm rounded border bg-transparent"
              style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
            />

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-3 py-1.5 text-sm rounded border bg-transparent"
              style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
            >
              <option value="all">All Secret Types</option>
              <option value="database_credential">Database Credential</option>
              <option value="api_key">API Key</option>
              <option value="oauth_client_secret">OAuth Client Secret</option>
              <option value="jwt_signing_key">JWT Signing Key</option>
              <option value="tls_certificate">TLS Certificate</option>
            </select>

            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="px-3 py-1.5 text-sm rounded border bg-transparent"
              style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
            >
              <option value="all">All Providers</option>
              <option value="env">Environment Variables</option>
              <option value="vault">HashiCorp Vault</option>
              <option value="aws_secrets_manager">AWS Secrets Manager</option>
              <option value="azure_key_vault">Azure Key Vault</option>
              <option value="gcp_secret_manager">GCP Secret Manager</option>
              <option value="kubernetes">Kubernetes</option>
              <option value="docker">Docker</option>
              <option value="custom">Custom Provider</option>
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span style={{ color: 'var(--akaal-text-muted)' }}>Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-2 py-1 rounded border bg-transparent text-xs"
              style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
            >
              <option value="updated">Recently Updated</option>
              <option value="name">Name (A-Z)</option>
              <option value="versions">Version Count</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-lg border overflow-hidden" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase border-b" style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text-muted)' }}>
              <tr>
                <th className="p-4">Name / Path</th>
                <th className="p-4">Type</th>
                <th className="p-4">Provider</th>
                <th className="p-4">Version</th>
                <th className="p-4">Status</th>
                <th className="p-4">Last Rotated</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--akaal-border)' }}>
              {secrets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center" style={{ color: 'var(--akaal-text-muted)' }}>
                    No secrets found matching filters.
                  </td>
                </tr>
              ) : (
                secrets.map((sec) => (
                  <tr key={sec.id} className="hover:bg-white/5 transition-colors">
                    <td className="p-4">
                      <div className="font-semibold flex items-center gap-2">
                        {sec.name}
                        {sec.expiresAt && new Date(sec.expiresAt).getTime() < Date.now() + 30 * 864e5 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Expiring</span>
                        )}
                      </div>
                      <div className="text-xs font-mono" style={{ color: 'var(--akaal-text-muted)' }}>{sec.providerPath}</div>
                    </td>
                    <td className="p-4 text-xs font-mono">{sec.type}</td>
                    <td className="p-4 text-xs">
                      <span className="px-2 py-0.5 rounded border text-[11px]" style={{ borderColor: 'var(--akaal-border)' }}>
                        {sec.provider}
                      </span>
                    </td>
                    <td className="p-4 text-xs font-mono">
                      v{sec.versions.length} ({sec.currentVersionId})
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => handleToggleStatus(sec)}
                        title="Click to toggle Status"
                        className={`px-2 py-0.5 rounded-full text-[11px] font-semibold transition-opacity hover:opacity-80 ${
                          sec.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}
                      >
                        {sec.status}
                      </button>
                    </td>
                    <td className="p-4 text-xs text-muted">
                      {sec.lastRotatedAt ? new Date(sec.lastRotatedAt).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="p-4 text-right space-x-1.5">
                      <button
                        onClick={() => setViewingSecret(sec)}
                        className="px-2.5 py-1 text-xs rounded border hover:bg-white/10"
                        style={{ borderColor: 'var(--akaal-border)' }}
                      >
                        Details
                      </button>
                      <button
                        onClick={() => {
                          setEditingSecret(sec);
                          setEditDesc(sec.description);
                          setEditExpiresAt(sec.expiresAt ? sec.expiresAt.slice(0, 10) : '');
                        }}
                        className="px-2.5 py-1 text-xs rounded border hover:bg-white/10"
                        style={{ borderColor: 'var(--akaal-border)' }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setShowRotateModal(sec)}
                        className="px-2.5 py-1 text-xs rounded border hover:bg-white/10"
                        style={{ borderColor: 'var(--akaal-border)' }}
                      >
                        Rotate
                      </button>
                      <button
                        onClick={() => handleDelete(sec.id, sec.name)}
                        className="px-2 py-1 text-xs rounded border border-rose-500/50 text-rose-400 hover:bg-rose-500/10"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md p-6 rounded-lg border space-y-4" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-lg font-bold">Create New Secret</h2>
            <form onSubmit={handleCreate} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs mb-1">Secret Name</label>
                <input required type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
              </div>
              <div>
                <label className="block text-xs mb-1">Type</label>
                <select value={type} onChange={(e) => setType(e.target.value as any)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }}>
                  <option value="database_credential">Database Credential</option>
                  <option value="api_key">API Key</option>
                  <option value="oauth_client_secret">OAuth Client Secret</option>
                  <option value="jwt_signing_key">JWT Signing Key</option>
                  <option value="tls_certificate">TLS Certificate</option>
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1">Target Provider</label>
                <select value={provider} onChange={(e) => setProvider(e.target.value as any)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }}>
                  <option value="env">Environment Variables</option>
                  <option value="vault">HashiCorp Vault</option>
                  <option value="aws_secrets_manager">AWS Secrets Manager</option>
                  <option value="azure_key_vault">Azure Key Vault</option>
                  <option value="gcp_secret_manager">GCP Secret Manager</option>
                  <option value="kubernetes">Kubernetes</option>
                  <option value="docker">Docker</option>
                  <option value="custom">Custom Provider</option>
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1">Provider Path / Key</label>
                <input type="text" placeholder="e.g. DB_SECRET_PROD" value={path} onChange={(e) => setPath(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
              </div>
              <div>
                <label className="block text-xs mb-1">Secret Value</label>
                <textarea required rows={3} value={value} onChange={(e) => setValue(e.target.value)} className="w-full p-2 rounded border bg-transparent font-mono text-xs" style={{ borderColor: 'var(--akaal-border)' }} />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-3 py-1.5 rounded border text-xs" style={{ borderColor: 'var(--akaal-border)' }}>Cancel</button>
                <button type="submit" className="px-3 py-1.5 rounded text-xs font-semibold" style={{ background: 'var(--akaal-primary)', color: '#fff' }}>Save Secret</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Metadata Modal */}
      {editingSecret && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md p-6 rounded-lg border space-y-4" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-lg font-bold">Edit Secret Metadata: {editingSecret.name}</h2>
            <form onSubmit={handleEdit} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs mb-1">Description</label>
                <textarea rows={2} value={editDesc} onChange={(e) => setEditDesc(e.target.value)} className="w-full p-2 rounded border bg-transparent text-xs" style={{ borderColor: 'var(--akaal-border)' }} />
              </div>
              <div>
                <label className="block text-xs mb-1">Expiration Date (YYYY-MM-DD)</label>
                <input type="date" value={editExpiresAt} onChange={(e) => setEditExpiresAt(e.target.value)} className="w-full p-2 rounded border bg-transparent text-xs" style={{ borderColor: 'var(--akaal-border)' }} />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditingSecret(null)} className="px-3 py-1.5 rounded border text-xs" style={{ borderColor: 'var(--akaal-border)' }}>Cancel</button>
                <button type="submit" className="px-3 py-1.5 rounded text-xs font-semibold" style={{ background: 'var(--akaal-primary)', color: '#fff' }}>Save Metadata</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Details & Version History Drawer */}
      {viewingSecret && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-end p-4 z-50">
          <div className="w-full max-w-lg h-full p-6 rounded-lg border overflow-y-auto space-y-6" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--akaal-border)' }}>
              <div>
                <h2 className="text-lg font-bold">{viewingSecret.name}</h2>
                <div className="text-xs font-mono text-muted">{viewingSecret.id}</div>
              </div>
              <button onClick={() => setViewingSecret(null)} className="px-2.5 py-1 text-xs rounded border" style={{ borderColor: 'var(--akaal-border)' }}>Close</button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div><span className="text-muted block">Provider:</span> <span className="font-mono font-semibold">{viewingSecret.provider}</span></div>
                <div><span className="text-muted block">Path:</span> <span className="font-mono">{viewingSecret.providerPath}</span></div>
                <div><span className="text-muted block">Type:</span> <span>{viewingSecret.type}</span></div>
                <div><span className="text-muted block">Status:</span> <span className="capitalize font-semibold">{viewingSecret.status}</span></div>
                <div><span className="text-muted block">Owner:</span> <span>{viewingSecret.owner}</span></div>
                <div><span className="text-muted block">Created:</span> <span>{new Date(viewingSecret.createdAt).toLocaleDateString()}</span></div>
              </div>
              {viewingSecret.description && (
                <div><span className="text-muted block">Description:</span> <p className="mt-1">{viewingSecret.description}</p></div>
              )}
            </div>

            {/* Version History */}
            <div className="space-y-3 pt-4 border-t" style={{ borderColor: 'var(--akaal-border)' }}>
              <h3 className="text-sm font-bold">Version History ({viewingSecret.versions.length})</h3>
              <div className="space-y-2">
                {viewingSecret.versions.map((ver: SecretVersion) => (
                  <div key={ver.versionId} className="p-3 rounded border space-y-1" style={{ borderColor: 'var(--akaal-border)', background: ver.isActive ? 'rgba(16, 185, 129, 0.1)' : 'transparent' }}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold font-mono">v{ver.versionNumber} ({ver.versionId})</span>
                      {ver.isActive ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold">Active</span>
                      ) : (
                        <button
                          onClick={() => handleRollback(viewingSecret.id, ver.versionId)}
                          className="px-2 py-0.5 rounded text-[10px] border border-amber-500/50 text-amber-300 hover:bg-amber-500/10"
                        >
                          Rollback to this
                        </button>
                      )}
                    </div>
                    <div className="text-[11px] text-muted flex justify-between">
                      <span>Created by: {ver.createdBy}</span>
                      <span>{new Date(ver.createdAt).toLocaleString()}</span>
                    </div>
                    <div className="text-[10px] font-mono text-muted truncate">Checksum: {ver.checksum}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rotate Modal */}
      {showRotateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md p-6 rounded-lg border space-y-4" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-lg font-bold">Rotate Secret: {showRotateModal.name}</h2>
            <form onSubmit={handleRotate} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs mb-1">New Secret Value</label>
                <textarea required rows={3} value={newValue} onChange={(e) => setNewValue(e.target.value)} className="w-full p-2 rounded border bg-transparent font-mono text-xs" style={{ borderColor: 'var(--akaal-border)' }} />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="emergency" checked={isEmergency} onChange={(e) => setIsEmergency(e.target.checked)} />
                <label htmlFor="emergency" className="text-xs text-rose-400 font-medium">Emergency Rotation (Bypass Grace Period)</label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowRotateModal(null)} className="px-3 py-1.5 rounded border text-xs" style={{ borderColor: 'var(--akaal-border)' }}>Cancel</button>
                <button type="submit" className="px-3 py-1.5 rounded text-xs font-semibold bg-emerald-600 text-white">Rotate Secret</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
