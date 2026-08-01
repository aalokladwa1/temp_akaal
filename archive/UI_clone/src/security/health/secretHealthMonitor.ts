/**
 * AKAAL Secret Health Monitor
 * Stage 7.3
 *
 * Aggregates provider connectivity, key expiration, certificate validity,
 * and trust posture into a single health dashboard model.
 */

import { SecretProviderHealth } from '../secrets/secretTypes';
import { secretRegistry } from '../secrets/secretProviderFactory';
import { CertMonitor } from '../certificates/certMonitor';
import { KeyManagementService } from '../keys/keyManagementService';
import { SecretRotationEngine } from '../secrets/secretRotationEngine';
import { TrustStoreManager } from '../trust/trustStoreManager';

export interface AggregateHealthReport {
  overallStatus: 'healthy' | 'degraded' | 'critical';
  providers: SecretProviderHealth[];
  certificates: {
    total: number;
    expiringSoon: number;
    expired: number;
  };
  keys: {
    total: number;
    active: number;
    revoked: number;
    expired: number;
  };
  rotations: {
    totalRecorded: number;
    recentFailures: number;
  };
  trust: {
    anchorsCount: number;
    pinsCount: number;
  };
  generatedAt: string;
}

export class SecretHealthMonitor {
  public static async getAggregateHealth(): Promise<AggregateHealthReport> {
    const providers = await secretRegistry.checkAllHealth();
    const certReport = CertMonitor.generateReport();
    const keys = KeyManagementService.list();
    const rotationHistory = SecretRotationEngine.getHistory();
    const trustReport = TrustStoreManager.generateReport();

    const now = Date.now();
    const keysExpired = keys.filter((k) => k.expiresAt && new Date(k.expiresAt).getTime() <= now).length;
    const keysRevoked = keys.filter((k) => k.status === 'revoked').length;
    const keysActive = keys.filter((k) => k.status === 'active').length;

    const recentFailures = rotationHistory.filter((r) => r.status === 'failed').length;

    const hasProviderFailures = providers.some((p) => p.status === 'unreachable' || p.status === 'unauthenticated');
    const hasCertExpired = certReport.expired > 0;
    const hasKeyExpired = keysExpired > 0;

    let overallStatus: AggregateHealthReport['overallStatus'] = 'healthy';
    if (hasProviderFailures || hasCertExpired || hasKeyExpired) {
      overallStatus = 'critical';
    } else if (certReport.expiringSoon > 0 || recentFailures > 0) {
      overallStatus = 'degraded';
    }

    return {
      overallStatus,
      providers,
      certificates: {
        total: certReport.totalCerts,
        expiringSoon: certReport.expiringSoon,
        expired: certReport.expired,
      },
      keys: {
        total: keys.length,
        active: keysActive,
        revoked: keysRevoked,
        expired: keysExpired,
      },
      rotations: {
        totalRecorded: rotationHistory.length,
        recentFailures,
      },
      trust: {
        anchorsCount: trustReport.trustAnchors,
        pinsCount: trustReport.pinnedHosts,
      },
      generatedAt: new Date().toISOString(),
    };
  }
}
