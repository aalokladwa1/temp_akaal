/**
 * AKAAL Secret Provider — Docker Secrets
 * Stage 7.3
 *
 * Reads Docker secrets from the /run/secrets/ filesystem mount.
 * Docker Swarm mounts secrets as files at /run/secrets/<secret-name>.
 * Server-side (Node.js) only. Read-only — Docker secrets cannot be created via this provider.
 */

import { SecretProviderConfig, SecretProviderHealth } from '../secretTypes';
import { SecretProviderInterface } from './envProvider';

export class DockerSecretProvider implements SecretProviderInterface {
  public readonly providerType = 'docker' as const;
  public readonly displayName = 'Docker Secrets';

  private readonly config: SecretProviderConfig;
  private readonly secretsPath: string;
  private retryCount: number = 0;
  private lastFailure?: string;
  private lastFailureReason?: string;

  constructor(config: SecretProviderConfig) {
    this.config = config;
    this.secretsPath = config.docker?.secretsPath ?? '/run/secrets';
  }

  public async getSecret(key: string): Promise<string | null> {
    if (typeof window !== 'undefined') return null;
    const filePath = `${this.secretsPath}/${key}`;
    try {
      const getFs = new Function("try { return require('fs'); } catch { return null; }");
      const fs = getFs();
      if (!fs || !fs.existsSync(filePath)) return null;
      const value = fs.readFileSync(filePath, 'utf-8').trim();
      return value || null;
    } catch (err: unknown) {
      if ((err as NodeJS.ErrnoException).code === 'ENOENT') return null;
      throw new Error(`Docker secret read '${key}' from '${filePath}': ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  // Docker secrets are read-only at runtime — created via Docker Swarm config or compose
  public async setSecret(key: string, _value: string): Promise<void> {
    throw new Error(
      `DockerSecretProvider: cannot create secret '${key}' at runtime. ` +
      `Configure Docker secrets via docker secret create or docker-compose secrets.`
    );
  }

  public async deleteSecret(key: string): Promise<void> {
    throw new Error(
      `DockerSecretProvider: cannot delete secret '${key}' at runtime. ` +
      `Remove via docker secret rm or update your Docker Compose / Swarm stack.`
    );
  }

  public async listSecrets(prefix?: string): Promise<string[]> {
    if (typeof window !== 'undefined') return [];
    try {
      const getFs = new Function("try { return require('fs'); } catch { return null; }");
      const fs = getFs();
      if (!fs || !fs.existsSync(this.secretsPath)) return [];

      const entries = fs.readdirSync(this.secretsPath);
      const files = entries.filter((entry: string) => {
        const fullPath = `${this.secretsPath}/${entry}`;
        return fs.statSync(fullPath).isFile();
      });

      return prefix ? files.filter((f: string) => f.startsWith(prefix)) : files;
    } catch {
      return [];
    }
  }

  public async testConnectivity(): Promise<SecretProviderHealth> {
    const start = Date.now();

    try {
      const fs = await import('fs');
      const exists = fs.existsSync(this.secretsPath);

      if (!exists) {
        const latencyMs = Date.now() - start;
        this.retryCount++;
        this.lastFailure = new Date().toISOString();
        this.lastFailureReason = `Docker secrets path '${this.secretsPath}' does not exist`;
        return this.buildHealthResult('unreachable', latencyMs, this.lastFailureReason);
      }

      const files = await this.listSecrets();
      const latencyMs = Date.now() - start;
      this.retryCount = 0;
      return {
        ...this.buildHealthResult('healthy', latencyMs),
        providerVersion: `${files.length} secret(s) mounted at ${this.secretsPath}`,
      };
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
      providerId: 'docker',
      providerType: 'docker',
      displayName: this.displayName,
      status,
      latencyMs,
      lastChecked: new Date().toISOString(),
      lastSuccess: status === 'healthy' ? new Date().toISOString() : undefined,
      lastFailure: this.lastFailure,
      failureReason,
      retryCount: this.retryCount,
      providerVersion: `Docker Secrets (/run/secrets)`,
      authStatus: 'authenticated', // File system access; no explicit auth
      availability: status === 'healthy' ? 100 : 0,
    };
  }
}
