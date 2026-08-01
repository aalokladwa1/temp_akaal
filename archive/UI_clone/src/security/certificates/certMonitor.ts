/**
 * AKAAL Certificate Monitor
 * Stage 7.3
 *
 * Real-time monitoring & reporting for certificate expiration & health.
 */

import { CertMonitorReport, CertRecord } from './certTypes';
import { CertificateManager } from './certificateManager';

export class CertMonitor {
  public static generateReport(): CertMonitorReport {
    const certs = CertificateManager.list();
    const now = new Date().toISOString();

    let valid = 0;
    let expiringSoon = 0;
    let expired = 0;
    let revoked = 0;
    let pendingRenewal = 0;
    let invalid = 0;

    const expiringWithin30Days: CertRecord[] = [];
    const expiringWithin7Days: CertRecord[] = [];
    const alreadyExpired: CertRecord[] = [];

    for (const cert of certs) {
      switch (cert.status) {
        case 'valid':
          valid++;
          break;
        case 'expiring_soon':
          expiringSoon++;
          break;
        case 'expired':
          expired++;
          break;
        case 'revoked':
          revoked++;
          break;
        case 'pending_renewal':
          pendingRenewal++;
          break;
        case 'invalid':
          invalid++;
          break;
      }

      if (cert.status !== 'revoked') {
        if (cert.daysUntilExpiry <= 0) {
          alreadyExpired.push(cert);
        } else if (cert.daysUntilExpiry <= 7) {
          expiringWithin7Days.push(cert);
          expiringWithin30Days.push(cert);
        } else if (cert.daysUntilExpiry <= 30) {
          expiringWithin30Days.push(cert);
        }
      }
    }

    return {
      totalCerts: certs.length,
      valid,
      expiringSoon,
      expired,
      revoked,
      pendingRenewal,
      invalid,
      expiringWithin30Days,
      expiringWithin7Days,
      alreadyExpired,
      generatedAt: now,
    };
  }
}
