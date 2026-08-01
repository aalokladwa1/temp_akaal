/**
 * AKAAL Secret Provider — Azure Key Vault
 * Stage 7.3
 *
 * Full Azure Key Vault integration via Azure REST API.
 * Supports Client Credentials (Service Principal) and Managed Identity auth.
 * Becomes operational when AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET are configured.
 */

import { SecretProviderConfig, SecretProviderHealth } from '../secretTypes';
import { SecretProviderInterface } from './envProvider';

interface AzureTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  expires_on?: string;
}

interface AzureSecretResponse {
  id: string;
  value: string;
  attributes: {
    enabled: boolean;
    created: number;
    updated: number;
    exp?: number;
  };
  contentType?: string;
}

interface AzureSecretListResponse {
  value: { id: string }[];
  nextLink?: string;
}

export class AzureKeyVaultProvider implements SecretProviderInterface {
  public readonly providerType = 'azure_key_vault' as const;
  public readonly displayName = 'Azure Key Vault';

  private readonly config: SecretProviderConfig;
  private accessToken: string | null = null;
  private tokenExpiresAt: number = 0;
  private retryCount: number = 0;
  private lastFailure?: string;
  private lastFailureReason?: string;

  constructor(config: SecretProviderConfig) {
    this.config = config;
  }

  private get azureConfig() {
    return this.config.azure!;
  }

  private get vaultUrl(): string {
    return this.azureConfig.vaultUrl.replace(/\/$/, '');
  }

  private get apiVersion(): string {
    return '7.4'; // Latest stable Azure Key Vault API version
  }

  private async getAccessToken(): Promise<string> {
    if (this.accessToken && Date.now() < this.tokenExpiresAt) {
      return this.accessToken;
    }

    const { tenantId, clientId, clientSecret, useManagedIdentity } = this.azureConfig;

    if (useManagedIdentity) {
      // Azure IMDS endpoint for managed identity
      const imdsUrl = 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net';
      const response = await fetch(imdsUrl, {
        headers: { Metadata: 'true' },
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) {
        throw new Error(`Azure Managed Identity token fetch failed: HTTP ${response.status}`);
      }
      const data: AzureTokenResponse = await response.json();
      this.accessToken = data.access_token;
      this.tokenExpiresAt = Date.now() + (data.expires_in - 60) * 1000;
      return this.accessToken;
    }

    if (!tenantId || !clientId || !clientSecret) {
      throw new Error('Azure Key Vault: tenantId, clientId, and clientSecret are required');
    }

    const tokenUrl = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`;
    const body = new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: clientId,
      client_secret: clientSecret,
      scope: 'https://vault.azure.net/.default',
    });

    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Azure Key Vault auth failed: HTTP ${response.status} — ${text}`);
    }

    const data: AzureTokenResponse = await response.json();
    this.accessToken = data.access_token;
    this.tokenExpiresAt = Date.now() + (data.expires_in - 60) * 1000;
    return this.accessToken;
  }

  private buildSecretName(key: string): string {
    // Azure Key Vault secret names: alphanumeric and dashes only
    const baseName = (this.azureConfig.prefix ? `${this.azureConfig.prefix}-${key}` : key)
      .replace(/[^a-zA-Z0-9-]/g, '-')
      .replace(/-+/g, '-')
      .slice(0, 127);
    return baseName;
  }

  public async getSecret(key: string): Promise<string | null> {
    if (!this.config.azure?.vaultUrl) return null;

    const token = await this.getAccessToken();
    const name = this.buildSecretName(key);
    const url = `${this.vaultUrl}/secrets/${name}?api-version=${this.apiVersion}`;

    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(10_000),
    });

    if (response.status === 404) return null;
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Azure Key Vault getSecret '${key}': HTTP ${response.status} — ${text}`);
    }

    const data: AzureSecretResponse = await response.json();
    return data.value;
  }

  public async setSecret(key: string, value: string): Promise<void> {
    const token = await this.getAccessToken();
    const name = this.buildSecretName(key);
    const url = `${this.vaultUrl}/secrets/${name}?api-version=${this.apiVersion}`;

    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ value, attributes: { enabled: true } }),
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Azure Key Vault setSecret '${key}': HTTP ${response.status} — ${text}`);
    }
  }

  public async deleteSecret(key: string): Promise<void> {
    const token = await this.getAccessToken();
    const name = this.buildSecretName(key);
    const url = `${this.vaultUrl}/secrets/${name}?api-version=${this.apiVersion}`;

    const response = await fetch(url, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok && response.status !== 404) {
      const text = await response.text();
      throw new Error(`Azure Key Vault deleteSecret '${key}': HTTP ${response.status} — ${text}`);
    }
  }

  public async listSecrets(prefix?: string): Promise<string[]> {
    if (!this.config.azure?.vaultUrl) return [];

    const token = await this.getAccessToken();
    const names: string[] = [];
    let nextLink: string | undefined = `${this.vaultUrl}/secrets?api-version=${this.apiVersion}&maxresults=25`;

    while (nextLink) {
      const response = await fetch(nextLink, {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(10_000),
      });

      if (!response.ok) break;

      const data: AzureSecretListResponse = await response.json();
      const extracted = data.value.map((s) => {
        const parts = s.id.split('/');
        return parts[parts.length - 1];
      });

      const filtered = prefix ? extracted.filter((n) => n.startsWith(prefix)) : extracted;
      names.push(...filtered);
      nextLink = data.nextLink;
    }

    return names;
  }

  public async testConnectivity(): Promise<SecretProviderHealth> {
    const start = Date.now();

    if (!this.config.azure?.vaultUrl) {
      return this.buildHealthResult('unconfigured', 0, 'Azure Key Vault URL not configured');
    }

    try {
      await this.getAccessToken();
      await this.listSecrets();
      const latencyMs = Date.now() - start;
      this.retryCount = 0;
      return this.buildHealthResult('healthy', latencyMs);
    } catch (err: unknown) {
      const latencyMs = Date.now() - start;
      const reason = err instanceof Error ? err.message : String(err);
      this.retryCount++;
      this.lastFailure = new Date().toISOString();
      this.lastFailureReason = reason;
      const status = reason.toLowerCase().includes('auth') ? 'unauthenticated' : 'unreachable';
      return this.buildHealthResult(status, latencyMs, reason);
    }
  }

  private buildHealthResult(
    status: SecretProviderHealth['status'],
    latencyMs: number,
    failureReason?: string,
  ): SecretProviderHealth {
    return {
      providerId: 'azure_key_vault',
      providerType: 'azure_key_vault',
      displayName: this.displayName,
      status,
      latencyMs,
      lastChecked: new Date().toISOString(),
      lastSuccess: status === 'healthy' ? new Date().toISOString() : undefined,
      lastFailure: this.lastFailure,
      failureReason,
      retryCount: this.retryCount,
      providerVersion: `Azure Key Vault API ${this.apiVersion}`,
      authStatus: this.accessToken ? 'authenticated' : 'unauthenticated',
      availability: status === 'healthy' ? 100 : status === 'degraded' ? 50 : 0,
    };
  }
}
