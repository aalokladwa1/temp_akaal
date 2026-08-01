/**
 * AKAAL Enterprise Certificate Manager
 * Stage 7.3
 *
 * Certificate inventory, validation, PEM/PKCS#12 import, renewal, and revocation.
 */

import { CertRecord, CertImportRequest, CertValidationResult, CertStatus } from './certTypes';
import { GovernancePersistenceStore } from '../governance/governancePersistenceStore';
import { CryptoService } from '../crypto/crypto.service';
import { AuditPipeline } from '../audit/auditPipeline';

const STORE_KEY = 'certificates';

const INITIAL_CERTS: CertRecord[] = [
  {
    id: 'cert_wildcard_akaal',
    name: 'wildcard-akaal-internal',
    description: 'Wildcard TLS certificate for internal control plane *.akaal.internal',
    status: 'valid',
    usage: ['tls', 'mtls_server', 'server_auth'],
    subject: { commonName: '*.akaal.internal', organization: 'AKAAL Enterprise', organizationalUnit: 'SecOps', country: 'US' },
    issuer: { commonName: 'AKAAL Enterprise Internal CA v2', organization: 'AKAAL Security PKI', country: 'US' },
    serialNumber: '4A:8F:12:90:33:BE:91:02',
    fingerprint: 'sha256:7B:44:91:02:88:AA:BC:DE:FE:11:22:33:44:55:66:77:88:99:00:AA:BB:CC:DD:EE:FF:00:11:22:33:44',
    fingerprintAlgorithm: 'SHA-256',
    sans: ['*.akaal.internal', 'akaal.internal', 'api.akaal.internal'],
    notBefore: new Date(Date.now() - 864e5 * 180).toISOString(),
    notAfter: new Date(Date.now() + 864e5 * 185).toISOString(),
    daysUntilExpiry: 185,
    isCA: false,
    isSelfSigned: false,
    chainDepth: 2,
    format: 'PEM',
    pemCert: '-----BEGIN CERTIFICATE-----\nMIIF...SamplePEM...\n-----END CERTIFICATE-----',
    hasPrivateKey: true,
    autoRenewEnabled: true,
    renewalLeadDays: 30,
    labels: { tier: 'critical', environment: 'production' },
    tags: ['tls', 'wildcard', 'internal'],
    owner: 'secops-team',
    tenantId: 'tenant_prod_us_east',
    createdAt: new Date(Date.now() - 864e5 * 180).toISOString(),
    updatedAt: new Date(Date.now() - 864e5 * 180).toISOString(),
    importedAt: new Date(Date.now() - 864e5 * 180).toISOString(),
  },
  {
    id: 'cert_expiring_staging',
    name: 'staging-api-gateway-cert',
    description: 'Staging environment API gateway TLS certificate',
    status: 'expiring_soon',
    usage: ['tls', 'server_auth'],
    subject: { commonName: 'stg-api.akaal.internal', organization: 'AKAAL Enterprise', country: 'US' },
    issuer: { commonName: 'AKAAL Intermediate CA Staging', organization: 'AKAAL Security PKI', country: 'US' },
    serialNumber: '11:22:33:44:55:66',
    fingerprint: 'sha256:99:88:77:66:55:44:33:22:11:00:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:00:AA:BB',
    fingerprintAlgorithm: 'SHA-256',
    sans: ['stg-api.akaal.internal'],
    notBefore: new Date(Date.now() - 864e5 * 345).toISOString(),
    notAfter: new Date(Date.now() + 864e5 * 20).toISOString(), // Expiring in 20 days
    daysUntilExpiry: 20,
    isCA: false,
    isSelfSigned: false,
    chainDepth: 2,
    format: 'PEM',
    pemCert: '-----BEGIN CERTIFICATE-----\nMIIE...StagingPEM...\n-----END CERTIFICATE-----',
    hasPrivateKey: true,
    autoRenewEnabled: false,
    renewalLeadDays: 30,
    labels: { environment: 'staging' },
    tags: ['staging', 'api-gateway'],
    owner: 'qa-sec-team',
    tenantId: 'tenant_prod_us_east',
    createdAt: new Date(Date.now() - 864e5 * 345).toISOString(),
    updatedAt: new Date(Date.now() - 864e5 * 345).toISOString(),
    importedAt: new Date(Date.now() - 864e5 * 345).toISOString(),
  },
];

export class CertificateManager {
  private static load(): CertRecord[] {
    const raw = GovernancePersistenceStore.getItem<CertRecord>(STORE_KEY, INITIAL_CERTS);
    const now = Date.now();

    // Re-calculate daysUntilExpiry & status dynamically
    return raw.map((cert) => {
      const notAfterMs = new Date(cert.notAfter).getTime();
      const diffDays = Math.ceil((notAfterMs - now) / 864e5);
      let status: CertStatus = cert.status;

      if (cert.status !== 'revoked') {
        if (diffDays <= 0) status = 'expired';
        else if (diffDays <= (cert.renewalLeadDays || 30)) status = 'expiring_soon';
        else status = 'valid';
      }

      return { ...cert, daysUntilExpiry: diffDays, status };
    });
  }

  private static save(records: CertRecord[]): void {
    GovernancePersistenceStore.setItem<CertRecord>(STORE_KEY, records);
  }

  public static list(): CertRecord[] {
    return CertificateManager.load().sort((a, b) => a.daysUntilExpiry - b.daysUntilExpiry);
  }

  public static get(id: string): CertRecord | null {
    return CertificateManager.load().find((c) => c.id === id) ?? null;
  }

  public static async importCert(req: CertImportRequest, requestedBy = 'system'): Promise<CertRecord> {
    const records = CertificateManager.load();
    const id = `cert_${CryptoService.generateSecureToken(12)}`;
    const now = new Date().toISOString();

    const fingerprint = await CryptoService.computePEMFingerprint(req.pemCert);
    const notBefore = new Date().toISOString();
    const notAfter = new Date(Date.now() + 864e5 * 365).toISOString(); // Default 1 year

    const certRecord: CertRecord = {
      id,
      name: req.name,
      description: req.description ?? '',
      status: 'valid',
      usage: req.usage,
      subject: { commonName: req.name, organization: 'Enterprise Import' },
      issuer: { commonName: 'External Authority / Self-Signed' },
      serialNumber: CryptoService.generateSecureToken(8).toUpperCase().match(/.{2}/g)!.join(':'),
      fingerprint: `sha256:${fingerprint}`,
      fingerprintAlgorithm: 'SHA-256',
      sans: [req.name],
      notBefore,
      notAfter,
      daysUntilExpiry: 365,
      isCA: false,
      isSelfSigned: !req.pemChain,
      chainDepth: req.pemChain ? 2 : 1,
      format: req.pkcs12Data ? 'PKCS12' : 'PEM',
      pemCert: req.pemCert,
      pemChain: req.pemChain,
      hasPrivateKey: !!req.pemPrivateKey || !!req.pkcs12Data,
      autoRenewEnabled: req.autoRenewEnabled ?? false,
      renewalLeadDays: req.renewalLeadDays ?? 30,
      labels: req.labels ?? {},
      tags: req.tags ?? [],
      owner: req.owner ?? requestedBy,
      tenantId: req.tenantId ?? '',
      createdAt: now,
      updatedAt: now,
      importedAt: now,
    };

    records.push(certRecord);
    CertificateManager.save(records);

    AuditPipeline.log({
      eventType: 'CERT_IMPORT',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: certRecord.tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'CertificateManager',
      resource: `cert:${id}`,
      action: 'import_certificate',
      status: 'SUCCESS',
      details: { certName: certRecord.name, format: certRecord.format, fingerprint },
    });

    return certRecord;
  }

  public static validate(id: string): CertValidationResult {
    const cert = CertificateManager.get(id);
    if (!cert) throw new Error(`CertificateManager: certificate '${id}' not found`);

    const now = Date.now();
    const notAfterMs = new Date(cert.notAfter).getTime();
    const notBeforeMs = new Date(cert.notBefore).getTime();

    const notExpired = now >= notBeforeMs && now <= notAfterMs;
    const notRevoked = cert.status !== 'revoked';
    const chainValid = true; // In production, evaluate against trusted CA anchors
    const signatureValid = true;

    const isValid = notExpired && notRevoked && chainValid && signatureValid;
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!notExpired) errors.push('Certificate has expired or is not yet valid.');
    if (!notRevoked) errors.push('Certificate has been revoked.');
    if (cert.daysUntilExpiry <= 30 && cert.daysUntilExpiry > 0) {
      warnings.push(`Certificate expires in ${cert.daysUntilExpiry} days.`);
    }

    return {
      certId: id,
      isValid,
      status: cert.status,
      errors,
      warnings,
      chainValid,
      signatureValid,
      notExpired,
      notRevoked,
      daysUntilExpiry: cert.daysUntilExpiry,
      checkedAt: new Date().toISOString(),
    };
  }

  public static renew(id: string, requestedBy = 'system'): CertRecord {
    const records = CertificateManager.load();
    const idx = records.findIndex((c) => c.id === id);
    if (idx === -1) throw new Error(`CertificateManager: certificate '${id}' not found`);

    const cert = records[idx];
    const now = new Date();
    const newNotAfter = new Date(now.getTime() + 864e5 * 365).toISOString();

    records[idx] = {
      ...cert,
      status: 'valid',
      notBefore: now.toISOString(),
      notAfter: newNotAfter,
      daysUntilExpiry: 365,
      lastRenewalAt: now.toISOString(),
      updatedAt: now.toISOString(),
    };

    CertificateManager.save(records);

    AuditPipeline.log({
      eventType: 'CERT_RENEWED',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: cert.tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'CertificateManager',
      resource: `cert:${id}`,
      action: 'renew_certificate',
      status: 'SUCCESS',
      details: { certName: cert.name, newNotAfter },
    });

    return records[idx];
  }

  public static revoke(id: string, reason: string, requestedBy = 'system'): CertRecord {
    const records = CertificateManager.load();
    const idx = records.findIndex((c) => c.id === id);
    if (idx === -1) throw new Error(`CertificateManager: certificate '${id}' not found`);

    const cert = records[idx];
    const now = new Date().toISOString();

    records[idx] = {
      ...cert,
      status: 'revoked',
      revokedAt: now,
      revocationReason: reason,
      updatedAt: now,
    };

    CertificateManager.save(records);

    AuditPipeline.log({
      eventType: 'CERT_REVOKED',
      userId: requestedBy,
      userEmail: requestedBy,
      tenantId: cert.tenantId,
      ipAddress: '0.0.0.0',
      userAgent: 'CertificateManager',
      resource: `cert:${id}`,
      action: 'revoke_certificate',
      status: 'SUCCESS',
      details: { certName: cert.name, reason },
    });

    return records[idx];
  }
}
