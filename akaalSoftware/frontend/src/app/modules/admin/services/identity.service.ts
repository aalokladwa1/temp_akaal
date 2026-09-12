/**
 * AKAAL Administration — 5.4 Identity & Security Service
 */

import { Injectable, signal } from '@angular/core';
import {
  AuthPolicy,
  MfaConfig,
  SsoProvider,
  LdapConfig,
  ScimEndpoint,
  IdentityFederationTrust,
  WorkloadIdentityEntry,
  SpiffeServerConfig,
  X509CertificateRecord,
  VaultSecretEngineConfig,
  KmsMasterKey,
  SecretRotationRule
} from '../models/identity.models';

@Injectable({
  providedIn: 'root'
})
export class IdentityService {
  // Auth Policies
  public readonly authPolicies = signal<AuthPolicy[]>([
    {
      id: 'pol-auth-001',
      name: 'Global Baseline Security Policy',
      tier: 'ENTERPRISE_HIGH',
      description: 'Default authentication standard applied to all corporate users and contractors.',
      minPasswordLength: 14,
      requireSpecialChars: true,
      requireNumbers: true,
      requireUppercase: true,
      passwordMaxAgeDays: 90,
      lockoutThresholdAttempts: 5,
      lockoutDurationMinutes: 30,
      sessionIdleTimeoutMinutes: 30,
      sessionAbsoluteTimeoutHours: 12,
      mfaEnforcement: 'ENFORCED_ALL',
      ipAllowlist: ['10.0.0.0/8', '192.168.1.0/24', '172.16.0.0/12'],
      adaptiveRiskBasedAuth: true,
      status: 'ACTIVE',
      assignedPrincipalsCount: 1420,
      updatedAt: '2026-02-15 08:30 UTC'
    },
    {
      id: 'pol-auth-002',
      name: 'Privileged Operator Strict Policy',
      tier: 'CRITICAL_GOV',
      description: 'Strict biometric & hardware token policy required for platform admins and SEC/SOC.',
      minPasswordLength: 20,
      requireSpecialChars: true,
      requireNumbers: true,
      requireUppercase: true,
      passwordMaxAgeDays: 45,
      lockoutThresholdAttempts: 3,
      lockoutDurationMinutes: 120,
      sessionIdleTimeoutMinutes: 15,
      sessionAbsoluteTimeoutHours: 8,
      mfaEnforcement: 'ENFORCED_ALL',
      ipAllowlist: ['10.240.0.0/16', '10.250.10.0/24'],
      adaptiveRiskBasedAuth: true,
      status: 'ACTIVE',
      assignedPrincipalsCount: 28,
      updatedAt: '2026-03-01 11:45 UTC'
    }
  ]);

  // MFA Configuration
  public readonly mfaConfig = signal<MfaConfig>({
    id: 'mfa-cfg-global',
    enforceFido2WebAuthn: true,
    enforceTotp: true,
    allowHardwareSecurityKeys: true,
    allowSmsOtpWithWarning: false,
    allowEmailOtpWithWarning: false,
    rememberDeviceDays: 14,
    gracePeriodDays: 3,
    backupCodesCount: 10,
    totalEnrolledUsers: 1395,
    totalHardwareKeysRegistered: 342,
    fido2AdoptionRatePercent: 92.4
  });

  // SSO Providers
  public readonly ssoProviders = signal<SsoProvider[]>([
    {
      id: 'sso-001',
      name: 'Corporate Microsoft Entra ID',
      protocol: 'OIDC',
      providerType: 'AZURE_AD',
      entityIdOrIssuer: 'https://login.microsoftonline.com/akaal-corp-tenant-uuid/v2.0',
      singleSignOnUrl: 'https://login.microsoftonline.com/akaal-corp-tenant-uuid/oauth2/v2.0/authorize',
      clientId: 'akaal-enterprise-client-id-998',
      signingCertificateThumbprint: '9B:4F:2E:7A:1C:88:9D:44:FA:01',
      jitProvisioningEnabled: true,
      defaultRoleAssign: 'Data Engineer Standard',
      attributeMapping: {
        email: 'userPrincipalName',
        fullName: 'displayName',
        groups: 'memberOf',
        department: 'department'
      },
      status: 'ACTIVE',
      lastAuthEvent: '2 minutes ago',
      activeUsersCount: 1150,
      createdAt: '2025-01-10'
    },
    {
      id: 'sso-002',
      name: 'Okta Workforce Federation',
      protocol: 'SAML_2_0',
      providerType: 'OKTA',
      entityIdOrIssuer: 'http://www.okta.com/exk871239akaalcorp',
      singleSignOnUrl: 'https://akaal-corp.okta.com/app/akaal_prod/sso/saml',
      clientId: 'akaal-okta-saml-sp',
      signingCertificateThumbprint: 'E3:11:78:90:A4:CC:81:45:90:BB',
      jitProvisioningEnabled: false,
      defaultRoleAssign: 'Viewer',
      attributeMapping: {
        email: 'email',
        fullName: 'name',
        groups: 'groups',
        department: 'department'
      },
      status: 'ACTIVE',
      lastAuthEvent: '14 minutes ago',
      activeUsersCount: 270,
      createdAt: '2025-03-12'
    }
  ]);

  // LDAP / Active Directory
  public readonly ldapConfigs = signal<LdapConfig[]>([
    {
      id: 'ldap-001',
      name: 'Primary Active Directory Domain Controller',
      directoryType: 'ACTIVE_DIRECTORY',
      serverUrl: 'ldaps://ad-dc01.corp.akaaltech.internal',
      port: 636,
      useTls: true,
      bindDn: 'CN=svc-akaal-sync,OU=ServiceAccounts,DC=corp,DC=akaaltech,DC=internal',
      baseDn: 'DC=corp,DC=akaaltech,DC=internal',
      userSearchFilter: '(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))',
      groupSearchFilter: '(objectClass=group)',
      syncIntervalMinutes: 60,
      groupRoleMappingsCount: 18,
      status: 'CONNECTED',
      lastSyncTimestamp: '2026-03-11 14:00 UTC',
      syncedUsersCount: 1420,
      syncedGroupsCount: 34
    }
  ]);

  // SCIM Endpoints
  public readonly scimEndpoints = signal<ScimEndpoint[]>([
    {
      id: 'scim-001',
      name: 'Inbound Azure Entra SCIM Provisioning',
      providerType: 'AZURE_ENTRA_SCIM',
      endpointUrl: 'https://admin.akaal.enterprise/api/v1/scim/v2/tenants/akaal-global',
      tokenSecretHint: 'scim_live_tok_****_882b',
      tokenExpiryDate: '2027-01-01',
      inboundProvisioning: true,
      outboundProvisioning: false,
      syncUsers: true,
      syncGroups: true,
      deprovisionAction: 'SUSPEND',
      status: 'ACTIVE',
      lastWebhookTimestamp: '4 minutes ago',
      provisionedUsersCount: 1280
    }
  ]);

  // Identity Federation
  public readonly federationTrusts = signal<IdentityFederationTrust[]>([
    {
      id: 'fed-001',
      trustDomain: 'partner.fintech-consortium.global',
      partnerTenantName: 'Consortium Global Settlement Portal',
      partnerTenantId: 'tenant-consortium-994',
      trustProtocol: 'SAML_2_0_FEDERATION',
      allowedClaimScopes: ['openid', 'email', 'roles:auditor', 'settlement:read'],
      status: 'ESTABLISHED',
      expiresAt: '2027-06-30',
      crossTenantPrincipalsCount: 14
    }
  ]);

  // Workload Identity
  public readonly workloadIdentities = signal<WorkloadIdentityEntry[]>([
    {
      id: 'workload-001',
      name: 'Data Pipeline Worker K8s Projection',
      type: 'KUBERNETES_SERVICE_ACCOUNT',
      identityIdentifier: 'spiffe://akaal.enterprise/ns/dataplane-prod/sa/pipeline-worker',
      trustDomain: 'akaal.enterprise',
      associatedNamespaceOrCluster: 'k8s-prod-eu-west-01/dataplane-prod',
      tokenTtlMinutes: 60,
      mfaOrAttestationMethod: 'k8s_sat (Service Account Token Projected Attestation)',
      status: 'ACTIVE',
      lastAttestedAt: '5 minutes ago',
      activeWorkloadsCount: 64
    },
    {
      id: 'workload-002',
      name: 'AWS S3 Lakehouse IAM Cross-Role',
      type: 'AWS_IAM_ROLE',
      identityIdentifier: 'arn:aws:iam::123456789012:role/akaal-lakehouse-ingest-role',
      trustDomain: 'aws-us-east-1',
      associatedNamespaceOrCluster: 'lakehouse-storage-boundary',
      tokenTtlMinutes: 120,
      mfaOrAttestationMethod: 'OIDC Federation via AWS STS AssumeRoleWithWebIdentity',
      status: 'ACTIVE',
      lastAttestedAt: '12 minutes ago',
      activeWorkloadsCount: 12
    }
  ]);

  // SPIFFE / SPIRE
  public readonly spiffeConfig = signal<SpiffeServerConfig>({
    id: 'spire-srv-01',
    trustDomain: 'akaal.enterprise',
    spireServerEndpoint: 'spire-server.spire-system.svc.cluster.local:8081',
    caKeyAlgorithm: 'ECDSA_P384',
    svidDefaultTtlHours: 1,
    svidMaxTtlHours: 6,
    federatedTrustDomains: ['partner.fintech-consortium.global', 'akaal.cloud.apac'],
    attestationPlugins: ['k8s_sat', 'k8s_psat', 'join_token', 'unix_socket'],
    status: 'HEALTHY',
    activeSvidsCount: 128,
    agentsConnectedCount: 18
  });

  // X.509 Certificates / PKI
  public readonly certificates = signal<X509CertificateRecord[]>([
    {
      id: 'cert-001',
      commonName: 'AKAAL Enterprise Root CA - G2',
      type: 'ROOT_CA',
      issuerName: 'AKAAL Root Certificate Authority',
      serialNumber: '4F:29:A1:00:88:BB:92:41',
      validFrom: '2024-01-01',
      validTo: '2034-01-01',
      daysRemaining: 2850,
      algorithm: 'RSA_4096',
      autoRenewEnabled: false,
      boundServicesCount: 42,
      status: 'VALID'
    },
    {
      id: 'cert-002',
      commonName: '*.dataplane.akaal.enterprise',
      type: 'SERVER_TLS',
      issuerName: 'AKAAL Intermediate Issuing CA - 01',
      serialNumber: '7A:91:EE:12:44:CD:19:93',
      validFrom: '2025-06-01',
      validTo: '2026-06-01',
      daysRemaining: 81,
      algorithm: 'ECDSA_P384',
      autoRenewEnabled: true,
      boundServicesCount: 18,
      status: 'VALID'
    },
    {
      id: 'cert-003',
      commonName: 'legacy-gateway.external.corp',
      type: 'CLIENT_MTLS',
      issuerName: 'DigiCert Global Intermediate',
      serialNumber: '11:22:33:44:55:66:77:88',
      validFrom: '2025-04-01',
      validTo: '2026-04-01',
      daysRemaining: 20,
      algorithm: 'RSA_4096',
      autoRenewEnabled: false,
      boundServicesCount: 3,
      status: 'EXPIRING_SOON'
    }
  ]);

  // Secrets & Vault Engines
  public readonly vaultEngines = signal<VaultSecretEngineConfig[]>([
    {
      id: 'vlt-001',
      engineName: 'KV Secret Storage v2',
      engineType: 'KV_V2',
      mountPath: 'secret/akaal-prod/',
      vaultClusterUrl: 'https://vault-cluster.internal.akaaltech.corp:8200',
      authMethod: 'KUBERNETES_AUTH',
      leaseTtlHours: 24,
      maxLeaseTtlHours: 168,
      managedSecretsCount: 480,
      status: 'CONNECTED',
      lastRotatedAt: '2026-03-08 04:00 UTC'
    },
    {
      id: 'vlt-002',
      engineName: 'PostgreSQL Dynamic Database Credential Generator',
      engineType: 'DATABASE_DYNAMIC',
      mountPath: 'database/creds/pg-analytics',
      vaultClusterUrl: 'https://vault-cluster.internal.akaaltech.corp:8200',
      authMethod: 'APP_ROLE',
      leaseTtlHours: 1,
      maxLeaseTtlHours: 8,
      managedSecretsCount: 120,
      status: 'CONNECTED',
      lastRotatedAt: '15 minutes ago'
    }
  ]);

  // KMS / CMK / BYOK
  public readonly kmsKeys = signal<KmsMasterKey[]>([
    {
      id: 'kms-001',
      keyAlias: 'akaal-data-lake-cmk-master',
      keyArnOrId: 'arn:aws:kms:eu-west-1:123456789012:key/cmk-4921-9988-bb71',
      algorithm: 'AES_256_GCM',
      keyOrigin: 'CUSTOMER_MANAGED_CMK',
      hsmModuleModel: 'Thales Luna PCIe HSM 7.0 (FIPS 140-2 Level 3)',
      rotationIntervalDays: 365,
      nextScheduledRotation: '2026-09-15',
      encryptedVolumesCount: 84,
      status: 'ENABLED'
    },
    {
      id: 'kms-002',
      keyAlias: 'byok-pci-tokenization-envelope-key',
      keyArnOrId: 'hsm-cluster-key-slot-48201',
      algorithm: 'RSA_4096',
      keyOrigin: 'BYOK_EXTERNAL_HSM',
      hsmModuleModel: 'Utimaco CryptoServer LAN v4',
      rotationIntervalDays: 180,
      nextScheduledRotation: '2026-05-01',
      encryptedVolumesCount: 16,
      status: 'ENABLED'
    }
  ]);

  // Rotation Rules
  public readonly rotationRules = signal<SecretRotationRule[]>([
    {
      id: 'rot-001',
      name: 'PostgreSQL Migration Stage DB Password Auto-Rotate',
      targetType: 'DATABASE_CREDENTIALS',
      targetResourceName: 'pg-migration-stage-cluster',
      rotationFrequencyDays: 30,
      lastRotationTimestamp: '2026-03-01 02:00 UTC',
      nextRotationTimestamp: '2026-03-31 02:00 UTC',
      automatedExecution: true,
      lastRotationStatus: 'SUCCESS',
      auditLogId: 'audit-rot-9821'
    },
    {
      id: 'rot-002',
      name: 'KMS Master Envelope Wrapping Key Rotation',
      targetType: 'KMS_WRAPPING_KEY',
      targetResourceName: 'akaal-data-lake-cmk-master',
      rotationFrequencyDays: 365,
      lastRotationTimestamp: '2025-09-15 00:00 UTC',
      nextRotationTimestamp: '2026-09-15 00:00 UTC',
      automatedExecution: true,
      lastRotationStatus: 'SUCCESS',
      auditLogId: 'audit-rot-4410'
    }
  ]);

  // Methods for Auth Policies
  public createAuthPolicy(data: Partial<AuthPolicy>): AuthPolicy {
    const newPolicy: AuthPolicy = {
      id: 'pol-auth-' + Date.now().toString(36),
      name: data.name || 'Custom Auth Policy',
      tier: data.tier || 'STANDARD',
      description: data.description || '',
      minPasswordLength: data.minPasswordLength || 12,
      requireSpecialChars: data.requireSpecialChars ?? true,
      requireNumbers: data.requireNumbers ?? true,
      requireUppercase: data.requireUppercase ?? true,
      passwordMaxAgeDays: data.passwordMaxAgeDays || 90,
      lockoutThresholdAttempts: data.lockoutThresholdAttempts || 5,
      lockoutDurationMinutes: data.lockoutDurationMinutes || 30,
      sessionIdleTimeoutMinutes: data.sessionIdleTimeoutMinutes || 30,
      sessionAbsoluteTimeoutHours: data.sessionAbsoluteTimeoutHours || 12,
      mfaEnforcement: data.mfaEnforcement || 'ENFORCED_ALL',
      ipAllowlist: data.ipAllowlist || [],
      adaptiveRiskBasedAuth: data.adaptiveRiskBasedAuth ?? true,
      status: 'ACTIVE',
      assignedPrincipalsCount: 0,
      updatedAt: 'Just now'
    };
    this.authPolicies.update(list => [newPolicy, ...list]);
    return newPolicy;
  }

  public updateMfaConfig(data: Partial<MfaConfig>): void {
    this.mfaConfig.update(cfg => ({ ...cfg, ...data }));
  }

  public createSsoProvider(data: Partial<SsoProvider>): SsoProvider {
    const newProvider: SsoProvider = {
      id: 'sso-' + Date.now().toString(36),
      name: data.name || 'New SSO Provider',
      protocol: data.protocol || 'OIDC',
      providerType: data.providerType || 'AZURE_AD',
      entityIdOrIssuer: data.entityIdOrIssuer || '',
      singleSignOnUrl: data.singleSignOnUrl || '',
      clientId: data.clientId || '',
      signingCertificateThumbprint: data.signingCertificateThumbprint || 'Generated on handshake',
      jitProvisioningEnabled: data.jitProvisioningEnabled ?? true,
      defaultRoleAssign: data.defaultRoleAssign || 'Standard User',
      attributeMapping: data.attributeMapping || {
        email: 'email',
        fullName: 'name',
        groups: 'groups',
        department: 'department'
      },
      status: 'TESTING',
      activeUsersCount: 0,
      createdAt: new Date().toISOString().split('T')[0]
    };
    this.ssoProviders.update(list => [newProvider, ...list]);
    return newProvider;
  }

  public triggerLdapSync(ldapId: string): void {
    this.ldapConfigs.update(list =>
      list.map(item =>
        item.id === ldapId
          ? {
              ...item,
              status: 'CONNECTED',
              lastSyncTimestamp: 'Just now'
            }
          : item
      )
    );
  }

  public triggerSecretRotation(ruleId: string): void {
    this.rotationRules.update(list =>
      list.map(r =>
        r.id === ruleId
          ? {
              ...r,
              lastRotationTimestamp: 'Just now',
              lastRotationStatus: 'SUCCESS'
            }
          : r
      )
    );
  }
}
