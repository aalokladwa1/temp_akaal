'use client';

import React, { useState, useRef, useEffect, useId } from 'react';
import AppImage from '@/components/ui/AppImage';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

// ─── Types ────────────────────────────────────────────────────────────────────

type ErrorType = 'invalid_credentials' | 'server_unavailable' | 'network_disconnected' | 'session_expired' | null;

interface FormState {
  email: string;
  password: string;
  rememberMe: boolean;
}

interface FieldErrors {
  email: string;
  password: string;
}

const ERROR_MESSAGES: Record<NonNullable<ErrorType>, { title: string; detail: string }> = {
  invalid_credentials: {
    title: 'Authentication Failed',
    detail: 'Invalid email or password. Please verify your credentials and try again.',
  },
  server_unavailable: {
    title: 'Service Unavailable',
    detail: 'The authentication service is temporarily unavailable. Please try again in a few moments.',
  },
  network_disconnected: {
    title: 'Network Error',
    detail: 'Unable to reach the server. Check your network connection and try again.',
  },
  session_expired: {
    title: 'Session Expired',
    detail: 'Your previous session has expired. Please sign in again to continue.',
  },
};

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

function AlertBanner({ type, onDismiss }: { type: NonNullable<ErrorType>; onDismiss: () => void }) {
  const msg = ERROR_MESSAGES[type];
  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      className="flex items-start gap-3 rounded-lg p-3.5"
      style={{
        background: 'rgba(239,68,68,0.08)',
        border: '1px solid rgba(239,68,68,0.25)',
        animation: 'modal-enter 0.2s cubic-bezier(0.16,1,0.3,1) forwards',
      }}
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: '#EF4444' }}>
        <path d="M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-3a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 5Zm0 6.5a.875.875 0 1 1 0-1.75.875.875 0 0 1 0 1.75Z" fill="currentColor" />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold" style={{ color: '#EF4444', fontFamily: "'JetBrains Mono', monospace" }}>{msg.title}</p>
        <p className="text-xs mt-0.5 leading-relaxed" style={{ color: '#94A3B8', fontFamily: "'Inter', sans-serif" }}>{msg.detail}</p>
      </div>
      <button type="button" onClick={onDismiss} aria-label="Dismiss error" className="flex-shrink-0 transition-opacity hover:opacity-70 focus:outline-none focus-visible:ring-1 rounded" style={{ color: '#64748B' }}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
          <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}

// ─── Premium Background SVG ───────────────────────────────────────────────────

function PremiumBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 overflow-hidden">
      {/* Deep base */}
      <div className="absolute inset-0" style={{ background: '#080E1A' }} />

      {/* Primary ambient light — upper left */}
      <div className="absolute" style={{
        top: '-15%', left: '-10%', width: '70%', height: '70%',
        background: 'radial-gradient(ellipse at top left, rgba(37,99,235,0.14) 0%, rgba(37,99,235,0.06) 35%, transparent 70%)',
        filter: 'blur(60px)',
      }} />

      {/* Secondary ambient — upper right */}
      <div className="absolute" style={{
        top: '-8%', right: '-8%', width: '50%', height: '50%',
        background: 'radial-gradient(ellipse at top right, rgba(56,189,248,0.08) 0%, rgba(56,189,248,0.03) 40%, transparent 70%)',
        filter: 'blur(70px)',
      }} />

      {/* Tertiary accent — bottom center */}
      <div className="absolute" style={{
        bottom: '-10%', left: '30%', width: '40%', height: '40%',
        background: 'radial-gradient(ellipse at bottom, rgba(59,130,246,0.07) 0%, transparent 65%)',
        filter: 'blur(50px)',
      }} />

      {/* Abstract geometric grid */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
        <defs>
          <pattern id="grid-fine" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M 48 0 L 0 0 0 48" fill="none" stroke="rgba(255,255,255,0.028)" strokeWidth="0.5"/>
          </pattern>
          <pattern id="grid-major" width="192" height="192" patternUnits="userSpaceOnUse">
            <path d="M 192 0 L 0 0 0 192" fill="none" stroke="rgba(255,255,255,0.045)" strokeWidth="0.5"/>
          </pattern>
          <radialGradient id="grid-fade" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="white" stopOpacity="1"/>
            <stop offset="70%" stopColor="white" stopOpacity="0.4"/>
            <stop offset="100%" stopColor="white" stopOpacity="0"/>
          </radialGradient>
          <mask id="grid-mask">
            <rect width="100%" height="100%" fill="url(#grid-fade)"/>
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid-fine)" mask="url(#grid-mask)" />
        <rect width="100%" height="100%" fill="url(#grid-major)" mask="url(#grid-mask)" />
      </svg>

      {/* Abstract topology nodes */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
        {/* Connection lines */}
        <line x1="15%" y1="20%" x2="35%" y2="35%" stroke="rgba(59,130,246,0.12)" strokeWidth="0.8"/>
        <line x1="35%" y1="35%" x2="60%" y2="25%" stroke="rgba(59,130,246,0.10)" strokeWidth="0.8"/>
        <line x1="60%" y1="25%" x2="80%" y2="40%" stroke="rgba(56,189,248,0.08)" strokeWidth="0.8"/>
        <line x1="35%" y1="35%" x2="45%" y2="60%" stroke="rgba(59,130,246,0.08)" strokeWidth="0.8"/>
        <line x1="60%" y1="25%" x2="55%" y2="55%" stroke="rgba(59,130,246,0.07)" strokeWidth="0.8"/>
        <line x1="80%" y1="40%" x2="75%" y2="65%" stroke="rgba(56,189,248,0.06)" strokeWidth="0.8"/>
        <line x1="10%" y1="65%" x2="30%" y2="75%" stroke="rgba(59,130,246,0.07)" strokeWidth="0.8"/>
        <line x1="30%" y1="75%" x2="45%" y2="60%" stroke="rgba(59,130,246,0.08)" strokeWidth="0.8"/>
        <line x1="75%" y1="65%" x2="85%" y2="80%" stroke="rgba(56,189,248,0.06)" strokeWidth="0.8"/>
        {/* Nodes */}
        <circle cx="15%" cy="20%" r="2.5" fill="rgba(59,130,246,0.35)"/>
        <circle cx="35%" cy="35%" r="3.5" fill="rgba(59,130,246,0.30)"/>
        <circle cx="60%" cy="25%" r="2.5" fill="rgba(56,189,248,0.28)"/>
        <circle cx="80%" cy="40%" r="2" fill="rgba(56,189,248,0.22)"/>
        <circle cx="45%" cy="60%" r="3" fill="rgba(59,130,246,0.25)"/>
        <circle cx="55%" cy="55%" r="2" fill="rgba(59,130,246,0.20)"/>
        <circle cx="75%" cy="65%" r="2.5" fill="rgba(56,189,248,0.20)"/>
        <circle cx="10%" cy="65%" r="2" fill="rgba(59,130,246,0.18)"/>
        <circle cx="30%" cy="75%" r="2" fill="rgba(59,130,246,0.18)"/>
        <circle cx="85%" cy="80%" r="1.5" fill="rgba(56,189,248,0.15)"/>
        {/* Outer rings on key nodes */}
        <circle cx="35%" cy="35%" r="7" fill="none" stroke="rgba(59,130,246,0.12)" strokeWidth="0.8"/>
        <circle cx="45%" cy="60%" r="6" fill="none" stroke="rgba(59,130,246,0.10)" strokeWidth="0.8"/>
      </svg>

      {/* Abstract geometric shapes — subtle */}
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
        {/* Large hexagon outline — top right */}
        <polygon points="82%,5% 92%,11% 92%,23% 82%,29% 72%,23% 72%,11%" fill="none" stroke="rgba(56,189,248,0.06)" strokeWidth="0.8"/>
        {/* Medium hexagon — bottom left */}
        <polygon points="8%,70% 15%,66% 22%,70% 22%,78% 15%,82% 8%,78%" fill="none" stroke="rgba(59,130,246,0.07)" strokeWidth="0.8"/>
        {/* Diamond — right side */}
        <polygon points="88%,55% 93%,62% 88%,69% 83%,62%" fill="none" stroke="rgba(56,189,248,0.06)" strokeWidth="0.8"/>
        {/* Small squares — scattered */}
        <rect x="5%" y="30%" width="12" height="12" fill="none" stroke="rgba(59,130,246,0.08)" strokeWidth="0.6" transform="rotate(15, 5%, 30%)"/>
        <rect x="88%" y="15%" width="10" height="10" fill="none" stroke="rgba(56,189,248,0.07)" strokeWidth="0.6" transform="rotate(30, 88%, 15%)"/>
        <rect x="65%" y="80%" width="14" height="14" fill="none" stroke="rgba(59,130,246,0.06)" strokeWidth="0.6" transform="rotate(20, 65%, 80%)"/>
      </svg>

      {/* Edge vignette */}
      <div className="absolute inset-0" style={{
        background: 'radial-gradient(ellipse at 50% 45%, transparent 35%, rgba(0,0,0,0.55) 100%)',
      }} />

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-48" style={{
        background: 'linear-gradient(to top, rgba(8,14,26,0.8) 0%, transparent 100%)',
      }} />
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SignInPage() {
  const emailId = useId();
  const passwordId = useId();
  const rememberMeId = useId();
  const router = useRouter();

  const [form, setForm] = useState<FormState>({ email: '', password: '', rememberMe: false });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({ email: '', password: '' });
  const [serverError, setServerError] = useState<ErrorType>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [mounted, setMounted] = useState(false);

  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setMounted(true);
    emailRef.current?.focus();
  }, []);

  function validateEmail(value: string): string {
    if (!value.trim()) return 'Email address is required.';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) return 'Enter a valid email address.';
    return '';
  }

  function validatePassword(value: string): string {
    if (!value) return 'Password is required.';
    return '';
  }

  function validateAll(): boolean {
    const emailErr = validateEmail(form.email);
    const passwordErr = validatePassword(form.password);
    setFieldErrors({ email: emailErr, password: passwordErr });
    setTouched({ email: true, password: true });
    return !emailErr && !passwordErr;
  }

  function handleEmailChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setForm(f => ({ ...f, email: val }));
    if (touched.email) setFieldErrors(fe => ({ ...fe, email: validateEmail(val) }));
    if (serverError) setServerError(null);
  }

  function handlePasswordChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setForm(f => ({ ...f, password: val }));
    if (touched.password) setFieldErrors(fe => ({ ...fe, password: validatePassword(val) }));
    if (serverError) setServerError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validateAll()) return;
    setIsLoading(true);
    setServerError(null);
    try {
      await new Promise<void>((_, reject) =>
        setTimeout(() => reject(new Error('invalid_credentials')), 1800)
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '';
      if (msg === 'server_unavailable') setServerError('server_unavailable');
      else if (msg === 'network_disconnected') setServerError('network_disconnected');
      else setServerError('invalid_credentials');
    } finally {
      setIsLoading(false);
    }
  }

  function handleSSOClick() {
    router.push('/sso-redirect');
  }

  const isDisabled = isLoading;
  const emailHasError = touched.email && !!fieldErrors.email;
  const passwordHasError = touched.password && !!fieldErrors.password;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden">
      <PremiumBackground />

      {/* Auth card entrance animation */}
      <main
        className="relative w-full flex flex-col"
        style={{
          maxWidth: '440px',
          opacity: mounted ? 1 : 0,
          transform: mounted ? 'translateY(0)' : 'translateY(16px)',
          transition: 'opacity 0.4s cubic-bezier(0.16,1,0.3,1), transform 0.4s cubic-bezier(0.16,1,0.3,1)',
        }}
        aria-label="Sign in to AKAAL"
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="mb-4 relative"
            style={{
              filter: 'drop-shadow(0 0 16px rgba(59,130,246,0.4)) drop-shadow(0 2px 8px rgba(0,0,0,0.5))',
            }}
          >
            <AppImage src="/assets/images/app_logo.png" alt="AKAAL logo" width={52} height={52} />
          </div>
          <h1
            className="font-bold tracking-widest uppercase"
            style={{
              color: '#F8FAFC',
              letterSpacing: '0.22em',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '18px',
              textShadow: '0 0 30px rgba(59,130,246,0.3)',
            }}
          >
            AKAAL
          </h1>
          <p className="text-xs mt-1.5 tracking-wider" style={{ color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>
            Enterprise Database Migration Platform
          </p>
        </div>

        {/* Glassmorphism card */}
        <div
          className="rounded-xl p-8"
          style={{
            background: 'rgba(15, 23, 42, 0.75)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.09)',
            boxShadow: [
              '0 0 0 1px rgba(255,255,255,0.04) inset',
              '0 1px 0 rgba(255,255,255,0.08) inset',
              '0 24px 64px rgba(0,0,0,0.7)',
              '0 8px 24px rgba(0,0,0,0.4)',
              '0 0 80px rgba(37,99,235,0.06)',
            ].join(', '),
          }}
        >
          {/* Card heading */}
          <div className="mb-6">
            <h2 className="font-semibold" style={{ color: '#F1F5F9', fontFamily: "'Inter', sans-serif", fontSize: '15px' }}>
              Sign in to your account
            </h2>
            <p className="text-xs mt-1" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>
              Access your migration workspace
            </p>
          </div>

          {/* Server error banner */}
          {serverError && (
            <div className="mb-5">
              <AlertBanner type={serverError} onDismiss={() => setServerError(null)} />
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate aria-label="Sign in form">
            {/* Email */}
            <div className="mb-4">
              <label
                htmlFor={emailId}
                className="block text-xs font-medium mb-1.5"
                style={{ color: emailHasError ? '#EF4444' : '#94A3B8', fontFamily: "'Inter', sans-serif", letterSpacing: '0.02em' }}
              >
                Email Address
              </label>
              <input
                ref={emailRef}
                id={emailId}
                type="email"
                name="email"
                autoComplete="email"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                value={form.email}
                onChange={handleEmailChange}
                onBlur={() => { setTouched(t => ({ ...t, email: true })); setFieldErrors(fe => ({ ...fe, email: validateEmail(form.email) })); }}
                disabled={isDisabled}
                aria-required="true"
                aria-invalid={emailHasError}
                aria-describedby={emailHasError ? `${emailId}-error` : undefined}
                placeholder="you@company.com"
                className="w-full text-sm rounded-lg px-3 py-2.5 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: `1px solid ${emailHasError ? 'rgba(239,68,68,0.6)' : 'rgba(255,255,255,0.1)'}`,
                  color: '#F1F5F9',
                  caretColor: '#3B82F6',
                  fontFamily: "'Inter', sans-serif",
                  boxShadow: emailHasError ? '0 0 0 3px rgba(239,68,68,0.12)' : 'none',
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                }}
                onFocus={e => {
                  if (!emailHasError) {
                    e.currentTarget.style.borderColor = 'rgba(59,130,246,0.6)';
                    e.currentTarget.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.15)';
                    e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                  }
                }}
                onBlurCapture={e => {
                  if (!emailHasError) {
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                    e.currentTarget.style.boxShadow = 'none';
                    e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                  }
                }}
              />
              {emailHasError && (
                <p id={`${emailId}-error`} role="alert" className="text-xs mt-1.5" style={{ color: '#EF4444', fontFamily: "'Inter', sans-serif" }}>
                  {fieldErrors.email}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="mb-4">
              <label
                htmlFor={passwordId}
                className="block text-xs font-medium mb-1.5"
                style={{ color: passwordHasError ? '#EF4444' : '#94A3B8', fontFamily: "'Inter', sans-serif", letterSpacing: '0.02em' }}
              >
                Password
              </label>
              <div className="relative">
                <input
                  id={passwordId}
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  autoComplete="current-password"
                  value={form.password}
                  onChange={handlePasswordChange}
                  onBlur={() => { setTouched(t => ({ ...t, password: true })); setFieldErrors(fe => ({ ...fe, password: validatePassword(form.password) })); }}
                  disabled={isDisabled}
                  aria-required="true"
                  aria-invalid={passwordHasError}
                  aria-describedby={passwordHasError ? `${passwordId}-error` : undefined}
                  placeholder="••••••••••••"
                  className="w-full text-sm rounded-lg px-3 py-2.5 pr-10 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    border: `1px solid ${passwordHasError ? 'rgba(239,68,68,0.6)' : 'rgba(255,255,255,0.1)'}`,
                    color: '#F1F5F9',
                    caretColor: '#3B82F6',
                    fontFamily: "'Inter', sans-serif",
                    boxShadow: passwordHasError ? '0 0 0 3px rgba(239,68,68,0.12)' : 'none',
                    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                  }}
                  onFocus={e => {
                    if (!passwordHasError) {
                      e.currentTarget.style.borderColor = 'rgba(59,130,246,0.6)';
                      e.currentTarget.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.15)';
                      e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                    }
                  }}
                  onBlurCapture={e => {
                    if (!passwordHasError) {
                      e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                      e.currentTarget.style.boxShadow = 'none';
                      e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                    }
                  }}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword(v => !v)}
                  disabled={isDisabled}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transition-opacity hover:opacity-80 focus:outline-none disabled:opacity-30"
                  style={{ color: '#64748B' }}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                      <path d="M1 1l14 14M6.5 6.6A2 2 0 0 0 9.4 9.5M3.4 3.5A7.9 7.9 0 0 0 1.5 8c1.3 3 4 5 6.5 5a7.5 7.5 0 0 0 3.6-.9M6 2.2A7.5 7.5 0 0 1 8 2c2.5 0 5.2 2 6.5 5a8 8 0 0 1-1.5 2.3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                      <path d="M1.5 8C2.8 5 5.5 3 8 3s5.2 2 6.5 5c-1.3 3-4 5-6.5 5S2.8 11 1.5 8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
                      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.2"/>
                    </svg>
                  )}
                </button>
              </div>
              {passwordHasError && (
                <p id={`${passwordId}-error`} role="alert" className="text-xs mt-1.5" style={{ color: '#EF4444', fontFamily: "'Inter', sans-serif" }}>
                  {fieldErrors.password}
                </p>
              )}
            </div>

            {/* Remember Me + Forgot Password */}
            <div className="flex items-center justify-between mb-6">
              <label htmlFor={rememberMeId} className="flex items-center gap-2 cursor-pointer select-none">
                <div className="relative flex-shrink-0">
                  <input
                    id={rememberMeId}
                    type="checkbox"
                    name="rememberMe"
                    checked={form.rememberMe}
                    onChange={e => setForm(f => ({ ...f, rememberMe: e.target.checked }))}
                    disabled={isDisabled}
                    aria-label="Remember me for 30 days"
                    className="sr-only"
                  />
                  <div
                    className="w-4 h-4 rounded flex items-center justify-center"
                    style={{
                      background: form.rememberMe ? '#3B82F6' : 'rgba(255,255,255,0.06)',
                      border: `1px solid ${form.rememberMe ? '#3B82F6' : 'rgba(255,255,255,0.15)'}`,
                      transition: 'background 0.15s ease, border-color 0.15s ease',
                      opacity: isDisabled ? 0.5 : 1,
                    }}
                    aria-hidden="true"
                  >
                    {form.rememberMe && (
                      <svg width="10" height="8" viewBox="0 0 10 8" fill="none" aria-hidden="true">
                        <path d="M1 4l2.5 2.5L9 1" stroke="#ffffff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                </div>
                <span className="text-xs" style={{ color: '#64748B', fontFamily: "'Inter', sans-serif" }}>
                  Remember me for 30 days
                </span>
              </label>

              <Link
                href="/forgot-password"
                className="text-xs transition-colors focus:outline-none focus-visible:underline"
                style={{ color: '#3B82F6', fontFamily: "'Inter', sans-serif" }}
                onMouseEnter={e => (e.currentTarget as HTMLAnchorElement).style.color = '#60A5FA'}
                onMouseLeave={e => (e.currentTarget as HTMLAnchorElement).style.color = '#3B82F6'}
              >
                Forgot password?
              </Link>
            </div>

            {/* Sign In button */}
            <button
              type="submit"
              disabled={isDisabled}
              aria-label={isLoading ? 'Signing in, please wait' : 'Sign in to AKAAL'}
              aria-busy={isLoading}
              className="w-full flex items-center justify-center gap-2 text-sm font-semibold rounded-lg py-2.5 focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed"
              style={{
                background: isDisabled ? 'rgba(59,130,246,0.5)' : 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
                color: '#ffffff',
                fontFamily: "'Inter', sans-serif",
                letterSpacing: '0.01em',
                boxShadow: isDisabled ? 'none' : '0 1px 0 rgba(255,255,255,0.1) inset, 0 4px 16px rgba(37,99,235,0.35)',
                transition: 'filter 0.15s ease, box-shadow 0.15s ease, transform 0.1s ease',
              }}
              onMouseEnter={e => {
                if (!isDisabled) {
                  e.currentTarget.style.filter = 'brightness(1.1)';
                  e.currentTarget.style.boxShadow = '0 1px 0 rgba(255,255,255,0.1) inset, 0 6px 20px rgba(37,99,235,0.45)';
                  e.currentTarget.style.transform = 'translateY(-0.5px)';
                }
              }}
              onMouseLeave={e => {
                if (!isDisabled) {
                  e.currentTarget.style.filter = '';
                  e.currentTarget.style.boxShadow = '0 1px 0 rgba(255,255,255,0.1) inset, 0 4px 16px rgba(37,99,235,0.35)';
                  e.currentTarget.style.transform = '';
                }
              }}
              onMouseDown={e => { if (!isDisabled) e.currentTarget.style.transform = 'translateY(0)'; }}
              onMouseUp={e => { if (!isDisabled) e.currentTarget.style.transform = 'translateY(-0.5px)'; }}
            >
              {isLoading && <Spinner />}
              <span>{isLoading ? 'Authenticating…' : 'Sign In'}</span>
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5" aria-hidden="true">
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.08)' }} />
            <span className="text-xs" style={{ color: '#475569', fontFamily: "'Inter', sans-serif" }}>OR</span>
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.08)' }} />
          </div>

          {/* SSO button */}
          <button
            type="button"
            onClick={handleSSOClick}
            disabled={isDisabled}
            aria-label="Continue with Single Sign-On"
            className="w-full flex items-center justify-center gap-2 text-xs font-medium rounded-lg py-2.5 focus:outline-none focus-visible:ring-2 disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#94A3B8',
              fontFamily: "'Inter', sans-serif",
              transition: 'background 0.15s ease, border-color 0.15s ease, color 0.15s ease',
            }}
            onMouseEnter={e => {
              if (!isDisabled) {
                e.currentTarget.style.background = 'rgba(255,255,255,0.07)';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.18)';
                e.currentTarget.style.color = '#CBD5E1';
              }
            }}
            onMouseLeave={e => {
              if (!isDisabled) {
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                e.currentTarget.style.color = '#94A3B8';
              }
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <rect x="1" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.2"/>
              <rect x="8" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.2"/>
              <rect x="1" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M10.5 8v5M8 10.5h5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
            </svg>
            Continue with SSO
          </button>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-5 px-1" aria-label="Application metadata">
          <span className="text-xs" style={{ color: '#334155', fontFamily: "'JetBrains Mono', monospace" }}>v1.0.0</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#22C55E' }} aria-hidden="true" />
            <span className="text-xs" style={{ color: '#334155', fontFamily: "'JetBrains Mono', monospace" }}>Production</span>
          </div>
        </div>
      </main>
    </div>
  );
}
