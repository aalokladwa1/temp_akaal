/**
 * AKAAL Trust Store Manager
 * Stage 7.3
 *
 * Manages trusted CA anchors and public key certificate pinning policies.
 */

import { TrustAnchor, CertPin, TrustReport, TrustValidationResult } from './trustTypes';
import { GovernancePersistenceStore } from '../governance/governancePersistenceStore';

const ANCHORS_KEY = 'trust_anchors';
const PINS_KEY = 'cert_pins';

const INITIAL_ANCHORS: TrustAnchor[] = [
  {
    id: 'anchor_akaal_root_ca',
    name: 'AKAAL Global Root CA v1',
    description: 'Internal Enterprise Root Certificate Authority',
    certId: 'cert_wildcard_akaal',
    subjectDN: 'CN=AKAAL Root CA v1, O=AKAAL Enterprise, C=US',
    fingerprint: 'sha256:88:77:66:55:44:33:22:11:00:AA:BB:CC:DD:EE:FF',
    isRootCA: true,
    isIntermediate: false,
    enabled: true,
    addedAt: new Date(Date.now() - 864e5 * 365).toISOString(),
    expiresAt: new Date(Date.now() + 864e5 * 3650).toISOString(),
    trustedForPurposes: ['server_auth', 'client_auth', 'tls', 'mtls'],
  },
];

const INITIAL_PINS: CertPin[] = [
  {
    id: 'pin_control_plane',
    hostname: 'controlplane.akaal.internal',
    subjectPublicKeyInfoHash: 'pin-sha256="47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="',
    backupPins: ['pin-sha256="YLh1d67h6/gOw6FuE85A6+M7kP3151nKL6nNjyvV264="'],
    includeSubdomains: true,
    maxAgeSeconds: 5184000, // 60 days
    enabled: true,
    createdAt: new Date().toISOString(),
  },
];

export class TrustStoreManager {
  public static listAnchors(): TrustAnchor[] {
    return GovernancePersistenceStore.getItem<TrustAnchor>(ANCHORS_KEY, INITIAL_ANCHORS);
  }

  public static listPins(): CertPin[] {
    return GovernancePersistenceStore.getItem<CertPin>(PINS_KEY, INITIAL_PINS);
  }

  public static addAnchor(anchor: Omit<TrustAnchor, 'id' | 'addedAt'>): TrustAnchor {
    const anchors = TrustStoreManager.listAnchors();
    const newAnchor: TrustAnchor = {
      ...anchor,
      id: `anchor_${Date.now()}`,
      addedAt: new Date().toISOString(),
    };
    anchors.push(newAnchor);
    GovernancePersistenceStore.setItem(ANCHORS_KEY, anchors);
    return newAnchor;
  }

  public static addPin(pin: Omit<CertPin, 'id' | 'createdAt'>): CertPin {
    const pins = TrustStoreManager.listPins();
    const newPin: CertPin = {
      ...pin,
      id: `pin_${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    pins.push(newPin);
    GovernancePersistenceStore.setItem(PINS_KEY, pins);
    return newPin;
  }

  public static validateTrust(hostname: string): TrustValidationResult {
    const anchors = TrustStoreManager.listAnchors().filter((a) => a.enabled);
    const pins = TrustStoreManager.listPins().filter((p) => p.enabled && p.hostname === hostname);

    const isValid = anchors.length > 0;
    const errors: string[] = [];
    const warnings: string[] = [];

    if (anchors.length === 0) {
      errors.push('No active trusted CA anchors configured.');
    }

    if (pins.length > 0) {
      warnings.push(`Hostname ${hostname} enforces certificate pinning.`);
    }

    return {
      isValid,
      chain: ['CN=AKAAL Root CA v1'],
      anchorsUsed: anchors.map((a) => a.name),
      errors,
      warnings,
      validatedAt: new Date().toISOString(),
    };
  }

  public static generateReport(): TrustReport {
    const anchors = TrustStoreManager.listAnchors();
    const pins = TrustStoreManager.listPins();
    const now = Date.now();

    const expiredAnchors = anchors.filter((a) => new Date(a.expiresAt).getTime() <= now).length;
    const expiringAnchors = anchors.filter(
      (a) =>
        new Date(a.expiresAt).getTime() > now &&
        new Date(a.expiresAt).getTime() <= now + 30 * 864e5,
    ).length;

    return {
      tlsConfigs: 1,
      mtlsEnabled: true,
      trustAnchors: anchors.length,
      pinnedHosts: pins.length,
      expiredAnchors,
      expiringAnchors,
      generatedAt: new Date().toISOString(),
    };
  }
}
