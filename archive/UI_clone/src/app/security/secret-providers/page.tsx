'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { secretRegistry } from '@/security/secrets/secretProviderFactory';
import { SecretProviderHealth, SecretProviderConfig, SecretProviderType } from '@/security/secrets/secretTypes';

export default function SecretProvidersPage() {
  const [healthList, setHealthList] = useState<SecretProviderHealth[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  // Modals
  const [showConfigModal, setShowConfigModal] = useState<SecretProviderType | null>(null);

  // Config form state
  const [vaultAddress, setVaultAddress] = useState('');
  const [vaultToken, setVaultToken] = useState('');
  const [awsRegion, setAwsRegion] = useState('us-east-1');
  const [awsAccessKey, setAwsAccessKey] = useState('');
  const [azureVaultUrl, setAzureVaultUrl] = useState('');
  const [azureTenantId, setAzureTenantId] = useState('');

  const reloadHealth = async () => {
    const list = await secretRegistry.checkAllHealth();
    setHealthList(list);
  };

  useEffect(() => {
    reloadHealth();
  }, []);

  const showToastMsg = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleTestConnection = async (type: SecretProviderType) => {
    showToastMsg(`Testing connectivity for ${type}...`);
    await reloadHealth();
  };

  const handleToggleEnable = (p: SecretProviderHealth) => {
    const isCurrentlyDisabled = p.status === 'disabled';
    const updatedConfig: SecretProviderConfig = {
      type: p.providerType,
      enabled: isCurrentlyDisabled,
      priority: 10,
      displayName: p.displayName,
    };
    secretRegistry.registerProvider(updatedConfig);
    showToastMsg(`Provider ${p.displayName} is now ${isCurrentlyDisabled ? 'enabled' : 'disabled'}.`);
    reloadHealth();
  };

  const handleSaveConfig = (e: React.FormEvent) => {
    e.preventDefault();
    if (!showConfigModal) return;

    const baseConfig: SecretProviderConfig = {
      type: showConfigModal,
      enabled: true,
      priority: 5,
      displayName: showConfigModal.toUpperCase(),
      vault: showConfigModal === 'vault' ? { address: vaultAddress, token: vaultToken, authMethod: 'token', mountPath: 'secret' } : undefined,
      aws: showConfigModal === 'aws_secrets_manager' ? { region: awsRegion, accessKeyId: awsAccessKey } : undefined,
      azure: showConfigModal === 'azure_key_vault' ? { vaultUrl: azureVaultUrl, tenantId: azureTenantId } : undefined,
    };

    secretRegistry.registerProvider(baseConfig);
    showToastMsg(`Configuration updated for provider ${showConfigModal}.`);
    setShowConfigModal(null);
    reloadHealth();
  };

  return (
    <div className="min-h-screen p-6" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      <header className="max-w-7xl mx-auto mb-6">
        <nav className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)' }}>
          <Link href="/dashboard" className="hover:underline">Platform</Link> / <Link href="/security/secrets" className="hover:underline">Security</Link> / Secret Providers
        </nav>
        <h1 className="text-2xl font-bold tracking-tight">Secret Provider Framework & Registry</h1>
        <p className="text-sm mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>
          Configuration-driven secret provider abstraction layer with dependency injection and failover diagnostics.
        </p>
      </header>

      {toast && (
        <div className="max-w-7xl mx-auto mb-4 p-3 rounded text-sm bg-emerald-900/40 text-emerald-300 border border-emerald-700/50">
          {toast}
        </div>
      )}

      <main className="max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {healthList.map((p) => (
            <div key={p.providerId} className="p-5 rounded-lg border space-y-3" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
              <div className="flex items-center justify-between">
                <div className="font-bold text-base">{p.displayName}</div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                  p.status === 'healthy' ? 'bg-emerald-500/20 text-emerald-400' :
                  p.status === 'degraded' ? 'bg-amber-500/20 text-amber-400' :
                  p.status === 'disabled' ? 'bg-gray-500/20 text-gray-400' : 'bg-rose-500/20 text-rose-400'
                }`}>
                  {p.status}
                </span>
              </div>

              <div className="text-xs space-y-1.5 font-mono" style={{ color: 'var(--akaal-text-muted)' }}>
                <div>Type: {p.providerType}</div>
                <div>Latency: {p.latencyMs ?? 0} ms</div>
                <div>Auth Status: {p.authStatus}</div>
                <div>Availability: {p.availability}%</div>
                <div>Retry Count: {p.retryCount}</div>
                <div>Version: {p.providerVersion || 'N/A'}</div>
                {p.failureReason && <div className="text-rose-400">Error: {p.failureReason}</div>}
              </div>

              <div className="pt-2 flex justify-end gap-2 border-t" style={{ borderColor: 'var(--akaal-border)' }}>
                <button
                  onClick={() => handleToggleEnable(p)}
                  className="px-3 py-1 text-xs rounded border hover:bg-white/10"
                  style={{ borderColor: 'var(--akaal-border)' }}
                >
                  {p.status === 'disabled' ? 'Enable' : 'Disable'}
                </button>
                <button
                  onClick={() => setShowConfigModal(p.providerType)}
                  className="px-3 py-1 text-xs rounded border hover:bg-white/10"
                  style={{ borderColor: 'var(--akaal-border)' }}
                >
                  Configure
                </button>
                <button
                  onClick={() => handleTestConnection(p.providerType)}
                  className="px-3 py-1 text-xs rounded border hover:bg-white/10"
                  style={{ borderColor: 'var(--akaal-border)' }}
                >
                  Test Connection
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* Configure Provider Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md p-6 rounded-lg border space-y-4" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-lg font-bold">Configure Provider: {showConfigModal}</h2>
            <form onSubmit={handleSaveConfig} className="space-y-3 text-sm">
              {showConfigModal === 'vault' && (
                <>
                  <div>
                    <label className="block text-xs mb-1">Vault Server Address</label>
                    <input type="text" placeholder="https://vault.internal:8200" value={vaultAddress} onChange={(e) => setVaultAddress(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                  <div>
                    <label className="block text-xs mb-1">Vault Client Token</label>
                    <input type="password" value={vaultToken} onChange={(e) => setVaultToken(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                </>
              )}

              {showConfigModal === 'aws_secrets_manager' && (
                <>
                  <div>
                    <label className="block text-xs mb-1">AWS Region</label>
                    <input type="text" value={awsRegion} onChange={(e) => setAwsRegion(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                  <div>
                    <label className="block text-xs mb-1">AWS Access Key ID</label>
                    <input type="text" value={awsAccessKey} onChange={(e) => setAwsAccessKey(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                </>
              )}

              {showConfigModal === 'azure_key_vault' && (
                <>
                  <div>
                    <label className="block text-xs mb-1">Vault URL</label>
                    <input type="text" placeholder="https://myvault.vault.azure.net" value={azureVaultUrl} onChange={(e) => setAzureVaultUrl(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                  <div>
                    <label className="block text-xs mb-1">Tenant ID</label>
                    <input type="text" value={azureTenantId} onChange={(e) => setAzureTenantId(e.target.value)} className="w-full p-2 rounded border bg-transparent" style={{ borderColor: 'var(--akaal-border)' }} />
                  </div>
                </>
              )}

              {showConfigModal !== 'vault' && showConfigModal !== 'aws_secrets_manager' && showConfigModal !== 'azure_key_vault' && (
                <div className="text-xs text-muted">
                  Generic configuration for {showConfigModal}. Enable/Disable settings applied directly.
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowConfigModal(null)} className="px-3 py-1.5 rounded border text-xs" style={{ borderColor: 'var(--akaal-border)' }}>Cancel</button>
                <button type="submit" className="px-3 py-1.5 rounded text-xs font-semibold" style={{ background: 'var(--akaal-primary)', color: '#fff' }}>Save Configuration</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
