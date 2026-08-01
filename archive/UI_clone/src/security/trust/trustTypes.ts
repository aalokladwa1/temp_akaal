/**
 * AKAAL Enterprise Trust Infrastructure — Domain Types
 * Stage 7.3
 */

export type TLSVersion = 'TLSv1.2' | 'TLSv1.3';

export type CipherSuite =
  | 'TLS_AES_256_GCM_SHA384'
  | 'TLS_AES_128_GCM_SHA256'
  | 'TLS_CHACHA20_POLY1305_SHA256'
  | 'ECDHE-RSA-AES256-GCM-SHA384'
  | 'ECDHE-RSA-AES128-GCM-SHA256'
  | 'ECDHE-ECDSA-AES256-GCM-SHA384'
  | 'ECDHE-ECDSA-AES128-GCM-SHA256';

export interface TLSConfig {
  id: string;
  name: string;
  description: string;

  // Protocol versions
  minVersion: TLSVersion;
  maxVersion: TLSVersion;

  // Cipher suites (TLS 1.3 uses built-in suites; TLS 1.2 configurable)
  cipherSuites: CipherSuite[];

  // HSTS
  hstsEnabled: boolean;
  hstsMaxAgeSeconds: number;
  hstsIncludeSubdomains: boolean;
  hstsPreload: boolean;

  // Certificate configuration
  serverCertId?: string;
  clientCertRequired: boolean;
  clientCertTrustAnchors: string[]; // CA cert IDs

  // Session configuration
  sessionResumptionEnabled: boolean;
  sessionTimeoutSeconds: number;

  // OCSP Stapling
  ocspStaplingEnabled: boolean;

  createdAt: string;
  updatedAt: string;
  isDefault: boolean;
}

export interface MTLSConfig {
  id: string;
  name: string;
  enabled: boolean;
  requireClientCert: boolean;
  clientCACertIds: string[]; // Trusted CA cert IDs for client validation
  serverCertId: string;
  verifyDepth: number;
  allowSelfSigned: boolean;
  subjectDNFilters?: string[]; // Optional DN pattern filters
  createdAt: string;
  updatedAt: string;
}

export interface CertPin {
  id: string;
  hostname: string;
  subjectPublicKeyInfoHash: string; // SHA-256 of SPKI in base64
  backupPins: string[];
  includeSubdomains: boolean;
  reportUri?: string;
  maxAgeSeconds: number;
  enabled: boolean;
  createdAt: string;
  expiresAt?: string;
}

export interface TrustAnchor {
  id: string;
  name: string;
  description: string;
  certId: string; // References CertRecord
  subjectDN: string;
  fingerprint: string;
  isRootCA: boolean;
  isIntermediate: boolean;
  enabled: boolean;
  addedAt: string;
  expiresAt: string;
  trustedForPurposes: ('server_auth' | 'client_auth' | 'tls' | 'mtls')[];
}

export interface TrustStoreConfig {
  id: string;
  name: string;
  description: string;
  anchors: TrustAnchor[];
  pins: CertPin[];
  useSystemCAs: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface TrustValidationResult {
  isValid: boolean;
  chain: string[];
  anchorsUsed: string[];
  errors: string[];
  warnings: string[];
  validatedAt: string;
}

export interface TrustReport {
  tlsConfigs: number;
  mtlsEnabled: boolean;
  trustAnchors: number;
  pinnedHosts: number;
  expiredAnchors: number;
  expiringAnchors: number;
  generatedAt: string;
}
