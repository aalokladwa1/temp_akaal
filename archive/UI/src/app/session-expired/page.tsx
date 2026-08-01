'use client';

import React from 'react';
import Link from 'next/link';

export default function SessionExpiredPage() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden"
      style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}
    >
      {/* Background lighting */}
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-10%', left: '-10%', width: '65%', height: '65%', background: 'radial-gradient(ellipse at top left, rgba(59,130,246,0.09) 0%, rgba(59,130,246,0.04) 35%, transparent 70%)', filter: 'blur(40px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-5%', right: '-5%', width: '40%', height: '40%', background: 'radial-gradient(ellipse at top right, rgba(56,189,248,0.04) 0%, transparent 65%)', filter: 'blur(50px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.3) 100%)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ backgroundImage: 'linear-gradient(var(--akaal-border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--akaal-border-subtle) 1px, transparent 1px)', backgroundSize: '48px 48px', opacity: 0.4 }} />

      <main className="relative w-full flex flex-col" style={{ maxWidth: '460px' }} aria-label="Session expired">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="mb-4 w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'var(--akaal-primary-subtle)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-primary)' }}>
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h1 className="font-bold tracking-widest uppercase" style={{ color: 'var(--akaal-text)', letterSpacing: '0.18em', fontFamily: "'JetBrains Mono', monospace", fontSize: '16px' }}>AKAAL</h1>
          <p className="text-xs mt-1 tracking-wider" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>Enterprise Database Migration Platform</p>
        </div>

        {/* Card */}
        <div className="rounded-xl p-8" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }}>
          <div className="flex flex-col items-center text-center">
            <div className="flex items-center justify-center w-12 h-12 rounded-xl mb-5" style={{ background: 'var(--akaal-warning-bg)', border: '1px solid rgba(250,204,21,0.2)' }} aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-warning)' }}>
                <circle cx="11" cy="11" r="9" stroke="currentColor" strokeWidth="1.5" />
                <path d="M11 6v5.5l3.5 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>

            <h2 className="font-semibold text-base mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Session Expired</h2>
            <p className="text-xs leading-relaxed mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", maxWidth: '320px' }}>
              Your authentication session has expired due to inactivity.
            </p>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", maxWidth: '320px' }}>
              Please sign in again to continue accessing your migration workspace.
            </p>

            <div className="w-full h-px my-6" style={{ background: 'var(--akaal-border)' }} aria-hidden="true" />

            {/* Session info */}
            <div className="w-full rounded-lg p-3 mb-6 text-left" style={{ background: 'var(--akaal-surface-elevated)', border: '1px solid var(--akaal-border)' }}>
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Reason</span>
                <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>Idle timeout</span>
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Session policy</span>
                <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>30 min inactivity</span>
              </div>
            </div>

            <Link
              href="/sign-in"
              className="w-full flex items-center justify-center gap-2 text-sm font-semibold rounded-lg py-2.5 focus:outline-none focus-visible:ring-2"
              style={{
                background: 'var(--akaal-primary)',
                color: '#ffffff',
                fontFamily: "'Inter', sans-serif",
                letterSpacing: '0.01em',
                boxShadow: '0 1px 3px var(--akaal-shadow-sm)',
                transition: 'filter 0.15s ease, transform 0.1s ease',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.filter = 'brightness(1.1)'; (e.currentTarget as HTMLAnchorElement).style.transform = 'translateY(-0.5px)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.filter = ''; (e.currentTarget as HTMLAnchorElement).style.transform = ''; }}
              aria-label="Return to Sign In"
            >
              Return to Sign In
            </Link>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-5 px-1" aria-label="Application metadata">
          <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>Version 1.0.0</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--akaal-success)' }} aria-hidden="true" />
            <span className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>Production</span>
          </div>
        </div>
      </main>
    </div>
  );
}
