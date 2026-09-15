/**
 * AKAAL Administration — 5.4 Identity & Security and 5.5 Template & Configuration Library Unit Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { IdentityService } from './services/identity.service';
import { TemplatesConfigService } from './services/templates-config.service';

describe('5.4 Identity & Security Service & Workflows', () => {
  let identityService: IdentityService;

  beforeEach(() => {
    identityService = new IdentityService();
  });

  it('should initialize with baseline authentication policies and zero-trust MFA parameters', () => {
    expect(identityService.authPolicies().length).toBeGreaterThanOrEqual(2);
    expect(identityService.mfaConfig().totalEnrolledUsers).toBeGreaterThan(0);
    expect(identityService.mfaConfig().enforceFido2WebAuthn).toBe(true);
  });

  it('should create and register a new custom authentication policy', () => {
    const policy = identityService.createAuthPolicy({
      name: 'Ultra Strict Sovereign Cloud Policy',
      tier: 'CRITICAL_GOV',
      minPasswordLength: 24,
      mfaEnforcement: 'ENFORCED_ALL',
      lockoutThresholdAttempts: 3,
      sessionIdleTimeoutMinutes: 10
    });

    expect(policy.id).toBeDefined();
    expect(policy.minPasswordLength).toBe(24);
    expect(identityService.authPolicies().find(p => p.id === policy.id)).toBeDefined();
  });

  it('should update global MFA configuration thresholds', () => {
    identityService.updateMfaConfig({
      rememberDeviceDays: 7,
      allowSmsOtpWithWarning: false,
      fido2AdoptionRatePercent: 95.0
    });

    const updated = identityService.mfaConfig();
    expect(updated.rememberDeviceDays).toBe(7);
    expect(updated.allowSmsOtpWithWarning).toBe(false);
    expect(updated.fido2AdoptionRatePercent).toBe(95.0);
  });

  it('should create, configure, and register an enterprise SSO provider', () => {
    const provider = identityService.createSsoProvider({
      name: 'Ping Identity Corporate OIDC',
      protocol: 'OIDC',
      providerType: 'PING_IDENTITY',
      entityIdOrIssuer: 'https://auth.pingone.com/akaal-corp',
      singleSignOnUrl: 'https://auth.pingone.com/akaal-corp/as/authorize',
      clientId: 'ping-client-9912',
      jitProvisioningEnabled: true
    });

    expect(provider.id).toBeDefined();
    expect(identityService.ssoProviders().find(p => p.id === provider.id)).toBeDefined();
  });

  it('should trigger LDAP directory synchronization and update timestamp', () => {
    const ldapId = identityService.ldapConfigs()[0].id;
    identityService.triggerLdapSync(ldapId);

    const ldap = identityService.ldapConfigs().find(l => l.id === ldapId);
    expect(ldap?.status).toBe('CONNECTED');
    expect(ldap?.lastSyncTimestamp).toBe('Just now');
  });

  it('should trigger automated secret rotation and update audit state', () => {
    const ruleId = identityService.rotationRules()[0].id;
    identityService.triggerSecretRotation(ruleId);

    const rule = identityService.rotationRules().find(r => r.id === ruleId);
    expect(rule?.lastRotationStatus).toBe('SUCCESS');
    expect(rule?.lastRotationTimestamp).toBe('Just now');
  });

  it('should maintain inventory of X.509 PKI certificates and KMS master keys', () => {
    expect(identityService.certificates().length).toBeGreaterThanOrEqual(2);
    expect(identityService.kmsKeys().length).toBeGreaterThanOrEqual(2);
    expect(identityService.vaultEngines().length).toBeGreaterThanOrEqual(2);
    expect(identityService.workloadIdentities().length).toBeGreaterThanOrEqual(2);
  });
});

describe('5.5 Template & Configuration Library Service & Workflows', () => {
  let libraryService: TemplatesConfigService;

  beforeEach(() => {
    libraryService = new TemplatesConfigService();
  });

  it('should initialize with six distinct asset families and compute summary metrics', () => {
    const summaries = libraryService.familySummaries();
    expect(summaries.length).toBe(6);
    expect(summaries.map(s => s.family)).toEqual(
      expect.arrayContaining([
        'MIGRATION_TEMPLATE',
        'MAPPING_TEMPLATE',
        'TRANSFORMATION_TEMPLATE',
        'PRIVACY_POLICY',
        'DATA_QUALITY_POLICY',
        'CONFIGURATION_PROFILE'
      ])
    );
  });

  it('should retrieve assets filtered by family', () => {
    const migrationAssets = libraryService.getAssetsByFamily('MIGRATION_TEMPLATE');
    expect(migrationAssets.length).toBeGreaterThanOrEqual(1);
    expect(migrationAssets.every(a => a.family === 'MIGRATION_TEMPLATE')).toBe(true);
  });

  it('should create a new template asset with initial version 1.0.0', () => {
    const asset = libraryService.createAsset({
      name: 'Custom Clickhouse Ingestion Blueprint',
      family: 'MIGRATION_TEMPLATE',
      category: 'Real-time Analytics',
      description: 'Streamed high-volume batch conversion to Clickhouse MergeTree engine.',
      specPayload: '{"engine": "CLICKHOUSE_MERGETREE"}'
    });

    expect(asset.id).toBeDefined();
    expect(asset.currentVersion).toBe('1.0.0');
    expect(asset.versions.length).toBe(1);
    expect(libraryService.getAssetById(asset.id)).toBeDefined();
  });

  it('should promote an asset across lifecycle tiers (Development -> Staging -> Production)', () => {
    const asset = libraryService.createAsset({
      name: 'Staging Candidate Profile',
      family: 'CONFIGURATION_PROFILE',
      environmentTier: 'DEVELOPMENT'
    });

    libraryService.promoteAsset(asset.id, 'STAGING');
    expect(libraryService.getAssetById(asset.id)?.environmentTier).toBe('STAGING');

    libraryService.promoteAsset(asset.id, 'PRODUCTION');
    expect(libraryService.getAssetById(asset.id)?.environmentTier).toBe('PRODUCTION');
  });

  it('should mark an asset as deprecated with migration guidance and notice', () => {
    const asset = libraryService.assets()[0];
    libraryService.deprecateAsset(asset.id, 'Superseded by v3 modern connector pipeline architecture.');

    const deprecatedAsset = libraryService.getAssetById(asset.id);
    expect(deprecatedAsset?.status).toBe('DEPRECATED');
    expect(deprecatedAsset?.deprecationNotice?.reason).toContain('Superseded');
  });
});
