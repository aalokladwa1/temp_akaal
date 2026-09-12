/**
 * AKAAL Administration — 5.8 Compliance, 5.9 Audit, 5.10 Platform Administration, 5.11 Integrations & Notifications Unit Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { ComplianceService } from './services/compliance.service';
import { AuditService } from './services/audit.service';
import { PlatformAdminService } from './services/platform-admin.service';
import { IntegrationsService } from './services/integrations.service';

describe('5.8 Compliance Service & Governance Workflows', () => {
  let complianceService: ComplianceService;

  beforeEach(() => {
    complianceService = new ComplianceService();
  });

  it('should initialize with canonical control frameworks (GDPR, PCI-DSS, SOC 2, HIPAA, ISO 27001)', () => {
    const frameworks = complianceService.frameworks();
    expect(frameworks.length).toBeGreaterThanOrEqual(5);

    const domains = frameworks.map(f => f.regulatoryDomain);
    expect(domains).toContain('SOC_2');
    expect(domains).toContain('GDPR');
    expect(domains).toContain('PCI_DSS');
    expect(domains).toContain('HIPAA');
    expect(domains).toContain('ISO_27001');

    for (const f of frameworks) {
      expect(f.mappedControlsCount).toBeGreaterThan(0);
      expect(f.totalControls).toBeGreaterThanOrEqual(f.mappedControlsCount);
      expect(f.isBuiltIn).toBe(true);
    }
  });

  it('should retrieve framework by id and domain with technical controls', () => {
    const soc2 = complianceService.getFrameworkById('fw-soc2');
    expect(soc2).toBeDefined();
    expect(soc2?.name).toContain('SOC 2 Type II');

    const gdpr = complianceService.getFrameworkByDomain('GDPR');
    expect(gdpr).toBeDefined();
    expect(gdpr?.id).toBe('fw-gdpr');

    const controls = complianceService.getControlsForFramework('fw-soc2');
    expect(controls.length).toBeGreaterThanOrEqual(1);

    // Verify mapped technical controls exist
    for (const ctrl of controls) {
      expect(ctrl.mappedTechnicalControls.length).toBeGreaterThan(0);
      expect(['FULLY_MAPPED', 'PARTIALLY_MAPPED', 'NOT_MAPPED']).toContain(ctrl.mappingState);
    }
  });

  it('should create a custom framework and make it retrievable in customFrameworks signal', () => {
    const initialCount = complianceService.customFrameworks().length;
    complianceService.createCustomFramework({
      code: 'CORP-FIN-2026',
      name: 'Internal Financial Audit Standard 2026',
      version: '1.0.0',
      description: 'Internal policy controls for high-throughput transactional ledgers',
      authorityOwner: 'Internal Governance Board',
      controlsCount: 18
    });

    const customList = complianceService.customFrameworks();
    expect(customList.length).toBe(initialCount + 1);

    const created = customList.find(f => f.code === 'CORP-FIN-2026');
    expect(created).toBeDefined();
    expect(created?.name).toBe('Internal Financial Audit Standard 2026');
    expect(created?.status).toBe('ACTIVE');
    expect(created?.id).toContain('cfw-');
  });

  it('should create an approved compliance exception with full audit details', () => {
    const initialExceptions = complianceService.exceptions().length;
    complianceService.createException({
      code: 'EXC-2026-002',
      title: 'Legacy CDC Bridge Service Account WebAuthn Exemption',
      frameworkId: 'fw-soc2',
      controlCode: 'SOC2-CC6.1',
      reason: 'Automated batch bridge runs in isolated hardware enclave without user interaction',
      scope: 'Service Account: svc-cdc-bridge-02',
      justification: 'Enclave isolation and mutual TLS authentication provide compensating control',
      approvedBy: 'Chief Information Security Officer',
      validUntil: '2026-12-31'
    });

    const exceptions = complianceService.exceptions();
    expect(exceptions.length).toBe(initialExceptions + 1);

    const created = exceptions.find(e => e.code === 'EXC-2026-002');
    expect(created).toBeDefined();
    expect(created?.status).toBe('APPROVED');
    expect(created?.approvedBy).toBe('Chief Information Security Officer');
  });

  it('should track verifiable compliance evidence records with cryptographic SHA-256 digests', () => {
    const evidenceList = complianceService.evidence();
    expect(evidenceList.length).toBeGreaterThanOrEqual(3);

    for (const ev of evidenceList) {
      expect(ev.sha256Digest).toBeDefined();
      expect(ev.sha256Digest.length).toBe(64); // Valid SHA-256 length
      expect(ev.verificationStatus).toBe('DIGEST_VERIFIED');
    }

    const singleEv = complianceService.getEvidenceById('ev-01');
    expect(singleEv).toBeDefined();
    expect(singleEv?.evidenceType).toBe('HASH_ATTESTATION');
  });
});

describe('5.9 Audit Service & Governance Workflows', () => {
  let auditService: AuditService;

  beforeEach(() => {
    auditService = new AuditService();
  });

  it('should initialize with enterprise audit policies and destinations', () => {
    const policies = auditService.auditPolicies();
    expect(policies.length).toBeGreaterThanOrEqual(3);

    const destinations = auditService.destinations();
    expect(destinations.length).toBeGreaterThanOrEqual(2);

    // Verify all configured destinations use vault references for secrets
    for (const dest of destinations) {
      if (dest.credentialRef) {
        expect(dest.credentialRef).toMatch(/^vault:\/\//);
      }
    }
  });

  it('should create an audit policy with retention and severity filters', () => {
    const initialCount = auditService.auditPolicies().length;
    auditService.createAuditPolicy({
      name: 'Realtime Privileged Operations Policy',
      description: 'Captures all break-glass and elevated credential actions',
      retentionDays: 1095,
      category: 'ADMIN_ACTIONS',
      severityFilter: 'ALL',
      destinations: ['adest-syslog-01', 'adest-splunk-01']
    });

    const updated = auditService.auditPolicies();
    expect(updated.length).toBe(initialCount + 1);

    const created = updated.find(p => p.name === 'Realtime Privileged Operations Policy');
    expect(created).toBeDefined();
    expect(created?.id).toContain('apol-');
    expect(created?.status).toBe('ACTIVE');
  });

  it('should register an audit export destination with vault credential', () => {
    const initialCount = auditService.destinations().length;
    auditService.createDestination({
      name: 'Corporate Cold Archive S3 Ingestion',
      destinationType: 'SIEM_COLLECTOR',
      endpointUrl: 'https://s3.eu-west-1.amazonaws.com/akaal-audit-cold-archive',
      format: 'JSON_STRUCTURED',
      credentialRef: 'vault://aws/cold-archive-role',
      tlsEnforced: true
    });

    const destinations = auditService.destinations();
    expect(destinations.length).toBe(initialCount + 1);

    const created = destinations.find(d => d.name === 'Corporate Cold Archive S3 Ingestion');
    expect(created).toBeDefined();
    expect(created?.id).toContain('adest-');
    expect(created?.credentialRef).toMatch(/^vault:\/\//);
  });

  it('should impose and release legal holds on audit evidence', () => {
    const initialHolds = auditService.legalHolds().length;
    auditService.createLegalHold({
      caseId: 'CASE-2026-LIT-099',
      matterName: 'Q3 External Regulatory Discovery',
      custodian: 'Legal Compliance Office',
      scopeDescription: 'All migration pipelines and execution digests for Workspace FinCore.'
    });

    const holds = auditService.legalHolds();
    expect(holds.length).toBe(initialHolds + 1);

    const created = holds.find(h => h.caseId === 'CASE-2026-LIT-099');
    expect(created).toBeDefined();
    expect(created?.id).toContain('hold-');
    expect(created?.status).toBe('ACTIVE');

    // Release legal hold
    auditService.releaseLegalHold(created!.id, 'Case settled with regulatory signoff');
    const released = auditService.getLegalHoldById(created!.id);
    expect(released?.status).toBe('RELEASED');
    expect(released?.releaseReason).toContain('settled');
  });

  it('should verify audit chain integrity via Merkle root cryptographic hash', () => {
    const verifications = auditService.verifications();
    expect(verifications.length).toBeGreaterThanOrEqual(1);

    const vrf = verifications[0];
    expect(vrf.verificationResult).toBe('DIGEST_VERIFIED');
    expect(vrf.sha256MerkleRootDigest.length).toBe(64);
    expect(vrf.totalEntriesEvaluated).toBeGreaterThan(0);
  });

  it('should trigger an audit export request with date range and format', () => {
    const initialExports = auditService.exportRequests().length;
    auditService.triggerExport('JSON', '2026-02-01 to 2026-02-19');

    const exportsList = auditService.exportRequests();
    expect(exportsList.length).toBe(initialExports + 1);

    const latest = exportsList[0];
    expect(latest.id).toContain('exp-');
    expect(latest.status).toBe('COMPLETED');
    expect(latest.format).toBe('JSON');
  });
});

describe('5.10 Platform Administration Service & Lifecycle Workflows', () => {
  let platformService: PlatformAdminService;

  beforeEach(() => {
    platformService = new PlatformAdminService();
  });

  it('should inspect platform configuration and service topology', () => {
    const configs = platformService.platformConfigs();
    expect(configs.length).toBeGreaterThanOrEqual(4);

    const keys = configs.map(c => c.key);
    expect(keys).toContain('system.max_concurrent_worker_threads');
    expect(keys).toContain('security.tls_minimum_protocol_version');

    const nodes = platformService.serviceNodes();
    expect(nodes.length).toBeGreaterThanOrEqual(3);
    expect(nodes.some(n => n.serviceName.includes('Daemon'))).toBe(true);

    const deployment = platformService.deploymentConfig();
    expect(deployment.orchestrator).toBe('KUBERNETES');
    expect(deployment.rolloutStrategy).toBe('ROLLING');
  });

  it('should update platform runtime configurations safely', () => {
    const configItem = platformService.platformConfigs().find(c => c.key === 'system.max_concurrent_worker_threads');
    expect(configItem).toBeDefined();

    platformService.updateConfigValue(configItem!.id, '128');
    const updated = platformService.platformConfigs().find(c => c.id === configItem!.id);
    expect(updated?.value).toBe('128');

    // Revert
    platformService.updateConfigValue(configItem!.id, '64');
    const reverted = platformService.platformConfigs().find(c => c.id === configItem!.id);
    expect(reverted?.value).toBe('64');
  });

  it('should track version inventory and available patch/minor updates', () => {
    const versions = platformService.versions();
    expect(versions.appVersion).toBe('2.4.0');
    expect(versions.backendVersion).toBe('1.9.2');
    expect(versions.buildCommit).toBe('9c4f881b');

    const upgrade = platformService.upgradeInfo();
    expect(upgrade.targetVersion).toBe('2.4.1');
    expect(upgrade.severity).toBe('RECOMMENDED');
    expect(upgrade.readinessCheckPassed).toBe(true);
  });

  it('should schedule maintenance windows cleanly', () => {
    const initialCount = platformService.maintenanceWindows().length;
    platformService.createMaintenanceWindow({
      title: 'Database Cluster OS Kernel Security Patch',
      scheduledStartTime: '2026-04-01 02:00 UTC',
      scheduledEndTime: '2026-04-01 04:00 UTC',
      allowJobDrain: true,
      scope: 'CLUSTER_WIDE'
    });

    const windows = platformService.maintenanceWindows();
    expect(windows.length).toBe(initialCount + 1);

    const created = windows[0];
    expect(created.id).toContain('maint-');
    expect(created.status).toBe('SCHEDULED');
    expect(created.title).toBe('Database Cluster OS Kernel Security Patch');
  });

  it('should enforce commercial license limits and entitlements', () => {
    const license = platformService.licensing();
    expect(license.edition).toBe('ENTERPRISE_CORE');
    expect(license.licensedNodes).toBeGreaterThanOrEqual(32);
    expect(license.status).toBe('ACTIVE');
    expect(license.features.length).toBeGreaterThanOrEqual(4);
    expect(license.features).toContain('Data Masking & Format-Preserving Encryption');
  });

  it('should inspect backup records and request diagnostics bundles', () => {
    const backups = platformService.backups();
    expect(backups.length).toBeGreaterThanOrEqual(1);

    const b = backups[0];
    expect(b.sha256Checksum.length).toBe(64);
    expect(b.status).toBe('AVAILABLE');

    const initialDiags = platformService.diagnostics().length;
    platformService.requestDiagnostics('TICKET-2026-OPS-441');

    const diags = platformService.diagnostics();
    expect(diags.length).toBe(initialDiags + 1);

    const newDiag = diags[0];
    expect(newDiag.ticketRef).toBe('TICKET-2026-OPS-441');
    expect(newDiag.status).toBe('READY');
  });
});

describe('5.11 Integrations & Notifications Service & Workflows', () => {
  let integrationsService: IntegrationsService;

  beforeEach(() => {
    integrationsService = new IntegrationsService();
  });

  it('should initialize with notification channels and enforce vault references for all secrets', () => {
    const channels = integrationsService.channels();
    expect(channels.length).toBeGreaterThanOrEqual(3);

    const types = channels.map(c => c.channelType);
    expect(types).toContain('SLACK');
    expect(types).toContain('PAGERDUTY');
    expect(types).toContain('EMAIL_SMTP');

    // Check zero plaintext secrets in channel credentials
    for (const ch of channels) {
      expect(ch.credentialRef).toMatch(/^vault:\/\//);
    }
  });

  it('should create a notification channel with strict vault credential reference', () => {
    const initialCount = integrationsService.channels().length;
    integrationsService.createChannel({
      name: 'Tier-1 Security Response Slack Channel',
      channelType: 'SLACK',
      targetEndpointOrAddress: 'https://hooks.slack.com/services/T00/B00/secops',
      credentialRef: 'vault://tokens/secops-slack-webhook',
      isEnabled: true,
      description: 'Dedicated bridge for Tier-1 SecOps critical alerts'
    });

    const channels = integrationsService.channels();
    expect(channels.length).toBe(initialCount + 1);

    const created = channels[0];
    expect(created.id).toContain('chan-');
    expect(created.credentialRef).toBe('vault://tokens/secops-slack-webhook');
  });

  it('should configure dispatch policies and event routing rules', () => {
    const initialPolicies = integrationsService.policies().length;
    integrationsService.createPolicy({
      name: 'Critical Security Alert Policy',
      severityLevels: ['CRITICAL'],
      channelIds: ['chan-email-01', 'chan-pagerduty-01'],
      escalationDelayMinutes: 5
    });

    const policies = integrationsService.policies();
    expect(policies.length).toBe(initialPolicies + 1);

    const createdPolicy = policies[0];
    expect(createdPolicy.id).toContain('npol-');
    expect(createdPolicy.status).toBe('ACTIVE');

    const initialRules = integrationsService.eventRoutingRules().length;
    integrationsService.createEventRule({
      eventFamily: 'SECURITY',
      filterPattern: 'security.auth.* | security.kms.*',
      targetChannelIds: ['chan-email-01'],
      description: 'Captures and routes all security exceptions'
    });

    const rules = integrationsService.eventRoutingRules();
    expect(rules.length).toBe(initialRules + 1);

    const createdRule = rules[0];
    expect(createdRule.id).toContain('erule-');
    expect(createdRule.status).toBe('ENABLED');
  });

  it('should manage SIEM integrations with vault credentials', () => {
    const siems = integrationsService.siemIntegrations();
    expect(siems.length).toBeGreaterThanOrEqual(2);

    const splunk = siems.find(s => s.siemType === 'SPLUNK');
    expect(splunk).toBeDefined();
    expect(splunk?.credentialRef).toMatch(/^vault:\/\//);

    const initialCount = siems.length;
    integrationsService.createSiemIntegration({
      name: 'Corporate Microsoft Sentinel Forwarder',
      siemType: 'ELASTICSEARCH',
      endpointUrl: 'https://sentinel.workspace.azure.com/api/events',
      protocol: 'HTTPS_POST',
      credentialRef: 'vault://azure/sentinel-workspace-key'
    });

    const updated = integrationsService.siemIntegrations();
    expect(updated.length).toBe(initialCount + 1);

    const created = updated[0];
    expect(created.id).toContain('siem-');
    expect(created.status).toBe('CONFIGURED');
  });

  it('should manage ITSM integrations with vault credentials', () => {
    const itsms = integrationsService.itsmIntegrations();
    expect(itsms.length).toBeGreaterThanOrEqual(2);

    const snow = itsms.find(i => i.provider === 'SERVICENOW');
    expect(snow).toBeDefined();
    expect(snow?.credentialRef).toMatch(/^vault:\/\//);

    const initialCount = itsms.length;
    integrationsService.createItsmIntegration({
      name: 'Corporate Jira Service Management Cloud',
      provider: 'JIRA',
      instanceUrl: 'https://jira.enterprise.internal/rest/api/3',
      defaultProjectOrQueue: 'INFRA-OPS',
      credentialRef: 'vault://jira/service-token',
      issueTypeMapping: 'Incident'
    });

    const updated = integrationsService.itsmIntegrations();
    expect(updated.length).toBe(initialCount + 1);

    const created = updated[0];
    expect(created.id).toContain('itsm-');
    expect(created.status).toBe('CONFIGURED');
  });

  it('should query credential references catalog with zero plaintext secrets', () => {
    const refs = integrationsService.credentialRefs();
    expect(refs.length).toBeGreaterThanOrEqual(3);

    for (const ref of refs) {
      expect(ref.vaultUri).toMatch(/^vault:\/\//);
      expect(ref.status).toBe('VALID');
      expect(ref.lastRotatedAt).toBeDefined();
    }
  });
});
