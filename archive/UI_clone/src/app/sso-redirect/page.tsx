'use client';

import React, { useState, useEffect, useCallback } from 'react';
import AppImage from '@/components/ui/AppImage';
import Link from 'next/link';

// ─── Types ────────────────────────────────────────────────────────────────────

type SSOState = 'redirecting' | 'timeout' | 'unavailable' | 'success';

const REDIRECT_TIMEOUT_MS = 12000;
const PROGRESS_INTERVAL_MS = 80;

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SSORedirectPage() {
  const [ssoState, setSSOState] = useState<SSOState>('redirecting');
  const [progress, setProgress] = useState(0);
  const [isCancelling, setIsCancelling] = useState(false);

  const startRedirect = useCallback(() => {
    setSSOState('redirecting');
    setProgress(0);
    setIsCancelling(false);
  }, []);

  useEffect(() => {
    if (ssoState !== 'redirecting') return;

    let elapsed = 0;
    const interval = setInterval(() => {
      elapsed += PROGRESS_INTERVAL_MS;
      const raw = elapsed / REDIRECT_TIMEOUT_MS;
      // Ease-out: fast start, slow finish
      const eased = 1 - Math.pow(1 - Math.min(raw, 0.92), 2);
      setProgress(Math.round(eased * 100));

      if (elapsed >= REDIRECT_TIMEOUT_MS) {
        clearInterval(interval);
        setSSOState('timeout');
        setProgress(100);
      }
    }, PROGRESS_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [ssoState]);

  function handleCancel() {
    setIsCancelling(true);
    setTimeout(() => {
      window.location.href = '/sign-in';
    }, 300);
  }

  function handleRetry() {
    startRedirect();
  }

  // ── Timeout state ─────────────────────────────────────────────────────────

  if (ssoState === 'timeout' || ssoState === 'unavailable') {
    const isUnavailable = ssoState === 'unavailable';
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden"
        style={{ background: '#0B1220', fontFamily: "'Inter', sans-serif" }}
      >
        <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-10%', left: '-10%', width: '65%', height: '65%', background: 'radial-gradient(ellipse at top left, rgba(37,99,235,0.09) 0%, rgba(37,99,235,0.04) 35%, transparent 70%)', filter: 'blur(40px)' }} />
        <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-5%', right: '-5%', width: '40%', height: '40%', background: 'radial-gradient(ellipse at top right, rgba(56,189,248,0.04) 0%, transparent 65%)', filter: 'blur(50px)' }} />
        <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.45) 100%)' }} />
        <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)', backgroundSize: '48px 48px' }} />

        <main className="relative w-full flex flex-col" style={{ maxWidth: '460px' }}>
          <div className="flex flex-col items-center mb-8">
            <AppImage src="/assets/images/app_logo.png" alt="AKAAL logo" width={48} height={48} className="mb-4" style={{ filter: 'drop-shadow(0 2px 8px rgba(37,99,235,0.3))' }} />
            <h1 className="font-bold tracking-widest uppercase text-lg" style={{ color: '#F8FAFC', letterSpacing: '0.18em', fontFamily: "'JetBrains Mono', monospace" }}>AKAAL</h1>
            <p className="text-xs mt-1 tracking-wider" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace" }}>Enterprise Database Migration Platform</p>
          </div>

          <div className="rounded-lg p-8" style={{ background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 1px 0 0 rgba(255,255,255,0.06) inset, 0 8px 40px rgba(0,0,0,0.55), 0 2px 12px rgba(0,0,0,0.35)' }}>
            <div className="flex flex-col items-center text-center">
              <div
                className="flex items-center justify-center w-12 h-12 rounded-md mb-5"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}
                aria-hidden="true"
              >
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true" style={{ color: '#EF4444' }}>
                  {isUnavailable ? (
                    <path d="M11 3v10M11 17v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  ) : (
                    <>
                      <circle cx="11" cy="11" r="9" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M11 6v5.5l3.5 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </>
                  )}
                </svg>
              </div>

              <h2 className="font-semibold text-base mb-2" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>
                {isUnavailable ? 'SSO Provider Unavailable' : 'SSO Redirect Timed Out'}
              </h2>
              <p className="text-xs leading-relaxed" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif", maxWidth: '320px' }}>
                {isUnavailable
                  ? 'The identity provider is currently unreachable. Contact your IT administrator if this issue persists.'
                  : 'The redirect to your identity provider took too long. This may be a temporary issue.'}
              </p>

              <div className="w-full h-px my-6" style={{ background: '#2A3647' }} aria-hidden="true" />

              <div className="flex flex-col gap-3 w-full">
                <button
                  type="button"
                  onClick={handleRetry}
                  className="w-full flex items-center justify-center gap-2 text-sm font-semibold rounded-md py-2.5 transition-all duration-200 focus:outline-none focus-visible:ring-2"
                  style={{ background: '#2563EB', color: '#ffffff', fontFamily: "'Inter', sans-serif", letterSpacing: '0.01em', boxShadow: '0 1px 3px rgba(0,0,0,0.3), 0 1px 0 rgba(255,255,255,0.06) inset' }}
                  onMouseEnter={e => e.currentTarget.style.background = '#1D4ED8'}
                  onMouseLeave={e => e.currentTarget.style.background = '#2563EB'}
                  onMouseDown={e => e.currentTarget.style.background = '#1E40AF'}
                  onMouseUp={e => e.currentTarget.style.background = '#1D4ED8'}
                >
                  Try Again
                </button>
                <Link
                  href="/sign-in"
                  className="w-full flex items-center justify-center gap-2 text-xs font-medium rounded-md py-2.5 transition-all duration-200 focus:outline-none focus-visible:ring-2"
                  style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
                  onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.borderColor = '#4B5563'; (e.currentTarget as HTMLAnchorElement).style.color = '#CBD5E1'; (e.currentTarget as HTMLAnchorElement).style.background = 'rgba(255,255,255,0.03)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.borderColor = '#374151'; (e.currentTarget as HTMLAnchorElement).style.color = '#94A3B8'; (e.currentTarget as HTMLAnchorElement).style.background = 'transparent'; }}
                >
                  Return to Sign In
                </Link>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between mt-5 px-1">
            <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>Version 1.0.0</span>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#22C55E' }} aria-hidden="true" />
              <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>Production</span>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // ── Redirecting state ─────────────────────────────────────────────────────

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden"
      style={{ background: '#0B1220', fontFamily: "'Inter', sans-serif" }}
    >
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-10%', left: '-10%', width: '65%', height: '65%', background: 'radial-gradient(ellipse at top left, rgba(37,99,235,0.09) 0%, rgba(37,99,235,0.04) 35%, transparent 70%)', filter: 'blur(40px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-5%', right: '-5%', width: '40%', height: '40%', background: 'radial-gradient(ellipse at top right, rgba(56,189,248,0.04) 0%, transparent 65%)', filter: 'blur(50px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.45) 100%)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)', backgroundSize: '48px 48px' }} />

      <main
        className="relative w-full flex flex-col"
        style={{ maxWidth: '460px' }}
        aria-label="SSO redirect in progress"
        aria-live="polite"
        aria-busy="true"
      >
        <div className="flex flex-col items-center mb-8">
          <AppImage src="/assets/images/app_logo.png" alt="AKAAL logo" width={48} height={48} className="mb-4" style={{ filter: 'drop-shadow(0 2px 8px rgba(37,99,235,0.3))' }} />
          <h1 className="font-bold tracking-widest uppercase text-lg" style={{ color: '#F8FAFC', letterSpacing: '0.18em', fontFamily: "'JetBrains Mono', monospace" }}>AKAAL</h1>
          <p className="text-xs mt-1 tracking-wider" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace" }}>Enterprise Database Migration Platform</p>
        </div>

        <div className="rounded-lg p-8" style={{ background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 1px 0 0 rgba(255,255,255,0.06) inset, 0 8px 40px rgba(0,0,0,0.55), 0 2px 12px rgba(0,0,0,0.35)' }}>
          <div className="flex flex-col items-center text-center">

            {/* Organization logo placeholder */}
            <div
              className="flex items-center justify-center w-16 h-16 rounded-lg mb-5"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
              aria-label="Organization logo"
            >
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true" style={{ color: '#4B5563' }}>
                <rect x="3" y="3" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
                <rect x="15" y="3" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
                <rect x="3" y="15" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
                <rect x="15" y="15" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
              </svg>
            </div>

            <h2 className="font-semibold text-base mb-1" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>
              Signing in with SSO
            </h2>
            <p className="text-xs" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>
              Redirecting to your identity provider…
            </p>

            {/* Progress bar */}
            <div className="w-full mt-6 mb-2">
              <div
                className="w-full h-1 rounded-full overflow-hidden"
                style={{ background: '#1F2937' }}
                role="progressbar"
                aria-valuenow={progress}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`SSO redirect progress: ${progress}%`}
              >
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${progress}%`,
                    background: 'linear-gradient(90deg, #2563EB 0%, #38BDF8 100%)',
                    transition: 'width 0.08s linear',
                  }}
                />
              </div>
            </div>
            <p className="text-xs mb-6" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>
              {progress}%
            </p>

            {/* Status steps */}
            <div
              className="w-full rounded-md p-3 mb-6 text-left"
              style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid #2A3647' }}
            >
              {[
                { label: 'Authenticating request', done: progress >= 20 },
                { label: 'Contacting identity provider', done: progress >= 50 },
                { label: 'Awaiting authorization', done: progress >= 80 },
              ].map((step, i) => (
                <div key={i} className={`flex items-center gap-2.5 ${i > 0 ? 'mt-2.5' : ''}`}>
                  <div
                    className="flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center"
                    style={{ background: step.done ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.04)', border: `1px solid ${step.done ? 'rgba(34,197,94,0.3)' : '#2A3647'}` }}
                    aria-hidden="true"
                  >
                    {step.done ? (
                      <svg width="8" height="8" viewBox="0 0 8 8" fill="none" aria-hidden="true">
                        <path d="M1.5 4l2 2 3-3" stroke="#22C55E" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : (
                      <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: '#374151' }} />
                    )}
                  </div>
                  <span className="text-xs" style={{ color: step.done ? '#CBD5E1' : '#64748B', fontFamily: "'Inter', sans-serif" }}>
                    {step.label}
                  </span>
                </div>
              ))}
            </div>

            {/* Cancel button */}
            <button
              type="button"
              onClick={handleCancel}
              disabled={isCancelling}
              aria-label="Cancel SSO redirect and return to sign in"
              className="w-full flex items-center justify-center gap-2 text-xs font-medium rounded-md py-2.5 transition-all duration-200 focus:outline-none focus-visible:ring-2 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => { if (!isCancelling) { e.currentTarget.style.borderColor = '#4B5563'; e.currentTarget.style.color = '#CBD5E1'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; } }}
              onMouseLeave={e => { if (!isCancelling) { e.currentTarget.style.borderColor = '#374151'; e.currentTarget.style.color = '#94A3B8'; e.currentTarget.style.background = 'transparent'; } }}
            >
              {isCancelling ? 'Cancelling…' : 'Cancel'}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between mt-5 px-1" aria-label="Application metadata">
          <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>Version 1.0.0</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#22C55E' }} aria-hidden="true" />
            <span className="text-xs" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>Production</span>
          </div>
        </div>
      </main>
    </div>
  );
}
