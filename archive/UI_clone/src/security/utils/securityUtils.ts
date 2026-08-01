/**
 * AKAAL Enterprise Security Utilities
 * Stage 7.3
 *
 * Uses only Web Crypto API (globalThis.crypto) — available in Node 18+ and all modern browsers.
 * No manual algorithm implementations.
 */

/**
 * Performs a timing-safe comparison of two strings.
 * Prevents timing side-channel attacks.
 */
export function timingSafeEqual(a: string, b: string): boolean {
  const aBytes = new TextEncoder().encode(a);
  const bBytes = new TextEncoder().encode(b);
  if (aBytes.length !== bBytes.length) {
    // Still iterate to maintain constant time
    let dummy = 0;
    for (let i = 0; i < aBytes.length; i++) {
      dummy |= aBytes[i];
    }
    return false;
  }
  let diff = 0;
  for (let i = 0; i < aBytes.length; i++) {
    diff |= aBytes[i] ^ bBytes[i];
  }
  return diff === 0;
}

/**
 * Securely wipes sensitive string/object fields by overwriting with zeros.
 * Intended for in-memory cleanup of short-lived secret material.
 */
export function secureWipe(obj: Record<string, unknown>): void {
  for (const key of Object.keys(obj)) {
    const val = obj[key];
    if (typeof val === 'string') {
      // Overwrite with null chars — best-effort in managed JS runtimes
      (obj as Record<string, unknown>)[key] = '\x00'.repeat(val.length);
    } else if (typeof val === 'object' && val !== null) {
      secureWipe(val as Record<string, unknown>);
    }
    delete obj[key];
  }
}

/**
 * Generates a cryptographically secure random token of the given byte length,
 * returned as a lowercase hex string.
 */
export function secureRandomToken(byteLength: number = 32): string {
  const bytes = new Uint8Array(byteLength);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Generates a cryptographically secure nonce as a base64url-encoded string.
 */
export function generateNonce(byteLength: number = 16): string {
  const bytes = new Uint8Array(byteLength);
  globalThis.crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

/**
 * Generates a 12-byte AES-GCM Initialization Vector.
 */
export function generateIV(): Uint8Array {
  const iv = new Uint8Array(12);
  globalThis.crypto.getRandomValues(iv);
  return iv;
}

/**
 * Generates a 16-byte random salt for use with PBKDF2 or similar KDFs.
 */
export function generateSalt(byteLength: number = 16): Uint8Array {
  const salt = new Uint8Array(byteLength);
  globalThis.crypto.getRandomValues(salt);
  return salt;
}

/**
 * Generates a cryptographically secure UUID v4.
 */
export function generateSecureUUID(): string {
  const bytes = new Uint8Array(16);
  globalThis.crypto.getRandomValues(bytes);
  // Set version (4) and variant bits
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('');
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join('-');
}

/**
 * Validates that a string value has sufficient entropy.
 * Returns false if the value is too short, too uniform, or obviously weak.
 */
export function validateEntropy(value: string, minLength: number = 16): boolean {
  if (!value || value.length < minLength) return false;

  // Shannon entropy check: require at least 3.5 bits per character
  const freq: Record<string, number> = {};
  for (const ch of value) {
    freq[ch] = (freq[ch] ?? 0) + 1;
  }
  let entropy = 0;
  const len = value.length;
  for (const count of Object.values(freq)) {
    const p = count / len;
    entropy -= p * Math.log2(p);
  }

  return entropy >= 3.5;
}

/**
 * Converts a Uint8Array to a hex string.
 */
export function uint8ArrayToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Converts a hex string to a Uint8Array.
 */
export function hexToUint8Array(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.slice(i, i + 2), 16);
  }
  return bytes;
}

/**
 * Converts a Uint8Array to a base64 string.
 */
export function uint8ArrayToBase64(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes));
}

/**
 * Converts a base64 string to a Uint8Array.
 */
export function base64ToUint8Array(base64: string): Uint8Array {
  const cleaned = base64.replace(/-/g, '+').replace(/_/g, '/').replace(/[^A-Za-z0-9+/=]/g, '');
  const binary = atob(cleaned);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}
