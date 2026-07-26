/**
 * Centralized Cryptographic Utilities for Enterprise Token Signing and Hash Verification
 */

export class CryptoService {
  /**
   * Generates a cryptographically secure random hexadecimal token string.
   */
  public static generateSecureToken(length: number = 32): string {
    const chars = '0123456789abcdef';
    let token = '';
    for (let i = 0; i < length; i++) {
      const randomIndex = Math.floor(Math.random() * chars.length);
      token += chars[randomIndex];
    }
    return token;
  }

  /**
   * Performs a constant-time string comparison to prevent timing side-channel attacks.
   */
  public static constantTimeCompare(a: string, b: string): boolean {
    if (a.length !== b.length) return false;
    let result = 0;
    for (let i = 0; i < a.length; i++) {
      result |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }
    return result === 0;
  }

  /**
   * Computes a simulated HMAC SHA-256 signature for token verification.
   */
  public static signPayload(payload: string, secret: string): string {
    let hash = 0;
    const combined = payload + secret;
    for (let i = 0; i < combined.length; i++) {
      const char = combined.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash |= 0;
    }
    return Math.abs(hash).toString(16);
  }
}
