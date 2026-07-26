'use client';

import React, { useState } from 'react';
import Link from 'next/link';

interface ActiveDeviceSession {
  sessionId: string;
  deviceName: string;
  browser: string;
  ipAddress: string;
  location: string;
  lastActive: string;
  isCurrent: boolean;
}

export default function SessionManagementPage() {
  const [sessions, setSessions] = useState<ActiveDeviceSession[]>([
    {
      sessionId: 'sess_948201',
      deviceName: 'MacBook Pro 16" (M3 Max)',
      browser: 'Chrome 126.0 (macOS)',
      ipAddress: '192.168.1.42',
      location: 'New York, US',
      lastActive: 'Just now',
      isCurrent: true,
    },
    {
      sessionId: 'sess_384019',
      deviceName: 'Linux Workstation',
      browser: 'Firefox 127.0 (Ubuntu)',
      ipAddress: '10.0.4.19',
      location: 'Secaucus Data Center',
      lastActive: '14 minutes ago',
      isCurrent: false,
    },
    {
      sessionId: 'sess_719402',
      deviceName: 'iPad Pro (Safari)',
      browser: 'Safari 17.4 (iPadOS)',
      ipAddress: '172.16.0.8',
      location: 'New York, US',
      lastActive: '2 hours ago',
      isCurrent: false,
    },
  ]);

  const handleRevokeSession = (sessionId: string) => {
    setSessions(prev => prev.filter(s => s.sessionId !== sessionId));
  };

  const handleLogoutEverywhere = () => {
    setSessions(prev => prev.filter(s => s.isCurrent));
  };

  return (
    <div className="min-h-screen p-6" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      <header className="max-w-5xl mx-auto mb-6 flex items-center justify-between">
        <div>
          <nav className="text-xs mb-1" style={{ color: 'var(--akaal-text-muted)' }}>
            <Link href="/dashboard" className="hover:underline">Platform</Link> / <Link href="/settings" className="hover:underline">Settings</Link> / Active Sessions
          </nav>
          <h1 className="text-xl font-bold">Enterprise Session Management</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>Manage active device sessions, security tokens, and remote revocations.</p>
        </div>
        <button
          type="button"
          onClick={handleLogoutEverywhere}
          className="px-3 py-1.5 rounded-md text-xs font-semibold transition-all"
          style={{ background: 'var(--akaal-error-bg)', color: 'var(--akaal-error)', border: '1px solid rgba(239,68,68,0.3)' }}
        >
          Logout All Other Devices
        </button>
      </header>

      <main className="max-w-5xl mx-auto space-y-4">
        <div className="rounded-lg p-4" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)' }}>
          <h2 className="text-sm font-semibold mb-3">Active Device Sessions ({sessions.length})</h2>
          <div className="space-y-3">
            {sessions.map(sess => (
              <div
                key={sess.sessionId}
                className="flex items-center justify-between p-3 rounded-md"
                style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold">{sess.deviceName}</span>
                    {sess.isCurrent && (
                      <span className="px-1.5 py-0.5 rounded text-xs font-mono font-semibold" style={{ background: 'rgba(34,197,94,0.15)', color: '#22C55E', fontSize: '9px' }}>
                        THIS DEVICE
                      </span>
                    )}
                  </div>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)' }}>
                    {sess.browser} • {sess.ipAddress} ({sess.location})
                  </p>
                  <p className="text-xs font-mono mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontSize: '10px' }}>
                    Last active: {sess.lastActive}
                  </p>
                </div>
                {!sess.isCurrent && (
                  <button
                    type="button"
                    onClick={() => handleRevokeSession(sess.sessionId)}
                    className="px-2.5 py-1 rounded text-xs font-medium transition-all"
                    style={{ background: 'var(--akaal-hover-bg)', color: 'var(--akaal-error)', border: '1px solid var(--akaal-border)' }}
                  >
                    Revoke Session
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
