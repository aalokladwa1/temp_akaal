'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { KeyManagementService } from '@/security/keys/keyManagementService';
import { KeyRecord, KeyAlgorithm, KeyPurpose } from '@/security/keys/keyTypes';

export default function KeysPage() {
  const [keys, setKeys] = useState<KeyRecord[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [viewingKey, setViewingKey] = useState<KeyRecord | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [algorithm, setAlgorithm] = useState<KeyAlgorithm>('AES-256-GCM');
  const [purpose, setPurpose] = useState<KeyPurpose>('encryption');

  const reloadKeys = () => {
    setKeys(KeyManagementService.list());
  };

  useEffect(() => {
    reloadKeys();
  }, []);

  const showToastMsg = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await KeyManagementService.create({ name, description, algorithm, purpose }, 'admin');
      showToastMsg(`Key "${name}" generated successfully.`);
      setShowCreateModal(false);
      setName(''); setDescription('');
      reloadKeys();
    } catch (err: any) {
      showToastMsg(`Key creation failed: ${err.message}`);
    }
  };

  const handleRotate = async (id: string, name: string) => {
    try {
      await KeyManagementService.rotate(id, 'admin');
      showToastMsg(`Key "${name}" rotated successfully.`);
      reloadKeys();
    } catch (err: any) {
      showToastMsg(`Rotation failed: ${err.message}`);
    }
  };

  const handleRevoke = (id: string, name: string) => {
    const reason = prompt(`Enter revocation reason for key "${name}":`);
    if (reason) {
      KeyManagementService.revoke(id, reason, 'admin');
      showToastMsg(`Key "${name}" revoked.`);
      reloadKeys();
    }
  };

  return (
    <div className="min-h-screen p-6" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      <header className="max-w-7xl mx-auto mb-6 flex items-center justify-between">
        <div>
          <nav className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)' }}>
            <Link href="/dashboard" className="hover:underline">Platform</Link> / <Link href="/security/secrets" className="hover:underline">Security</Link> / Key Management
          </nav>
          <h1 className="text-2xl font-bold tracking-tight">Key Management Catalog</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>
            Centralized cryptographic key lifecycle: creation, rotation, versioning, metadata, and revocation.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 text-sm font-medium rounded-md transition-opacity hover:opacity-90"
          style={{ background: 'var(--akaal-primary)', color: '#fff' }}
        >
          + Generate Key
        </button>
      </header>

      {toast && (
        <div className="max-w-7xl mx-auto mb-4 p-3 rounded text-sm bg-emerald-900/40 text-emerald-300 border border-emerald-700/50">
          {toast}
        </div>
      )}

      <main className="max-w-7xl mx-auto space-y-6">
        <div className="rounded-lg border overflow-hidden" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase border-b" style={{ borderColor: 'var(--akaal-border)', color: 'var(--akaal-text-muted)' }}>
              <tr>
                <th className="p-4">Key Name</th>
                <th className="p-4">Algorithm</th>
                <th className="p-4">Purpose</th>
                <th className="p-4">Current Version</th>
                <th className="p-4">Status</th>
                <th className="p-4">Next Rotation</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--akaal-border)' }}>
              {keys.map((k) => (
                <tr key={k.id} className="hover:bg-white/5 transition-colors">
                  <td className="p-4 font-semibold">{k.name}</td>
                  <td className="p-4 text-xs font-mono">{k.algorithm}</td>
                  <td className="p-4 text-xs capitalize">{k.purpose}</td>
                  <td className="p-4 text-xs font-mono">v{k.versions.length} ({k.currentVersionId})</td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                      k.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                    }`}>
                      {k.status}
                    </span>
                  </td>
                  <td className="p-4 text-xs text-muted">
                    {k.nextRotationAt ? new Date(k.nextRotationAt).toLocaleDateString() : 'N/A'}
                  </td>
                  <td className="p-4 text-right space-x-1.5">
                    <button
                      onClick={() => setViewingKey(k)}
                      className="px-2.5 py-1 text-xs rounded border hover:bg-white/10"
                      style={{ borderColor: 'var(--akaal-border)' }}
                    >
                      Details
                    </button>
                    <button
                      onClick={() => handleRotate(k.id, k.name)}
                      disabled={k.status === 'revoked'}
                      className="px-2.5 py-1 text-xs rounded border hover:bg-white/10 disabled:opacity-40"
                      style={{ borderColor: 'var(--akaal-border)' }}
                    >
                      Rotate
                    </button>
                    <button
                      onClick={() => handleRevoke(k.id, k.name)}
                      disabled={k.status === 'revoked'}
                      className="px-2.5 py-1 text-xs rounded border border-rose-500/50 text-rose-400 hover:bg-rose-500/10 disabled:opacity-40"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>

      {/* Generate Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md p-6 rounded-lg border space-y-4" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-lg font-bold">Generate Cryptographic Key</h2>
            <form onSubmit={handleCreate} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs mb-1">Key Name</label>
                <input required type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
              </div>
              <div>
                <label className="block text-xs mb-1">Algorithm</label>
                <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value as any)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }}>
                  <option value="AES-256-GCM">AES-256-GCM</option>
                  <option value="RSA-4096">RSA-4096</option>
                  <option value="ECDSA-P256">ECDSA-P256</option>
                  <option value="Ed25519">Ed25519</option>
                  <option value="HMAC-SHA256">HMAC-SHA256</option>
                </select>
              </div>
              <div>
                <label className="block text-xs mb-1">Key Purpose</label>
                <select value={purpose} onChange={(e) => setPurpose(e.target.value as any)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }}>
                  <option value="encryption">Encryption / Decryption</option>
                  <option value="signing">Digital Signatures</option>
                  <option value="jwt_signing">JWT Token Signing</option>
                  <option value="tls">TLS Identity</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-3 py-1.5 rounded border text-xs" style={{ borderColor: 'var(--akaal-border)' }}>Cancel</button>
                <button type="submit" className="px-3 py-1.5 rounded text-xs font-semibold" style={{ background: 'var(--akaal-primary)', color: '#fff' }}>Generate</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Key Details Drawer */}
      {viewingKey && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-end p-4 z-50">
          <div className="w-full max-w-lg h-full p-6 rounded-lg border overflow-y-auto space-y-6" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--akaal-border)' }}>
              <div>
                <h2 className="text-lg font-bold">{viewingKey.name}</h2>
                <div className="text-xs font-mono text-muted">{viewingKey.id}</div>
              </div>
              <button onClick={() => setViewingKey(null)} className="px-2.5 py-1 text-xs rounded border" style={{ borderColor: 'var(--akaal-border)' }}>Close</button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div><span className="text-muted block">Algorithm:</span> <span className="font-mono font-semibold">{viewingKey.algorithm}</span></div>
                <div><span className="text-muted block">Purpose:</span> <span className="capitalize">{viewingKey.purpose}</span></div>
                <div><span className="text-muted block">Status:</span> <span className="capitalize font-semibold">{viewingKey.status}</span></div>
                <div><span className="text-muted block">Owner:</span> <span>{viewingKey.owner}</span></div>
              </div>

              <div className="pt-3 border-t space-y-1.5" style={{ borderColor: 'var(--akaal-border)' }}>
                <span className="text-muted block font-semibold">Usage Policy</span>
                <div>Operations: <span className="font-mono">{viewingKey.usagePolicy.allowedOperations.join(', ')}</span></div>
                <div>Environments: <span className="font-mono">{viewingKey.usagePolicy.allowedEnvironments.join(', ')}</span></div>
                <div>Requires MFA: <span className="font-semibold">{viewingKey.usagePolicy.requiresMFA ? 'Yes' : 'No'}</span></div>
              </div>
            </div>

            {/* Version History */}
            <div className="space-y-3 pt-4 border-t" style={{ borderColor: 'var(--akaal-border)' }}>
              <h3 className="text-sm font-bold">Key Version History ({viewingKey.versions.length})</h3>
              <div className="space-y-2">
                {viewingKey.versions.map((ver) => (
                  <div key={ver.versionId} className="p-3 rounded border space-y-1 text-xs" style={{ borderColor: 'var(--akaal-border)', background: ver.isActive ? 'rgba(16, 185, 129, 0.1)' : 'transparent' }}>
                    <div className="flex items-center justify-between">
                      <span className="font-bold font-mono">v{ver.versionNumber} ({ver.versionId})</span>
                      {ver.isActive ? <span className="text-emerald-400 font-semibold">Active</span> : <span className="text-muted">Previous</span>}
                    </div>
                    <div className="text-[11px] text-muted">Created: {new Date(ver.createdAt).toLocaleString()}</div>
                    <div className="text-[10px] font-mono text-muted">Fingerprint: {ver.fingerprint}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
