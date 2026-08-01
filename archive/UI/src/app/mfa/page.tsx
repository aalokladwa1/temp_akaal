'use client';

import React, { useState, useRef, useEffect, useId, useCallback } from 'react';
import AppImage from '@/components/ui/AppImage';
import Link from 'next/link';

// ─── Types ────────────────────────────────────────────────────────────────────

type MFAError = 'invalid_code' | 'expired_code' | 'too_many_attempts' | null;

// ─── Spinner ──────────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <svg className="animate-spin" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.3" strokeWidth="2" />
      <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

// ─── Alert Banner ─────────────────────────────────────────────────────────────

const MFA_ERRORS: Record<NonNullable<MFAError>, { title: string; detail: string }> = {
  invalid_code: {
    title: 'Invalid Code',
    detail: 'The verification code you entered is incorrect. Please try again.',
  },
  expired_code: {
    title: 'Code Expired',
    detail: 'This verification code has expired. Request a new code to continue.',
  },
  too_many_attempts: {
    title: 'Too Many Attempts',
    detail: 'You have exceeded the maximum number of attempts. Please wait before trying again.',
  },
};

function AlertBanner({ type, onDismiss }: { type: NonNullable<MFAError>; onDismiss: () => void }) {
  const msg = MFA_ERRORS[type];
  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      className="flex items-start gap-3 rounded-md p-3"
      style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.22)' }}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: '#EF4444' }}>
        <path d="M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-3a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 5Zm0 6.5a.875.875 0 1 1 0-1.75.875.875 0 0 1 0 1.75Z" fill="currentColor" />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold tracking-wide" style={{ color: '#EF4444', fontFamily: "'JetBrains Mono', monospace" }}>{msg.title}</p>
        <p className="text-xs mt-0.5" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>{msg.detail}</p>
      </div>
      <button type="button" onClick={onDismiss} aria-label="Dismiss error" className="flex-shrink-0 transition-opacity hover:opacity-70 focus:outline-none focus-visible:ring-1 rounded" style={{ color: '#64748B' }}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
          <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

const RESEND_SECONDS = 30;
const CODE_LENGTH = 6;

export default function MFAPage() {
  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(''));
  const [isLoading, setIsLoading] = useState(false);
  const [mfaError, setMfaError] = useState<MFAError>(null);
  const [countdown, setCountdown] = useState(RESEND_SECONDS);
  const [isResending, setIsResending] = useState(false);
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState('');
  const [recoveryError, setRecoveryError] = useState('');

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const recoveryId = useId();

  // Countdown timer
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  // Auto-focus first digit on mount
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const code = digits.join('');
  const isComplete = code.length === CODE_LENGTH && digits.every(d => d !== '');
  const isDisabled = isLoading || isResending;

  const handleDigitChange = useCallback((index: number, value: string) => {
    // Handle paste of full code
    if (value.length > 1) {
      const pasted = value.replace(/\D/g, '').slice(0, CODE_LENGTH);
      if (pasted.length > 0) {
        const newDigits = Array(CODE_LENGTH).fill('');
        pasted.split('').forEach((ch, i) => { newDigits[i] = ch; });
        setDigits(newDigits);
        setMfaError(null);
        const nextIndex = Math.min(pasted.length, CODE_LENGTH - 1);
        setTimeout(() => inputRefs.current[nextIndex]?.focus(), 0);
      }
      return;
    }
    const digit = value.replace(/\D/g, '').slice(-1);
    const newDigits = [...digits];
    newDigits[index] = digit;
    setDigits(newDigits);
    setMfaError(null);
    if (digit && index < CODE_LENGTH - 1) {
      setTimeout(() => inputRefs.current[index + 1]?.focus(), 0);
    }
  }, [digits]);

  const handleDigitKeyDown = useCallback((index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (digits[index]) {
        const newDigits = [...digits];
        newDigits[index] = '';
        setDigits(newDigits);
      } else if (index > 0) {
        const newDigits = [...digits];
        newDigits[index - 1] = '';
        setDigits(newDigits);
        setTimeout(() => inputRefs.current[index - 1]?.focus(), 0);
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < CODE_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  }, [digits]);

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    if (!isComplete || isDisabled) return;
    setIsLoading(true);
    setMfaError(null);
    try {
      await new Promise<void>((_, reject) =>
        setTimeout(() => reject(new Error('invalid_code')), 1500)
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '';
      if (msg === 'expired_code') setMfaError('expired_code');
      else if (msg === 'too_many_attempts') setMfaError('too_many_attempts');
      else setMfaError('invalid_code');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleResend() {
    if (countdown > 0 || isDisabled) return;
    setIsResending(true);
    setMfaError(null);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      setCountdown(RESEND_SECONDS);
      setDigits(Array(CODE_LENGTH).fill(''));
      setTimeout(() => inputRefs.current[0]?.focus(), 0);
    } finally {
      setIsResending(false);
    }
  }

  function handleRecoverySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!recoveryCode.trim()) {
      setRecoveryError('Recovery code is required.');
      return;
    }
    setRecoveryError('');
    // Recovery code flow
  }

  const formatCountdown = (s: number) => `0:${s.toString().padStart(2, '0')}`;

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden"
      style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}
    >
      {/* Background lighting */}
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-10%', left: '-10%', width: '65%', height: '65%', background: 'radial-gradient(ellipse at top left, rgba(37,99,235,0.09) 0%, rgba(37,99,235,0.04) 35%, transparent 70%)', filter: 'blur(40px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-5%', right: '-5%', width: '40%', height: '40%', background: 'radial-gradient(ellipse at top right, rgba(56,189,248,0.04) 0%, transparent 65%)', filter: 'blur(50px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.45) 100%)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)', backgroundSize: '48px 48px' }} />

      <main className="relative w-full flex flex-col" style={{ maxWidth: '460px' }} aria-label="Multi-factor authentication">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <AppImage src="/assets/images/app_logo.png" alt="AKAAL logo" width={48} height={48} className="mb-4" style={{ filter: 'drop-shadow(0 2px 8px rgba(37,99,235,0.3))' }} />
          <h1 className="font-bold tracking-widest uppercase text-lg" style={{ color: '#F8FAFC', letterSpacing: '0.18em', fontFamily: "'JetBrains Mono', monospace" }}>AKAAL</h1>
          <p className="text-xs mt-1 tracking-wider" style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace" }}>Enterprise Database Migration Platform</p>
        </div>

        {/* Card */}
        <div className="rounded-lg p-8" style={{ background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 1px 0 0 rgba(255,255,255,0.06) inset, 0 8px 40px rgba(0,0,0,0.55), 0 2px 12px rgba(0,0,0,0.35)' }}>

          {!showRecovery ? (
            <>
              {/* Header */}
              <div className="mb-6">
                {/* Shield icon */}
                <div className="flex items-center justify-center w-10 h-10 rounded-md mb-4" style={{ background: 'rgba(37,99,235,0.12)', border: '1px solid rgba(37,99,235,0.2)' }}>
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true" style={{ color: '#2563EB' }}>
                    <path d="M10 2L3 5v5c0 4.418 3.134 8.55 7 9.5C13.866 18.55 17 14.418 17 10V5l-7-3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                    <path d="M7 10l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <h2 className="font-semibold text-base" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>Two-Factor Authentication</h2>
                <p className="text-xs mt-1" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>Enter the 6-digit code from your authenticator app</p>
              </div>

              {/* Error banner */}
              {mfaError && (
                <div className="mb-5">
                  <AlertBanner type={mfaError} onDismiss={() => setMfaError(null)} />
                </div>
              )}

              {/* Code input form */}
              <form onSubmit={handleVerify} noValidate aria-label="Verification code form">
                <div className="mb-5">
                  <label className="block text-xs font-medium mb-3 tracking-wide" style={{ color: '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>
                    Verification Code
                  </label>
                  <div className="flex gap-2 justify-between" role="group" aria-label="6-digit verification code">
                    {digits.map((digit, i) => (
                      <input
                        key={i}
                        ref={el => { inputRefs.current[i] = el; }}
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength={6}
                        value={digit}
                        onChange={e => handleDigitChange(i, e.target.value)}
                        onKeyDown={e => handleDigitKeyDown(i, e)}
                        onFocus={e => {
                          e.currentTarget.style.border = '1px solid #2563EB';
                          e.currentTarget.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.45)';
                        }}
                        onBlur={e => {
                          e.currentTarget.style.border = mfaError ? '1px solid #EF4444' : '1px solid #374151';
                          e.currentTarget.style.boxShadow = mfaError ? '0 0 0 3px rgba(239,68,68,0.12)' : 'none';
                        }}
                        disabled={isDisabled}
                        aria-label={`Digit ${i + 1} of 6`}
                        className="text-center text-lg font-semibold rounded-md outline-none transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                          width: '44px',
                          height: '52px',
                          background: '#111827',
                          border: `1px solid ${mfaError ? '#EF4444' : '#374151'}`,
                          color: '#F8FAFC',
                          caretColor: '#2563EB',
                          fontFamily: "'JetBrains Mono', monospace",
                          boxShadow: mfaError ? '0 0 0 3px rgba(239,68,68,0.12)' : 'none',
                        }}
                      />
                    ))}
                  </div>
                </div>

                {/* Resend row */}
                <div className="flex items-center justify-between mb-6">
                  <span className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>
                    {countdown > 0 ? (
                      <>Resend code in <span style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace" }}>{formatCountdown(countdown)}</span></>
                    ) : (
                      "Didn't receive a code?"
                    )}
                  </span>
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={countdown > 0 || isDisabled}
                    className="text-xs font-medium transition-colors focus:outline-none focus-visible:underline disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{ color: countdown > 0 ? '#64748B' : '#2563EB', fontFamily: "'Inter', sans-serif" }}
                    onMouseEnter={e => { if (countdown === 0 && !isDisabled) e.currentTarget.style.color = '#1D4ED8'; }}
                    onMouseLeave={e => { if (countdown === 0 && !isDisabled) e.currentTarget.style.color = '#2563EB'; }}
                  >
                    {isResending ? 'Sending…' : 'Resend Code'}
                  </button>
                </div>

                {/* Verify button */}
                <button
                  type="submit"
                  disabled={!isComplete || isDisabled}
                  aria-busy={isLoading}
                  aria-label={isLoading ? 'Verifying code, please wait' : 'Verify code'}
                  className="w-full flex items-center justify-center gap-2 text-sm font-semibold rounded-md py-2.5 transition-all duration-200 focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed"
                  style={{
                    background: (!isComplete || isDisabled) ? 'rgba(37,99,235,0.5)' : '#2563EB',
                    color: '#ffffff',
                    fontFamily: "'Inter', sans-serif",
                    letterSpacing: '0.01em',
                    boxShadow: (!isComplete || isDisabled) ? 'none' : '0 1px 3px rgba(0,0,0,0.3), 0 1px 0 rgba(255,255,255,0.06) inset',
                  }}
                  onMouseEnter={e => { if (isComplete && !isDisabled) { e.currentTarget.style.background = '#1D4ED8'; } }}
                  onMouseLeave={e => { if (isComplete && !isDisabled) { e.currentTarget.style.background = '#2563EB'; } }}
                  onMouseDown={e => { if (isComplete && !isDisabled) e.currentTarget.style.background = '#1E40AF'; }}
                  onMouseUp={e => { if (isComplete && !isDisabled) e.currentTarget.style.background = '#1D4ED8'; }}
                >
                  {isLoading && <Spinner />}
                  <span>{isLoading ? 'Verifying…' : 'Verify Code'}</span>
                </button>
              </form>

              {/* Divider */}
              <div className="flex items-center gap-3 my-5" aria-hidden="true">
                <div className="flex-1 h-px" style={{ background: '#2A3647' }} />
                <span className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>OR</span>
                <div className="flex-1 h-px" style={{ background: '#2A3647' }} />
              </div>

              {/* Recovery code option */}
              <button
                type="button"
                onClick={() => setShowRecovery(true)}
                className="w-full flex items-center justify-center gap-2 text-xs font-medium rounded-md py-2.5 transition-all duration-200 focus:outline-none focus-visible:ring-2"
                style={{ background: 'transparent', border: '1px solid #374151', color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#4B5563'; e.currentTarget.style.color = '#CBD5E1'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#374151'; e.currentTarget.style.color = '#94A3B8'; e.currentTarget.style.background = 'transparent'; }}
              >
                Use recovery code instead
              </button>
            </>
          ) : (
            <>
              {/* Recovery code view */}
              <div className="mb-6">
                <button
                  type="button"
                  onClick={() => { setShowRecovery(false); setRecoveryCode(''); setRecoveryError(''); }}
                  className="flex items-center gap-1.5 text-xs mb-4 transition-colors focus:outline-none focus-visible:underline"
                  style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}
                  onMouseEnter={e => e.currentTarget.style.color = '#94A3B8'}
                  onMouseLeave={e => e.currentTarget.style.color = '#64748B'}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                    <path d="M8 1L3 6l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Back to verification code
                </button>
                <h2 className="font-semibold text-base" style={{ color: '#F8FAFC', fontFamily: "'Inter', sans-serif" }}>Recovery Code</h2>
                <p className="text-xs mt-1" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>Enter one of your saved recovery codes</p>
              </div>

              <form onSubmit={handleRecoverySubmit} noValidate>
                <div className="mb-5">
                  <label htmlFor={recoveryId} className="block text-xs font-medium mb-1.5 tracking-wide" style={{ color: recoveryError ? '#EF4444' : '#CBD5E1', fontFamily: "'Inter', sans-serif" }}>
                    Recovery Code
                  </label>
                  <input
                    id={recoveryId}
                    type="text"
                    value={recoveryCode}
                    onChange={e => { setRecoveryCode(e.target.value); setRecoveryError(''); }}
                    placeholder="XXXX-XXXX-XXXX-XXXX"
                    aria-invalid={!!recoveryError}
                    aria-describedby={recoveryError ? `${recoveryId}-error` : undefined}
                    className="w-full text-sm rounded-md px-3 py-2.5 transition-all duration-150 outline-none"
                    style={{ background: '#111827', border: `1px solid ${recoveryError ? '#EF4444' : '#374151'}`, color: '#F8FAFC', caretColor: '#2563EB', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.08em', boxShadow: recoveryError ? '0 0 0 3px rgba(239,68,68,0.12)' : 'none' }}
                    onFocus={e => { if (!recoveryError) { e.currentTarget.style.border = '1px solid #2563EB'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.45)'; } }}
                    onBlur={e => { if (!recoveryError) { e.currentTarget.style.border = '1px solid #374151'; e.currentTarget.style.boxShadow = 'none'; } }}
                  />
                  {recoveryError && <p id={`${recoveryId}-error`} role="alert" className="text-xs mt-1.5" style={{ color: '#EF4444', fontFamily: "'Inter', sans-serif" }}>{recoveryError}</p>}
                </div>
                <button
                  type="submit"
                  className="w-full flex items-center justify-center gap-2 text-sm font-semibold rounded-md py-2.5 transition-all duration-200 focus:outline-none focus-visible:ring-2"
                  style={{ background: '#2563EB', color: '#ffffff', fontFamily: "'Inter', sans-serif", letterSpacing: '0.01em', boxShadow: '0 1px 3px rgba(0,0,0,0.3), 0 1px 0 rgba(255,255,255,0.06) inset' }}
                  onMouseEnter={e => { e.currentTarget.style.background = '#1D4ED8'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = '#2563EB'; }}
                  onMouseDown={e => { e.currentTarget.style.background = '#1E40AF'; }}
                  onMouseUp={e => { e.currentTarget.style.background = '#1D4ED8'; }}
                >
                  Verify Recovery Code
                </button>
              </form>
            </>
          )}

          {/* Back to sign in */}
          <div className="mt-5 text-center">
            <Link
              href="/sign-in"
              className="text-xs transition-colors focus:outline-none focus-visible:underline"
              style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => (e.currentTarget as HTMLAnchorElement).style.color = '#94A3B8'}
              onMouseLeave={e => (e.currentTarget as HTMLAnchorElement).style.color = '#64748B'}
            >
              ← Back to Sign In
            </Link>
          </div>
        </div>

        {/* Footer */}
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
