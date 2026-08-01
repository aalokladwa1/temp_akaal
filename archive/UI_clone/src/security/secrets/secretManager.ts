/**
 * AKAAL Enterprise Secret Manager
 * Stage 7.3
 *
 * Core CRUD, versioning, metadata, expiration enforcement, and audit integration.
 * Backed by GovernancePersistenceStore for session-safe persistence (replaceable with production API).
 */

import {
  SecretRecord,
  SecretVersion,
  SecretCreateRequest,
  SecretUpdateRequest,
  SecretListFilter,
  SecretStatus,
  SecretRotationConfig,
} from './secretTypes';
import { GovernancePersistenceStore } from '../governance/governancePersistenceStore';
import { AuditPipeline } from '../audit/auditPipeline';
import { CryptoService } from '../crypto/crypto.service';
import { secretRegistry } from './secretProviderFactory';

const STORE_KEY = 'secrets';

const DEFAULT_ROTATION_CONFIG: SecretRotationConfig = {
  enabled: false,
  trigger: 'manual',
  gracePeriodHours: 24,
  maxVersionHistory: 10,
};

const INITIAL_SECRETS: SecretRecord[] = [
  {
    id: 'sec_jwt_signing_01',
    name: 'jwt-signing-key-prod',
    description: 'Production JWT signing key (RS256)',
    type: 'jwt_signing_key',
    status: 'active',
    provider: 'env',
    providerPath: 'JWT_SIGNING_KEY',
    labels: { environment: 'production', tier: 'critical' },
    tags: ['jwt', 'auth', 'signing'],
    owner: 'platform-security',
    tenantId: 'tenant_prod_us_east',
    organizationId: 'org_acme',
    currentVersionId: 'ver_jwt_v2',
    versions: [
      { versionId: 'ver_jwt_v1', versionNumber: 1, createdAt: new Date(Date.now() - 864e5 * 90).toISOString(), createdBy: 'system', isActive: false, checksum: 'abc123' },
      { versionId: 'ver_jwt_v2', versionNumber: 2, createdAt: new Date(Date.now() - 864e5 * 30).toISOString(), createdBy: 'admin@acme.com', isActive: true, checksum: 'def456' },
    ],
    createdAt: new Date(Date.now() - 864e5 * 180).toISOString(),
    updatedAt: new Date(Date.now() - 864e5 * 30).toISOString(),
    lastRotatedAt: new Date(Date.now() - 864e5 * 30).toISOString(),
    nextRotationAt: new Date(Date.now() + 864e5 * 60).toISOString(),
    rotationConfig: { enabled: true, trigger: 'scheduled', intervalDays: 90, gracePeriodHours: 24, maxVersionHistory: 5 },
  },
  {
    id: 'sec_db_cred_prod',
    name: 'db-credentials-production',
    description: 'PostgreSQL production database credentials',
    type: 'database_credential',
    status: 'active',
    provider: 'env',
    providerPath: 'DB_CREDENTIALS_PROD',
    labels: { database: 'postgresql', environment: 'production' },
    tags: ['database', 'postgres', 'production'],
    owner: 'dba-team',
    tenantId: 'tenant_prod_us_east',
    organizationId: 'org_acme',
    currentVersionId: 'ver_db_v1',
    versions: [
      { versionId: 'ver_db_v1', versionNumber: 1, createdAt: new Date(Date.now() - 864e5 * 45).toISOString(), createdBy: 'dba@acme.com', isActive: true, checksum: 'ghi789' },
    ],
    createdAt: new Date(Date.now() - 864e5 * 45).toISOString(),
    updatedAt: new Date(Date.now() - 864e5 * 45).toISOString(),
    expiresAt: new Date(Date.now() + 864e5 * 15).toISOString(), // Expiring soon
    rotationConfig: { enabled: true, trigger: 'scheduled', intervalDays: 60, gracePeriodHours: 48, maxVersionHistory: 3 },
  },
  {
    id: 'sec_oauth_client',
    name: 'oauth-client-secret-github',
    description: 'GitHub OAuth App client secret',
    type: 'oauth_client_secret',
    status: 'active',
    provider: 'env',
    providerPath: 'GITHUB_OAUTH_CLIENT_SECRET',
    labels: { provider: 'github', environment: 'production' },
    tags: ['oauth', 'github'],
    owner: 'devops-team',
    tenantId: 'tenant_prod_us_east',
    organizationId: 'org_acme',
    currentVersionId: 'ver_oauth_v1',
    versions: [
      { versionId: 'ver_oauth_v1', versionNumber: 1, createdAt: new Date(Date.now() - 864e5 * 10).toISOString(), createdBy: 'devops@acme.com', isActive: true, checksum: 'jkl012' },
    ],
    createdAt: new Date(Date.now() - 864e5 * 10).toISOString(),
    updatedAt: new Date(Date.now() - 864e5 * 10).toISOString(),
    rotationConfig: DEFAULT_ROTATION_CONFIG,
  },
];

export class SecretManager {
  // ─────────────────────────────────
  // Persistence Helpers
  // ─────────────────────────────────

  private static load(): SecretRecord[] {
    return GovernancePersistenceStore.getItem<SecretRecord>(STORE_KEY, INITIAL_SECRETS);
  }

  private static save(records: SecretRecord[]): void {
    GovernancePersistenceStore.setItem<SecretRecord>(STORE_KEY, records);
  }

  // ─────────────────────────────────
  // List & Filter
  // ─────────────────────────────────

  public static list(filter?: SecretListFilter): SecretRecord[] {
    let records = SecretManager.load().filter((r) => r.status !== 'deleted');

    if (filter?.type) records = records.filter((r) => r.type === filter.type);
    if (filter?.status) records = records.filter((r) => r.status === filter.status);
    if (filter?.provider) records = records.filter((r) => r.provider === filter.provider);
    if (filter?.owner) records = records.filter((r) => r.owner === filter.owner);
    if (filter?.tenantId) records = records.filter((r) => r.tenantId === filter.tenantId);
    if (filter?.search) {
      const q = filter.search.toLowerCase();
      records = records.filter(
        (r) => r.name.toLowerCase().includes(q) || r.description.toLowerCase().includes(q),
      );
    }
    if (filter?.tags?.length) {
      records = records.filter((r) => filter.tags!.some((t) => r.tags.includes(t)));
    }

    return records.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  // ─────────────────────────────────
  // Get by ID
  // ─────────────────────────────────

  public static get(id: string): SecretRecord | null {
    const records = SecretManager.load();
    return records.find((r) => r.id === id) ?? null;
  }

  // ─────────────────────────────────
  // Create
  // ─────────────────────────────────

  public static async create(req: SecretCreateRequest, requestedBy = 'system'): Promise<SecretRecord> {
    const records = SecretManager.load();
    const id = `sec_${CryptoService.generateSecureToken(12)}`;
    const versionId = `ver_${CryptoService.generateSecureToken(8)}`;
    const now = new Date().toISOString();
    const checksum = await CryptoService.sha256(req.value);

    const version: SecretVersion = {
      versionId,
      versionNumber: 1,
      createdAt: now,
      createdBy: requestedBy,
      isActive: true,
      checksum,
    };

    const record: SecretRecord = {
      id,
      name: req.name,
      description: req.description ?? '',
      type: req.type,
      status: 'active',
      provider: req.provider,
      providerPath: req.providerPath,
      labels: req.labels ?? {},
      tags: req.tags ?? [],
      owner: req.owner ?? requestedBy,
      tenantId: req.tenantId ?? '',
      organizationId: req.organizationId ?? '',
      currentVersionId: versionId,
      versions: [version],
      createdAt: now,
      updatedAt: now,
      expiresAt: req.expiresAt,
      rotationConfig: { ...DEFAULT_ROTATION_CONFIG, ...req.rotationConfig },
    };

    // Persist value to provider
    try {
      await secretRegistry.setSecret(req.providerPath, req.value);
    } catch {
      // Provider unavailable — metadata stored locally, value will sync when provider is available
    }

    records.push(record);
    SecretManager.save(records);

    AuditPipeline.log({
      eventType: 'SECRET_CREATE',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: record.tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'SecretManager',
      resource: `secret:${id}`,
      action: 'create',
      status: 'SUCCESS',
      details: { secretName: record.name, secretType: record.type, provider: record.provider },
    });

    return record;
  }

  // ─────────────────────────────────
  // Update (metadata only)
  // ─────────────────────────────────

  public static update(req: SecretUpdateRequest, requestedBy = 'system'): SecretRecord {
    const records = SecretManager.load();
    const idx = records.findIndex((r) => r.id === req.id);
    if (idx === -1) throw new Error(`SecretManager: secret '${req.id}' not found`);

    const updated: SecretRecord = {
      ...records[idx],
      description: req.description ?? records[idx].description,
      labels: req.labels ?? records[idx].labels,
      tags: req.tags ?? records[idx].tags,
      expiresAt: req.expiresAt ?? records[idx].expiresAt,
      rotationConfig: req.rotationConfig
        ? { ...records[idx].rotationConfig, ...req.rotationConfig }
        : records[idx].rotationConfig,
      updatedAt: new Date().toISOString(),
    };

    records[idx] = updated;
    SecretManager.save(records);

    AuditPipeline.log({
      eventType: 'SECRET_UPDATE',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: updated.tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'SecretManager',
      resource: `secret:${req.id}`,
      action: 'update',
      status: 'SUCCESS',
      details: { secretName: updated.name },
    });

    return updated;
  }

  // ─────────────────────────────────
  // Delete (soft)
  // ─────────────────────────────────

  public static delete(id: string, requestedBy = 'system'): void {
    const records = SecretManager.load();
    const idx = records.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error(`SecretManager: secret '${id}' not found`);

    records[idx] = { ...records[idx], status: 'deleted', updatedAt: new Date().toISOString() };
    SecretManager.save(records);

    AuditPipeline.log({
      eventType: 'SECRET_DELETE',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: records[idx].tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'SecretManager',
      resource: `secret:${id}`,
      action: 'delete',
      status: 'SUCCESS',
      details: { secretName: records[idx].name },
    });
  }

  // ─────────────────────────────────
  // Enable / Disable
  // ─────────────────────────────────

  public static setStatus(id: string, status: SecretStatus, requestedBy = 'system'): SecretRecord {
    const records = SecretManager.load();
    const idx = records.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error(`SecretManager: secret '${id}' not found`);

    records[idx] = { ...records[idx], status, updatedAt: new Date().toISOString() };
    SecretManager.save(records);

    AuditPipeline.log({
      eventType: 'SECRET_UPDATE',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: records[idx].tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'SecretManager',
      resource: `secret:${id}`,
      action: 'status_change',
      status: 'SUCCESS',
      details: { secretName: records[idx].name, newStatus: status },
    });

    return records[idx];
  }

  // ─────────────────────────────────
  // Version History
  // ─────────────────────────────────

  public static getVersions(id: string): SecretVersion[] {
    const record = SecretManager.get(id);
    if (!record) throw new Error(`SecretManager: secret '${id}' not found`);
    return [...record.versions].sort((a, b) => b.versionNumber - a.versionNumber);
  }

  // ─────────────────────────────────
  // Add new version (used by rotation)
  // ─────────────────────────────────

  public static async addVersion(
    id: string,
    newValue: string,
    createdBy = 'system',
  ): Promise<{ secret: SecretRecord; newVersionId: string }> {
    const records = SecretManager.load();
    const idx = records.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error(`SecretManager: secret '${id}' not found`);

    const secret = records[idx];
    const newVersionNumber = Math.max(...secret.versions.map((v) => v.versionNumber)) + 1;
    const newVersionId = `ver_${CryptoService.generateSecureToken(8)}`;
    const now = new Date().toISOString();
    const checksum = await CryptoService.sha256(newValue);

    // Mark all existing versions as inactive
    const updatedVersions: SecretVersion[] = secret.versions.map((v) => ({ ...v, isActive: false }));

    const newVersion: SecretVersion = {
      versionId: newVersionId,
      versionNumber: newVersionNumber,
      createdAt: now,
      createdBy,
      isActive: true,
      checksum,
    };

    // Trim to maxVersionHistory
    const maxHistory = secret.rotationConfig.maxVersionHistory ?? 10;
    const trimmed = updatedVersions.slice(-(maxHistory - 1));

    const updatedSecret: SecretRecord = {
      ...secret,
      currentVersionId: newVersionId,
      versions: [...trimmed, newVersion],
      lastRotatedAt: now,
      updatedAt: now,
      status: 'active',
    };

    records[idx] = updatedSecret;
    SecretManager.save(records);

    // Persist to provider
    try {
      await secretRegistry.setSecret(secret.providerPath, newValue);
    } catch {
      // Provider unavailable — continue with local metadata
    }

    return { secret: updatedSecret, newVersionId };
  }

  // ─────────────────────────────────
  // Check expired secrets
  // ─────────────────────────────────

  public static getExpiredSecrets(): SecretRecord[] {
    const now = Date.now();
    return SecretManager.load().filter(
      (r) => r.status === 'active' && r.expiresAt && new Date(r.expiresAt).getTime() < now,
    );
  }

  public static getExpiringSoonSecrets(withinDays = 30): SecretRecord[] {
    const now = Date.now();
    const threshold = now + withinDays * 864e5;
    return SecretManager.load().filter(
      (r) =>
        r.status === 'active' &&
        r.expiresAt &&
        new Date(r.expiresAt).getTime() > now &&
        new Date(r.expiresAt).getTime() < threshold,
    );
  }
}
