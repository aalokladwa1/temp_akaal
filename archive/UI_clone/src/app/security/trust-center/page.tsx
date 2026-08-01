'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { SecretHealthMonitor, AggregateHealthReport } from '@/security/health/secretHealthMonitor';
import { TLSConfigService } from '@/security/trust/tlsConfigService';
import { TrustStoreManager } from '@/security/trust/trustStoreManager';
import { SecretRotationEngine } from '@/security/secrets/secretRotationEngine';

export default function TrustCenterPage() {
  const [health, setHealth] = useState<AggregateHealthReport | null>(null);
  const [dueRotationsCount, setDueRotationsCount] = useState(0);
  const tlsConfig = TLSConfigService.getTLSConfig();
  const mtlsConfig = TLSConfigService.getMTLSConfig();
  const anchors = TrustStoreManager.listAnchors();
  const pins = TrustStoreManager.listPins();

  const reload = async () => {
    const report = await SecretHealthMonitor.getAggregateHealth();
    setHealth(report);
    setDueRotationsCount(SecretRotationEngine.getDueForRotation().length);
  };

  useEffect(() => {
    reload();
  }, []);

  return (
    <div className="min-h-screen p-6" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      <header className="max-w-7xl mx-auto mb-6 flex items-center justify-between">
        <div>
          <nav className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)' }}>
            <Link href="/dashboard" className="hover:underline">Platform</Link> / <Link href="/security/secrets" className="hover:underline">Security</Link> / Trust Center
          </nav>
          <h1 className="text-2xl font-bold tracking-tight">Enterprise Trust Center & Security Posture</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>
            Real-time visibility into secret providers, key health, PKI trust anchors, and TLS configuration posture.
          </p>
        </div>
        <button
          onClick={reload}
          className="px-3.5 py-1.5 text-xs font-medium rounded border hover:bg-white/10"
          style={{ borderColor: 'var(--akaal-border)' }}
        >
          Refresh Health Diagnostics
        </button>
      </header>

      <main className="max-w-7xl mx-auto space-y-6">
        {/* Overall Status Banner */}
        <div className={`p-5 rounded-lg border flex items-center justify-between ${
          health?.overallStatus === 'healthy' ? 'bg-emerald-950/30 border-emerald-800/50' :
          health?.overallStatus === 'degraded' ? 'bg-amber-950/30 border-amber-800/50' : 'bg-rose-950/30 border-rose-800/50'
        }`}>
          <div>
            <div className="text-xs uppercase tracking-wider font-semibold opacity-75">Global Security Posture</div>
            <div className="text-xl font-bold capitalize mt-1">{health?.overallStatus ?? 'Evaluating...'}</div>
          </div>
          <div className="text-right text-xs opacity-75 font-mono">
            Last Checked: {health ? new Date(health.generatedAt).toLocaleTimeString() : '...'}
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="p-4 rounded-lg border" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <div className="text-xs text-muted uppercase font-semibold">Active Providers</div>
            <div className="text-2xl font-bold mt-2">{health?.providers.filter(p => p.status === 'healthy').length ?? 0} / {health?.providers.length ?? 0}</div>
          </div>
          <div className="p-4 rounded-lg border" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <div className="text-xs text-muted uppercase font-semibold">Certificates Valid</div>
            <div className="text-2xl font-bold mt-2">{health?.certificates.total ?? 0}</div>
            {health?.certificates.expiringSoon ? (
              <div className="text-xs text-amber-400 mt-1">{health.certificates.expiringSoon} expiring soon</div>
            ) : null}
          </div>
          <div className="p-4 rounded-lg border" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <div className="text-xs text-muted uppercase font-semibold">Active Keys</div>
            <div className="text-2xl font-bold mt-2">{health?.keys.active ?? 0}</div>
          </div>
          <div className="p-4 rounded-lg border" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <div className="text-xs text-muted uppercase font-semibold">Rotation Warnings</div>
            <div className="text-2xl font-bold mt-2">{dueRotationsCount} Due</div>
          </div>
          <div className="p-4 rounded-lg border" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <div className="text-xs text-muted uppercase font-semibold">Trust Anchors</div>
            <div className="text-2xl font-bold mt-2">{anchors.length} CA Anchors</div>
          </div>
        </div>

        {/* TLS Policy & mTLS */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-5 rounded-lg border space-y-3" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-base font-bold border-b pb-2" style={{ borderColor: 'var(--akaal-border)' }}>TLS Configuration Posture</h2>
            <div className="text-sm space-y-2">
              <div className="flex justify-between"><span className="text-muted">Minimum Protocol:</span> <span className="font-mono font-semibold">{tlsConfig.minVersion}</span></div>
              <div className="flex justify-between"><span className="text-muted">HSTS Preload:</span> <span className="text-emerald-400 font-semibold">{tlsConfig.hstsPreload ? 'Enabled' : 'Disabled'}</span></div>
              <div className="flex justify-between"><span className="text-muted">Session Resumption:</span> <span className="font-semibold">{tlsConfig.sessionResumptionEnabled ? 'Active' : 'Disabled'}</span></div>
              <div className="flex justify-between"><span className="text-muted">OCSP Stapling:</span> <span className="text-emerald-400 font-semibold">{tlsConfig.ocspStaplingEnabled ? 'Enabled' : 'Disabled'}</span></div>
            </div>
          </div>

          <div className="p-5 rounded-lg border space-y-3" style={{ background: 'var(--akaal-card-bg)', borderColor: 'var(--akaal-border)' }}>
            <h2 className="text-base font-bold border-b pb-2" style={{ borderColor: 'var(--akaal-border)' }}>Zero-Trust mTLS Status</h2>
            <div className="text-sm space-y-2">
              <div className="flex justify-between"><span className="text-muted">Mutual TLS Enforcement:</span> <span className="text-emerald-400 font-semibold">{mtlsConfig.enabled ? 'Enforced' : 'Disabled'}</span></div>
              <div className="flex justify-between"><span className="text-muted">Client Cert Required:</span> <span className="font-semibold">{mtlsConfig.requireClientCert ? 'Yes' : 'No'}</span></div>
              <div className="flex justify-between"><span className="text-muted">Cert Pinning Rules:</span> <span className="font-semibold">{pins.length} Active Pins</span></div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
