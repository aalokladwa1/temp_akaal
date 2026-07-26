'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function NotFound() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden"
      style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}
    >
      {/* Background lighting */}
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-10%', left: '-10%', width: '60%', height: '60%', background: 'radial-gradient(ellipse at top left, rgba(59,130,246,0.08) 0%, transparent 70%)', filter: 'blur(60px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ bottom: '-10%', right: '-10%', width: '50%', height: '50%', background: 'radial-gradient(ellipse at bottom right, rgba(56,189,248,0.05) 0%, transparent 70%)', filter: 'blur(60px)' }} />

      <main
        className="relative w-full flex flex-col items-center text-center"
        style={{
          maxWidth: '520px',
          opacity: mounted ? 1 : 0,
          transform: mounted ? 'translateY(0)' : 'translateY(16px)',
          transition: 'opacity 0.35s cubic-bezier(0.16,1,0.3,1), transform 0.35s cubic-bezier(0.16,1,0.3,1)',
        }}
      >
        {/* Error code */}
        <div className="mb-6 relative">
          <div
            className="text-8xl font-bold select-none"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: 'var(--akaal-primary)',
              opacity: 0.12,
              letterSpacing: '-0.04em',
              lineHeight: 1,
            }}
            aria-hidden="true"
          >
            404
          </div>
          <div
            className="absolute inset-0 flex items-center justify-center"
          >
            <div
              className="flex items-center justify-center w-16 h-16 rounded-2xl"
              style={{
                background: 'var(--akaal-primary-subtle)',
                border: '1px solid rgba(59,130,246,0.2)',
              }}
            >
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-primary)' }}>
                <path d="M14 4a10 10 0 1 0 0 20A10 10 0 0 0 14 4ZM2 14a12 12 0 1 1 24 0A12 12 0 0 1 2 14Zm12-5a1 1 0 0 1 1 1v5a1 1 0 0 1-2 0v-5a1 1 0 0 1 1-1Zm0 9.5a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5Z" fill="currentColor"/>
              </svg>
            </div>
          </div>
        </div>

        {/* Heading */}
        <h1 className="text-xl font-semibold mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
          Page Not Found
        </h1>
        <p className="text-sm leading-relaxed mb-2" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
          The requested route does not exist or has been moved.
        </p>

        {/* Diagnostic card */}
        <div
          className="w-full rounded-lg p-4 mb-6 text-left"
          style={{
            background: 'var(--akaal-surface)',
            border: '1px solid var(--akaal-border)',
          }}
        >
          <p className="text-xs font-semibold mb-3" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Diagnostic
          </p>
          <div className="space-y-2">
            {[
              { label: 'Error Code', value: 'HTTP 404 — Not Found' },
              { label: 'Possible Cause', value: 'Route removed, renamed, or mistyped URL' },
              { label: 'Suggested Action', value: 'Navigate to Dashboard or go back' },
            ].map(item => (
              <div key={item.label} className="flex items-start gap-3">
                <span className="text-xs flex-shrink-0 w-32" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>{item.label}</span>
                <span className="text-xs" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 w-full">
          <Link
            href="/dashboard"
            className="flex-1 flex items-center justify-center gap-2 text-sm font-semibold rounded-lg py-2.5 focus:outline-none focus-visible:ring-2"
            style={{
              background: 'var(--akaal-primary)',
              color: '#ffffff',
              fontFamily: "'Inter', sans-serif",
              boxShadow: '0 1px 3px var(--akaal-shadow-sm)',
              transition: 'filter 0.15s ease, transform 0.1s ease',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.filter = 'brightness(1.1)'; (e.currentTarget as HTMLAnchorElement).style.transform = 'translateY(-0.5px)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.filter = ''; (e.currentTarget as HTMLAnchorElement).style.transform = ''; }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M1 7h12M7 1l6 6-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Go to Dashboard
          </Link>
          <button
            type="button"
            onClick={() => router.back()}
            className="flex-1 flex items-center justify-center gap-2 text-sm font-medium rounded-lg py-2.5 focus:outline-none focus-visible:ring-2"
            style={{
              background: 'transparent',
              border: '1px solid var(--akaal-border)',
              color: 'var(--akaal-text-secondary)',
              fontFamily: "'Inter', sans-serif",
              transition: 'background 0.15s ease, border-color 0.15s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--akaal-hover-bg)'; e.currentTarget.style.borderColor = 'var(--akaal-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'var(--akaal-border)'; }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M13 7H1M7 1L1 7l6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Go Back
          </button>
        </div>

        {/* Quick links */}
        <div className="flex items-center gap-4 mt-6">
          {[
            { href: '/migration-workspace', label: 'Migrations' },
            { href: '/databases', label: 'Databases' },
            { href: '/reports', label: 'Reports' },
            { href: '/settings', label: 'Settings' },
          ].map(link => (
            <Link
              key={link.href}
              href={link.href}
              className="text-xs transition-colors focus:outline-none focus-visible:underline"
              style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => (e.currentTarget as HTMLAnchorElement).style.color = 'var(--akaal-primary)'}
              onMouseLeave={e => (e.currentTarget as HTMLAnchorElement).style.color = 'var(--akaal-text-muted)'}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}