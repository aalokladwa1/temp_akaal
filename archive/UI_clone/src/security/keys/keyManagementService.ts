/**
 * AKAAL Enterprise Key Management Service
 * Stage 7.3
 *
 * Implements Key Creation, Rotation, Versioning, Revocation, Expiration, and Audit.
 */

import { KeyRecord, KeyVersion, KeyCreateRequest, KeyRotationResult, KeyRevocationResult } from './keyTypes';
import { KeyStore } from './keyStore';
import { CryptoService } from '../crypto/crypto.service';
import { AuditPipeline } from '../audit/auditPipeline';

export class KeyManagementService {
  public static list(): KeyRecord[] {
    return KeyStore.load().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  public static get(id: string): KeyRecord | null {
    return KeyStore.get(id);
  }

  public static async create(req: KeyCreateRequest, requestedBy = 'system'): Promise<KeyRecord> {
    const records = KeyStore.load();
    const id = `key_${CryptoService.generateSecureToken(12)}`;
    const versionId = `kver_${CryptoService.generateSecureToken(8)}`;
    const now = new Date().toISOString();
    const keyId = `kid_${CryptoService.generateSecureToken(16)}`;

    let publicKeyPem: string | undefined;
    let cryptoKeyOrPair: CryptoKey | CryptoKeyPair | undefined;

    // Generate actual CryptoKey using enterprise CryptoService
    if (req.algorithm === 'AES-256-GCM' || req.algorithm === 'AES-128-GCM') {
      const res = await CryptoService.generateAESKey();
      cryptoKeyOrPair = res.cryptoKey;
    } else if (req.algorithm === 'RSA-4096' || req.algorithm === 'RSA-2048') {
      const res = await CryptoService.generateRSAKeyPair();
      publicKeyPem = res.publicKeyPem;
      cryptoKeyOrPair = res.cryptoKeyPair;
    } else if (req.algorithm === 'ECDSA-P256' || req.algorithm === 'ECDSA-P384') {
      const res = await CryptoService.generateECDSAKeyPair(req.algorithm === 'ECDSA-P256' ? 'P-256' : 'P-384');
      publicKeyPem = res.publicKeyPem;
      cryptoKeyOrPair = res.cryptoKeyPair;
    } else if (req.algorithm === 'Ed25519') {
      const res = await CryptoService.generateEd25519KeyPair();
      cryptoKeyOrPair = res.cryptoKeyPair;
    }

    if (cryptoKeyOrPair) {
      KeyStore.storeKeyMaterial(versionId, cryptoKeyOrPair);
    }

    const version: KeyVersion = {
      versionId,
      versionNumber: 1,
      algorithm: req.algorithm,
      createdAt: now,
      isActive: true,
      publicKeyPem,
      keyId,
      fingerprint: `sha256:${await CryptoService.sha256(keyId)}`,
    };

    const record: KeyRecord = {
      id,
      name: req.name,
      description: req.description ?? '',
      algorithm: req.algorithm,
      purpose: req.purpose,
      status: 'active',
      labels: req.labels ?? {},
      tags: req.tags ?? [],
      owner: req.owner ?? requestedBy,
      tenantId: req.tenantId ?? '',
      currentVersionId: versionId,
      versions: [version],
      createdAt: now,
      updatedAt: now,
      expiresAt: req.expiresAt,
      usagePolicy: {
        allowedOperations: req.usagePolicy?.allowedOperations ?? ['encrypt', 'decrypt', 'sign', 'verify'],
        allowedEnvironments: req.usagePolicy?.allowedEnvironments ?? ['production', 'staging', 'development'],
        requiresMFA: req.usagePolicy?.requiresMFA ?? false,
        requiresApproval: req.usagePolicy?.requiresApproval ?? false,
      },
      autoRotateEnabled: req.autoRotateEnabled ?? false,
      rotationIntervalDays: req.rotationIntervalDays ?? 90,
      nextRotationAt: req.autoRotateEnabled
        ? new Date(Date.now() + (req.rotationIntervalDays ?? 90) * 864e5).toISOString()
        : undefined,
    };

    records.push(record);
    KeyStore.save(records);

    AuditPipeline.log({
      eventType: 'KEY_CREATE',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: record.tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'KeyManagementService',
      resource: `key:${id}`,
      action: 'create_key',
      status: 'SUCCESS',
      details: { keyName: record.name, algorithm: record.algorithm, purpose: record.purpose },
    });

    return record;
  }

  public static async rotate(id: string, requestedBy = 'system'): Promise<KeyRotationResult> {
    const records = KeyStore.load();
    const idx = records.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error(`KeyManagementService: key '${id}' not found`);

    const record = records[idx];
    const oldVersionId = record.currentVersionId;
    const newVersionNumber = Math.max(...record.versions.map((v) => v.versionNumber)) + 1;
    const newVersionId = `kver_${CryptoService.generateSecureToken(8)}`;
    const newKeyId = `kid_${CryptoService.generateSecureToken(16)}`;
    const now = new Date().toISOString();

    let publicKeyPem: string | undefined;
    let cryptoKeyOrPair: CryptoKey | CryptoKeyPair | undefined;

    if (record.algorithm === 'AES-256-GCM' || record.algorithm === 'AES-128-GCM') {
      const res = await CryptoService.generateAESKey();
      cryptoKeyOrPair = res.cryptoKey;
    } else if (record.algorithm === 'RSA-4096' || record.algorithm === 'RSA-2048') {
      const res = await CryptoService.generateRSAKeyPair();
      publicKeyPem = res.publicKeyPem;
      cryptoKeyOrPair = res.cryptoKeyPair;
    } else if (record.algorithm === 'ECDSA-P256' || record.algorithm === 'ECDSA-P384') {
      const res = await CryptoService.generateECDSAKeyPair(record.algorithm === 'ECDSA-P256' ? 'P-256' : 'P-384');
      publicKeyPem = res.publicKeyPem;
      cryptoKeyOrPair = res.cryptoKeyPair;
    } else if (record.algorithm === 'Ed25519') {
      const res = await CryptoService.generateEd25519KeyPair();
      cryptoKeyOrPair = res.cryptoKeyPair;
    }

    if (cryptoKeyOrPair) {
      KeyStore.storeKeyMaterial(newVersionId, cryptoKeyOrPair);
    }

    const updatedVersions = record.versions.map((v) => ({ ...v, isActive: false }));

    const newVersion: KeyVersion = {
      versionId: newVersionId,
      versionNumber: newVersionNumber,
      algorithm: record.algorithm,
      createdAt: now,
      isActive: true,
      publicKeyPem,
      keyId: newKeyId,
      fingerprint: `sha256:${await CryptoService.sha256(newKeyId)}`,
    };

    records[idx] = {
      ...record,
      currentVersionId: newVersionId,
      versions: [...updatedVersions, newVersion],
      lastRotatedAt: now,
      updatedAt: now,
      nextRotationAt: record.autoRotateEnabled && record.rotationIntervalDays
        ? new Date(Date.now() + record.rotationIntervalDays * 864e5).toISOString()
        : undefined,
    };

    KeyStore.save(records);

    AuditPipeline.log({
      eventType: 'KEY_ROTATE',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: record.tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'KeyManagementService',
      resource: `key:${id}`,
      action: 'rotate_key',
      status: 'SUCCESS',
      details: { keyName: record.name, oldVersionId, newVersionId },
    });

    return {
      keyId: id,
      oldVersionId,
      newVersionId,
      rotatedAt: now,
      algorithm: record.algorithm,
    };
  }

  public static revoke(id: string, reason: string, requestedBy = 'system'): KeyRevocationResult {
    const records = KeyStore.load();
    const idx = records.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error(`KeyManagementService: key '${id}' not found`);

    const record = records[idx];
    const now = new Date().toISOString();

    const updatedVersions = record.versions.map((v) => {
      if (v.versionId === record.currentVersionId) {
        return { ...v, isActive: false, revokedAt: now, revocationReason: reason };
      }
      return v;
    });

    records[idx] = {
      ...record,
      status: 'revoked',
      versions: updatedVersions,
      updatedAt: now,
    };

    KeyStore.save(records);

    AuditPipeline.log({
      eventType: 'KEY_REVOKE',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: record.tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'KeyManagementService',
      resource: `key:${id}`,
      action: 'revoke_key',
      status: 'SUCCESS',
      details: { keyName: record.name, reason, versionId: record.currentVersionId },
    });

    return {
      keyId: id,
      versionId: record.currentVersionId,
      revokedAt: now,
      reason,
    };
  }
}
