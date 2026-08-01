/**
 * AKAAL Enterprise Key Store
 * Stage 7.3
 *
 * Persists key metadata via GovernancePersistenceStore.
 * Raw key material is NEVER stored in localStorage — only metadata and public keys.
 * An in-memory map holds live CryptoKey objects for the current session.
 */

import { KeyRecord, KeyVersion } from './keyTypes';
import { GovernancePersistenceStore } from '../governance/governancePersistenceStore';

const STORE_KEY = 'encryption_keys';

// In-memory map: versionId → CryptoKey (raw key material, never serialized)
const keyMaterialStore = new Map<string, CryptoKey | CryptoKeyPair>();

const INITIAL_KEYS: KeyRecord[] = [
  {
    id: 'key_aes_data_enc',
    name: 'data-encryption-key-prod',
    description: 'Primary AES-256-GCM data encryption key for production',
    algorithm: 'AES-256-GCM',
    purpose: 'encryption',
    status: 'active',
    labels: { environment: 'production', tier: 'critical' },
    tags: ['encryption', 'data', 'production'],
    owner: 'platform-security',
    tenantId: 'tenant_prod_us_east',
    currentVersionId: 'kver_aes_v2',
    versions: [
      { versionId: 'kver_aes_v1', versionNumber: 1, algorithm: 'AES-256-GCM', createdAt: new Date(Date.now() - 864e5 * 120).toISOString(), isActive: false, keyId: 'kid_aes_v1', fingerprint: 'sha256:abc123' },
      { versionId: 'kver_aes_v2', versionNumber: 2, algorithm: 'AES-256-GCM', createdAt: new Date(Date.now() - 864e5 * 30).toISOString(), isActive: true, keyId: 'kid_aes_v2', fingerprint: 'sha256:def456' },
    ],
    createdAt: new Date(Date.now() - 864e5 * 180).toISOString(),
    updatedAt: new Date(Date.now() - 864e5 * 30).toISOString(),
    lastRotatedAt: new Date(Date.now() - 864e5 * 30).toISOString(),
    usagePolicy: { allowedOperations: ['encrypt', 'decrypt'], allowedEnvironments: ['production'], requiresMFA: false, requiresApproval: false },
    autoRotateEnabled: true,
    rotationIntervalDays: 90,
    nextRotationAt: new Date(Date.now() + 864e5 * 60).toISOString(),
  },
  {
    id: 'key_rsa_signing',
    name: 'rsa-4096-signing-key',
    description: 'RSA-4096 signing key for document verification',
    algorithm: 'RSA-4096',
    purpose: 'signing',
    status: 'active',
    labels: { environment: 'production', usage: 'signing' },
    tags: ['rsa', 'signing', 'documents'],
    owner: 'platform-security',
    tenantId: 'tenant_prod_us_east',
    currentVersionId: 'kver_rsa_v1',
    versions: [
      { versionId: 'kver_rsa_v1', versionNumber: 1, algorithm: 'RSA-4096', createdAt: new Date(Date.now() - 864e5 * 60).toISOString(), isActive: true, keyId: 'kid_rsa_v1', fingerprint: 'sha256:ghi789', publicKeyPem: '-----BEGIN PUBLIC KEY-----\n[RSA-4096 Public Key]\n-----END PUBLIC KEY-----' },
    ],
    createdAt: new Date(Date.now() - 864e5 * 60).toISOString(),
    updatedAt: new Date(Date.now() - 864e5 * 60).toISOString(),
    usagePolicy: { allowedOperations: ['sign', 'verify'], allowedEnvironments: ['production', 'staging'], requiresMFA: true, requiresApproval: false },
    autoRotateEnabled: false,
  },
];

export class KeyStore {
  public static load(): KeyRecord[] {
    return GovernancePersistenceStore.getItem<KeyRecord>(STORE_KEY, INITIAL_KEYS);
  }

  public static save(records: KeyRecord[]): void {
    GovernancePersistenceStore.setItem<KeyRecord>(STORE_KEY, records);
  }

  public static get(id: string): KeyRecord | null {
    return KeyStore.load().find((r) => r.id === id) ?? null;
  }

  public static getByVersion(versionId: string): { record: KeyRecord; version: KeyVersion } | null {
    const records = KeyStore.load();
    for (const record of records) {
      const version = record.versions.find((v) => v.versionId === versionId);
      if (version) return { record, version };
    }
    return null;
  }

  // ─────────────────────────────────
  // Key Material (in-memory only)
  // ─────────────────────────────────

  public static storeKeyMaterial(versionId: string, key: CryptoKey | CryptoKeyPair): void {
    keyMaterialStore.set(versionId, key);
  }

  public static getKeyMaterial(versionId: string): CryptoKey | CryptoKeyPair | undefined {
    return keyMaterialStore.get(versionId);
  }

  public static removeKeyMaterial(versionId: string): void {
    keyMaterialStore.delete(versionId);
  }

  public static isKeyMaterialLoaded(versionId: string): boolean {
    return keyMaterialStore.has(versionId);
  }
}
