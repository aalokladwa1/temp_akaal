'use client';

import React, { useState, useRef, useEffect, useId } from 'react';
import Link from 'next/link';

type ForgotState = 'idle' | 'loading' | 'sent' | 'not_found' | 'network_error';

function Spinner() {
  return (
    <svg className="animate-spin" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.3" strokeWidth="2" />
      <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden" style={{ background: 'var(--akaal-bg)', fontFamily: "'Inter', sans-serif" }}>
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-10%', left: '-10%', width: '65%', height: '65%', background: 'radial-gradient(ellipse at top left, rgba(59,130,246,0.09) 0%, rgba(59,130,246,0.04) 35%, transparent 70%)', filter: 'blur(40px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed" style={{ top: '-5%', right: '-5%', width: '40%', height: '40%', background: 'radial-gradient(ellipse at top right, rgba(56,189,248,0.04) 0%, transparent 65%)', filter: 'blur(50px)' }} />
      <div aria-hidden="true" className="pointer-events-none fixed inset-0" style={{ backgroundImage: 'linear-gradient(var(--akaal-border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--akaal-border-subtle) 1px, transparent 1px)', backgroundSize: '48px 48px', opacity: 0.4 }} />
      <main className="relative w-full flex flex-col" style={{ maxWidth: '460px' }}>
        <div className="flex flex-col items-center mb-8">
          <div className="mb-4 w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'var(--akaal-primary-subtle)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-primary)' }}>
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h1 className="font-bold tracking-widest uppercase" style={{ color: 'var(--akaal-text)', letterSpacing: '0.18em', fontFamily: "'JetBrains Mono', monospace", fontSize: '16px' }}>AKAAL</h1>
          <p className="text-xs mt-1 tracking-wider" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>Enterprise Database Migration Platform</p>
        </div>
        {children}
        <div className="flex items-center justify-between mt-5 px-1">
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

export default function ForgotPasswordPage() {
  const emailId = useId();
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [touched, setTouched] = useState(false);
  const [state, setState] = useState<ForgotState>('idle');
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => { emailRef.current?.focus(); }, []);

  function validateEmail(value: string): string {
    if (!value.trim()) return 'Email address is required.';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) return 'Enter a valid email address.';
    return '';
  }

  function handleEmailChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setEmail(val);
    if (touched) setEmailError(validateEmail(val));
    if (state === 'not_found' || state === 'network_error') setState('idle');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    const err = validateEmail(email);
    setEmailError(err);
    if (err) return;
    setState('loading');
    try {
      await new Promise<void>(resolve => setTimeout(() => resolve(), 1800));
      setState('sent');
    } catch {
      setState('network_error');
    }
  }

  const isLoading = state === 'loading';
  const emailHasError = touched && !!emailError;

  if (state === 'sent') {
    return (
      <PageShell>
        <div className="rounded-xl p-8" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }}>
          <div className="flex flex-col items-center text-center py-2">
            <div className="flex items-center justify-center w-12 h-12 rounded-xl mb-5" style={{ background: 'var(--akaal-success-bg)', border: '1px solid rgba(34,197,94,0.2)' }}>
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-success)' }}>
                <path d="M2 6l9 6 9-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <rect x="2" y="4" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
              </svg>
            </div>
            <h2 className="font-semibold text-base mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Check your email</h2>
            <p className="text-xs leading-relaxed mb-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>If an account exists for</p>
            <p className="text-xs font-medium mb-3" style={{ color: 'var(--akaal-text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{email}</p>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>you will receive a password reset link within a few minutes.</p>
            <div className="w-full h-px my-6" style={{ background: 'var(--akaal-border)' }} />
            <p className="text-xs mb-4" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Didn&apos;t receive the email? Check your spam folder or try again.</p>
            <button type="button" onClick={() => setState('idle')} className="text-xs font-medium transition-colors focus:outline-none focus-visible:underline" style={{ color: 'var(--akaal-primary)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => e.currentTarget.style.opacity = '0.8'}
              onMouseLeave={e => e.currentTarget.style.opacity = '1'}
            >
              Try a different email address
            </button>
          </div>
          <div className="mt-5 text-center">
            <Link href="/sign-in" className="text-xs transition-colors focus:outline-none focus-visible:underline" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
              onMouseEnter={e => (e.currentTarget as HTMLAnchorElement).style.color = 'var(--akaal-text-secondary)'}
              onMouseLeave={e => (e.currentTarget as HTMLAnchorElement).style.color = 'var(--akaal-text-muted)'}
            >
              ← Back to Sign In
            </Link>
          </div>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="rounded-xl p-8" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }}>
        <div className="mb-6">
          <h2 className="font-semibold text-base" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Reset your password</h2>
          <p className="text-xs mt-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Enter your email and we&apos;ll send you a reset link.</p>
        </div>

        {state === 'network_error' && (
          <div className="mb-5 flex items-start gap-3 rounded-lg p-3.5" style={{ background: 'var(--akaal-error-bg)', border: '1px solid rgba(239,68,68,0.25)' }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--akaal-error)' }}>
              <path d="M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Z" fill="currentColor" fillOpacity="0.15" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M8 5v4M8 11v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <div>
              <p className="text-xs font-semibold" style={{ color: 'var(--akaal-error)', fontFamily: "'JetBrains Mono', monospace" }}>Network Error</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Unable to reach the server. Please check your connection.</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-5">
            <label htmlFor={emailId} className="block text-xs font-medium mb-1.5" style={{ color: emailHasError ? 'var(--akaal-error)' : 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>
              Email Address
            </label>
            <input
              ref={emailRef}
              id={emailId}
              type="email"
              name="email"
              autoComplete="email"
              value={email}
              onChange={handleEmailChange}
              onBlur={() => { setTouched(true); setEmailError(validateEmail(email)); }}
              disabled={isLoading}
              aria-required="true"
              aria-invalid={emailHasError}
              placeholder="you@company.com"
              className="w-full text-sm rounded-lg px-3 py-2.5 outline-none disabled:opacity-50"
              style={{
                background: 'var(--akaal-input-bg)',
                border: `1px solid ${emailHasError ? 'var(--akaal-error)' : 'var(--akaal-input-border)'}`,
                color: 'var(--akaal-text)',
                caretColor: 'var(--akaal-primary)',
                fontFamily: "'Inter', sans-serif",
                boxShadow: emailHasError ? '0 0 0 3px var(--akaal-error-bg)' : 'none',
                transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
              }}
              onFocus={e => { if (!emailHasError) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--akaal-focus-ring)'; } }}
              onBlurCapture={e => { if (!emailHasError) { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; } }}
            />
            {emailHasError && <p role="alert" className="text-xs mt-1.5" style={{ color: 'var(--akaal-error)', fontFamily: "'Inter', sans-serif" }}>{emailError}</p>}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 text-sm font-semibold rounded-lg py-2.5 focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed"
            style={{
              background: isLoading ? 'rgba(59,130,246,0.5)' : 'var(--akaal-primary)',
              color: '#ffffff',
              fontFamily: "'Inter', sans-serif",
              boxShadow: isLoading ? 'none' : '0 1px 3px var(--akaal-shadow-sm)',
              transition: 'filter 0.15s ease, transform 0.1s ease',
            }}
            onMouseEnter={e => { if (!isLoading) { e.currentTarget.style.filter = 'brightness(1.1)'; e.currentTarget.style.transform = 'translateY(-0.5px)'; } }}
            onMouseLeave={e => { if (!isLoading) { e.currentTarget.style.filter = ''; e.currentTarget.style.transform = ''; } }}
          >
            {isLoading && <Spinner />}
            <span>{isLoading ? 'Sending…' : 'Send Reset Link'}</span>
          </button>
        </form>

        <div className="mt-5 text-center">
          <Link href="/sign-in" className="text-xs transition-colors focus:outline-none focus-visible:underline" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={e => (e.currentTarget as HTMLAnchorElement).style.color = 'var(--akaal-text-secondary)'}
            onMouseLeave={e => (e.currentTarget as HTMLAnchorElement).style.color = 'var(--akaal-text-muted)'}
          >
            ← Back to Sign In
          </Link>
        </div>
      </div>
    </PageShell>
  );
}
