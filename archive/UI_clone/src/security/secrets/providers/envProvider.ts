/**
 * AKAAL Secret Provider — Environment Variables
 * Stage 7.3
 *
 * Reads secrets from process.env. Supports prefix namespacing.
 * Server-side only for real values; client-side returns null for all keys.
 */

import { SecretProviderConfig, SecretProviderHealth } from '../secretTypes';

export interface SecretProviderInterface {
  readonly providerType: string;
  readonly displayName: string;
  getSecret(key: string): Promise<string | null>;
  setSecret(key: string, value: string): Promise<void>;
  deleteSecret(key: string): Promise<void>;
  listSecrets(prefix?: string): Promise<string[]>;
  testConnectivity(): Promise<SecretProviderHealth>;
}

export class EnvironmentSecretProvider implements SecretProviderInterface {
  public readonly providerType = 'env' as const;
  public readonly displayName = 'Environment Variables';

  private readonly config: SecretProviderConfig;
  private readonly prefix: string;

  constructor(config: SecretProviderConfig) {
    this.config = config;
    this.prefix = '';
  }

  public async getSecret(key: string): Promise<string | null> {
    if (typeof process === 'undefined' || !process.env) return null;
    const fullKey = this.prefix ? `${this.prefix}_${key}` : key;
    return process.env[fullKey] ?? null;
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  public async setSecret(_key: string, _value: string): Promise<void> {
    // Environment variables are read-only at runtime
    throw new Error('EnvironmentSecretProvider: cannot write to environment variables at runtime. Set them in your deployment configuration.');
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  public async deleteSecret(_key: string): Promise<void> {
    throw new Error('EnvironmentSecretProvider: cannot delete environment variables at runtime.');
  }

  public async listSecrets(prefix?: string): Promise<string[]> {
    if (typeof process === 'undefined' || !process.env) return [];
    const allKeys = Object.keys(process.env);
    if (!prefix) return allKeys;
    return allKeys.filter((k) => k.startsWith(prefix));
  }

  public async testConnectivity(): Promise<SecretProviderHealth> {
    const start = Date.now();
    const isAvailable = typeof process !== 'undefined' && !!process.env;
    const keyCount = isAvailable ? Object.keys(process.env).length : 0;
    const latencyMs = Date.now() - start;

    return {
      providerId: 'env',
      providerType: 'env',
      displayName: this.displayName,
      status: isAvailable ? 'healthy' : 'unreachable',
      latencyMs,
      lastChecked: new Date().toISOString(),
      lastSuccess: isAvailable ? new Date().toISOString() : undefined,
      retryCount: 0,
      providerVersion: 'process.env',
      authStatus: 'authenticated',
      availability: isAvailable ? 100 : 0,
      failureReason: isAvailable ? undefined : `No environment available. Keys found: ${keyCount}`,
    };
  }

  public isConfigured(): boolean {
    return true; // Always available if process.env exists
  }
}
