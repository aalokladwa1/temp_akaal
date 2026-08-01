'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { MFAService, MFAEnrollment } from '@/security/mfa/mfa.service';

export default function MFAEnrollmentPage() {
  const [enrollment] = useState<MFAEnrollment>(() => MFAService.generateMFAEnrollment('sarah.chen@company.com'));
  const [verificationCode, setVerificationCode] = useState('');
  const [isVerified, setIsVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (MFAService.verifyTOTP(verificationCode)) {
      setIsVerified(true);
      setError(null);
    } else {
      setError('Invalid 6-digit TOTP verification code. Please try again.');
    }
  };

  return (
    <div className="min-h-screen p-6 flex flex-col justify-center items-center" style={{ background: 'var(--akaal-bg)', color: 'var(--akaal-text)', fontFamily: "'Inter', sans-serif" }}>
      <div className="max-w-md w-full p-6 rounded-xl" style={{ background: 'var(--akaal-surface)', border: '1px solid var(--akaal-border)', boxShadow: '0 8px 32px var(--akaal-shadow)' }}>
        <h1 className="text-xl font-bold mb-1">MFA Security Enrollment</h1>
        <p className="text-xs mb-4" style={{ color: 'var(--akaal-text-muted)' }}>Secure your enterprise AKAAL account with Time-based One-Time Passwords (TOTP).</p>

        {isVerified ? (
          <div className="p-4 rounded-lg text-center space-y-3" style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)' }}>
            <span className="text-2xl">✓</span>
            <p className="text-sm font-semibold text-green-400">MFA Successfully Enabled!</p>
            <p className="text-xs text-gray-300">Your account is now protected by two-factor authentication.</p>
            <Link href="/dashboard" className="inline-block mt-2 px-4 py-2 bg-blue-600 text-white rounded text-xs font-semibold">
              Return to Dashboard
            </Link>
          </div>
        ) : (
          <form onSubmit={handleVerify} className="space-y-4">
            <div className="p-3 rounded-lg flex flex-col items-center justify-center text-center gap-2" style={{ background: 'var(--akaal-surface-elevated)', border: '1px dashed var(--akaal-border)' }}>
              <p className="text-xs font-mono font-bold" style={{ color: 'var(--akaal-primary)' }}>SECRET: {enrollment.secret}</p>
              <p className="text-xs" style={{ color: 'var(--akaal-text-muted)', fontSize: '10px' }}>Scan this key in Okta Verify, 1Password, or Google Authenticator</p>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1">6-Digit Verification Code</label>
              <input
                type="text"
                maxLength={6}
                placeholder="123456"
                value={verificationCode}
                onChange={e => setVerificationCode(e.target.value)}
                className="w-full text-center tracking-widest text-lg font-mono py-2 rounded border outline-none"
                style={{ background: 'var(--akaal-input-bg)', borderColor: 'var(--akaal-border)', color: 'var(--akaal-text)' }}
              />
            </div>

            {error && <p className="text-xs font-semibold text-red-400">{error}</p>}

            <button type="submit" className="w-full py-2 rounded font-semibold text-xs text-white bg-blue-600 hover:bg-blue-700 transition-all">
              Verify & Enable MFA
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
