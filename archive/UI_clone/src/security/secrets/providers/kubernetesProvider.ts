/**
 * AKAAL Secret Provider — Kubernetes Secrets
 * Stage 7.3
 *
 * Full Kubernetes Secrets integration via the Kubernetes REST API.
 * Authenticates using in-cluster service account token or kubeconfig bearer token.
 * Becomes operational in a Kubernetes pod environment.
 */

import { SecretProviderConfig, SecretProviderHealth } from '../secretTypes';
import { SecretProviderInterface } from './envProvider';

interface K8sSecret {
  apiVersion: string;
  kind: string;
  metadata: { name: string; namespace: string; labels?: Record<string, string> };
  data?: Record<string, string>; // base64-encoded values
}

interface K8sSecretList {
  items: K8sSecret[];
  metadata: { continue?: string };
}

export class KubernetesSecretProvider implements SecretProviderInterface {
  public readonly providerType = 'kubernetes' as const;
  public readonly displayName = 'Kubernetes Secrets';

  private readonly config: SecretProviderConfig;
  private serviceAccountToken: string | null = null;
  private retryCount: number = 0;
  private lastFailure?: string;
  private lastFailureReason?: string;

  private static readonly DEFAULT_SA_TOKEN_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/token';
  private static readonly DEFAULT_CA_CERT_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt';
  private static readonly DEFAULT_API_SERVER = 'https://kubernetes.default.svc';

  constructor(config: SecretProviderConfig) {
    this.config = config;
  }

  private get k8sConfig() {
    return this.config.kubernetes!;
  }

  private get namespace(): string {
    return this.k8sConfig.namespace || 'default';
  }

  private get apiServer(): string {
    return this.k8sConfig.apiServer ?? KubernetesSecretProvider.DEFAULT_API_SERVER;
  }

  private async getToken(): Promise<string> {
    if (this.serviceAccountToken) return this.serviceAccountToken;
    if (typeof window !== 'undefined') {
      throw new Error('Kubernetes: service account token file reading is only available on server-side');
    }

    const tokenPath = this.k8sConfig.serviceAccountTokenPath ?? KubernetesSecretProvider.DEFAULT_SA_TOKEN_PATH;

    try {
      const getFs = new Function("try { return require('fs'); } catch { return null; }");
      const fs = getFs();
      if (!fs) throw new Error('fs module unavailable');
      const tokenContent = fs.readFileSync(tokenPath, 'utf-8');
      this.serviceAccountToken = String(tokenContent).trim();
      return this.serviceAccountToken;
    } catch (err: unknown) {
      throw new Error(`Kubernetes: cannot read service account token from '${tokenPath}': ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  private buildHeaders(token: string): Record<string, string> {
    return {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
      'Content-Type': 'application/json',
    };
  }

  // Kubernetes encodes secret data in base64. Decodes a single field value.
  private decodeBase64(value: string): string {
    return atob(value);
  }

  private encodeBase64(value: string): string {
    return btoa(value);
  }

  /**
   * Retrieves a Kubernetes Secret object and returns the 'value' field
   * or the first available field from the secret's data map.
   * The key format is: "<secret-name>[/<field>]"
   * e.g., "db-credentials/password"
   */
  public async getSecret(key: string): Promise<string | null> {
    if (!this.config.kubernetes) return null;

    const [secretName, fieldName] = key.split('/');
    const token = await this.getToken();
    const url = `${this.apiServer}/api/v1/namespaces/${this.namespace}/secrets/${secretName}`;

    const response = await fetch(url, {
      headers: this.buildHeaders(token),
      signal: AbortSignal.timeout(10_000),
    });

    if (response.status === 404) return null;
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Kubernetes getSecret '${secretName}': HTTP ${response.status} — ${text}`);
    }

    const secret: K8sSecret = await response.json();
    if (!secret.data) return null;

    if (fieldName && secret.data[fieldName]) {
      return this.decodeBase64(secret.data[fieldName]);
    }

    // Return first field if no specific field requested
    const firstValue = Object.values(secret.data)[0];
    return firstValue ? this.decodeBase64(firstValue) : null;
  }

  /**
   * Creates or updates a Kubernetes Secret.
   * Key format: "<secret-name>[/<field>]" — defaults to field "value"
   */
  public async setSecret(key: string, value: string): Promise<void> {
    const [secretName, fieldName = 'value'] = key.split('/');
    const token = await this.getToken();
    const baseUrl = `${this.apiServer}/api/v1/namespaces/${this.namespace}/secrets`;

    const secretBody: K8sSecret = {
      apiVersion: 'v1',
      kind: 'Secret',
      metadata: { name: secretName, namespace: this.namespace, labels: { 'managed-by': 'akaal-secrets' } },
      data: { [fieldName]: this.encodeBase64(value) },
    };

    // Try to update existing secret first
    const getResponse = await fetch(`${baseUrl}/${secretName}`, {
      headers: this.buildHeaders(token),
      signal: AbortSignal.timeout(10_000),
    });

    if (getResponse.ok) {
      // Merge with existing data
      const existing: K8sSecret = await getResponse.json();
      const merged = { ...existing.data, [fieldName]: this.encodeBase64(value) };
      const putBody = { ...secretBody, data: merged };

      const putResponse = await fetch(`${baseUrl}/${secretName}`, {
        method: 'PUT',
        headers: this.buildHeaders(token),
        body: JSON.stringify(putBody),
        signal: AbortSignal.timeout(10_000),
      });

      if (!putResponse.ok) {
        const text = await putResponse.text();
        throw new Error(`Kubernetes setSecret (update) '${secretName}': HTTP ${putResponse.status} — ${text}`);
      }
    } else {
      // Create new secret
      const postResponse = await fetch(baseUrl, {
        method: 'POST',
        headers: this.buildHeaders(token),
        body: JSON.stringify(secretBody),
        signal: AbortSignal.timeout(10_000),
      });

      if (!postResponse.ok) {
        const text = await postResponse.text();
        throw new Error(`Kubernetes setSecret (create) '${secretName}': HTTP ${postResponse.status} — ${text}`);
      }
    }
  }

  public async deleteSecret(key: string): Promise<void> {
    const [secretName] = key.split('/');
    const token = await this.getToken();
    const url = `${this.apiServer}/api/v1/namespaces/${this.namespace}/secrets/${secretName}`;

    const response = await fetch(url, {
      method: 'DELETE',
      headers: this.buildHeaders(token),
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok && response.status !== 404) {
      const text = await response.text();
      throw new Error(`Kubernetes deleteSecret '${secretName}': HTTP ${response.status} — ${text}`);
    }
  }

  public async listSecrets(prefix?: string): Promise<string[]> {
    if (!this.config.kubernetes) return [];

    const token = await this.getToken();
    const names: string[] = [];
    let continueToken: string | undefined;

    const labelSelector = this.k8sConfig.labelSelector ? `&labelSelector=${encodeURIComponent(this.k8sConfig.labelSelector)}` : '';

    do {
      let url = `${this.apiServer}/api/v1/namespaces/${this.namespace}/secrets?limit=100${labelSelector}`;
      if (continueToken) url += `&continue=${continueToken}`;

      const response = await fetch(url, {
        headers: this.buildHeaders(token),
        signal: AbortSignal.timeout(10_000),
      });

      if (!response.ok) break;

      const data: K8sSecretList = await response.json();
      const secretNames = data.items.map((s) => s.metadata.name);
      const filtered = prefix ? secretNames.filter((n) => n.startsWith(prefix)) : secretNames;
      names.push(...filtered);
      continueToken = data.metadata.continue;
    } while (continueToken);

    return names;
  }

  public async testConnectivity(): Promise<SecretProviderHealth> {
    const start = Date.now();

    if (!this.config.kubernetes) {
      return this.buildHealthResult('unconfigured', 0, 'Kubernetes configuration not provided');
    }

    try {
      const token = await this.getToken();
      const url = `${this.apiServer}/api/v1/namespaces/${this.namespace}/secrets?limit=1`;
      const response = await fetch(url, {
        headers: this.buildHeaders(token),
        signal: AbortSignal.timeout(5000),
      });

      const latencyMs = Date.now() - start;

      if (response.ok) {
        this.retryCount = 0;
        return this.buildHealthResult('healthy', latencyMs);
      } else {
        const reason = `HTTP ${response.status}`;
        this.retryCount++;
        this.lastFailure = new Date().toISOString();
        this.lastFailureReason = reason;
        return this.buildHealthResult('degraded', latencyMs, reason);
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
      providerId: 'kubernetes',
      providerType: 'kubernetes',
      displayName: this.displayName,
      status,
      latencyMs,
      lastChecked: new Date().toISOString(),
      lastSuccess: status === 'healthy' ? new Date().toISOString() : undefined,
      lastFailure: this.lastFailure,
      failureReason,
      retryCount: this.retryCount,
      providerVersion: 'Kubernetes API v1',
      authStatus: this.serviceAccountToken ? 'authenticated' : 'unknown',
      availability: status === 'healthy' ? 100 : status === 'degraded' ? 50 : 0,
    };
  }
}
