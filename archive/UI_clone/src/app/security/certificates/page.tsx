'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { CertificateManager } from '@/security/certificates/certificateManager';
import { CertRecord, CertValidationResult } from '@/security/certificates/certTypes';

export default function CertificatesPage() {
  const [certs, setCerts] = useState<CertRecord[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  // Modals
  const [showImportModal, setShowImportModal] = useState(false);
  const [validatingCert, setValidatingCert] = useState<CertValidationResult | null>(null);

  // Form State
  const [importFormat, setImportFormat] = useState<'PEM' | 'PKCS12'>('PEM');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [pemCert, setPemCert] = useState('');
  const [pemChain, setPemChain] = useState('');
  const [pkcs12Data, setPkcs12Data] = useState('');
  const [pkcs12Password, setPkcs12Password] = useState('');

  const reloadCerts = () => {
    setCerts(CertificateManager.list());
  };

  useEffect(() => {
    reloadCerts();
  }, []);

  const showToastMsg = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (importFormat === 'PEM') {
        await CertificateManager.importCert({
          name,
          description,
          pemCert,
          pemChain: pemChain || undefined,
          usage: ['tls', 'server_auth'],
        }, 'admin');
      } else {
        await CertificateManager.importCert({
          name,
          description,
          pemCert: `-----BEGIN CERTIFICATE-----\n[PKCS#12 Extracted Certificate: ${name}]\n-----END CERTIFICATE-----`,
          pkcs12Data,
          pkcs12Password,
          usage: ['tls', 'mtls_client'],
        }, 'admin');
      }
      showToastMsg(`Certificate "${name}" imported successfully.`);
      setShowImportModal(false);
      setName(''); setDescription(''); setPemCert(''); setPemChain(''); setPkcs12Data(''); setPkcs12Password('');
      reloadCerts();
    } catch (err: any) {
      showToastMsg(`Import failed: ${err.message}`);
    }
  };

  const handleValidate = (id: string) => {
    try {
      const result = CertificateManager.validate(id);
      setValidatingCert(result);
    } catch (err: any) {
      showToastMsg(`Validation failed: ${err.message}`);
    }
  };

  const handleRenew = (id: string, name: string) => {
    try {
      CertificateManager.renew(id, 'admin');
      showToastMsg(`Certificate "${name}" renewed successfully.`);
      reloadCerts();
    } catch (err: any) {
      showToastMsg(`Renewal failed: ${err.message}`);
    }
  };

  const handleRevoke = (id: string, name: string) => {
    const reason = prompt(`Enter revocation reason for certificate "${name}":`);
    if (reason) {
      CertificateManager.revoke(id, reason, 'admin');
      showToastMsg(`Certificate "${name}" revoked.`);
      reloadCerts();
    }
  };

  return (
    <div className="min-h-screen p-6" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      <header className="max-w-7xl mx-auto mb-6 flex items-center justify-between">
        <div>
          <nav className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)' }}>
            <Link href="/dashboard" className="hover:underline">Platform</Link> / <Link href="/security/secrets" className="hover:underline">Security</Link> / Certificate Inventory
          </nav>
          <h1 className="text-2xl font-bold tracking-tight">Certificate Inventory & PKI</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>
            X.509 Certificate tracking, PEM & PKCS#12 import, chain validation, automated renewal, and revocation.
          </p>
        </div>
        <button
          onClick={() => setShowImportModal(true)}
          className="px-4 py-2 text-sm font-medium rounded-md transition-opacity hover:opacity-90"
          style={{ background: 'var(--akaal-primary)', color: '#fff' }}
        >
          + Import Certificate
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
                <th className="p-4">Certificate Name / CN</th>
                <th className="p-4">Format</th>
                <th className="p-4">Issuer</th>
                <th className="p-4">Fingerprint</th>
                <th className="p-4">Expires In</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--akaal-border)' }}>
              {certs.map((c) => (
                <tr key={c.id} className="hover:bg-white/5 transition-colors">
                  <td className="p-4">
                    <div className="font-semibold">{c.name}</div>
                    <div className="text-xs font-mono" style={{ color: 'var(--akaal-text-muted)' }}>{c.subject.commonName}</div>
                  </td>
                  <td className="p-4 text-xs font-mono">{c.format}</td>
                  <td className="p-4 text-xs text-muted">{c.issuer.commonName}</td>
                  <td className="p-4 text-xs font-mono truncate max-w-[150px]">{c.fingerprint}</td>
                  <td className="p-4 text-xs font-semibold">
                    <span className={c.daysUntilExpiry <= 30 ? 'text-amber-400' : 'text-emerald-400'}>
                      {c.daysUntilExpiry} days
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                      c.status === 'valid' ? 'bg-emerald-500/20 text-emerald-400' :
                      c.status === 'expiring_soon' ? 'bg-amber-500/20 text-amber-400' : 'bg-rose-500/20 text-rose-400'
                    }`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="p-4 text-right space-x-1.5">
                    <button
                      onClick={() => handleValidate(c.id)}
                      className="px-2.5 py-1 text-xs rounded border hover:bg-white/10"
                      style={{ borderColor: 'var(--akaal-border)' }}
                    >
                      Validate
                    </button>
                    <button
                      onClick={() => handleRenew(c.id, c.name)}
                      disabled={c.status === 'revoked'}
                      className="px-2.5 py-1 text-xs rounded border hover:bg-white/10 disabled:opacity-40"
                      style={{ borderColor: 'var(--akaal-border)' }}
                    >
                      Renew
                    </button>
                    <button
                      onClick={() => handleRevoke(c.id, c.name)}
                      disabled={c.status === 'revoked'}
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

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md p-6 rounded-lg border space-y-4" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-lg font-bold">Import Certificate</h2>

            <div className="flex border-b text-xs" style={{ borderColor: 'var(--akaal-border)' }}>
              <button
                type="button"
                onClick={() => setImportFormat('PEM')}
                className={`flex-1 py-2 font-semibold border-b-2 ${importFormat === 'PEM' ? 'border-amber-400 text-amber-400' : 'border-transparent text-muted'}`}
              >
                PEM Format
              </button>
              <button
                type="button"
                onClick={() => setImportFormat('PKCS12')}
                className={`flex-1 py-2 font-semibold border-b-2 ${importFormat === 'PKCS12' ? 'border-amber-400 text-amber-400' : 'border-transparent text-muted'}`}
              >
                PKCS#12 (.pfx/.p12)
              </button>
            </div>

            <form onSubmit={handleImport} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs mb-1">Name</label>
                <input required type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
              </div>

              {importFormat === 'PEM' ? (
                <>
                  <div>
                    <label className="block text-xs mb-1">PEM Certificate</label>
                    <textarea required rows={4} placeholder="-----BEGIN CERTIFICATE-----..." value={pemCert} onChange={(e) => setPemCert(e.target.value)} className="w-full p-2 rounded border bg-transparent font-mono text-xs" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                  <div>
                    <label className="block text-xs mb-1">PEM Chain (Optional)</label>
                    <textarea rows={3} placeholder="-----BEGIN CERTIFICATE-----..." value={pemChain} onChange={(e) => setPemChain(e.target.value)} className="w-full p-2 rounded border bg-transparent font-mono text-xs" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-xs mb-1">PKCS#12 Base64 Data</label>
                    <textarea required rows={4} placeholder="Base64 encoded PKCS#12 container..." value={pkcs12Data} onChange={(e) => setPkcs12Data(e.target.value)} className="w-full p-2 rounded border bg-transparent font-mono text-xs" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                  <div>
                    <label className="block text-xs mb-1">PKCS#12 Password</label>
                    <input type="password" value={pkcs12Password} onChange={(e) => setPkcs12Password(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                </>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowImportModal(false)} className="px-3 py-1.5 rounded border text-xs" style={{ borderColor: 'var(--akaal-border)' }}>Cancel</button>
                <button type="submit" className="px-3 py-1.5 rounded text-xs font-semibold" style={{ background: 'var(--akaal-primary)', color: '#fff' }}>Import</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Validation Result Modal */}
      {validatingCert && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md p-6 rounded-lg border space-y-4 text-xs" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-base font-bold flex items-center justify-between">
              <span>Certificate Validation Result</span>
              <span className={`px-2 py-0.5 rounded text-xs font-semibold ${validatingCert.isValid ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                {validatingCert.isValid ? 'PASSED' : 'FAILED'}
              </span>
            </h2>

            <div className="space-y-2 border-t pt-3" style={{ borderColor: 'var(--akaal-border)' }}>
              <div className="flex justify-between"><span>Chain Validation:</span> <span className="text-emerald-400 font-semibold">{validatingCert.chainValid ? 'Valid' : 'Invalid'}</span></div>
              <div className="flex justify-between"><span>Signature Check:</span> <span className="text-emerald-400 font-semibold">{validatingCert.signatureValid ? 'Valid' : 'Invalid'}</span></div>
              <div className="flex justify-between"><span>Expiration Check:</span> <span className={validatingCert.notExpired ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>{validatingCert.notExpired ? 'Not Expired' : 'Expired'}</span></div>
              <div className="flex justify-between"><span>Revocation Check:</span> <span className={validatingCert.notRevoked ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>{validatingCert.notRevoked ? 'Not Revoked' : 'Revoked'}</span></div>
            </div>

            {validatingCert.warnings.length > 0 && (
              <div className="p-2 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 space-y-1">
                <span className="font-bold">Warnings:</span>
                {validatingCert.warnings.map((w, idx) => <div key={idx}>• {w}</div>)}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button onClick={() => setValidatingCert(null)} className="px-3 py-1.5 rounded border text-xs" style={{ borderColor: 'var(--akaal-border)' }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
