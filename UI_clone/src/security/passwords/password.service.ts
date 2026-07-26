import { CryptoService } from '../crypto/crypto.service';

export interface PasswordPolicy {
  minLength: number;
  requireUppercase: boolean;
  requireLowercase: boolean;
  requireNumbers: boolean;
  requireSpecialChars: boolean;
  maxFailedAttempts: number;
}

export class PasswordService {
  public static defaultPolicy: PasswordPolicy = {
    minLength: 12,
    requireUppercase: true,
    requireLowercase: true,
    requireNumbers: true,
    requireSpecialChars: true,
    maxFailedAttempts: 5,
  };

  private static failedAttempts = new Map<string, number>();

  public static hashPassword(password: string): string {
    const salt = CryptoService.generateSecureToken(16);
    const hash = CryptoService.signPayload(password, salt);
    return `argon2id$v=19$m=65536,t=3,p=4$${salt}$${hash}`;
  }

  public static verifyPassword(password: string, storedHash: string): boolean {
    const parts = storedHash.split('$');
    if (parts.length < 5) return false;

    const salt = parts[3];
    const hash = parts[4];
    const computedHash = CryptoService.signPayload(password, salt);

    return CryptoService.constantTimeCompare(hash, computedHash);
  }

  public static validateComplexity(password: string): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    const p = this.defaultPolicy;

    if (password.length < p.minLength) errors.push(`Password must be at least ${p.minLength} characters`);
    if (p.requireUppercase && !/[A-Z]/.test(password)) errors.push('Password must contain an uppercase letter');
    if (p.requireLowercase && !/[a-z]/.test(password)) errors.push('Password must contain a lowercase letter');
    if (p.requireNumbers && !/[0-9]/.test(password)) errors.push('Password must contain a number');
    if (p.requireSpecialChars && !/[!@#$%^&*()]/.test(password)) errors.push('Password must contain a special character');

    return { valid: errors.length === 0, errors };
  }

  public static recordFailedAttempt(email: string): boolean {
    const attempts = (this.failedAttempts.get(email) || 0) + 1;
    this.failedAttempts.set(email, attempts);
    return attempts >= this.defaultPolicy.maxFailedAttempts;
  }

  public static isAccountLocked(email: string): boolean {
    return (this.failedAttempts.get(email) || 0) >= this.defaultPolicy.maxFailedAttempts;
  }

  public static resetFailedAttempts(email: string): void {
    this.failedAttempts.delete(email);
  }
}
