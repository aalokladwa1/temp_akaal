/**
 * AKAAL Secret Provider — Custom Enterprise Provider
 * Stage 7.3
 *
 * A plug-in extensible provider for any enterprise secrets management system
 * that exposes an HTTP REST API.
 * Supports custom auth headers, bearer tokens, and arbitrary metadata.
 */

import { SecretProviderConfig, SecretProviderHealth } from '../secretTypes';
import { SecretProviderInterface } from './envProvider';

interface CustomSecretGetResponse {
  key: string;
  value: string;
  version?: number;
  metadata?: Record<string, string>;
}

interface CustomSecretListResponse {
  keys: string[];
  total?: number;
  nextCursor?: string;
}

export class CustomEnterpriseProvider implements SecretProviderInterface {
  public readonly providerType = 'custom' as const;
  public readonly displayName: string;

  private readonly config: SecretProviderConfig;
  private retryCount: number = 0;
  private lastFailure?: string;
  private lastFailureReason?: string;

  constructor(config: SecretProviderConfig) {
    this.config = config;
    this.displayName = config.displayName || 'Custom Enterprise Provider';
  }

  private get customConfig() {
    return this.config.custom!;
  }

  private get endpoint(): string {
    return this.customConfig.endpoint.replace(/\/$/, '');
  }

  private buildHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };

    if (this.customConfig.authHeader && this.customConfig.authToken) {
      headers[this.customConfig.authHeader] = this.customConfig.authToken;
    } else if (this.customConfig.authToken) {
      headers['Authorization'] = `Bearer ${this.customConfig.authToken}`;
    }

    // Include any additional custom metadata headers
    if (this.customConfig.metadata) {
      for (const [k, v] of Object.entries(this.customConfig.metadata)) {
        headers[k] = v;
      }
    }

    return headers;
  }

  public async getSecret(key: string): Promise<string | null> {
    if (!this.config.custom?.endpoint) return null;

    const response = await fetch(`${this.endpoint}/secrets/${encodeURIComponent(key)}`, {
      method: 'GET',
      headers: this.buildHeaders(),
      signal: AbortSignal.timeout(10_000),
    });

    if (response.status === 404) return null;
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Custom provider getSecret '${key}': HTTP ${response.status} — ${text}`);
    }

    const data: CustomSecretGetResponse = await response.json();
    return data.value;
  }

  public async setSecret(key: string, value: string): Promise<void> {
    if (!this.config.custom?.endpoint) {
      throw new Error('Custom provider: endpoint not configured');
    }

    const response = await fetch(`${this.endpoint}/secrets/${encodeURIComponent(key)}`, {
      method: 'PUT',
      headers: this.buildHeaders(),
      body: JSON.stringify({ key, value }),
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Custom provider setSecret '${key}': HTTP ${response.status} — ${text}`);
    }
  }

  public async deleteSecret(key: string): Promise<void> {
    if (!this.config.custom?.endpoint) {
      throw new Error('Custom provider: endpoint not configured');
    }

    const response = await fetch(`${this.endpoint}/secrets/${encodeURIComponent(key)}`, {
      method: 'DELETE',
      headers: this.buildHeaders(),
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok && response.status !== 404) {
      const text = await response.text();
      throw new Error(`Custom provider deleteSecret '${key}': HTTP ${response.status} — ${text}`);
    }
  }

  public async listSecrets(prefix?: string): Promise<string[]> {
    if (!this.config.custom?.endpoint) return [];

    const url = prefix
      ? `${this.endpoint}/secrets?prefix=${encodeURIComponent(prefix)}`
      : `${this.endpoint}/secrets`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.buildHeaders(),
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) return [];

    const data: CustomSecretListResponse = await response.json();
    return data.keys ?? [];
  }

  public async testConnectivity(): Promise<SecretProviderHealth> {
    const start = Date.now();

    if (!this.config.custom?.endpoint) {
      return this.buildHealthResult('unconfigured', 0, 'Custom provider endpoint not configured');
    }

    try {
      // Probe the health endpoint or list endpoint
      const healthUrl = `${this.endpoint}/health`;
      const response = await fetch(healthUrl, {
        method: 'GET',
        headers: this.buildHeaders(),
        signal: AbortSignal.timeout(5000),
      });

      const latencyMs = Date.now() - start;

      if (response.ok) {
        this.retryCount = 0;
        return this.buildHealthResult('healthy', latencyMs);
      } else if (response.status === 401 || response.status === 403) {
        this.retryCount++;
        this.lastFailure = new Date().toISOString();
        this.lastFailureReason = `HTTP ${response.status} Unauthorized`;
        return this.buildHealthResult('unauthenticated', latencyMs, this.lastFailureReason);
      } else {
        this.retryCount++;
        this.lastFailure = new Date().toISOString();
        this.lastFailureReason = `HTTP ${response.status}`;
        return this.buildHealthResult('degraded', latencyMs, this.lastFailureReason);
      }
    } catch (err: unknown) {
      const latencyMs = Date.now() - start;
      const reason = err instanceof Error ? err.message : String(err);
      this.retryCount++;
      this.lastFailure = new Date().toISOString();
      this.lastFailureReason = reason;
      return this.buildHealthResult('unreachable', latencyMs, reason);
    }
  }

  private buildHealthResult(
    status: SecretProviderHealth['status'],
    latencyMs: number,
    failureReason?: string,
  ): SecretProviderHealth {
    return {
      providerId: 'custom',
      providerType: 'custom',
      displayName: this.displayName,
      status,
      latencyMs,
      lastChecked: new Date().toISOString(),
      lastSuccess: status === 'healthy' ? new Date().toISOString() : undefined,
      lastFailure: this.lastFailure,
      failureReason,
      retryCount: this.retryCount,
      providerVersion: 'Custom HTTP REST API',
      authStatus: status === 'unauthenticated' ? 'unauthenticated' : status === 'healthy' ? 'authenticated' : 'unknown',
      availability: status === 'healthy' ? 100 : status === 'degraded' ? 50 : 0,
    };
  }
}
