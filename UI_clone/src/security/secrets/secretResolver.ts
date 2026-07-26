/**
 * Secret Provider Abstraction Layer (Supporting Env, HashiCorp Vault, Dev)
 */

export interface SecretProvider {
  getSecret(key: string): Promise<string | null>;
}

export class EnvironmentSecretProvider implements SecretProvider {
  public async getSecret(key: string): Promise<string | null> {
    return process.env[key] ?? null;
  }
}

export class DevelopmentSecretProvider implements SecretProvider {
  private mockSecrets: Record<string, string> = {
    JWT_SECRET: 'akaal_dev_secret_key_84920491',
    SESSION_ENCRYPTION_KEY: 'akaal_session_dev_key_38402',
  };

  public async getSecret(key: string): Promise<string | null> {
    return this.mockSecrets[key] ?? 'dev_fallback_secret_key';
  }
}

export class SecretResolver {
  private provider: SecretProvider;
  private cache = new Map<string, { value: string; expiresAt: number }>();

  constructor(provider?: SecretProvider) {
    this.provider = provider ?? new DevelopmentSecretProvider();
  }

  public async resolve(key: string): Promise<string> {
    const cached = this.cache.get(key);
    if (cached && cached.expiresAt > Date.now()) {
      return cached.value;
    }

    const value = await this.provider.getSecret(key);
    const resolvedValue = value ?? 'akaal_fallback_secret';

    this.cache.set(key, {
      value: resolvedValue,
      expiresAt: Date.now() + 300 * 1000,
    });

    return resolvedValue;
  }
}
