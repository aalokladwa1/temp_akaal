/**
 * AKAAL Enterprise Certificate Management — Domain Types
 * Stage 7.3
 */

export type CertStatus =
  | 'valid'
  | 'expiring_soon'
  | 'expired'
  | 'revoked'
  | 'pending_renewal'
  | 'pending_import'
  | 'invalid';

export type CertFormat = 'PEM' | 'PKCS12' | 'DER';

export type CertUsage =
  | 'server_auth'
  | 'client_auth'
  | 'code_signing'
  | 'email_protection'
  | 'tls'
  | 'mtls_client'
  | 'mtls_server'
  | 'ca'
  | 'intermediate_ca';

export interface SubjectInfo {
  commonName: string;
  organization?: string;
  organizationalUnit?: string;
  country?: string;
  state?: string;
  locality?: string;
  emailAddress?: string;
}

export interface CertRecord {
  id: string;
  name: string;
  description: string;
  status: CertStatus;
  usage: CertUsage[];

  // Certificate identity
  subject: SubjectInfo;
  issuer: SubjectInfo;
  serialNumber: string;
  fingerprint: string; // SHA-256 fingerprint
  fingerprintAlgorithm: 'SHA-256' | 'SHA-1';

  // Subject Alternative Names
  sans: string[];

  // Validity
  notBefore: string; // ISO 8601
  notAfter: string;  // ISO 8601
  daysUntilExpiry: number; // Computed field

  // Chain
  isCA: boolean;
  isSelfSigned: boolean;
  chainDepth: number;
  issuerCertId?: string; // References parent CA cert

  // Storage
  format: CertFormat;
  pemCert?: string;     // PEM encoded cert (public)
  pemChain?: string;    // Full chain PEM
  hasPrivateKey: boolean;

  // Renewal
  autoRenewEnabled: boolean;
  renewalLeadDays: number;
  lastRenewalAt?: string;
  renewalRequestedAt?: string;

  // Revocation
  revokedAt?: string;
  revocationReason?: string;
  crlDistributionPoints?: string[];
  ocspUrl?: string;

  // Metadata
  labels: Record<string, string>;
  tags: string[];
  owner: string;
  tenantId: string;
  createdAt: string;
  updatedAt: string;
  importedAt: string;
}

export interface CertValidationResult {
  certId: string;
  isValid: boolean;
  status: CertStatus;
  errors: string[];
  warnings: string[];
  chainValid: boolean;
  signatureValid: boolean;
  notExpired: boolean;
  notRevoked: boolean;
  daysUntilExpiry: number;
  checkedAt: string;
}

export interface CertImportRequest {
  name: string;
  description?: string;
  pemCert: string;
  pemChain?: string;
  pemPrivateKey?: string;
  pkcs12Data?: string; // Base64 encoded
  pkcs12Password?: string;
  usage: CertUsage[];
  labels?: Record<string, string>;
  tags?: string[];
  owner?: string;
  tenantId?: string;
  autoRenewEnabled?: boolean;
  renewalLeadDays?: number;
}

export interface CertMonitorReport {
  totalCerts: number;
  valid: number;
  expiringSoon: number; // Within warning threshold
  expired: number;
  revoked: number;
  pendingRenewal: number;
  invalid: number;
  expiringWithin30Days: CertRecord[];
  expiringWithin7Days: CertRecord[];
  alreadyExpired: CertRecord[];
  generatedAt: string;
}
