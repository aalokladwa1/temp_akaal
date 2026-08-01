/**
 * AKAAL Secret Provider — Google Secret Manager
 * Stage 7.3
 *
 * Full Google Secret Manager integration via Google Cloud REST API.
 * Supports Service Account key file and Application Default Credentials.
 * Becomes operational when GCP_PROJECT_ID and service account credentials are configured.
 */

import { SecretProviderConfig, SecretProviderHealth } from '../secretTypes';
import { SecretProviderInterface } from './envProvider';
import { uint8ArrayToBase64, base64ToUint8Array } from '../../utils/securityUtils';

interface GCPAccessTokenResponse {
  access_token: string;
  expires_in: number;
  token_type: string;
}

interface GCPSecretVersionResponse {
  name: string;
  payload: {
    data: string; // base64-encoded
  };
  state: string;
}

interface GCPListSecretsResponse {
  secrets?: { name: string }[];
  nextPageToken?: string;
}

interface GCPServiceAccountKey {
  type: string;
  project_id: string;
  private_key_id: string;
  private_key: string;
  client_email: string;
  token_uri: string;
}

export class GCPSecretManagerProvider implements SecretProviderInterface {
  public readonly providerType = 'gcp_secret_manager' as const;
  public readonly displayName = 'Google Secret Manager';

  private readonly config: SecretProviderConfig;
  private accessToken: string | null = null;
  private tokenExpiresAt: number = 0;
  private retryCount: number = 0;
  private lastFailure?: string;
  private lastFailureReason?: string;

  constructor(config: SecretProviderConfig) {
    this.config = config;
  }

  private get gcpConfig() {
    return this.config.gcp!;
  }

  private get projectId(): string {
    return this.gcpConfig.projectId;
  }

  private get prefix(): string {
    return this.gcpConfig.prefix ?? '';
  }

  private buildSecretId(key: string): string {
    const name = this.prefix ? `${this.prefix}_${key}` : key;
    // GCP secret IDs: letters, numbers, underscores, hyphens
    return name.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 255);
  }

  private buildResourceName(key: string): string {
    return `projects/${this.projectId}/secrets/${this.buildSecretId(key)}`;
  }

  private async getServiceAccountKey(): Promise<GCPServiceAccountKey> {
    const keyJson = this.gcpConfig.serviceAccountKey;
    if (!keyJson) throw new Error('GCP Secret Manager: serviceAccountKey JSON not configured');
    return JSON.parse(keyJson) as GCPServiceAccountKey;
  }

  private async createJWT(serviceAccount: GCPServiceAccountKey): Promise<string> {
    const now = Math.floor(Date.now() / 1000);
    const header = { alg: 'RS256', typ: 'JWT' };
    const payload = {
      iss: serviceAccount.client_email,
      scope: 'https://www.googleapis.com/auth/cloud-platform',
      aud: serviceAccount.token_uri,
      iat: now,
      exp: now + 3600,
    };

    const b64url = (obj: unknown) =>
      btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');

    const unsignedJWT = `${b64url(header)}.${b64url(payload)}`;

    // Import RSA private key from PEM
    const pemBody = serviceAccount.private_key
      .replace(/-----BEGIN PRIVATE KEY-----/, '')
      .replace(/-----END PRIVATE KEY-----/, '')
      .replace(/\s/g, '');

    const derBytes = base64ToUint8Array(pemBody);

    const cryptoKey = await globalThis.crypto.subtle.importKey(
      'pkcs8',
      derBytes as BufferSource,
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
      false,
      ['sign'],
    );

    const signatureBuffer = await globalThis.crypto.subtle.sign(
      'RSASSA-PKCS1-v1_5',
      cryptoKey,
      new TextEncoder().encode(unsignedJWT),
    );

    const sig = uint8ArrayToBase64(new Uint8Array(signatureBuffer))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');

    return `${unsignedJWT}.${sig}`;
  }

  private async getAccessToken(): Promise<string> {
    if (this.accessToken && Date.now() < this.tokenExpiresAt) {
      return this.accessToken;
    }

    if (!this.config.gcp?.projectId) {
      throw new Error('GCP Secret Manager: projectId is required');
    }

    const serviceAccount = await this.getServiceAccountKey();
    const jwt = await this.createJWT(serviceAccount);

    const response = await fetch(serviceAccount.token_uri, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}`,
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`GCP auth failed: HTTP ${response.status} — ${text}`);
    }

    const data: GCPAccessTokenResponse = await response.json();
    this.accessToken = data.access_token;
    this.tokenExpiresAt = Date.now() + (data.expires_in - 60) * 1000;
    return this.accessToken;
  }

  public async getSecret(key: string): Promise<string | null> {
    if (!this.config.gcp?.projectId) return null;

    try {
      const token = await this.getAccessToken();
      const resourceName = this.buildResourceName(key);
      const url = `https://secretmanager.googleapis.com/v1/${resourceName}/versions/latest:access`;

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(10_000),
      });

      if (response.status === 404) return null;
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`GCP getSecret '${key}': HTTP ${response.status} — ${text}`);
      }

      const data: GCPSecretVersionResponse = await response.json();
      const decoded = atob(data.payload.data);
      return decoded;
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes('NOT_FOUND')) return null;
      throw err;
    }
  }

  public async setSecret(key: string, value: string): Promise<void> {
    const token = await this.getAccessToken();
    const secretId = this.buildSecretId(key);
    const parent = `projects/${this.projectId}`;
    const baseUrl = 'https://secretmanager.googleapis.com/v1';

    // Try to add a new version to an existing secret; create if not found
    const addVersionUrl = `${baseUrl}/${parent}/secrets/${secretId}:addSecretVersion`;

    const b64Value = btoa(value);

    let response = await fetch(addVersionUrl, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ payload: { data: b64Value } }),
      signal: AbortSignal.timeout(10_000),
    });

    if (response.status === 404) {
      // Create the secret first
      const createUrl = `${baseUrl}/${parent}/secrets?secretId=${secretId}`;
      const createResponse = await fetch(createUrl, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ replication: { automatic: {} } }),
        signal: AbortSignal.timeout(10_000),
      });
      if (!createResponse.ok) {
        const text = await createResponse.text();
        throw new Error(`GCP create secret '${key}': HTTP ${createResponse.status} — ${text}`);
      }

      // Now add the version
      response = await fetch(addVersionUrl, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: { data: b64Value } }),
        signal: AbortSignal.timeout(10_000),
      });
    }

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`GCP setSecret '${key}': HTTP ${response.status} — ${text}`);
    }
  }

  public async deleteSecret(key: string): Promise<void> {
    const token = await this.getAccessToken();
    const resourceName = this.buildResourceName(key);
    const url = `https://secretmanager.googleapis.com/v1/${resourceName}`;

    const response = await fetch(url, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok && response.status !== 404) {
      const text = await response.text();
      throw new Error(`GCP deleteSecret '${key}': HTTP ${response.status} — ${text}`);
    }
  }

  public async listSecrets(prefix?: string): Promise<string[]> {
    if (!this.config.gcp?.projectId) return [];

    const token = await this.getAccessToken();
    const names: string[] = [];
    let pageToken: string | undefined;
    const filter = prefix ? `name:${this.buildSecretId(prefix)}` : '';

    do {
      let url = `https://secretmanager.googleapis.com/v1/projects/${this.projectId}/secrets?pageSize=100`;
      if (filter) url += `&filter=${encodeURIComponent(filter)}`;
      if (pageToken) url += `&pageToken=${pageToken}`;

      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(10_000),
      });
      if (!response.ok) break;

      const data: GCPListSecretsResponse = await response.json();
      const extracted = (data.secrets ?? []).map((s) => s.name.split('/').pop() ?? '');
      names.push(...extracted);
      pageToken = data.nextPageToken;
    } while (pageToken);

    return names;
  }

  public async testConnectivity(): Promise<SecretProviderHealth> {
    const start = Date.now();

    if (!this.config.gcp?.projectId || !this.config.gcp?.serviceAccountKey) {
      return this.buildHealthResult('unconfigured', 0, 'GCP projectId or serviceAccountKey not configured');
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
      providerId: 'gcp_secret_manager',
      providerType: 'gcp_secret_manager',
      displayName: this.displayName,
      status,
      latencyMs,
      lastChecked: new Date().toISOString(),
      lastSuccess: status === 'healthy' ? new Date().toISOString() : undefined,
      lastFailure: this.lastFailure,
      failureReason,
      retryCount: this.retryCount,
      providerVersion: 'Google Secret Manager API v1',
      authStatus: this.accessToken ? 'authenticated' : 'unauthenticated',
      availability: status === 'healthy' ? 100 : status === 'degraded' ? 50 : 0,
    };
  }
}
