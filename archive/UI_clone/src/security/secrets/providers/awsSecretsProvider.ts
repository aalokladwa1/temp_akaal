/**
 * AKAAL Secret Provider — AWS Secrets Manager
 * Stage 7.3
 *
 * Full AWS Secrets Manager integration via the AWS REST API with SigV4 signing.
 * Supports IAM credentials and AssumeRole. Becomes operational when AWS credentials are configured.
 */

import { SecretProviderConfig, SecretProviderHealth } from '../secretTypes';
import { SecretProviderInterface } from './envProvider';
import { CryptoService } from '../../crypto/crypto.service';

interface AWSGetSecretResponse {
  SecretString?: string;
  SecretBinary?: string;
  Name: string;
  ARN: string;
  VersionId: string;
  VersionStages: string[];
}

interface AWSCreateSecretResponse {
  ARN: string;
  Name: string;
  VersionId: string;
}

interface AWSListSecretsResponse {
  SecretList: { Name: string; ARN: string }[];
  NextToken?: string;
}

interface AWSErrorResponse {
  __type: string;
  Message: string;
}

export class AWSSecretsManagerProvider implements SecretProviderInterface {
  public readonly providerType = 'aws_secrets_manager' as const;
  public readonly displayName = 'AWS Secrets Manager';

  private readonly config: SecretProviderConfig;
  private retryCount: number = 0;
  private lastFailure?: string;
  private lastFailureReason?: string;

  constructor(config: SecretProviderConfig) {
    this.config = config;
  }

  private get awsConfig() {
    return this.config.aws!;
  }

  private get region(): string {
    return this.awsConfig.region || 'us-east-1';
  }

  private get endpoint(): string {
    return this.awsConfig.endpoint ?? `https://secretsmanager.${this.region}.amazonaws.com`;
  }

  private get secretPrefix(): string {
    return this.awsConfig.prefix ?? '';
  }

  private buildSecretId(key: string): string {
    return this.secretPrefix ? `${this.secretPrefix}/${key}` : key;
  }

  /**
   * AWS Signature Version 4 signing.
   * Reference: https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
   */
  private async signRequest(
    method: string,
    path: string,
    body: string,
    targetHeader: string,
  ): Promise<Record<string, string>> {
    const { accessKeyId, secretAccessKey, sessionToken } = this.awsConfig;

    if (!accessKeyId || !secretAccessKey) {
      throw new Error('AWS Secrets Manager: accessKeyId and secretAccessKey are required');
    }

    const now = new Date();
    const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, '').slice(0, 15) + 'Z';
    const dateStamp = amzDate.slice(0, 8);
    const service = 'secretsmanager';
    const algorithm = 'AWS4-HMAC-SHA256';
    const credentialScope = `${dateStamp}/${this.region}/${service}/aws4_request`;
    const host = new URL(this.endpoint).host;

    const canonicalHeaders = [
      `content-type:application/x-amz-json-1.1`,
      `host:${host}`,
      `x-amz-date:${amzDate}`,
      `x-amz-target:${targetHeader}`,
      ...(sessionToken ? [`x-amz-security-token:${sessionToken}`] : []),
    ].join('\n') + '\n';

    const signedHeaders = ['content-type', 'host', 'x-amz-date', 'x-amz-target',
      ...(sessionToken ? ['x-amz-security-token'] : [])].join(';');

    const payloadHash = await CryptoService.sha256(body);
    const canonicalRequest = [method, path, '', canonicalHeaders, signedHeaders, payloadHash].join('\n');
    const stringToSign = [algorithm, amzDate, credentialScope, await CryptoService.sha256(canonicalRequest)].join('\n');

    // HMAC-based key derivation for SigV4
    const enc = (s: string) => new TextEncoder().encode(s);
    const hmacRaw = async (key: Uint8Array, data: Uint8Array): Promise<Uint8Array> => {
      const cryptoKey = await globalThis.crypto.subtle.importKey('raw', key as BufferSource, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
      const sig = await globalThis.crypto.subtle.sign('HMAC', cryptoKey, data as BufferSource);
      return new Uint8Array(sig);
    };

    const signingKey = await hmacRaw(
      await hmacRaw(
        await hmacRaw(
          await hmacRaw(enc(`AWS4${secretAccessKey}`), enc(dateStamp)),
          enc(this.region),
        ),
        enc(service),
      ),
      enc('aws4_request'),
    );

    const signatureBytes = await hmacRaw(signingKey, enc(stringToSign));
    const signature = Array.from(signatureBytes).map((b) => b.toString(16).padStart(2, '0')).join('');

    const authorizationHeader = `${algorithm} Credential=${accessKeyId}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/x-amz-json-1.1',
      'X-Amz-Date': amzDate,
      'X-Amz-Target': targetHeader,
      Authorization: authorizationHeader,
    };

    if (sessionToken) {
      headers['X-Amz-Security-Token'] = sessionToken;
    }

    return headers;
  }

  private async callAWS<T>(target: string, body: Record<string, unknown>): Promise<T> {
    const bodyStr = JSON.stringify(body);
    const headers = await this.signRequest('POST', '/', bodyStr, target);

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers,
      body: bodyStr,
      signal: AbortSignal.timeout(10_000),
    });

    const responseText = await response.text();

    if (!response.ok) {
      let errorMsg: string;
      try {
        const err: AWSErrorResponse = JSON.parse(responseText);
        errorMsg = `${err.__type}: ${err.Message}`;
      } catch {
        errorMsg = `HTTP ${response.status}: ${responseText}`;
      }
      throw new Error(`AWS Secrets Manager — ${target}: ${errorMsg}`);
    }

    return JSON.parse(responseText) as T;
  }

  public async getSecret(key: string): Promise<string | null> {
    if (!this.awsConfig?.accessKeyId) return null;

    try {
      const data = await this.callAWS<AWSGetSecretResponse>('secretsmanager.GetSecretValue', {
        SecretId: this.buildSecretId(key),
      });
      return data.SecretString ?? null;
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes('ResourceNotFoundException')) return null;
      throw err;
    }
  }

  public async setSecret(key: string, value: string): Promise<void> {
    const secretId = this.buildSecretId(key);
    try {
      // Try to update first
      await this.callAWS<AWSCreateSecretResponse>('secretsmanager.PutSecretValue', {
        SecretId: secretId,
        SecretString: value,
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes('ResourceNotFoundException')) {
        // Create the secret if it doesn't exist
        await this.callAWS<AWSCreateSecretResponse>('secretsmanager.CreateSecret', {
          Name: secretId,
          SecretString: value,
        });
      } else {
        throw err;
      }
    }
  }

  public async deleteSecret(key: string): Promise<void> {
    await this.callAWS<Record<string, string>>('secretsmanager.DeleteSecret', {
      SecretId: this.buildSecretId(key),
      ForceDeleteWithoutRecovery: false, // Default: 30-day recovery window
    });
  }

  public async listSecrets(prefix?: string): Promise<string[]> {
    if (!this.awsConfig?.accessKeyId) return [];

    const allNames: string[] = [];
    let nextToken: string | undefined;

    do {
      const body: Record<string, unknown> = { MaxResults: 100 };
      if (nextToken) body['NextToken'] = nextToken;

      const data = await this.callAWS<AWSListSecretsResponse>('secretsmanager.ListSecrets', body);
      const names = data.SecretList.map((s) => s.Name);
      const filtered = prefix ? names.filter((n) => n.startsWith(prefix)) : names;
      allNames.push(...filtered);
      nextToken = data.NextToken;
    } while (nextToken);

    return allNames;
  }

  public async testConnectivity(): Promise<SecretProviderHealth> {
    const start = Date.now();

    if (!this.config.aws?.accessKeyId || !this.config.aws?.secretAccessKey) {
      return this.buildHealthResult('unconfigured', 0, 'AWS credentials not configured');
    }

    try {
      await this.callAWS<AWSListSecretsResponse>('secretsmanager.ListSecrets', { MaxResults: 1 });
      const latencyMs = Date.now() - start;
      this.retryCount = 0;
      return this.buildHealthResult('healthy', latencyMs);
    } catch (err: unknown) {
      const latencyMs = Date.now() - start;
      const reason = err instanceof Error ? err.message : String(err);
      this.retryCount++;
      this.lastFailure = new Date().toISOString();
      this.lastFailureReason = reason;
      const status = reason.includes('credentials') || reason.includes('AccessDenied') ? 'unauthenticated' : 'unreachable';
      return this.buildHealthResult(status, latencyMs, reason);
    }
  }

  private buildHealthResult(
    status: SecretProviderHealth['status'],
    latencyMs: number,
    failureReason?: string,
  ): SecretProviderHealth {
    return {
      providerId: 'aws_secrets_manager',
      providerType: 'aws_secrets_manager',
      displayName: this.displayName,
      status,
      latencyMs,
      lastChecked: new Date().toISOString(),
      lastSuccess: status === 'healthy' ? new Date().toISOString() : undefined,
      lastFailure: this.lastFailure,
      failureReason,
      retryCount: this.retryCount,
      providerVersion: 'AWS Secrets Manager API v1',
      authStatus: status === 'healthy' ? 'authenticated' : status === 'unauthenticated' ? 'unauthenticated' : 'unknown',
      availability: status === 'healthy' ? 100 : status === 'degraded' ? 50 : 0,
    };
  }
}
