/**
 * AKAAL Enterprise Key Management — Domain Types
 * Stage 7.3
 */

export type KeyAlgorithm =
  | 'AES-256-GCM'
  | 'AES-128-GCM'
  | 'RSA-4096'
  | 'RSA-2048'
  | 'ECDSA-P256'
  | 'ECDSA-P384'
  | 'Ed25519'
  | 'HMAC-SHA256'
  | 'HMAC-SHA512';

export type KeyStatus = 'active' | 'rotated' | 'revoked' | 'expired' | 'pending' | 'compromised';

export type KeyPurpose =
  | 'encryption'
  | 'decryption'
  | 'signing'
  | 'verification'
  | 'key_wrapping'
  | 'authentication'
  | 'jwt_signing'
  | 'tls';

export type KeyUsageOperation =
  | 'encrypt'
  | 'decrypt'
  | 'sign'
  | 'verify'
  | 'wrapKey'
  | 'unwrapKey'
  | 'deriveKey'
  | 'deriveBits';

export interface KeyUsagePolicy {
  allowedOperations: KeyUsageOperation[];
  allowedEnvironments: ('production' | 'staging' | 'development')[];
  maxUsageCount?: number; // Optional hard limit
  requiresMFA: boolean;
  requiresApproval: boolean;
  expiresAt?: string;
}

export interface KeyVersion {
  versionId: string;
  versionNumber: number;
  algorithm: KeyAlgorithm;
  createdAt: string;
  isActive: boolean;
  revokedAt?: string;
  revocationReason?: string;
  publicKeyPem?: string; // For asymmetric keys — public key only, never private
  keyId: string; // Key identifier for referencing without exposing material
  fingerprint: string; // Hash of the public key or key material hash
}

export interface KeyRecord {
  id: string;
  name: string;
  description: string;
  algorithm: KeyAlgorithm;
  purpose: KeyPurpose;
  status: KeyStatus;

  // Metadata
  labels: Record<string, string>;
  tags: string[];
  owner: string;
  tenantId: string;

  // Version history
  currentVersionId: string;
  versions: KeyVersion[];

  // Lifecycle
  createdAt: string;
  updatedAt: string;
  lastRotatedAt?: string;
  expiresAt?: string;

  // Policy
  usagePolicy: KeyUsagePolicy;

  // Rotation
  autoRotateEnabled: boolean;
  rotationIntervalDays?: number;
  nextRotationAt?: string;
}

export interface KeyCreateRequest {
  name: string;
  description?: string;
  algorithm: KeyAlgorithm;
  purpose: KeyPurpose;
  labels?: Record<string, string>;
  tags?: string[];
  owner?: string;
  tenantId?: string;
  expiresAt?: string;
  usagePolicy?: Partial<KeyUsagePolicy>;
  autoRotateEnabled?: boolean;
  rotationIntervalDays?: number;
}

export interface KeyRotationResult {
  keyId: string;
  oldVersionId: string;
  newVersionId: string;
  rotatedAt: string;
  algorithm: KeyAlgorithm;
}

export interface KeyRevocationResult {
  keyId: string;
  versionId: string;
  revokedAt: string;
  reason: string;
}
