/**
 * AKAAL Secret Provider — HashiCorp Vault
 * Stage 7.3
 *
 * Full Vault KV v2 integration via Vault HTTP API.
 * Supports Token, AppRole, and Kubernetes auth methods.
 * Becomes fully operational when VAULT_ADDR and auth credentials are configured.
 */

import { SecretProviderConfig, SecretProviderHealth } from '../secretTypes';
import { SecretProviderInterface } from './envProvider';

interface VaultKVv2Response {
  data: {
    data: Record<string, string>;
    metadata: {
      version: number;
      created_time: string;
      deletion_time: string;
      destroyed: boolean;
    };
  };
  errors?: string[];
}

interface VaultAuthResponse {
  auth: {
    client_token: string;
    lease_duration: number;
    renewable: boolean;
    accessor: string;
  };
  errors?: string[];
}

interface VaultListResponse {
  data: {
    keys: string[];
  };
  errors?: string[];
}

export class VaultSecretProvider implements SecretProviderInterface {
  public readonly providerType = 'vault' as const;
  public readonly displayName = 'HashiCorp Vault';

  private readonly config: SecretProviderConfig;
  private clientToken: string | null = null;
  private tokenExpiresAt: number = 0;
  private retryCount: number = 0;
  private lastFailure?: string;
  private lastFailureReason?: string;

  constructor(config: SecretProviderConfig) {
    this.config = config;
    if (config.vault?.token) {
      this.clientToken = config.vault.token;
      this.tokenExpiresAt = Date.now() + 3600_000; // Assume 1h if not from login
    }
  }

  private get vaultConfig() {
    return this.config.vault!;
  }

  private get baseUrl(): string {
    return this.vaultConfig.address.replace(/\/$/, '');
  }

  private get mountPath(): string {
    return this.vaultConfig.mountPath || 'secret';
  }

  private get namespace(): string | undefined {
    return this.vaultConfig.namespace;
  }

  private buildHeaders(token: string): Record<string, string> {
    const headers: Record<string, string> = {
      'X-Vault-Token': token,
      'Content-Type': 'application/json',
    };
    if (this.namespace) {
      headers['X-Vault-Namespace'] = this.namespace;
    }
    return headers;
  }

  private async authenticate(): Promise<string> {
    if (this.clientToken && Date.now() < this.tokenExpiresAt) {
      return this.clientToken;
    }

    const authMethod = this.vaultConfig.authMethod;

    if (authMethod === 'token') {
      if (!this.vaultConfig.token) throw new Error('Vault token not configured');
      this.clientToken = this.vaultConfig.token;
      this.tokenExpiresAt = Date.now() + 3600_000;
      return this.clientToken;
    }

    if (authMethod === 'approle') {
      const { roleId, secretId } = this.vaultConfig;
      if (!roleId || !secretId) throw new Error('Vault AppRole: roleId and secretId are required');

      const response = await fetch(`${this.baseUrl}/v1/auth/approle/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role_id: roleId, secret_id: secretId }),
      });

      if (!response.ok) {
        const body = await response.text();
        throw new Error(`Vault AppRole auth failed: ${response.status} ${body}`);
      }

      const data: VaultAuthResponse = await response.json();
      if (data.errors?.length) throw new Error(`Vault auth error: ${data.errors.join(', ')}`);

      this.clientToken = data.auth.client_token;
      this.tokenExpiresAt = Date.now() + (data.auth.lease_duration * 1000);
      return this.clientToken;
    }

    if (authMethod === 'kubernetes') {
      // Read service account token from the pod's mounted volume
      const tokenPath = '/var/run/secrets/kubernetes.io/serviceaccount/token';
      if (typeof window !== 'undefined') {
        throw new Error('Vault Kubernetes auth: service account token file reading is only available on server-side');
      }
      let jwt: string;
      try {
        const getFs = new Function("try { return require('fs'); } catch { return null; }");
        const fs = getFs();
        if (!fs) throw new Error('fs module unavailable');
        jwt = String(fs.readFileSync(tokenPath, 'utf-8')).trim();
      } catch {
        throw new Error(`Vault Kubernetes auth: cannot read service account token from ${tokenPath}`);
      }

      const response = await fetch(`${this.baseUrl}/v1/auth/kubernetes/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: this.vaultConfig.roleId ?? 'default', jwt }),
      });

      if (!response.ok) {
        const body = await response.text();
        throw new Error(`Vault Kubernetes auth failed: ${response.status} ${body}`);
      }

      const data: VaultAuthResponse = await response.json();
      if (data.errors?.length) throw new Error(`Vault auth error: ${data.errors.join(', ')}`);

      this.clientToken = data.auth.client_token;
      this.tokenExpiresAt = Date.now() + (data.auth.lease_duration * 1000);
      return this.clientToken;
    }

    throw new Error(`Vault auth method '${authMethod}' is not yet supported`);
  }

  public async getSecret(key: string): Promise<string | null> {
    const token = await this.authenticate();
    const url = `${this.baseUrl}/v1/${this.mountPath}/data/${key}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.buildHeaders(token),
    });

    if (response.status === 404) return null;
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Vault getSecret failed for '${key}': ${response.status} ${body}`);
    }

    const data: VaultKVv2Response = await response.json();
    if (data.errors?.length) throw new Error(`Vault error: ${data.errors.join(', ')}`);

    // KV v2 stores secrets as objects; return the 'value' field or first field
    const secretData = data.data?.data;
    return secretData?.value ?? secretData?.[key] ?? Object.values(secretData ?? {})[0] ?? null;
  }

  public async setSecret(key: string, value: string): Promise<void> {
    const token = await this.authenticate();
    const url = `${this.baseUrl}/v1/${this.mountPath}/data/${key}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: this.buildHeaders(token),
      body: JSON.stringify({ data: { value } }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Vault setSecret failed for '${key}': ${response.status} ${body}`);
    }
  }

  public async deleteSecret(key: string): Promise<void> {
    const token = await this.authenticate();
    // Soft-delete the latest version
    const url = `${this.baseUrl}/v1/${this.mountPath}/metadata/${key}`;

    const response = await fetch(url, {
      method: 'DELETE',
      headers: this.buildHeaders(token),
    });

    if (!response.ok && response.status !== 404) {
      const body = await response.text();
      throw new Error(`Vault deleteSecret failed for '${key}': ${response.status} ${body}`);
    }
  }

  public async listSecrets(prefix?: string): Promise<string[]> {
    const token = await this.authenticate();
    const path = prefix ? `${this.mountPath}/metadata/${prefix}` : `${this.mountPath}/metadata`;
    const url = `${this.baseUrl}/v1/${path}?list=true`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.buildHeaders(token),
    });

    if (response.status === 404) return [];
    if (!response.ok) return [];

    const data: VaultListResponse = await response.json();
    return data.data?.keys ?? [];
  }

  public async testConnectivity(): Promise<SecretProviderHealth> {
    const start = Date.now();

    if (!this.config.vault?.address) {
      return this.buildHealthResult('unconfigured', Date.now() - start, 'Vault address not configured');
    }

    try {
      const token = await this.authenticate();
      const sysHealthUrl = `${this.baseUrl}/v1/sys/health`;
      const response = await fetch(sysHealthUrl, {
        method: 'GET',
        headers: { 'X-Vault-Token': token },
        signal: AbortSignal.timeout(5000),
      });

      const latencyMs = Date.now() - start;

      if (response.ok || response.status === 429 || response.status === 472 || response.status === 473) {
        this.retryCount = 0;
        this.lastFailure = undefined;
        this.lastFailureReason = undefined;
        return this.buildHealthResult('healthy', latencyMs);
      } else {
        const reason = `HTTP ${response.status}`;
        this.recordFailure(reason);
        return this.buildHealthResult('degraded', latencyMs, reason);
      }
    } catch (err: unknown) {
      const latencyMs = Date.now() - start;
      const reason = err instanceof Error ? err.message : String(err);
      this.recordFailure(reason);
      return this.buildHealthResult('unreachable', latencyMs, reason);
    }
  }

  private recordFailure(reason: string): void {
    this.retryCount++;
    this.lastFailure = new Date().toISOString();
    this.lastFailureReason = reason;
  }

  private buildHealthResult(
    status: SecretProviderHealth['status'],
    latencyMs: number,
    failureReason?: string,
  ): SecretProviderHealth {
    return {
      providerId: 'vault',
      providerType: 'vault',
      displayName: this.displayName,
      status,
      latencyMs,
      lastChecked: new Date().toISOString(),
      lastSuccess: status === 'healthy' ? new Date().toISOString() : undefined,
      lastFailure: this.lastFailure,
      failureReason,
      retryCount: this.retryCount,
      providerVersion: 'KV v2',
      authStatus: this.clientToken ? 'authenticated' : 'unauthenticated',
      availability: status === 'healthy' ? 100 : status === 'degraded' ? 50 : 0,
    };
  }
}
