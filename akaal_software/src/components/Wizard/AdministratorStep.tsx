import { useState, useCallback, useMemo, type FC } from 'react';
import { FormField } from '../Form/FormField';
import { TextInput } from '../Form/TextInput';
import styles from './Wizard.module.css';

interface PasswordStrengthResult {
  score: number; // 0–4
  label: string;
}

function computeStrength(password: string): PasswordStrengthResult {
  if (!password) return { score: 0, label: '' };
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const labels = ['', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
  return { score: Math.min(score, 4), label: labels[Math.min(score, 5)] };
}

const segmentClasses = [
  styles.strengthSegmentWeak,
  styles.strengthSegmentFair,
  styles.strengthSegmentGood,
  styles.strengthSegmentStrong,
];

export interface AdministratorStepProps {
  adminFullName: string;
  adminUsername: string;
  adminPassword: string;
  adminConfirmPassword: string;
  adminFullNameError?: string;
  adminUsernameError?: string;
  adminPasswordError?: string;
  adminConfirmPasswordError?: string;
  onChange: (field: 'adminFullName' | 'adminUsername' | 'adminPassword' | 'adminConfirmPassword', value: string) => void;
  onBlur: (field: string) => void;
}

export const AdministratorStep: FC<AdministratorStepProps> = ({
  adminFullName,
  adminUsername,
  adminPassword,
  adminConfirmPassword,
  adminFullNameError,
  adminUsernameError,
  adminPasswordError,
  adminConfirmPasswordError,
  onChange,
  onBlur,
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const strength = useMemo(() => computeStrength(adminPassword), [adminPassword]);

  const handleUsernameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      // Normalize username: lowercase, strip invalid chars live
      const raw = e.target.value.replace(/[^a-z0-9_.\-]/gi, '').toLowerCase();
      onChange('adminUsername', raw);
    },
    [onChange]
  );

  return (
    <>
      <div className={styles.adminGrid}>
        <FormField
          label="Full Name"
          htmlFor="admin-full-name"
          error={adminFullNameError}
        >
          <TextInput
            id="admin-full-name"
            type="text"
            autoComplete="name"
            value={adminFullName}
            onChange={(e) => onChange('adminFullName', e.target.value)}
            onBlur={() => onBlur('adminFullName')}
            hasError={Boolean(adminFullNameError)}
            placeholder="Aalok Singh"
            maxLength={80}
            autoFocus
          />
        </FormField>

        <FormField
          label="Username"
          htmlFor="admin-username"
          error={adminUsernameError}
          helperText={adminUsernameError ? undefined : 'Lowercase letters, numbers, underscores, dots, hyphens.'}
        >
          <TextInput
            id="admin-username"
            type="text"
            autoComplete="username"
            value={adminUsername}
            onChange={handleUsernameChange}
            onBlur={() => onBlur('adminUsername')}
            hasError={Boolean(adminUsernameError)}
            placeholder="aalok"
            maxLength={32}
          />
        </FormField>
      </div>

      <FormField
        label="Password"
        htmlFor="admin-password"
        error={adminPasswordError}
      >
        <div className={styles.passwordInputRow}>
          <TextInput
            id="admin-password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={adminPassword}
            onChange={(e) => onChange('adminPassword', e.target.value)}
            onBlur={() => onBlur('adminPassword')}
            hasError={Boolean(adminPasswordError)}
            placeholder="Create a strong password"
            style={{ paddingRight: '40px', width: '100%' }}
          />
          <button
            type="button"
            className={styles.passwordToggleBtn}
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            tabIndex={-1}
          >
            {showPassword ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            )}
          </button>
        </div>

        {adminPassword && (
          <>
            <div className={styles.strengthBar} aria-hidden="true">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className={[
                    styles.strengthSegment,
                    i < strength.score ? segmentClasses[strength.score - 1] : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                />
              ))}
            </div>
            {strength.label && (
              <div className={styles.strengthLabel}>{strength.label}</div>
            )}
          </>
        )}
      </FormField>

      <FormField
        label="Confirm Password"
        htmlFor="admin-confirm-password"
        error={adminConfirmPasswordError}
      >
        <div className={styles.passwordInputRow}>
          <TextInput
            id="admin-confirm-password"
            type={showConfirm ? 'text' : 'password'}
            autoComplete="new-password"
            value={adminConfirmPassword}
            onChange={(e) => onChange('adminConfirmPassword', e.target.value)}
            onBlur={() => onBlur('adminConfirmPassword')}
            hasError={Boolean(adminConfirmPasswordError)}
            placeholder="Repeat your password"
            style={{ paddingRight: '40px', width: '100%' }}
          />
          <button
            type="button"
            className={styles.passwordToggleBtn}
            onClick={() => setShowConfirm((v) => !v)}
            aria-label={showConfirm ? 'Hide confirm password' : 'Show confirm password'}
            tabIndex={-1}
          >
            {showConfirm ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            )}
          </button>
        </div>
      </FormField>
    </>
  );
};
