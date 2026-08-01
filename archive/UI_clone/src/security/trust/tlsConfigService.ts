/**
 * AKAAL TLS Configuration Service
 * Stage 7.3
 *
 * Provides enterprise TLS & mTLS configuration management and policy generation.
 */

import { TLSConfig, MTLSConfig } from './trustTypes';
import { GovernancePersistenceStore } from '../governance/governancePersistenceStore';

const STORE_TLS_KEY = 'tls_config';
const STORE_MTLS_KEY = 'mtls_config';

const DEFAULT_TLS_CONFIG: TLSConfig = {
  id: 'tls_cfg_enterprise_default',
  name: 'Enterprise Default TLS 1.3 Strict',
  description: 'Strict TLS configuration with TLS 1.3 minimum and HSTS preloading enabled.',
  minVersion: 'TLSv1.3',
  maxVersion: 'TLSv1.3',
  cipherSuites: [
    'TLS_AES_256_GCM_SHA384',
    'TLS_AES_128_GCM_SHA256',
    'TLS_CHACHA20_POLY1305_SHA256',
  ],
  hstsEnabled: true,
  hstsMaxAgeSeconds: 31536000, // 1 year
  hstsIncludeSubdomains: true,
  hstsPreload: true,
  clientCertRequired: false,
  clientCertTrustAnchors: [],
  sessionResumptionEnabled: true,
  sessionTimeoutSeconds: 28800,
  ocspStaplingEnabled: true,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  isDefault: true,
};

const DEFAULT_MTLS_CONFIG: MTLSConfig = {
  id: 'mtls_cfg_zero_trust',
  name: 'Zero-Trust Internal mTLS',
  enabled: true,
  requireClientCert: true,
  clientCACertIds: ['cert_wildcard_akaal'],
  serverCertId: 'cert_wildcard_akaal',
  verifyDepth: 2,
  allowSelfSigned: false,
  subjectDNFilters: ['O=AKAAL Enterprise'],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export class TLSConfigService {
  public static getTLSConfig(): TLSConfig {
    const configs = GovernancePersistenceStore.getItem<TLSConfig>(STORE_TLS_KEY, [DEFAULT_TLS_CONFIG]);
    return configs.find((c) => c.isDefault) ?? configs[0] ?? DEFAULT_TLS_CONFIG;
  }

  public static saveTLSConfig(config: TLSConfig): TLSConfig {
    const updated = { ...config, updatedAt: new Date().toISOString() };
    GovernancePersistenceStore.setItem<TLSConfig>(STORE_TLS_KEY, [updated]);
    return updated;
  }

  public static getMTLSConfig(): MTLSConfig {
    const configs = GovernancePersistenceStore.getItem<MTLSConfig>(STORE_MTLS_KEY, [DEFAULT_MTLS_CONFIG]);
    return configs[0] ?? DEFAULT_MTLS_CONFIG;
  }

  public static saveMTLSConfig(config: MTLSConfig): MTLSConfig {
    const updated = { ...config, updatedAt: new Date().toISOString() };
    GovernancePersistenceStore.setItem<MTLSConfig>(STORE_MTLS_KEY, [updated]);
    return updated;
  }
}
