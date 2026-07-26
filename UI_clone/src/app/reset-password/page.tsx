'use client';

import React, { useState, useRef, useEffect, useId } from 'react';
import Link from 'next/link';

type ResetState = 'idle' | 'loading' | 'success';

interface PasswordRequirement {
  id: string;
  label: string;
  test: (pw: string) => boolean;
}

const REQUIREMENTS: PasswordRequirement[] = [
  { id: 'length', label: 'At least 12 characters', test: pw => pw.length >= 12 },
  { id: 'upper', label: 'One uppercase letter', test: pw => /[A-Z]/.test(pw) },
  { id: 'lower', label: 'One lowercase letter', test: pw => /[a-z]/.test(pw) },
  { id: 'number', label: 'One number', test: pw => /[0-9]/.test(pw) },
  { id: 'special', label: 'One special character', test: pw => /[^A-Za-z0-9]/.test(pw) },
];

function getStrength(pw: string): { score: number; label: string; color: string } {
  const passed = REQUIREMENTS.filter(r => r.test(pw)).length;
  if (pw.length === 0) return { score: 0, label: '', color: 'var(--akaal-border)' };
  if (passed <= 1) return { score: 1, label: 'Weak', color: 'var(--akaal-error)' };
  if (passed === 2) return { score: 2, label: 'Fair', color: 'var(--akaal-warning)' };
  if (passed === 3) return { score: 3, label: 'Good', color: 'var(--akaal-info)' };
  if (passed === 4) return { score: 4, label: 'Strong', color: 'var(--akaal-success)' };
  return { score: 5, label: 'Very Strong', color: 'var(--akaal-success)' };
}

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

export default function ResetPasswordPage() {
  const newPasswordId = useId();
  const confirmPasswordId = useId();

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [touched, setTouched] = useState({ new: false, confirm: false });
  const [errors, setErrors] = useState({ new: '', confirm: '' });
  const [resetState, setResetState] = useState<ResetState>('idle');
  const newPasswordRef = useRef<HTMLInputElement>(null);

  useEffect(() => { newPasswordRef.current?.focus(); }, []);

  const strength = getStrength(newPassword);
  const allRequirementsMet = REQUIREMENTS.every(r => r.test(newPassword));

  function validateNew(pw: string): string {
    if (!pw) return 'New password is required.';
    if (!REQUIREMENTS.every(r => r.test(pw))) return 'Password does not meet all requirements.';
    return '';
  }

  function validateConfirm(pw: string): string {
    if (!pw) return 'Please confirm your password.';
    if (pw !== newPassword) return 'Passwords do not match.';
    return '';
  }

  function handleNewChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setNewPassword(val);
    if (touched.new) setErrors(er => ({ ...er, new: validateNew(val) }));
    if (touched.confirm && confirmPassword) setErrors(er => ({ ...er, confirm: confirmPassword !== val ? 'Passwords do not match.' : '' }));
  }

  function handleConfirmChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setConfirmPassword(val);
    if (touched.confirm) setErrors(er => ({ ...er, confirm: validateConfirm(val) }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched({ new: true, confirm: true });
    const newErr = validateNew(newPassword);
    const confirmErr = validateConfirm(confirmPassword);
    setErrors({ new: newErr, confirm: confirmErr });
    if (newErr || confirmErr) return;
    setResetState('loading');
    try {
      await new Promise(resolve => setTimeout(resolve, 1600));
      setResetState('success');
    } catch {
      setResetState('idle');
    }
  }

  const isLoading = resetState === 'loading';
  const newHasError = touched.new && !!errors.new;
  const confirmHasError = touched.confirm && !!errors.confirm;

  if (resetState === 'success') {
    return (
      <PageShell>
        <div className="rounded-xl p-8" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }}>
          <div className="flex flex-col items-center text-center py-2">
            <div className="flex items-center justify-center w-12 h-12 rounded-xl mb-5" style={{ background: 'var(--akaal-success-bg)', border: '1px solid rgba(34,197,94,0.2)' }}>
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true" style={{ color: 'var(--akaal-success)' }}>
                <path d="M4 11l5 5 9-9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h2 className="font-semibold text-base mb-2" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Password reset successful</h2>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>
              Your password has been updated. You can now sign in with your new credentials.
            </p>
            <div className="w-full h-px my-6" style={{ background: 'var(--akaal-border)' }} />
            <Link
              href="/sign-in"
              className="w-full flex items-center justify-center gap-2 text-sm font-semibold rounded-lg py-2.5 focus:outline-none focus-visible:ring-2"
              style={{ background: 'var(--akaal-primary)', color: '#ffffff', fontFamily: "'Inter', sans-serif", boxShadow: '0 1px 3px var(--akaal-shadow-sm)', transition: 'filter 0.15s ease' }}
              onMouseEnter={e => (e.currentTarget as HTMLAnchorElement).style.filter = 'brightness(1.1)'}
              onMouseLeave={e => (e.currentTarget as HTMLAnchorElement).style.filter = ''}
            >
              Sign In Now
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
          <h2 className="font-semibold text-base" style={{ color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>Set new password</h2>
          <p className="text-xs mt-1" style={{ color: 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif" }}>Choose a strong password for your account.</p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {/* New Password */}
          <div className="mb-4">
            <label htmlFor={newPasswordId} className="block text-xs font-medium mb-1.5" style={{ color: newHasError ? 'var(--akaal-error)' : 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>
              New Password
            </label>
            <div className="relative">
              <input
                ref={newPasswordRef}
                id={newPasswordId}
                type={showNew ? 'text' : 'password'}
                value={newPassword}
                onChange={handleNewChange}
                onBlur={() => { setTouched(t => ({ ...t, new: true })); setErrors(er => ({ ...er, new: validateNew(newPassword) })); }}
                disabled={isLoading}
                aria-required="true"
                aria-invalid={newHasError}
                placeholder="••••••••••••"
                className="w-full text-sm rounded-lg px-3 py-2.5 pr-10 outline-none disabled:opacity-50"
                style={{
                  background: 'var(--akaal-input-bg)',
                  border: `1px solid ${newHasError ? 'var(--akaal-error)' : 'var(--akaal-input-border)'}`,
                  color: 'var(--akaal-text)',
                  caretColor: 'var(--akaal-primary)',
                  fontFamily: "'Inter', sans-serif",
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                }}
                onFocus={e => { if (!newHasError) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--akaal-focus-ring)'; } }}
                onBlurCapture={e => { if (!newHasError) { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; } }}
              />
              <button type="button" tabIndex={-1} onClick={() => setShowNew(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 hover:opacity-70 focus:outline-none" style={{ color: 'var(--akaal-text-muted)' }}>
                {showNew ? (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M1 1l14 14M6.5 6.6A2 2 0 0 0 9.4 9.5M3.4 3.5A7.9 7.9 0 0 0 1.5 8c1.3 3 4 5 6.5 5a7.5 7.5 0 0 0 3.6-.9M6 2.2A7.5 7.5 0 0 1 8 2c2.5 0 5.2 2 6.5 5a8 8 0 0 1-1.5 2.3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M1.5 8C2.8 5 5.5 3 8 3s5.2 2 6.5 5c-1.3 3-4 5-6.5 5S2.8 11 1.5 8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.2"/></svg>
                )}
              </button>
            </div>
            {newHasError && <p role="alert" className="text-xs mt-1.5" style={{ color: 'var(--akaal-error)', fontFamily: "'Inter', sans-serif" }}>{errors.new}</p>}
          </div>

          {/* Strength meter */}
          {newPassword.length > 0 && (
            <div className="mb-4">
              <div className="flex gap-1 mb-1.5">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="flex-1 h-1 rounded-full" style={{ background: i <= strength.score ? strength.color : 'var(--akaal-border)', transition: 'background 0.2s ease' }} />
                ))}
              </div>
              {strength.label && <p className="text-xs" style={{ color: strength.color, fontFamily: "'Inter', sans-serif" }}>{strength.label}</p>}
            </div>
          )}

          {/* Requirements */}
          <div className="mb-4 space-y-1.5">
            {REQUIREMENTS.map(req => {
              const met = req.test(newPassword);
              return (
                <div key={req.id} className="flex items-center gap-2">
                  <div className="flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center" style={{ background: met ? 'var(--akaal-success-bg)' : 'var(--akaal-hover-bg)', border: `1px solid ${met ? 'rgba(34,197,94,0.3)' : 'var(--akaal-border)'}`, transition: 'all 0.15s ease' }}>
                    {met && <svg width="8" height="8" viewBox="0 0 8 8" fill="none" aria-hidden="true"><path d="M1.5 4l2 2 3-3" stroke="var(--akaal-success)" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                  </div>
                  <span className="text-xs" style={{ color: met ? 'var(--akaal-success)' : 'var(--akaal-text-muted)', fontFamily: "'Inter', sans-serif", transition: 'color 0.15s ease' }}>{req.label}</span>
                </div>
              );
            })}
          </div>

          {/* Confirm Password */}
          <div className="mb-5">
            <label htmlFor={confirmPasswordId} className="block text-xs font-medium mb-1.5" style={{ color: confirmHasError ? 'var(--akaal-error)' : 'var(--akaal-text-secondary)', fontFamily: "'Inter', sans-serif" }}>
              Confirm Password
            </label>
            <div className="relative">
              <input
                id={confirmPasswordId}
                type={showConfirm ? 'text' : 'password'}
                value={confirmPassword}
                onChange={handleConfirmChange}
                onBlur={() => { setTouched(t => ({ ...t, confirm: true })); setErrors(er => ({ ...er, confirm: validateConfirm(confirmPassword) })); }}
                disabled={isLoading}
                aria-required="true"
                aria-invalid={confirmHasError}
                placeholder="••••••••••••"
                className="w-full text-sm rounded-lg px-3 py-2.5 pr-10 outline-none disabled:opacity-50"
                style={{
                  background: 'var(--akaal-input-bg)',
                  border: `1px solid ${confirmHasError ? 'var(--akaal-error)' : 'var(--akaal-input-border)'}`,
                  color: 'var(--akaal-text)',
                  caretColor: 'var(--akaal-primary)',
                  fontFamily: "'Inter', sans-serif",
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                }}
                onFocus={e => { if (!confirmHasError) { e.currentTarget.style.borderColor = 'var(--akaal-primary)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--akaal-focus-ring)'; } }}
                onBlurCapture={e => { if (!confirmHasError) { e.currentTarget.style.borderColor = 'var(--akaal-input-border)'; e.currentTarget.style.boxShadow = 'none'; } }}
              />
              <button type="button" tabIndex={-1} onClick={() => setShowConfirm(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 hover:opacity-70 focus:outline-none" style={{ color: 'var(--akaal-text-muted)' }}>
                {showConfirm ? (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M1 1l14 14M6.5 6.6A2 2 0 0 0 9.4 9.5M3.4 3.5A7.9 7.9 0 0 0 1.5 8c1.3 3 4 5 6.5 5a7.5 7.5 0 0 0 3.6-.9M6 2.2A7.5 7.5 0 0 1 8 2c2.5 0 5.2 2 6.5 5a8 8 0 0 1-1.5 2.3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M1.5 8C2.8 5 5.5 3 8 3s5.2 2 6.5 5c-1.3 3-4 5-6.5 5S2.8 11 1.5 8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.2"/></svg>
                )}
              </button>
            </div>
            {confirmHasError && <p role="alert" className="text-xs mt-1.5" style={{ color: 'var(--akaal-error)', fontFamily: "'Inter', sans-serif" }}>{errors.confirm}</p>}
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
            <span>{isLoading ? 'Resetting…' : 'Reset Password'}</span>
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
