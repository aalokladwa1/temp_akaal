/**
 * AKAAL Enterprise Secret Rotation Engine
 * Stage 7.3
 *
 * Manual, scheduled, automatic, and emergency rotation.
 * Grace period / dual-active versioning for zero-downtime rotation.
 * Full audit trail integration.
 */

import { SecretRotationRecord, RotationTrigger } from './secretTypes';
import { SecretManager } from './secretManager';
import { GovernancePersistenceStore } from '../governance/governancePersistenceStore';
import { AuditPipeline } from '../audit/auditPipeline';
import { CryptoService } from '../crypto/crypto.service';

const ROTATION_LOG_KEY = 'rotation_history';

const INITIAL_ROTATION_HISTORY: SecretRotationRecord[] = [
  {
    id: 'rot_001',
    secretId: 'sec_jwt_signing_01',
    secretName: 'jwt-signing-key-prod',
    trigger: 'scheduled',
    status: 'success',
    fromVersionId: 'ver_jwt_v1',
    toVersionId: 'ver_jwt_v2',
    initiatedBy: 'system-scheduler',
    initiatedAt: new Date(Date.now() - 864e5 * 30).toISOString(),
    completedAt: new Date(Date.now() - 864e5 * 30 + 3000).toISOString(),
    isEmergency: false,
    gracePeriodEndsAt: new Date(Date.now() - 864e5 * 29).toISOString(),
    notificationsSent: true,
  },
];

export class SecretRotationEngine {
  // ─────────────────────────────────
  // Rotation History
  // ─────────────────────────────────

  private static loadHistory(): SecretRotationRecord[] {
    return GovernancePersistenceStore.getItem<SecretRotationRecord>(ROTATION_LOG_KEY, INITIAL_ROTATION_HISTORY);
  }

  private static saveHistory(records: SecretRotationRecord[]): void {
    GovernancePersistenceStore.setItem<SecretRotationRecord>(ROTATION_LOG_KEY, records);
  }

  public static getHistory(secretId?: string): SecretRotationRecord[] {
    const history = SecretRotationEngine.loadHistory();
    const filtered = secretId ? history.filter((r) => r.secretId === secretId) : history;
    return filtered.sort((a, b) => b.initiatedAt.localeCompare(a.initiatedAt));
  }

  // ─────────────────────────────────
  // Core Rotation
  // ─────────────────────────────────

  /**
   * Performs a manual secret rotation.
   * Generates a new cryptographically secure value and creates a new version.
   */
  public static async rotateManual(
    secretId: string,
    newValue: string,
    requestedBy = 'system',
  ): Promise<SecretRotationRecord> {
    return SecretRotationEngine.executeRotation(secretId, 'manual', newValue, requestedBy, false);
  }

  /**
   * Emergency rotation — bypasses grace period.
   * Immediately activates the new version and marks the previous as deprecated.
   */
  public static async rotateEmergency(
    secretId: string,
    newValue: string,
    requestedBy = 'system',
  ): Promise<SecretRotationRecord> {
    return SecretRotationEngine.executeRotation(secretId, 'emergency', newValue, requestedBy, true);
  }

  /**
   * Scheduled/automatic rotation — called by the scheduler.
   */
  public static async rotateScheduled(
    secretId: string,
    requestedBy = 'system-scheduler',
  ): Promise<SecretRotationRecord> {
    // Generate a new secure random value for the secret
    const newValue = CryptoService.generateSecureToken(64);
    return SecretRotationEngine.executeRotation(secretId, 'scheduled', newValue, requestedBy, false);
  }

  /**
   * Core rotation logic.
   */
  private static async executeRotation(
    secretId: string,
    trigger: RotationTrigger,
    newValue: string,
    requestedBy: string,
    isEmergency: boolean,
  ): Promise<SecretRotationRecord> {
    const secret = SecretManager.get(secretId);
    if (!secret) throw new Error(`RotationEngine: secret '${secretId}' not found`);

    const fromVersionId = secret.currentVersionId;
    const now = new Date().toISOString();
    const rotationId = `rot_${CryptoService.generateSecureToken(10)}`;

    const rotationRecord: SecretRotationRecord = {
      id: rotationId,
      secretId,
      secretName: secret.name,
      trigger,
      status: 'in_progress',
      fromVersionId,
      initiatedBy: requestedBy,
      initiatedAt: now,
      isEmergency,
      notificationsSent: false,
    };

    const history = SecretRotationEngine.loadHistory();
    history.push(rotationRecord);
    SecretRotationEngine.saveHistory(history);

    try {
      const { newVersionId } = await SecretManager.addVersion(secretId, newValue, requestedBy);

      const gracePeriodHours = isEmergency ? 0 : (secret.rotationConfig.gracePeriodHours ?? 24);
      const gracePeriodEndsAt = gracePeriodHours > 0
        ? new Date(Date.now() + gracePeriodHours * 3600_000).toISOString()
        : undefined;

      // Update rotation record to success
      const idx = history.findIndex((r) => r.id === rotationId);
      const completed: SecretRotationRecord = {
        ...history[idx],
        status: 'success',
        toVersionId: newVersionId,
        completedAt: new Date().toISOString(),
        gracePeriodEndsAt,
        notificationsSent: false, // Will be updated when notifications are sent
      };
      history[idx] = completed;
      SecretRotationEngine.saveHistory(history);

      // Send notifications (best-effort)
      SecretRotationEngine.sendNotifications(completed, secret.rotationConfig.notificationWebhook).catch(() => {
        // Non-blocking — notification failure should not fail rotation
      });

      AuditPipeline.log({
        eventType: 'SECRET_ROTATION',
        userId: requestedBy,
        userEmail: requestedBy,
        tenantId: secret.tenantId,
        ipAddress: '0.0.0.0',
        userAgent: 'SecretRotationEngine',
        resource: `secret:${secretId}`,
        action: `rotate_${trigger}`,
        status: 'SUCCESS',
        details: {
          secretName: secret.name,
          trigger,
          isEmergency,
          fromVersionId,
          toVersionId: newVersionId,
          gracePeriodEndsAt,
        },
      });

      return completed;
    } catch (err: unknown) {
      const idx = history.findIndex((r) => r.id === rotationId);
      const failed: SecretRotationRecord = {
        ...history[idx],
        status: 'failed',
        failureReason: err instanceof Error ? err.message : String(err),
        completedAt: new Date().toISOString(),
      };
      history[idx] = failed;
      SecretRotationEngine.saveHistory(history);

      AuditPipeline.log({
        eventType: 'SECRET_ROTATION',
        userId: requestedBy,
        userEmail: requestedBy,
        tenantId: secret.tenantId,
        ipAddress: '0.0.0.0',
        userAgent: 'SecretRotationEngine',
        resource: `secret:${secretId}`,
        action: `rotate_${trigger}_failed`,
        status: 'FAILURE',
        details: { secretName: secret.name, trigger, error: failed.failureReason },
      });

      throw err;
    }
  }

  // ─────────────────────────────────
  // Rollback
  // ─────────────────────────────────

  /**
   * Rolls back a secret to the previous version.
   * The old value is marked active again; the current (failed) version is deprecated.
   */
  public static async rollback(secretId: string, targetVersionId: string, requestedBy = 'system'): Promise<SecretRotationRecord> {
    const secret = SecretManager.get(secretId);
    if (!secret) throw new Error(`RotationEngine: secret '${secretId}' not found`);

    const targetVersion = secret.versions.find((v) => v.versionId === targetVersionId);
    if (!targetVersion) throw new Error(`RotationEngine: version '${targetVersionId}' not found`);

    const fromVersionId = secret.currentVersionId;
    const rotationId = `rot_rollback_${CryptoService.generateSecureToken(8)}`;
    const now = new Date().toISOString();

    // Create rollback rotation record
    const rotationRecord: SecretRotationRecord = {
      id: rotationId,
      secretId,
      secretName: secret.name,
      trigger: 'manual',
      status: 'in_progress',
      fromVersionId,
      toVersionId: targetVersionId,
      initiatedBy: requestedBy,
      initiatedAt: now,
      isEmergency: false,
      notificationsSent: false,
    };

    const history = SecretRotationEngine.loadHistory();
    history.push(rotationRecord);
    SecretRotationEngine.saveHistory(history);

    try {
      // Mark the target version as active, all others inactive
      const allVersions = SecretManager.getVersions(secretId);
      const updatedVersions = allVersions.map((v) => ({
        ...v,
        isActive: v.versionId === targetVersionId,
      }));

      // Directly mutate via SecretManager internals (addVersion would create a new version)
      // We update the stored record
      const GovernancePersistenceStore = (await import('../governance/governancePersistenceStore')).GovernancePersistenceStore;
      const records = GovernancePersistenceStore.getItem<import('./secretTypes').SecretRecord>('secrets', []);
      const idx = records.findIndex((r: import('./secretTypes').SecretRecord) => r.id === secretId);
      if (idx !== -1) {
        records[idx] = {
          ...records[idx],
          currentVersionId: targetVersionId,
          versions: updatedVersions,
          updatedAt: now,
          lastRotatedAt: now,
        };
        GovernancePersistenceStore.setItem('secrets', records);
      }

      const idx2 = history.findIndex((r) => r.id === rotationId);
      history[idx2] = { ...history[idx2], status: 'rolled_back', completedAt: new Date().toISOString() };
      SecretRotationEngine.saveHistory(history);

      AuditPipeline.log({
        eventType: 'SECRET_ROTATION',
        userId: requestedBy,
        userEmail: requestedBy,
        tenantId: secret.tenantId,
        ipAddress: '0.0.0.0',
        userAgent: 'SecretRotationEngine',
        resource: `secret:${secretId}`,
        action: 'rollback',
        status: 'SUCCESS',
        details: { secretName: secret.name, fromVersionId, toVersionId: targetVersionId },
      });

      return history[idx2];
    } catch (err: unknown) {
      const idx = history.findIndex((r) => r.id === rotationId);
      history[idx] = {
        ...history[idx],
        status: 'failed',
        failureReason: err instanceof Error ? err.message : String(err),
        completedAt: new Date().toISOString(),
      };
      SecretRotationEngine.saveHistory(history);
      throw err;
    }
  }

  // ─────────────────────────────────
  // Notifications (non-blocking)
  // ─────────────────────────────────

  private static async sendNotifications(
    rotationRecord: SecretRotationRecord,
    webhookUrl?: string,
  ): Promise<void> {
    if (!webhookUrl) return;

    try {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: 'secret.rotated',
          secretId: rotationRecord.secretId,
          secretName: rotationRecord.secretName,
          trigger: rotationRecord.trigger,
          newVersionId: rotationRecord.toVersionId,
          rotatedAt: rotationRecord.completedAt,
          isEmergency: rotationRecord.isEmergency,
        }),
        signal: AbortSignal.timeout(5000),
      });
    } catch {
      // Notification failure is non-fatal
    }
  }

  // ─────────────────────────────────
  // Secrets Due for Rotation
  // ─────────────────────────────────

  public static getDueForRotation(): import('./secretTypes').SecretRecord[] {
    const now = Date.now();
    return SecretManager.list({ status: 'active' }).filter(
      (s) =>
        s.rotationConfig.enabled &&
        s.nextRotationAt &&
        new Date(s.nextRotationAt).getTime() <= now,
    );
  }
}
