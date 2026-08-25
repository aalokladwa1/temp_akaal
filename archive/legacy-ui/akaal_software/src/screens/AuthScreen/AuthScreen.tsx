import { useState, useRef, type FC, type FormEvent } from 'react';
import { useAuthentication } from '../../hooks/useAuthentication';
import { FormField } from '../../components/Form/FormField';
import { TextInput } from '../../components/Form/TextInput';
import { PrimaryButton, SecondaryButton } from '../../components/Button';
import { OrganizationModal } from '../../components/Auth/OrganizationModal';
import { ForgotPasswordModal } from '../../components/Auth/ForgotPasswordModal';
import backgroundImage from '../../assets/akaal-enterprise-bg.svg';
import styles from '../../components/Auth/Auth.module.css';

export interface AuthBannerError {
  title: string;
  message: string;
}

export const AuthScreen: FC = () => {
  const { lastUser, providers, login } = useAuthentication();
  const [username, setUsername] = useState(lastUser?.username || 'admin');
  const [password, setPassword] = useState('');
  const [rememberDevice, setRememberDevice] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isOrgModalOpen, setIsOrgModalOpen] = useState(false);
  const [isForgotPasswordModalOpen, setIsForgotPasswordModalOpen] = useState(false);

  // Error States
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [bannerError, setBannerError] = useState<AuthBannerError | null>(null);

  const passwordInputRef = useRef<HTMLInputElement>(null);

  const greetingTitle = lastUser?.displayName
    ? `Welcome back, ${lastUser.displayName}`
    : 'Secure Sign In';

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    // Reset error banners
    setBannerError(null);
    let hasFieldErrors = false;

    // Inline empty field validation
    if (!username.trim()) {
      setUsernameError('Username is required.');
      hasFieldErrors = true;
    } else {
      setUsernameError(null);
    }

    if (!password.trim()) {
      setPasswordError('Password is required.');
      hasFieldErrors = true;
    } else {
      setPasswordError(null);
    }

    if (hasFieldErrors) return;

    setIsSubmitting(true);

    try {
      await login(username, password, rememberDevice);
    } catch (err: unknown) {
      const rawError =
        typeof err === 'string'
          ? err
          : err instanceof Error
          ? err.message
          : String(err);

      // Clear password field & refocus
      setPassword('');
      setTimeout(() => {
        passwordInputRef.current?.focus();
      }, 0);

      // Categorize into Enterprise User-Facing Messaging
      const isLockout =
        rawError.toLowerCase().includes('locked') ||
        rawError.toLowerCase().includes('failed attempts') ||
        rawError.toLowerCase().includes('rate');

      const isInvalidCredentials =
        rawError.toLowerCase().includes('invalid') ||
        rawError.toLowerCase().includes('incorrect') ||
        rawError.toLowerCase().includes('password') ||
        rawError.toLowerCase().includes('user');

      if (isLockout) {
        setBannerError({
          title: 'Sign in failed',
          message: 'Too many failed attempts. Please wait before trying again.',
        });
      } else if (isInvalidCredentials) {
        setBannerError({
          title: 'Sign in failed',
          message:
            "The username or password you entered is incorrect.\n\nPlease try again or reset your password if you've forgotten it.",
        });
      } else {
        setBannerError({
          title: 'Something went wrong',
          message: "We couldn't complete your sign-in.\n\nPlease try again.",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`enterprise-light-theme ${styles.authWindow}`}>
      <img
        src={backgroundImage}
        alt=""
        aria-hidden="true"
        className={styles.bgImage}
      />

      <div className={styles.card}>
        <header className={styles.brandHeader}>
          <h1 className={styles.brandTitle}>AKAAL</h1>
          <p className={styles.workspaceSub}>Production Workspace</p>
          <h2 className={styles.greetingHeader}>{greetingTitle}</h2>
        </header>

        {bannerError && (
          <div
            className={styles.errorBanner}
            role="alert"
            aria-live="assertive"
          >
            <h4 className={styles.errorBannerTitle}>{bannerError.title}</h4>
            {bannerError.message.split('\n\n').map((paragraph, index) => (
              <p key={index} className={styles.errorBannerText}>
                {paragraph}
              </p>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.formBody}>
          <FormField
            label="Username"
            htmlFor="auth-username-input"
            error={usernameError || undefined}
          >
            <TextInput
              id="auth-username-input"
              value={username}
              disabled={isSubmitting}
              onChange={(e) => {
                setUsername(e.target.value);
                if (usernameError) setUsernameError(null);
                if (bannerError) setBannerError(null);
              }}
              placeholder="Username or email"
              hasError={Boolean(usernameError)}
              autoFocus
            />
          </FormField>

          <FormField
            label="Password"
            htmlFor="auth-password-input"
            error={passwordError || undefined}
          >
            <TextInput
              ref={passwordInputRef}
              id="auth-password-input"
              type="password"
              value={password}
              disabled={isSubmitting}
              onChange={(e) => {
                setPassword(e.target.value);
                if (passwordError) setPasswordError(null);
                if (bannerError) setBannerError(null);
              }}
              placeholder="••••••••••••"
              hasError={Boolean(passwordError || bannerError)}
            />
          </FormField>

          <div className={styles.checkboxRow}>
            <input
              type="checkbox"
              id="auth-remember-device"
              className={styles.checkboxInput}
              checked={rememberDevice}
              disabled={isSubmitting}
              onChange={(e) => setRememberDevice(e.target.checked)}
            />
            <label
              htmlFor="auth-remember-device"
              className={styles.checkboxLabel}
            >
              Remember this device
            </label>
          </div>

          <PrimaryButton
            type="submit"
            disabled={isSubmitting}
            className={styles.primaryButton}
          >
            {isSubmitting ? 'Signing you in...' : 'Sign In'}
          </PrimaryButton>

          <SecondaryButton
            type="button"
            disabled={isSubmitting}
            onClick={() => setIsOrgModalOpen(true)}
            className={styles.secondaryButton}
          >
            Sign in with Organization ▼
          </SecondaryButton>

          <button
            type="button"
            className={styles.forgotButton}
            onClick={() => setIsForgotPasswordModalOpen(true)}
          >
            Forgot Password?
          </button>
        </form>

        <footer className={styles.footerContainer}>
          <span>v0.1.0-alpha</span>
          <span>Secure DPAPI Session</span>
          <span>Enterprise</span>
        </footer>
      </div>

      <OrganizationModal
        isOpen={isOrgModalOpen}
        providers={providers}
        onClose={() => setIsOrgModalOpen(false)}
        onSelectProvider={(_p) => {
          setIsOrgModalOpen(false);
        }}
      />

      <ForgotPasswordModal
        isOpen={isForgotPasswordModalOpen}
        onClose={() => setIsForgotPasswordModalOpen(false)}
      />
    </div>
  );
};
