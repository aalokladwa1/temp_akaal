/**
 * AKAAL Secret Provider Factory & Registry
 * Stage 7.3
 *
 * Configuration-driven provider selection with dependency injection.
 * Application code must only use SecretProviderFactory — never instantiate providers directly.
 * Supports ordered failover chains and runtime provider switching.
 */

import { SecretProviderConfig, SecretProviderType, SecretProviderHealth } from './secretTypes';
import { SecretProviderInterface } from './providers/envProvider';
import { EnvironmentSecretProvider } from './providers/envProvider';
import { VaultSecretProvider } from './providers/vaultProvider';
import { AWSSecretsManagerProvider } from './providers/awsSecretsProvider';
import { AzureKeyVaultProvider } from './providers/azureKeyVaultProvider';
import { GCPSecretManagerProvider } from './providers/gcpSecretProvider';
import { KubernetesSecretProvider } from './providers/kubernetesProvider';
import { DockerSecretProvider } from './providers/dockerProvider';
import { CustomEnterpriseProvider } from './providers/customEnterpriseProvider';

export type { SecretProviderInterface };

// ─────────────────────────────────────────────────────────────────────────────
// Provider Factory
// ─────────────────────────────────────────────────────────────────────────────

export class SecretProviderFactory {
  /**
   * Instantiates the appropriate provider implementation based on configuration.
   * No provider-specific logic may exist outside this factory.
   */
  public static create(config: SecretProviderConfig): SecretProviderInterface {
    switch (config.type) {
      case 'env':
        return new EnvironmentSecretProvider(config);
      case 'vault':
        return new VaultSecretProvider(config);
      case 'aws_secrets_manager':
        return new AWSSecretsManagerProvider(config);
      case 'azure_key_vault':
        return new AzureKeyVaultProvider(config);
      case 'gcp_secret_manager':
        return new GCPSecretManagerProvider(config);
      case 'kubernetes':
        return new KubernetesSecretProvider(config);
      case 'docker':
        return new DockerSecretProvider(config);
      case 'custom':
        return new CustomEnterpriseProvider(config);
      default: {
        const _exhaustive: never = config.type;
        throw new Error(`SecretProviderFactory: unknown provider type '${_exhaustive}'`);
      }
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Provider Registry (Dependency Injection Container)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Singleton registry. Application code resolves providers through this registry.
 * Supports ordered failover: if the primary provider fails, the next enabled
 * provider in priority order is tried automatically.
 */
export class SecretProviderRegistry {
  private static instance: SecretProviderRegistry | null = null;
  private providers: Map<SecretProviderType, SecretProviderInterface> = new Map();
  private configs: Map<SecretProviderType, SecretProviderConfig> = new Map();
  private failoverChain: SecretProviderType[] = [];

  private constructor() {}

  public static getInstance(): SecretProviderRegistry {
    if (!SecretProviderRegistry.instance) {
      SecretProviderRegistry.instance = new SecretProviderRegistry();
    }
    return SecretProviderRegistry.instance;
  }

  /**
   * Register one or more providers. Providers are sorted by priority
   * (ascending) to form the failover chain.
   */
  public register(configs: SecretProviderConfig[]): void {
    const enabled = configs.filter((c) => c.enabled).sort((a, b) => a.priority - b.priority);

    for (const config of enabled) {
      this.configs.set(config.type, config);
      this.providers.set(config.type, SecretProviderFactory.create(config));
    }

    this.failoverChain = enabled.map((c) => c.type);
  }

  /**
   * Registers or updates a single provider configuration at runtime.
   */
  public registerProvider(config: SecretProviderConfig): void {
    this.configs.set(config.type, config);
    if (config.enabled) {
      this.providers.set(config.type, SecretProviderFactory.create(config));
      if (!this.failoverChain.includes(config.type)) {
        this.failoverChain.push(config.type);
        this.failoverChain.sort((a, b) => {
          const pa = this.configs.get(a)?.priority ?? 99;
          const pb = this.configs.get(b)?.priority ?? 99;
          return pa - pb;
        });
      }
    } else {
      // Disable
      this.providers.delete(config.type);
      this.failoverChain = this.failoverChain.filter((t) => t !== config.type);
    }
  }

  /**
   * Resolves the primary provider — the highest-priority enabled provider.
   */
  public getPrimaryProvider(): SecretProviderInterface {
    if (this.failoverChain.length === 0) {
      // Auto-register env provider as fallback
      const fallback: SecretProviderConfig = {
        type: 'env',
        enabled: true,
        priority: 100,
        displayName: 'Environment Variables (auto-fallback)',
      };
      this.register([fallback]);
    }

    const primary = this.failoverChain[0];
    const provider = this.providers.get(primary);
    if (!provider) throw new Error('SecretProviderRegistry: no providers registered');
    return provider;
  }

  /**
   * Resolves a secret using the failover chain.
   * Tries each provider in priority order until one returns a non-null value.
   */
  public async resolveWithFailover(key: string): Promise<string | null> {
    const errors: string[] = [];

    for (const providerType of this.failoverChain) {
      const provider = this.providers.get(providerType);
      if (!provider) continue;

      try {
        const value = await provider.getSecret(key);
        if (value !== null) return value;
      } catch (err: unknown) {
        errors.push(`${providerType}: ${err instanceof Error ? err.message : String(err)}`);
      }
    }

    if (errors.length > 0 && this.failoverChain.length > 0) {
      console.warn(`[SecretProviderRegistry] All providers failed for key '${key}':`, errors.join('; '));
    }

    return null;
  }

  /**
   * Writes a secret to the primary provider.
   */
  public async setSecret(key: string, value: string): Promise<void> {
    const provider = this.getPrimaryProvider();
    await provider.setSecret(key, value);
  }

  /**
   * Deletes a secret from the primary provider.
   */
  public async deleteSecret(key: string): Promise<void> {
    const provider = this.getPrimaryProvider();
    await provider.deleteSecret(key);
  }

  /**
   * Lists secrets from the primary provider.
   */
  public async listSecrets(prefix?: string): Promise<string[]> {
    const provider = this.getPrimaryProvider();
    return provider.listSecrets(prefix);
  }

  /**
   * Returns the registered provider configuration by type.
   */
  public getConfig(type: SecretProviderType): SecretProviderConfig | undefined {
    return this.configs.get(type);
  }

  /**
   * Returns all registered provider configurations.
   */
  public getAllConfigs(): SecretProviderConfig[] {
    return Array.from(this.configs.values());
  }

  /**
   * Returns the current failover chain order.
   */
  public getFailoverChain(): SecretProviderType[] {
    return [...this.failoverChain];
  }

  /**
   * Runs health checks on all registered providers.
   */
  public async checkAllHealth(): Promise<SecretProviderHealth[]> {
    const results: SecretProviderHealth[] = [];

    for (const [, provider] of this.providers) {
      try {
        const health = await provider.testConnectivity();
        results.push(health);
      } catch (err: unknown) {
        // Provider threw unexpectedly — mark as unreachable
        results.push({
          providerId: provider.providerType,
          providerType: provider.providerType as SecretProviderType,
          displayName: provider.displayName,
          status: 'unreachable',
          lastChecked: new Date().toISOString(),
          retryCount: 0,
          authStatus: 'unknown',
          availability: 0,
          failureReason: err instanceof Error ? err.message : String(err),
        });
      }
    }

    // Include unconfigured providers from the full set of known types
    const allTypes: SecretProviderType[] = [
      'env', 'vault', 'aws_secrets_manager', 'azure_key_vault',
      'gcp_secret_manager', 'kubernetes', 'docker', 'custom',
    ];
    for (const type of allTypes) {
      if (!this.providers.has(type)) {
        const config = this.configs.get(type);
        results.push({
          providerId: type,
          providerType: type,
          displayName: config?.displayName ?? type,
          status: 'disabled',
          lastChecked: new Date().toISOString(),
          retryCount: 0,
          authStatus: 'unknown',
          availability: 0,
        });
      }
    }

    return results.sort((a, b) => {
      const pa = this.configs.get(a.providerType)?.priority ?? 99;
      const pb = this.configs.get(b.providerType)?.priority ?? 99;
      return pa - pb;
    });
  }

  /**
   * Resets the registry — useful for testing and configuration reload.
   */
  public reset(): void {
    this.providers.clear();
    this.configs.clear();
    this.failoverChain = [];
  }

  /**
   * For testing: directly inject a mock provider.
   */
  public injectProvider(type: SecretProviderType, provider: SecretProviderInterface, config: SecretProviderConfig): void {
    this.configs.set(type, config);
    this.providers.set(type, provider);
    if (!this.failoverChain.includes(type)) {
      this.failoverChain.push(type);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience singleton access
// ─────────────────────────────────────────────────────────────────────────────

export const secretRegistry = SecretProviderRegistry.getInstance();

/**
 * Initialize the registry from configuration.
 * Call this once at application startup.
 */
export function initializeSecretProviders(configs: SecretProviderConfig[]): void {
  secretRegistry.register(configs);
}

/**
 * Resolve a secret value using the failover chain.
 * This is the recommended way for application code to retrieve secrets.
 */
export async function resolveSecret(key: string): Promise<string | null> {
  return secretRegistry.resolveWithFailover(key);
}
